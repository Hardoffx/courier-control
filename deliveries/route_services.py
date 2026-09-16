from django.db import transaction
from .models import Delivery, RouteRun, RouteTemplateItem


def _reset_detached_delivery(delivery):
    """Return a non-completed delivery to the unassigned day pool."""
    delivery.route_run = None
    delivery.courier = None
    if delivery.status == Delivery.Status.IN_PROGRESS:
        delivery.status = Delivery.Status.NEW
    delivery.save(update_fields=['route_run', 'courier', 'status', 'updated_at'])


@transaction.atomic
def generate_route_run(template, run_date, courier=None, enabled_item_ids=None):
    courier = courier or template.route.default_courier
    run, _ = RouteRun.objects.get_or_create(
        route=template.route,
        run_date=run_date,
        defaults={
            'template': template,
            'assigned_courier': courier,
            'status': RouteRun.Status.READY,
        },
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

    selected_point_ids = {item.point_id for item in selected}

    # Never delete a day's delivery merely because it was removed from a route.
    # Returning it to the unassigned pool preserves imported/manual work.
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
            # If the same point already exists in today's imported/manual pool,
            # attach that row to the route instead of creating a duplicate.
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
                delivery = Delivery(
                    route_run=run,
                    delivery_date=run_date,
                    point=point,
                )

        delivery.delivery_date = run_date
        delivery.route_run = run
        delivery.courier = courier
        delivery.route_order = order

        if adopted:
            # Preserve the real day's Excel/manual snapshot; only fill blanks.
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
    return run


@transaction.atomic
def dissolve_route_run(run):
    """Remove one day's named route without losing imported/manual deliveries.

    Legacy duplicate rows created by older route generation are removed when an
    equivalent direct day delivery already exists. The retained direct row is
    unassigned. Unique route rows are returned to the unassigned day pool.
    Completed work is never modified.
    """
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
    """Explicitly replace one permanent template with the canonical composition/order of a real day."""
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
