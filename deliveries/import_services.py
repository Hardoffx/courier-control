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


def import_workbook(content,actor):
    wb=load_workbook(BytesIO(content),data_only=True); ws=wb.active; rows=list(ws.iter_rows(values_only=True))
    if not rows: raise ValueError('Файл пуст')
    headers=[str(v or '').strip().lower() for v in rows[0]]; columns={ALIASES[h]:i for i,h in enumerate(headers) if h in ALIASES}
    if 'address' not in columns: raise ValueError('Не найдена колонка «Адрес»')
    summary=ImportSummary()
    def val(row,key): return str(row[columns[key]] or '').strip() if key in columns else ''
    with transaction.atomic():
        for number,row in enumerate(rows[1:],start=1):
            address=val(row,'address')
            if not address: summary.skipped+=1; continue
            label=val(row,'source_label'); phone=val(row,'phone'); match=resolve_point(label,address,phone,create=True); point=match.point
            if match.created: summary.new_points+=1
            else: summary.matched+=1
            canonical=canonical_delivery_values(point,label,address,phone)
            courier=User.objects.filter(role=User.Role.COURIER,username__iexact=val(row,'courier'),is_active=True).first() if val(row,'courier') else None
            delivery_date=_date(row[columns['delivery_date']] if 'delivery_date' in columns else None)
            order=number
            if 'route_order' in columns and row[columns['route_order']] is not None:
                try: order=int(row[columns['route_order']])
                except (TypeError,ValueError): summary.warnings.append(f'Строка {number+1}: неверный порядок')
            row_color=''
            try: row_color=COLORS.get(getattr(ws.cell(row=number+1,column=columns['address']+1).fill.fgColor,'rgb',None),'')
            except Exception: pass
            duplicate=Delivery.objects.filter(delivery_date=delivery_date,point=point).exclude(status=Delivery.Status.DONE).first() if point else None
            if duplicate:
                summary.skipped+=1; summary.warnings.append(f'Строка {number+1}: {canonical["source_label"] or canonical["address"]} уже есть на {delivery_date:%d.%m}')
                continue
            d=Delivery.objects.create(delivery_date=delivery_date,point=point,source_label=canonical['source_label'],address=canonical['address'],organization=val(row,'organization'),recipient=val(row,'recipient'),phone=canonical['phone'],comment=val(row,'comment'),time_window=val(row,'time_window'),row_color=row_color,courier=courier,route_order=order,status=Delivery.Status.IN_PROGRESS if courier else Delivery.Status.NEW)
            DeliveryEvent.objects.create(delivery=d,actor=actor,action='imported',note=f'Справочник: {match.method}')
            summary.created+=1
    return summary
