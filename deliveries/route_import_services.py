from dataclasses import dataclass, field
from django.db import transaction
from .import_services import _rows, validate_upload
from .models import Delivery, DeliveryEvent, RouteTemplateItem


@dataclass
class RouteImportSummary:
    total_rows: int = 0
    matched_target: int = 0
    known_library: int = 0
    new_points: int = 0
    missing_from_file: int = 0
    order_changed: bool = False
    preview: list = field(default_factory=list)
    applied: int = 0
    created_points: int = 0
    removed: int = 0


def _unique_rows(rows):
    result = []
    seen = set()
    for row in rows:
        key = row['point'].pk if row.get('point') else (
            (row.get('source_label') or '').strip().casefold(),
            (row.get('address') or '').strip().casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def preview_route_workbook(content, current_point_ids):
    validate_upload('route.xlsx', content)
    rows = _unique_rows(_rows(content, create_points=False))
    current = [int(v) for v in current_point_ids if v]
    current_set = set(current)
    incoming_known = []
    summary = RouteImportSummary(total_rows=len(rows))
    new_keys = set()

    for position, row in enumerate(rows, start=1):
        point = row.get('point')
        if point:
            incoming_known.append(point.pk)
            if point.pk in current_set:
                summary.matched_target += 1
                status = 'Уже в этом маршруте'
            else:
                summary.known_library += 1
                status = 'Есть в справочнике, новая для маршрута'
        else:
            key = ((row.get('source_label') or '').strip().casefold(), (row.get('address') or '').strip().casefold())
            new_keys.add(key)
            status = 'Новая точка — будет добавлена в справочник'
        if len(summary.preview) < 150:
            summary.preview.append({
                'position': position,
                'label': row.get('source_label') or '—',
                'address': row.get('address') or '',
                'time_window': row.get('time_window') or '',
                'status': status,
            })

    summary.new_points = len(new_keys)
    incoming_target_set = {pid for pid in incoming_known if pid in current_set}
    summary.missing_from_file = len(current_set - incoming_target_set)
    common_current = [pid for pid in current if pid in incoming_target_set]
    common_incoming = [pid for pid in incoming_known if pid in incoming_target_set]
    summary.order_changed = common_current != common_incoming
    return summary


@transaction.atomic
def apply_workbook_to_template(content, template, mode='replace'):
    if mode not in ('replace', 'add'):
        raise ValueError('Неизвестный режим импорта')
    validate_upload('route.xlsx', content)
    rows = _unique_rows(_rows(content, create_points=True))
    summary = RouteImportSummary(total_rows=len(rows))
    summary.created_points = sum(1 for row in rows if row.get('point_created'))

    existing = list(template.items.select_related('point').order_by('route_order', 'id'))
    by_point = {item.point_id: item for item in existing}

    if mode == 'replace':
        incoming_ids = {row['point'].pk for row in rows if row.get('point')}
        removed_qs = template.items.exclude(point_id__in=incoming_ids)
        summary.removed = removed_qs.count()
        removed_qs.delete()
        for order, row in enumerate(rows, start=1):
            point = row['point']
            item, _ = RouteTemplateItem.objects.get_or_create(template=template, point=point, defaults={'route_order': order})
            item.route_order = order
            item.enabled_by_default = True
            item.time_window = (row.get('time_window') or '')[:64]
            item.comment = (row.get('comment') or '')[:255]
            item.save(update_fields=['route_order', 'enabled_by_default', 'time_window', 'comment'])
            summary.applied += 1
    else:
        next_order = max([item.route_order for item in existing] or [0]) + 1
        for row in rows:
            point = row['point']
            item = by_point.get(point.pk)
            if item:
                changed = []
                time_window = (row.get('time_window') or '')[:64]
                comment = (row.get('comment') or '')[:255]
                if time_window and item.time_window != time_window:
                    item.time_window = time_window
                    changed.append('time_window')
                if comment and item.comment != comment:
                    item.comment = comment
                    changed.append('comment')
                if changed:
                    item.save(update_fields=changed)
            else:
                item = RouteTemplateItem.objects.create(template=template, point=point, route_order=next_order, enabled_by_default=True, time_window=(row.get('time_window') or '')[:64], comment=(row.get('comment') or '')[:255])
                by_point[point.pk] = item
                next_order += 1
            summary.applied += 1
    return summary


def _return_to_day_pool(delivery):
    delivery.route_run = None
    delivery.courier = None
    if delivery.status == Delivery.Status.IN_PROGRESS:
        delivery.status = Delivery.Status.NEW
    delivery.save(update_fields=['route_run', 'courier', 'status', 'updated_at'])


@transaction.atomic
def apply_workbook_to_run(content, run, actor=None, mode='replace'):
    if mode not in ('replace', 'add'):
        raise ValueError('Неизвестный режим импорта')
    if mode == 'replace' and run.deliveries.filter(status=Delivery.Status.DONE).exists():
        raise ValueError('Нельзя заменить состав: в маршруте уже есть выполненные точки')

    validate_upload('route.xlsx', content)
    rows = _unique_rows(_rows(content, create_points=True))
    summary = RouteImportSummary(total_rows=len(rows))
    summary.created_points = sum(1 for row in rows if row.get('point_created'))
    existing = list(run.deliveries.select_related('point').order_by('route_order', 'id'))
    by_point = {row.point_id: row for row in existing if row.point_id}

    if mode == 'replace':
        incoming_ids = {row['point'].pk for row in rows if row.get('point')}
        for delivery in list(run.deliveries.exclude(status=Delivery.Status.DONE).exclude(point_id__in=incoming_ids)):
            _return_to_day_pool(delivery)
            summary.removed += 1
        next_order = 1
    else:
        next_order = max([row.route_order for row in existing] or [0]) + 1

    for file_position, row in enumerate(rows, start=1):
        point = row['point']
        delivery = by_point.get(point.pk)
        was_in_run = bool(delivery and delivery.pk and delivery.route_run_id == run.pk)
        if not delivery:
            delivery = (
                Delivery.objects.filter(delivery_date=run.run_date, point=point, route_run__isnull=True)
                .exclude(status=Delivery.Status.DONE)
                .order_by('id')
                .first()
            )
            was_in_run = False
            if not delivery:
                delivery = Delivery(delivery_date=run.run_date, point=point)
            by_point[point.pk] = delivery

        delivery.route_run = run
        delivery.delivery_date = run.run_date
        delivery.courier = run.assigned_courier
        if mode == 'replace':
            delivery.route_order = file_position
        elif not was_in_run:
            delivery.route_order = next_order
            next_order += 1

        delivery.source_label = row.get('source_label') or point.code or point.name
        delivery.address = row.get('address') or point.address
        delivery.organization = row.get('organization') or ''
        delivery.recipient = row.get('recipient') or ''
        delivery.phone = row.get('phone') or point.phone
        delivery.comment = row.get('comment') or ''
        delivery.time_window = row.get('time_window') or ''
        delivery.row_color = row.get('row_color') or ''
        if delivery.status == Delivery.Status.NEW and run.assigned_courier:
            delivery.status = Delivery.Status.IN_PROGRESS
        elif delivery.status == Delivery.Status.IN_PROGRESS and not run.assigned_courier:
            delivery.status = Delivery.Status.NEW
        delivery.save()
        DeliveryEvent.objects.create(delivery=delivery, actor=actor, action='route_excel_import', note=f'Excel → {run.route.name}, позиция {delivery.route_order}')
        summary.applied += 1
    return summary
