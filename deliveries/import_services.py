import re
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from accounts.models import User
from .models import Delivery, DeliveryEvent
from .point_matching import canonical_delivery_values, resolve_point


ALIASES = {
    'адрес': 'address',
    'адрес доставки': 'address',
    'место доставки': 'address',
    'address': 'address',
    'объект': 'source_label',
    'код': 'source_label',
    'точка': 'source_label',
    'название': 'source_label',
    'организация': 'organization',
    'получатель': 'recipient',
    'телефон': 'phone',
    'комментарий': 'comment',
    'курьер': 'courier',
    'порядок': 'route_order',
    '№': 'route_order',
    'дата': 'delivery_date',
    'время': 'time_window',
    'временное окно': 'time_window',
}
COLORS = {
    'FFFFFF00': 'yellow',
    'FFFFC000': 'yellow',
    'FF92D050': 'green',
    'FFC6E0B4': 'green',
    'FFFFC7CE': 'red',
    'FFF4CCCC': 'red',
    'FFD9EAF7': 'blue',
    'FFD9EAD3': 'green',
    'FFD9D9D9': 'gray',
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_XLSX_EXPANDED_BYTES = 50 * 1024 * 1024
MAX_XLSX_FILES = 1000

TIME_WINDOW_RE = re.compile(r'^\s*\d{1,2}:\d{2}\s*[-–—]\s*\d{1,2}:\d{2}\s*$')
CMD_LABEL_RE = re.compile(r'^\s*\d+(?:\s*/\s*\d+)*\s*$')
ADDRESS_TOKEN_RE = re.compile(
    r'(?iu)(?:'
    r'\b(?:г|город|ул|улица|пер|переулок|проспект|пр-т|б-р|бульвар|'
    r'ш|шоссе|наб|набережная|пл|площадь|проезд|тупик|аллея|'
    r'д|дом|корпус|корп|стр|строение|владение|тер|территория|п|поселок|посёлок|деревня)\b'
    r'|\b(?:москва|санкт-петербург)\b'
    r')'
)
HOUSE_RE = re.compile(
    r'(?iu)(?:\b(?:д|дом)\.?\s*(?:№\s*)?\d+[а-яa-z]?(?:\s*/\s*\d+)?'
    r'|\b\d+[а-яa-z]?(?:\s*/\s*\d+)?\s*(?:к|корп(?:ус)?\.?|стр(?:оение)?\.?)\s*\d+)'
)
INTERIOR_START_RE = re.compile(
    r'(?iu)(?:[,;]\s*|\s+)'
    r'(?:пом(?:ещение)?\.?|комн(?:ата)?\.?|каб(?:инет)?\.?|офис|этаж|подъезд|секция)\b'
)
HOUSE_WORD_RE = re.compile(r'(?iu)\b(?:д|дом)\.?\s*(?:№\s*)?(?=\d)')
CORPUS_RE = re.compile(r'(?iu)(?:,?\s*)\b(?:корпус|корп\.|к\.)\s*(\d+[а-яa-z]?)\b')
BUILDING_RE = re.compile(r'(?iu)(?:,?\s*)\b(?:строение|стр\.)\s*(\d+[а-яa-z]?)\b')


@dataclass
class ImportSummary:
    created: int = 0
    skipped: int = 0
    matched: int = 0
    new_points: int = 0
    would_create_points: int = 0
    warnings: list = field(default_factory=list)
    preview: list = field(default_factory=list)
    total_rows: int = 0


def validate_upload(name, content):
    if not (name or '').lower().endswith('.xlsx'):
        raise ValueError('Разрешены только файлы .xlsx')
    if not content:
        raise ValueError('Файл пуст')
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError('Файл слишком большой. Максимум 5 МБ')
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_XLSX_FILES:
                raise ValueError('XLSX содержит слишком много внутренних файлов')
            expanded = sum(item.file_size for item in members)
            if expanded > MAX_XLSX_EXPANDED_BYTES:
                raise ValueError('XLSX слишком велик после распаковки')
            if not any(item.filename == '[Content_Types].xml' for item in members):
                raise ValueError('Файл не является корректным XLSX')
    except BadZipFile as exc:
        raise ValueError('Файл не является корректным XLSX') from exc


def _date(raw):
    if not raw:
        return timezone.localdate()
    if isinstance(raw, datetime):
        return raw.date()
    if hasattr(raw, 'year'):
        return raw
    return timezone.localdate()


def _header_candidate(ws, scan_rows=20):
    best = None
    for row_number, row in enumerate(
        ws.iter_rows(min_row=1, max_row=min(ws.max_row, scan_rows), values_only=True),
        start=1,
    ):
        headers = [str(v or '').strip().lower() for v in row]
        columns = {ALIASES[h]: i for i, h in enumerate(headers) if h in ALIASES}
        score = len(columns) + (5 if 'address' in columns else 0)
        if best is None or score > best[0]:
            best = (score, row_number, columns)
    if best and 'address' in best[2]:
        return best[1], best[2]
    return None


def _cell_text(value):
    return str(value or '').strip()


def _address_score(value):
    """Estimate whether a cell contains a postal address, without assuming a city."""
    text = _cell_text(value)
    if len(text) < 7 or TIME_WINDOW_RE.fullmatch(text):
        return 0
    score = len(ADDRESS_TOKEN_RE.findall(text)) * 2
    if HOUSE_RE.search(text):
        score += 4
    if re.search(r'\d', text):
        score += 1
    if ',' in text:
        score += 1
    return score


def _looks_like_source_label(value):
    text = _cell_text(value)
    if not text or TIME_WINDOW_RE.fullmatch(text):
        return False
    low = text.casefold()
    if CMD_LABEL_RE.fullmatch(text):
        return True
    if low.startswith('мо ') or 'в+' in low or 'инвитро' in low:
        return True
    return _address_score(text) < 4 and len(text) <= 120


def _infer_columns(ws, sample_rows=80):
    """
    Infer columns from cell contents when the workbook has no usable header.

    Position is deliberately only a tie-breaker. This keeps the importer usable
    when another organization exports the same information in a different order.
    """
    max_col = ws.max_column
    stats = [
        {'address_score': 0, 'address_hits': 0, 'time_hits': 0, 'source_hits': 0, 'nonempty': 0}
        for _ in range(max_col)
    ]
    end_row = min(ws.max_row, sample_rows)
    for row in ws.iter_rows(min_row=1, max_row=end_row, values_only=True):
        for index, value in enumerate(row):
            text = _cell_text(value)
            if not text:
                continue
            stat = stats[index]
            stat['nonempty'] += 1
            score = _address_score(text)
            stat['address_score'] += score
            if score >= 5:
                stat['address_hits'] += 1
            if TIME_WINDOW_RE.fullmatch(text):
                stat['time_hits'] += 1
            if _looks_like_source_label(text):
                stat['source_hits'] += 1

    address_index = max(
        range(max_col),
        key=lambda i: (stats[i]['address_hits'], stats[i]['address_score'], stats[i]['nonempty']),
        default=None,
    )
    if address_index is None or stats[address_index]['address_hits'] == 0:
        raise ValueError('Не удалось уверенно определить колонку с адресами')

    columns = {'address': address_index}
    time_candidates = [
        i for i in range(max_col)
        if i != address_index and stats[i]['time_hits'] > 0
    ]
    if time_candidates:
        columns['time_window'] = max(time_candidates, key=lambda i: stats[i]['time_hits'])

    excluded = set(columns.values())
    source_candidates = [
        i for i in range(max_col)
        if i not in excluded and stats[i]['source_hits'] > 0
    ]
    if source_candidates:
        columns['source_label'] = max(
            source_candidates,
            key=lambda i: (stats[i]['source_hits'], stats[i]['nonempty'], -abs(i - address_index)),
        )
    return 0, columns


def _detect_layout(ws):
    header = _header_candidate(ws)
    if header:
        return header
    return _infer_columns(ws)


def normalize_delivery_address(raw_address):
    """Normalize Russian delivery addresses conservatively, without geocoding."""
    value = _cell_text(raw_address).replace('\xa0', ' ')
    value = re.sub(r'[\r\n\t]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()

    interior = INTERIOR_START_RE.search(value)
    if interior:
        value = value[:interior.start()]

    # Harmless punctuation/noise first.
    value = re.sub(r'(?iu)\b(?:дом)\s*№\s*(?=\d)', 'дом ', value)
    value = re.sub(r'(?iu)\b(?:корпус|корп\.?|к\.)\s*№?\s*(\d+[а-яa-z]?)\b', r'к\1', value)
    value = re.sub(r'(?iu)\b(?:строение|стр\.?)\s*№?\s*(\d+[а-яa-z]?)\b', r'с\1', value)
    value = re.sub(r'(?iu)\b(?:владение|вл\.?)\s*№?\s*(\d+[а-яa-z]?)\b', r'вл\1', value)

    # Expand common abbreviated settlement prefixes. Keep these regexes
    # intentionally simple: comma/start + marker + human-readable name.
    for marker, canonical in (
        ('д.', 'деревня'), ('с.', 'село'), ('пос.', 'посёлок'),
        ('рп', 'рабочий посёлок'), ('пгт', 'пгт'), ('х.', 'хутор'),
    ):
        escaped = re.escape(marker)
        value = re.sub(
            rf'(?iu)(^|,\s*){escaped}\s+([^,;\d]{{2,80}}?)(?=\s*(?:,|$))',
            lambda m, c=canonical: f"{m.group(1)}{c} {m.group(2).strip()}",
            value,
        )

    # House marker is unambiguous only when immediately followed by a number.
    value = re.sub(r'(?iu)(?:\s*,\s*|\s+)\b(?:д|дом)\.?\s*(?:№\s*)?(?=\d)', ' ', value)


    # Settlement types. Prefix forms are unambiguous because a name follows.
    settlement_prefixes = (
        (r'деревня|дер\.?|д\.', 'деревня'),
        (r'село|с\.', 'село'),
        (r'пос[её]лок|пос\.?|п\.', 'посёлок'),
        (r'рабочий\s+пос[её]лок|р\.?\s*п\.?|рп', 'рабочий посёлок'),
        (r'пос[её]лок\s+городского\s+типа|п\.?\s*г\.?\s*т\.?|пгт', 'пгт'),
        (r'хутор|х\.', 'хутор'),
        (r'станица|ст-?ца\.?', 'станица'),
    )
    for pattern, canonical in settlement_prefixes:
        value = re.sub(
            rf'(?iu)(?P<prefix>^|,\s*)(?:{pattern})\s+(?P<name>[А-ЯЁA-Z][^,;\d]{{1,80}})(?=\s*(?:,|$))',
            lambda m, c=canonical: f"{m.group('prefix')}{c} {m.group('name').strip()}",
            value,
        )

    # Postfix settlement notation used by many Russian exports: «Юрлово д.».
    # Only accept it as a complete comma-separated component. Never guess on
    # an ambiguous token embedded in a street/building component.
    postfixes = (
        (r'д\.?' , 'деревня'), (r'с\.?' , 'село'), (r'пос\.?' , 'посёлок'),
        (r'рп', 'рабочий посёлок'), (r'пгт', 'пгт'), (r'х\.', 'хутор'),
    )
    for marker, canonical in postfixes:
        value = re.sub(
            rf'(?iu)(?P<prefix>^|,\s*)(?P<name>[А-ЯЁA-Z][А-ЯЁа-яёA-Za-z0-9 .\'\-]{{1,80}}?)\s+(?:{marker})(?=\s*(?:,|$))',
            lambda m, c=canonical: f"{m.group('prefix')}{c} {m.group('name').strip()}",
            value,
        )

    # City marker: display city name without redundant «г/город».
    value = re.sub(
        r'(?iu)(?P<prefix>^|,\s*)(?:г(?:ород)?\.?)\s+(?P<name>[А-ЯЁA-Z][^,;\d]{1,80})(?=\s*(?:,|$))',
        lambda m: f"{m.group('prefix')}{m.group('name').strip()}",
        value,
    )
    value = re.sub(
        r'(?iu)(?P<prefix>^|,\s*)(?P<name>[А-ЯЁA-Z][А-ЯЁа-яёA-Za-z .\'\-]{1,80}?)\s+г\.?(?=\s*(?:,|$))',
        lambda m: f"{m.group('prefix')}{m.group('name').strip()}",
        value,
    )

    # Dotted street abbreviations.
    for marker, canonical in (('ул.', 'ул'), ('пер.', 'пер'), ('наб.', 'наб'), ('пл.', 'пл'), ('ш.', 'ш')):
        value = re.sub(
            rf'(?iu)(?<![А-ЯЁа-яёA-Za-z]){re.escape(marker)}(?=\s)',
            canonical,
            value,
        )

    # Street words: normalize spelling but do not reorder uncertain components.
    street_aliases = (
        (r'улица|ул\.', 'ул'), (r'бульвар|б-р', 'б-р'),
        (r'проспект|пр-?т', 'пр-т'), (r'переулок|пер\.', 'пер'),
        (r'шоссе|ш\.', 'ш'), (r'набережная|наб\.', 'наб'),
        (r'площадь|пл\.', 'пл'), (r'проезд|пр-д', 'проезд'),
    )
    for pattern, canonical in street_aliases:
        value = re.sub(rf'(?iu)\b(?:{pattern})\b\.?', canonical, value)

    value = re.sub(r'\s*№\s*(?=\d)', ' ', value)
    value = re.sub(r'\s*,\s*', ', ', value)
    value = re.sub(r'\s+', ' ', value).strip(' ,;')
    return value


def _open(content):
    try:
        return load_workbook(BytesIO(content), data_only=True, read_only=False)
    except Exception as exc:
        raise ValueError('Не удалось открыть XLSX. Проверьте, что файл не повреждён') from exc


def _fill(cell):
    fill = cell.fill
    if not fill or fill.fill_type != 'solid':
        return ''
    color = fill.fgColor
    if color.type == 'rgb' and color.rgb:
        return COLORS.get(color.rgb.upper(), '')
    return ''


def _is_pryadilnaya_service_address(address):
    """Office/warehouse at 2-я Прядильная, house 1 is never a route point."""
    text = normalize_delivery_address(address).casefold().replace('ё', 'е')
    compact = re.sub(r'[^0-9a-zа-я]+', ' ', text).strip()
    street = (
        '2 я прядильная' in compact
        or '2я прядильная' in compact
        or 'прядильная 2 я' in compact
        or 'прядильная 2я' in compact
    )
    if not street:
        return False

    # After normalization house markers are removed, while corpus/building are
    # compacted. The house number follows the street component in our exports.
    match = re.search(
        r'(?:2\s*я\s+прядильная|прядильная\s+2\s*я)(?:\s+ул)?\s+(\d+)(?:\b|(?=[кс]\d))',
        compact,
    )
    return bool(match and match.group(1) == '1')

def _rows(content, create_points=False):
    wb = _open(content)
    ws = wb.active
    if ws.max_row < 1:
        raise ValueError('Файл пуст')

    header_row, columns = _detect_layout(ws)
    rows = []
    first_data_row = header_row + 1 if header_row else 1

    for excel_row, row in enumerate(ws.iter_rows(min_row=first_data_row), start=first_data_row):
        values = {
            field: row[index].value
            for field, index in columns.items()
            if index < len(row)
        }
        raw_address = _cell_text(values.get('address'))
        # Headered exports are explicit: keep accepting short/internal addresses\n        # such as «Старый адрес». Headerless sheets need semantic evidence so\n        # decorative text is not mistaken for a delivery row.\n        if not raw_address or (not header_row and _address_score(raw_address) < 3):\n            continue

        address = normalize_delivery_address(raw_address)
        if not address:
            continue

        # Permanent business rule: the office/warehouse at 2-я Прядильная, 1
        # is service infrastructure, never a courier delivery. Its row position
        # and source label are irrelevant.
        if _is_pryadilnaya_service_address(address):
            continue

        source = _cell_text(values.get('source_label'))
        phone = _cell_text(values.get('phone'))
        organization = _cell_text(values.get('organization'))
        recipient = _cell_text(values.get('recipient'))
        comment = _cell_text(values.get('comment'))
        time_window = _cell_text(values.get('time_window'))

        match = resolve_point(source, address, phone, create=create_points)
        point = match.point
        created = match.created
        canonical = canonical_delivery_values(point, source, address, phone)

        raw_order = values.get('route_order')
        route_order = int(raw_order) if isinstance(raw_order, (int, float)) else len(rows) + 1

        courier_name = _cell_text(values.get('courier'))
        courier = None
        if courier_name:
            courier = (
                User.objects.filter(role=User.Role.COURIER, username__iexact=courier_name).first()
                or User.objects.filter(role=User.Role.COURIER, first_name__iexact=courier_name).first()
            )

        # Row color is presentation metadata only; it never decides whether a
        # row is CMD/INVITRO or whether the row is a valid delivery.
        color = _fill(row[0]) if row else ''
        rows.append({
            'excel_row': excel_row,
            'delivery_date': _date(values.get('delivery_date')),
            'address': canonical['address'],
            'source_label': canonical['source_label'],
            'organization': organization,
            'recipient': recipient,
            'phone': canonical['phone'],
            'comment': comment,
            'courier': courier,
            'courier_name': courier_name,
            'route_order': route_order,
            'time_window': time_window,
            'row_color': color,
            'point': point,
            'point_created': created,
        })
    return rows


def _duplicate_key(row):
    return (row['delivery_date'], row['address'], row['source_label'], row['route_order'])


def _point_key(row):
    return (
        (row['source_label'] or '').strip().casefold(),
        (row['address'] or '').strip().casefold(),
    )


def preview_workbook(content):
    validate_upload('preview.xlsx', content)
    rows = _rows(content, create_points=False)
    summary = ImportSummary(total_rows=len(rows))
    seen_delivery_keys = set()
    new_point_keys = set()
    for row in rows:
        if row['point']:
            summary.matched += 1
        else:
            new_point_keys.add(_point_key(row))
        key = _duplicate_key(row)
        duplicate = key in seen_delivery_keys or Delivery.objects.filter(
            delivery_date=row['delivery_date'],
            address=row['address'],
            source_label=row['source_label'],
            route_order=row['route_order'],
        ).exists()
        seen_delivery_keys.add(key)
        if duplicate:
            summary.skipped += 1
        if len(summary.preview) < 100:
            summary.preview.append({
                'row': row['excel_row'],
                'label': row['source_label'],
                'address': row['address'],
                'date': row['delivery_date'],
                'time_window': row['time_window'],
                'duplicate': duplicate,
                'new_point': row['point'] is None,
                'match': str(row['point']) if row['point'] else '',
                'courier': row['courier'],
            })
        if row['courier_name'] and not row['courier']:
            summary.warnings.append(
                f"Строка {row['excel_row']}: курьер «{row['courier_name']}» не найден"
            )
    summary.would_create_points = len(new_point_keys)
    return summary


def import_workbook(content, actor=None):
    validate_upload('import.xlsx', content)
    rows = _rows(content, create_points=True)
    summary = ImportSummary(total_rows=len(rows))
    with transaction.atomic():
        for row in rows:
            if row['point']:
                summary.matched += 1
            if row['point_created']:
                summary.new_points += 1
            duplicate = Delivery.objects.filter(
                delivery_date=row['delivery_date'],
                address=row['address'],
                source_label=row['source_label'],
                route_order=row['route_order'],
            ).exists()
            if duplicate:
                summary.skipped += 1
                continue
            delivery = Delivery.objects.create(
                delivery_date=row['delivery_date'],
                address=row['address'],
                source_label=row['source_label'],
                organization=row['organization'],
                recipient=row['recipient'],
                phone=row['phone'],
                comment=row['comment'],
                courier=row['courier'],
                route_order=row['route_order'],
                time_window=row['time_window'],
                row_color=row['row_color'],
                point=row['point'],
            )
            summary.created += 1
            DeliveryEvent.objects.create(
                delivery=delivery,
                actor=actor,
                action='created',
                note='Импорт из Excel',
            )
            if row['courier_name'] and not row['courier']:
                summary.warnings.append(
                    f"Строка {row['excel_row']}: курьер «{row['courier_name']}» не найден"
                )
    return summary
