from django.db import transaction
from django.utils import timezone
from .models import (
    CourierRouteOrderPreference,
    Delivery,
    RouteOrderSuggestion,
    RouteRun,
    RouteTemplateItem,
)


def _reset_detached_delivery(delivery):
    """Return a non-completed delivery to the unassigned day pool."""
    delivery.route_run = None
    delivery.courier = None
    if delivery.status == Delivery.Status.IN_PROGRESS:
        delivery.status = Delivery.Status.NEW
    delivery.save(update_fields=['route_run', 'courier', 'status', 'updated_at'])


def _ordered_for_courier(template, items, courier):
    """Use a courier's learned order; unfamiliar/new points stay in template order at the end."""
    if not courier:
        return items
    preference = CourierRouteOrderPreference.objects.filter(template=template, courier=courier).first()
    if not preference or not preference.point_order:
        return items
    by_point = {item.point_id: item for item in items}
    ordered = [by_point[point_id] for point_id in preference.point_order if point_id in by_point]
    used = {item.point_id for item in ordered}
    ordered.extend(item for item in items if item.point_id not in used)
    return ordered


@transaction.atomic
def generate_route_run(template, run_date, courier=None, enabled_item_ids=None):
    courier = courier or template.route.default_courier
    # Reuse an open run while it still has work. Once every delivery in the
    # latest run is completed, a new assignment on the same date becomes a
    # separate trip instead of silently reopening/reusing the completed run.
    same_day_runs = RouteRun.objects.select_for_update().filter(
        route=template.route,
        run_date=run_date,
    ).order_by('-created_at', '-id')
    run = next(
        (candidate for candidate in same_day_runs if not candidate.deliveries.exists() or candidate.deliveries.exclude(status=Delivery.Status.DONE).exists()),
        None,
    )
    if run is None:
        run = RouteRun.objects.create(
            route=template.route,
            run_date=run_date,
            template=template,
            assigned_courier=courier,
            status=RouteRun.Status.READY,
        )
    run.template = template
    run.assigned_courier = courier
    if run.status == RouteRun.Status.DRAFT:
        run.status = RouteRun.Status.READY
    run.save(update_fields=['template', 'assigned_courier', 'status', 'updated_at'])

    items = list(template.items.select_related('point').order_by('route_order', 'id'))
    if enabled_item_ids is None:
        selected = [item for item in items if item.enabled_by_default]
    else:
        selected_ids = {int(v) for v in enabled_item_ids}
        selected = [item for item in items if item.id in selected_ids]
    selected = _ordered_for_courier(template, selected, courier)
    selected_point_ids = {item.point_id for item in selected}

    for delivery in list(
        run.deliveries.exclude(status=Delivery.Status.DONE)
        .exclude(point_id__in=selected_point_ids)
    ):
        _reset_detached_delivery(delivery)

    for order, item in enumerate(selected, start=1):
        point = item.point
        delivery = run.deliveries.filter(point=point).first()
        adopted = False

        if delivery and delivery.status == Delivery.Status.DONE:
            continue

        if not delivery:
            delivery = (
                Delivery.objects.filter(
                    delivery_date=run_date,
                    point=point,
                    route_run__isnull=True,
                )
                .exclude(status=Delivery.Status.DONE)
                .order_by('id')
                .first()
            )
            if delivery:
                adopted = True
                delivery.route_run = run
            else:
                delivery = Delivery(route_run=run, delivery_date=run_date, point=point)

        delivery.delivery_date = run_date
        delivery.route_run = run
        delivery.courier = courier
        delivery.route_order = order

        if adopted:
            if not delivery.source_label:
                delivery.source_label = point.code or point.name
            if not delivery.address:
                delivery.address = point.address
            if not delivery.phone:
                delivery.phone = point.phone
            if not delivery.time_window:
                delivery.time_window = item.time_window
        else:
            delivery.source_label = point.code or point.name
            delivery.address = point.address
            delivery.phone = point.phone
            delivery.time_window = item.time_window

        if delivery.status == Delivery.Status.NEW and courier:
            delivery.status = Delivery.Status.IN_PROGRESS
        elif delivery.status == Delivery.Status.IN_PROGRESS and not courier:
            delivery.status = Delivery.Status.NEW
        delivery.save()
    return run


def _reorder_run_by_preference(run, courier):
    if not courier or not run.template_id or run.deliveries.filter(status=Delivery.Status.DONE).exists():
        return False
    preference = CourierRouteOrderPreference.objects.filter(template=run.template, courier=courier).first()
    if not preference or not preference.point_order:
        return False
    rows = list(run.deliveries.order_by('route_order', 'id'))
    by_point = {row.point_id: row for row in rows if row.point_id}
    ordered = [by_point[point_id] for point_id in preference.point_order if point_id in by_point]
    used = {row.pk for row in ordered}
    ordered.extend(row for row in rows if row.pk not in used)
    for order, row in enumerate(ordered, start=1):
        if row.route_order != order:
            row.route_order = order
            row.save(update_fields=['route_order'])
    return True


@transaction.atomic
def reassign_route_run(run, courier):
    run.assigned_courier = courier
    run.save(update_fields=['assigned_courier', 'updated_at'])
    for delivery in run.deliveries.exclude(status=Delivery.Status.DONE):
        delivery.courier = courier
        if courier and delivery.status == Delivery.Status.NEW:
            delivery.status = Delivery.Status.IN_PROGRESS
        elif not courier and delivery.status == Delivery.Status.IN_PROGRESS:
            delivery.status = Delivery.Status.NEW
        delivery.save(update_fields=['courier', 'status', 'updated_at'])
    _reorder_run_by_preference(run, courier)
    return run


