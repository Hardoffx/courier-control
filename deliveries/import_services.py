from dataclasses import dataclass,field
from datetime import datetime
from io import BytesIO
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook
from accounts.models import User
from .models import Delivery, DeliveryEvent
from .point_matching import canonical_delivery_values, resolve_point

ALIASES={'адрес':'address','address':'address','объект':'source_label','код':'source_label','точка':'source_label','организация':'organization','получатель':'recipient','телефон':'phone','комментарий':'comment','курьер':'courier','порядок':'route_order','№':'route_order','дата':'delivery_date','время':'time_window','временное окно':'time_window'}
COLORS={'FFFFFF00':'yellow','FFFFC000':'yellow','FF92D050':'green','FFC6E0B4':'green','FFFFC7CE':'red','FFF4CCCC':'red','FFD9EAF7':'blue','FFD9EAD3':'green','FFD9D9D9':'gray'}
MAX_UPLOAD_BYTES=5*1024*1024

@dataclass
class ImportSummary:
    created:int=0; skipped:int=0; matched:int=0; new_points:int=0; warnings:list=field(default_factory=list); preview:list=field(default_factory=list); total_rows:int=0

def validate_upload(name,content):
    if not (name or '').lower().endswith('.xlsx'): raise ValueError('Разрешены только файлы .xlsx')
    if not content: raise ValueError('Файл пуст')
    if len(content)>MAX_UPLOAD_BYTES: raise ValueError('Файл слишком большой. Максимум 5 МБ')

def _date(raw):
    if not raw: return timezone.localdate()
    if isinstance(raw,datetime): return raw.date()
    if hasattr(raw,'year'): return raw
    return timezone.localdate()

def _find_header(ws,scan_rows=20):
    best=None
    for row_number,row in enumerate(ws.iter_rows(min_row=1,max_row=min(ws.max_row,scan_rows),values_only=True),start=1):
        headers=[str(v or '').strip().lower() for v in row]; columns={ALIASES[h]:i for i,h in enumerate(headers) if h in ALIASES}; score=len(columns)+(5 if 'address' in columns else 0)
        if best is None or score>best[0]: best=(score,row_number,columns)
    if not best or 'address' not in best[2]: raise ValueError('Не найдена строка заголовков с колонкой «Адрес» в первых 20 строках')
    return best[1],best[2]

def _open(content):
    try: return load_workbook(BytesIO(content),data_only=True,read_only=False)
    except Exception as exc: raise ValueError('Не удалось открыть XLSX. Проверьте, что файл не повреждён') from exc

def _rows(content,create_points=False):
    wb=_open(content); ws=wb.active
    if ws.max_row<1: raise ValueError('Файл пуст')
    header_row,columns=_find_header(ws)
    def val(row,key): return str(row[columns[key]] or '').strip() if key in columns and columns[key]<len(row) else ''
    for excel_row,row in enumerate(ws.iter_rows(min_row=header_row+1,values_only=True),start=header_row+1):
        address=val(row,'address')
        if not address: continue
        label=val(row,'source_label'); phone=val(row,'phone'); match=resolve_point(label,address,phone,create=create_points); point=match.point; canonical=canonical_delivery_values(point,label,address,phone); time_window=val(row,'time_window'); courier=User.objects.filter(role=User.Role.COURIER,username__iexact=val(row,'courier'),is_active=True).first() if val(row,'courier') else None; delivery_date=_date(row[columns['delivery_date']] if 'delivery_date' in columns else None); order=excel_row-header_row; warning=''
        if 'route_order' in columns and row[columns['route_order']] is not None:
            try: order=int(row[columns['route_order']])
            except (TypeError,ValueError): warning=f'Строка {excel_row}: неверный порядок'
        row_color=''
        try: row_color=COLORS.get(getattr(ws.cell(row=excel_row,column=columns['address']+1).fill.fgColor,'rgb',None),'')
        except Exception: pass
        duplicate=Delivery.objects.filter(delivery_date=delivery_date,point=point,source_label=canonical['source_label'],time_window=time_window,route_order=order).exists() if point else False
        yield {'excel_row':excel_row,'label':label,'address':address,'phone':phone,'point':point,'match':match,'canonical':canonical,'time_window':time_window,'courier':courier,'delivery_date':delivery_date,'order':order,'row_color':row_color,'organization':val(row,'organization'),'recipient':val(row,'recipient'),'comment':val(row,'comment'),'duplicate':duplicate,'warning':warning}

def preview_workbook(content,limit=100):
    summary=ImportSummary()
    for item in _rows(content,create_points=False):
        summary.total_rows+=1
        if item['duplicate']: summary.skipped+=1
        elif item['point']: summary.matched+=1
        else: summary.new_points+=1
        if item['warning']: summary.warnings.append(item['warning'])
        if len(summary.preview)<limit: summary.preview.append({'row':item['excel_row'],'label':item['canonical']['source_label'],'address':item['canonical']['address'],'time_window':item['time_window'],'date':item['delivery_date'],'courier':item['courier'],'match':item['match'].method,'duplicate':item['duplicate'],'new_point':not bool(item['point'])})
    if summary.total_rows>limit: summary.warnings.append(f'Предпросмотр показывает первые {limit} из {summary.total_rows} строк')
    return summary

def import_workbook(content,actor):
    summary=ImportSummary()
    with transaction.atomic():
        for item in _rows(content,create_points=True):
            summary.total_rows+=1; point=item['point']; match=item['match']; canonical=item['canonical']
            if match.created: summary.new_points+=1
            else: summary.matched+=1
            if item['warning']: summary.warnings.append(item['warning'])
            duplicate=Delivery.objects.filter(delivery_date=item['delivery_date'],point=point,source_label=canonical['source_label'],time_window=item['time_window'],route_order=item['order']).first() if point else None
            if duplicate: summary.skipped+=1; summary.warnings.append(f'Строка {item["excel_row"]}: уже импортирована — {canonical["source_label"] or canonical["address"]}, позиция {item["order"]}'); continue
            d=Delivery.objects.create(delivery_date=item['delivery_date'],point=point,source_label=canonical['source_label'],address=canonical['address'],organization=item['organization'],recipient=item['recipient'],phone=canonical['phone'],comment=item['comment'],time_window=item['time_window'],row_color=item['row_color'],courier=item['courier'],route_order=item['order'],status=Delivery.Status.IN_PROGRESS if item['courier'] else Delivery.Status.NEW); DeliveryEvent.objects.create(delivery=d,actor=actor,action='imported',note=f'Справочник: {match.method}; Excel row: {item["excel_row"]}'); summary.created+=1
    return summary
