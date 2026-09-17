from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class KnownLabPoint:
    address: str
    kind: str
    facility_code: str = ''


# Verified courier points carried over from courier-route-bot/app/catalog.py.
# The control panel uses this only for visual lab identity/LPU enrichment; it
# does not depend on any external map API.
KNOWN_LAB_POINTS: tuple[KnownLabPoint, ...] = (
    KnownLabPoint('г Красногорск, тер. Детский клинический центр к1', 'invitro'),
    KnownLabPoint('Москва г, ул Генерала Белобородова 19к1', 'invitro'),
    KnownLabPoint('Москва г, ул Дубравная 46', 'cmd', '458'),
    KnownLabPoint('Москва г, пер 3-й Митинский 7', 'invitro'),
    KnownLabPoint('Москва г, Митинский 3-й пер 4к1', 'cmd', '2939'),
    KnownLabPoint('Москва г, ул Митинская 10', 'invitro'),
    KnownLabPoint('Москва г, ул Митинская 48', 'invitro'),
    KnownLabPoint('Москва, ул Митинская 57', 'invitro'),
    KnownLabPoint('г Красногорск, п Отрадное, ул Кленовая 3', 'invitro'),
    KnownLabPoint('деревня Юрлово, 89, Московская область', 'cmd', '5827'),
    KnownLabPoint('Новое Аристово, ул Солнечная 5', 'external'),
    KnownLabPoint('Москва г, ул Митинская 44', 'cmd', '3433'),
    KnownLabPoint('Москва г, ул Митинская 27', 'invitro'),
    KnownLabPoint('Москва г, ул Митинская 17к4', 'cmd', '1346'),
    KnownLabPoint('Москва г, ул Дубравная 41к2', 'cmd', '1720'),
    KnownLabPoint('Москва г, ул Маршала Катукова 6', 'cmd', '251'),
    KnownLabPoint('Москва г, Строгинский б-р 10к3', 'cmd', '1513'),
    KnownLabPoint('Москва г, ул Маршала Катукова 24к5', 'cmd', '1370'),
    KnownLabPoint('Москва г, ш Волоколамское 71к2', 'invitro'),
    KnownLabPoint('Москва г, ул Габричевского 10к1', 'invitro'),
    KnownLabPoint('Москва г, ул Вишнёвая 13к1 стр. 1', 'invitro'),
    KnownLabPoint('Москва г, б-р Химкинский 9', 'invitro'),
    KnownLabPoint('Москва г, ул Планерная 5', 'invitro'),
    KnownLabPoint('Москва г, б-р Яна Райниса 10', 'invitro'),
    KnownLabPoint('Москва г, б-р Яна Райниса 31', 'cmd', '3885'),
    KnownLabPoint('Москва г, ул Нелидовская 20к1', 'cmd', '1645'),
    KnownLabPoint('Москва г, ул Планерная 3к1', 'cmd', '6935'),
)


def _canonical(text: str) -> str:
    value = (text or '').strip().lower().replace('ё', 'е')
    value = re.sub(r'^\d{6}\s*,\s*', '', value)
    value = value.replace('№', ' ')
    value = re.sub(r'\b(город|г\.)\s*', 'г ', value)
    value = re.sub(r'\bулица\s*|\bул\.\s*', 'ул ', value)
    value = re.sub(r'\bпереулок\s*|\bпер\.\s*', 'пер ', value)
    value = re.sub(r'\bшоссе\s*|\bш\.\s*', 'ш ', value)
    value = re.sub(r'\bдом\s*|\bд\.\s*', '', value)
    value = re.sub(r',?\s*корпус\s*(\d+[а-яa-z]?)', r'к\1', value)
    value = re.sub(r',?\s*к\.\s*(\d+[а-яa-z]?)', r'к\1', value)
    value = re.sub(r',?\s*стр\.\s*(\d+[а-яa-z]?)', r' стр \1', value)
    value = re.sub(r'[^0-9a-zа-я]+', ' ', value)
    return ' '.join(value.split())


def _house_signature(text: str) -> tuple[str, ...]:
    nums = re.findall(r'(?<!\w)\d+[а-яa-z]?(?:к\d+)?', _canonical(text))
    return tuple(nums[-2:])


def resolve_known_lab(address: str) -> KnownLabPoint | None:
    key = _canonical(address)
    if not key:
        return None
    if 'юрлово' in key:
        return next(point for point in KNOWN_LAB_POINTS if 'юрлово' in _canonical(point.address))
    sig = _house_signature(address)
    best = None
    best_score = 0.0
    for point in KNOWN_LAB_POINTS:
        candidate = _canonical(point.address)
        if key == candidate:
            return point
        candidate_sig = _house_signature(point.address)
        if sig and candidate_sig and sig != candidate_sig:
            continue
        score = SequenceMatcher(None, key, candidate).ratio()
        if score > best_score:
            best_score = score
            best = point
    return best if best_score >= 0.88 else None
