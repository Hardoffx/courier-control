from dataclasses import dataclass,field
from datetime import datetime
from io import BytesIO
from zipfile import BadZipFile,ZipFile
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook
from accounts.models import User
from .models import Delivery, DeliveryEvent
from .point_matching import canonical_delivery_values, resolve_point

ALIASES={'адрес':'address','address':'address','объект':'source_label','код':'source_label','точка':'source_label','организация':'organization','получатель':'recipient','телефон':'phone','комментарий':'comment','курьер':'courier','порядок':'route_order','№':'route_order','дата':'delivery_date','время':'time_window','временное окно':'time_window'}
COLORS={'FFFFFF00':'yellow','FFFFC000':'yellow','FF92D050':'green','FFC6E0B4':'green','FFFFC7CE':'red','FFF4CCCC':'red','FFD9EAF7':'blue','FFD9EAD3':'green','FFD9D9D9':'gray'}
MAX_UPLOAD_BYTES=5*1024*1024
MAX_XLSX_EXPANDED_BYTES=50*1024*1024
MAX_XLSX_FILES=1000

@dataclass
class ImportSummary:
    created:int=0; skipped:int=0; matched:int=0; new_points:int=0; would_create_points:int=0; warnings:list=field(default_factory=list); preview:list=field(default_factory=list); total_rows:int=0

def validate_upload(name,content):
    if not (name or '').lower().endswith('.xlsx'): raise ValueError('Разрешены только файлы .xlsx')
    if not content: raise ValueError('Файл пуст')
    if len(content)>MAX_UPLOAD_BYTES: raise ValueError('Файл слишком большой. Максимум 5 МБ')
    try:
        with ZipFile(BytesIO(content)) as archive:
            members=archive.infolist()
            if len(members)>MAX_XLSX_FILES: raise ValueError('XLSX содержит слишком много внутренних файлов')
            expanded=sum(item.file_size for item in members)
            if expanded>MAX_XLSX_EXPANDED_BYTES: raise ValueError('XLSX слишком велик после распаковки')
            if not any(item.filename=='[Content_Types].xml' for item in members): raise ValueError('Файл не является корректным XLSX')
    except BadZipFile as exc: raise ValueError('Файл не является корректным XLSX') from exc

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

def _fill(cell):
    fill=cell.fill
    if not fill or fill.fill_type!='solid': return ''
    color=fill.fgColor
    if color.type=='rgb' and color.rgb: return COLORS.get(color.rgb.upper(),'')
    return ''

def _rows(content,create_points=False):
    wb=_open(content); ws=wb.active
    if ws.max_row<1: raise ValueError('Файл пуст')
    header_row,columns=_find_header(ws); rows=[]
    for excel_row,row in enumerate(ws.iter_rows(min_row=header_row+1),start=header_row+1):
        values={field:row[index].value for field,index in columns.items() if index<len(row)}
        address=str(values.get('address') or '').strip()
        if not address: continue
        source=str(values.get('source_label') or '').strip(); phone=str(values.get('phone') or '').strip(); organization=str(values.get('organization') or '').strip(); recipient=str(values.get('recipient') or '').strip(); comment=str(values.get('comment') or '').strip(); time_window=str(values.get('time_window') or '').strip()
        match=resolve_point(source,address,phone,create=create_points); point=match.point; created=match.created; canonical=canonical_delivery_values(point,source,address,phone)
        raw_order=values.get('route_order'); route_order=int(raw_order) if isinstance(raw_order,(int,float)) else excel_row-header_row
        courier_name=str(values.get('courier') or '').strip(); courier=None
        if courier_name: courier=User.objects.filter(role=User.Role.COURIER,username__iexact=courier_name).first() or User.objects.filter(role=User.Role.COURIER,first_name__iexact=courier_name).first()
        color=_fill(row[0]) if row else ''
        rows.append({'excel_row':excel_row,'delivery_date':_date(values.get('delivery_date')),'address':canonical['address'],'source_label':canonical['source_label'],'organization':organization,'recipient':recipient,'phone':canonical['phone'],'comment':comment,'courier':courier,'courier_name':courier_name,'route_order':route_order,'time_window':time_window,'row_color':color,'point':point,'point_created':created})
    return rows

def _duplicate_key(row):
    return (row['delivery_date'],row['address'],row['source_label'],row['route_order'])

def _point_key(row):
    return ((row['source_label'] or '').strip().casefold(),(row['address'] or '').strip().casefold())

def preview_workbook(content):
    validate_upload('preview.xlsx',content); rows=_rows(content,create_points=False); summary=ImportSummary(total_rows=len(rows)); seen_delivery_keys=set(); new_point_keys=set()
    for row in rows:
        if row['point']: summary.matched+=1
        else: new_point_keys.add(_point_key(row))
        key=_duplicate_key(row); duplicate=key in seen_delivery_keys or Delivery.objects.filter(delivery_date=row['delivery_date'],address=row['address'],source_label=row['source_label'],route_order=row['route_order']).exists(); seen_delivery_keys.add(key)
        if duplicate: summary.skipped+=1
        if len(summary.preview)<100:
            summary.preview.append({'row':row['excel_row'],'label':row['source_label'],'address':row['address'],'date':row['delivery_date'],'time_window':row['time_window'],'duplicate':duplicate,'new_point':row['point'] is None,'match':str(row['point']) if row['point'] else '','courier':row['courier']})
        if row['courier_name'] and not row['courier']: summary.warnings.append(f"Строка {row['excel_row']}: курьер «{row['courier_name']}» не найден")
    summary.would_create_points=len(new_point_keys)
    return summary

def import_workbook(content,actor=None):
    validate_upload('import.xlsx',content); rows=_rows(content,create_points=True); summary=ImportSummary(total_rows=len(rows))
    with transaction.atomic():
        for row in rows:
            if row['point']: summary.matched+=1
            if row['point_created']: summary.new_points+=1
            duplicate=Delivery.objects.filter(delivery_date=row['delivery_date'],address=row['address'],source_label=row['source_label'],route_order=row['route_order']).exists()
            if duplicate: summary.skipped+=1; continue
            delivery=Delivery.objects.create(delivery_date=row['delivery_date'],address=row['address'],source_label=row['source_label'],organization=row['organization'],recipient=row['recipient'],phone=row['phone'],comment=row['comment'],courier=row['courier'],route_order=row['route_order'],time_window=row['time_window'],row_color=row['row_color'],point=row['point']); summary.created+=1
            DeliveryEvent.objects.create(delivery=delivery,actor=actor,action='created',note='Импорт из Excel')
            if row['courier_name'] and not row['courier']: summary.warnings.append(f"Строка {row['excel_row']}: курьер «{row['courier_name']}» не найден")
    return summary
