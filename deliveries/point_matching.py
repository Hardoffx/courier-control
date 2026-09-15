import re
from dataclasses import dataclass
from .models import Delivery, DeliveryPoint


def normalize(value):
    value=(value or '').strip().lower().replace('ё','е')
    value=re.sub(r'[.,;:]+',' ',value)
    return ' '.join(value.split())


def normalize_code(value):
    return re.sub(r'\s+','',normalize(value))

@dataclass
class PointMatch:
    point: DeliveryPoint|None
    method: str
    created: bool=False


def match_point(label='',address=''):
    label=(label or '').strip(); address=(address or '').strip()
    active=list(DeliveryPoint.objects.filter(is_active=True))
    kind=Delivery.infer_point_kind(label)
    if kind==DeliveryPoint.Kind.CMD and label:
        code=normalize_code(label)
        matches=[p for p in active if p.code and normalize_code(p.code)==code]
        if len(matches)==1: return PointMatch(matches[0],'code')
    naddr=normalize(address)
    if naddr:
        matches=[p for p in active if normalize(p.address)==naddr]
        if len(matches)==1: return PointMatch(matches[0],'address')
        nlabel=normalize(label)
        if len(matches)>1 and nlabel:
            named=[p for p in matches if normalize(p.name)==nlabel or normalize(p.code)==normalize_code(label)]
            if len(named)==1: return PointMatch(named[0],'address+name')
    nlabel=normalize(label)
    if nlabel:
        matches=[p for p in active if normalize(p.name)==nlabel]
        if len(matches)==1: return PointMatch(matches[0],'name')
    return PointMatch(None,'unmatched')


def resolve_point(label='',address='',phone='',create=True):
    match=match_point(label,address)
    if match.point or not create: return match
    label=(label or '').strip(); address=(address or '').strip()
    if not address: return match
    kind=Delivery.infer_point_kind(label)
    point=DeliveryPoint.objects.create(name=label or address,code=label if kind==DeliveryPoint.Kind.CMD else '',address=address,kind=kind,phone=(phone or '').strip()[:64])
    return PointMatch(point,'created',True)


def canonical_delivery_values(point,label='',address='',phone=''):
    if not point: return {'source_label':label,'address':address,'phone':phone}
    return {
        'source_label': point.code or label or point.name,
        'address': point.address or address,
        'phone': point.phone or phone,
    }
