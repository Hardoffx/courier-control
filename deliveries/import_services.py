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

@dataclass
class ImportSummary:
    created:int=0; skipped:int=0; matched:int=0; new_points:int=0; warnings:list=field(default_factory=list)

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

def import_workbook(content,actor):
    wb=load_workbook(BytesIO(content),data_only=True); ws=wb.active
    if ws.max_row<1: raise ValueError('Файл пуст')
    header_row,columns=_find_header(ws); summary=ImportSummary()
    def val(row,key): return str(row[columns[key]] or '').strip() if key in columns and columns[key]<len(row) else ''
    with transaction.atomic():
        for excel_row,row in enumerate(ws.iter_rows(min_row=header_row+1,values_only=True),start=header_row+1):
            address=val(row,'address')
            if not address: continue
            label=val(row,'source_label'); phone=val(row,'phone'); match=resolve_point(label,address,phone,create=True); point=match.point
            if match.created: summary.new_points+=1
            else: summary.matched+=1
            canonical=canonical_delivery_values(point,label,address,phone); time_window=val(row,'time_window'); courier=User.objects.filter(role=User.Role.COURIER,username__iexact=val(row,'courier'),is_active=True).first() if val(row,'courier') else None
            delivery_date=_date(row[columns['delivery_date']] if 'delivery_date' in columns else None); order=excel_row-header_row
            if 'route_order' in columns and row[columns['route_order']] is not None:
                try: order=int(row[columns['route_order']])
                except (TypeError,ValueError): summary.warnings.append(f'Строка {excel_row}: неверный порядок')
            row_color=''
            try: row_color=COLORS.get(getattr(ws.cell(row=excel_row,column=columns['address']+1).fill.fgColor,'rgb',None),'')
            except Exception: pass
            duplicate=Delivery.objects.filter(delivery_date=delivery_date,point=point,source_label=canonical['source_label'],time_window=time_window,route_order=order).first() if point else None
            if duplicate:
                summary.skipped+=1; summary.warnings.append(f'Строка {excel_row}: уже импортирована — {canonical["source_label"] or canonical["address"]}, позиция {order}')
                continue
            d=Delivery.objects.create(delivery_date=delivery_date,point=point,source_label=canonical['source_label'],address=canonical['address'],organization=val(row,'organization'),recipient=val(row,'recipient'),phone=canonical['phone'],comment=val(row,'comment'),time_window=time_window,row_color=row_color,courier=courier,route_order=order,status=Delivery.Status.IN_PROGRESS if courier else Delivery.Status.NEW)
            DeliveryEvent.objects.create(delivery=d,actor=actor,action='imported',note=f'Справочник: {match.method}; Excel row: {excel_row}'); summary.created+=1
    return summary