@transaction.atomic
def record_courier_order_change(run, courier, original_point_order, proposed_point_order):
    """Keep one pending manager review per daily route, updating it as the courier keeps adjusting."""
    original = [int(v) for v in original_point_order if v]
    proposed = [int(v) for v in proposed_point_order if v]
    if not run or not run.template_id or original == proposed:
        return None
    suggestion, created = RouteOrderSuggestion.objects.get_or_create(
        run=run,
        defaults={
            'courier': courier,
            'original_point_order': original,
            'proposed_point_order': proposed,
            'status': RouteOrderSuggestion.Status.PENDING,
        },
    )
    if not created:
        if suggestion.status != RouteOrderSuggestion.Status.PENDING:
            suggestion.original_point_order = original
        suggestion.courier = courier
        suggestion.proposed_point_order = proposed
        suggestion.status = RouteOrderSuggestion.Status.PENDING
        suggestion.decided_by = None
        suggestion.decided_at = None
        suggestion.save(update_fields=['courier', 'original_point_order', 'proposed_point_order', 'status', 'decided_by', 'decided_at', 'updated_at'])
    return suggestion


def suggestion_comparison(suggestion):
    """Return point objects in before/after order for manager UI."""
    point_ids = list(dict.fromkeys(suggestion.original_point_order + suggestion.proposed_point_order))
    from .models import DeliveryPoint
    points = {p.pk: p for p in DeliveryPoint.objects.filter(pk__in=point_ids)}
    before = [points[pid] for pid in suggestion.original_point_order if pid in points]
    after = [points[pid] for pid in suggestion.proposed_point_order if pid in points]
    return before, after


@transaction.atomic
def decide_order_suggestion(suggestion, action, actor):
    if suggestion.status != RouteOrderSuggestion.Status.PENDING:
        return suggestion
    run = suggestion.run
    if action == 'template':
        if not run.template_id:
            raise ValueError('У маршрута дня нет шаблона')
        items = list(run.template.items.select_related('point').order_by('route_order', 'id'))
        by_point = {item.point_id: item for item in items}
        ordered = [by_point[pid] for pid in suggestion.proposed_point_order if pid in by_point]
        used = {item.pk for item in ordered}
        ordered.extend(item for item in items if item.pk not in used)
        for order, item in enumerate(ordered, start=1):
            if item.route_order != order:
                item.route_order = order
                item.save(update_fields=['route_order'])
        suggestion.status = RouteOrderSuggestion.Status.APPLIED_TEMPLATE
    elif action == 'courier':
        if not run.template_id or not suggestion.courier_id:
            raise ValueError('Нельзя сохранить личный порядок без шаблона и курьера')
        CourierRouteOrderPreference.objects.update_or_create(
            template=run.template,
            courier=suggestion.courier,
            defaults={'point_order': suggestion.proposed_point_order},
        )
        suggestion.status = RouteOrderSuggestion.Status.APPLIED_COURIER
    elif action == 'dismiss':
        suggestion.status = RouteOrderSuggestion.Status.DISMISSED
    else:
        raise ValueError('Неизвестное действие')
    suggestion.decided_by = actor
    suggestion.decided_at = timezone.now()
    suggestion.save(update_fields=['status', 'decided_by', 'decided_at', 'updated_at'])
    return suggestion


@transaction.atomic
def dissolve_route_run(run):
    if run.deliveries.filter(status=Delivery.Status.DONE).exists():
        raise ValueError('Нельзя расформировать маршрут: в нём уже есть выполненные точки')

    detached = 0
    removed_duplicates = 0
    for delivery in list(run.deliveries.select_related('point').order_by('id')):
        duplicate = (
            Delivery.objects.filter(
                delivery_date=run.run_date,
                route_run__isnull=True,
                point_id=delivery.point_id,
            )
            .exclude(pk=delivery.pk)
            .order_by('id')
            .first()
        )
        if delivery.point_id and duplicate:
            delivery.delete()
            duplicate.courier = None
            if duplicate.status == Delivery.Status.IN_PROGRESS:
                duplicate.status = Delivery.Status.NEW
            duplicate.save(update_fields=['courier', 'status', 'updated_at'])
            removed_duplicates += 1
        else:
            _reset_detached_delivery(delivery)
            detached += 1

    run.delete()
    return detached, removed_duplicates


@transaction.atomic
def learn_template_from_run(run, template):
    if template.route_id != run.route_id:
        raise ValueError('Шаблон принадлежит другому маршруту')
    rows = list(
        run.deliveries.select_related('point')
        .exclude(point__isnull=True)
        .order_by('route_order', 'id')
    )
    if not rows:
        raise ValueError('В маршруте нет точек из справочника')
    seen = set()
    learned = []
    for row in rows:
        if row.point_id in seen:
            continue
        seen.add(row.point_id)
        learned.append(row)
    template.items.exclude(point_id__in=seen).delete()
    for order, row in enumerate(learned, start=1):
        item, _ = RouteTemplateItem.objects.get_or_create(
            template=template,
            point=row.point,
            defaults={'route_order': order},
        )
        item.route_order = order
        item.enabled_by_default = True
        item.time_window = row.time_window
        item.comment = row.comment[:255]
        item.save(update_fields=['route_order', 'enabled_by_default', 'time_window', 'comment'])
    return len(learned)
