from django.db import transaction
from .models import Delivery, RouteRun

@transaction.atomic
def generate_route_run(template, run_date, courier=None, enabled_item_ids=None):
    """Create/update a day's route from a template without touching completed deliveries.

    courier defaults to Route.default_courier. enabled_item_ids=None means use each
    item's enabled_by_default flag. Re-running updates pending rows by canonical point
    and never duplicates or deletes completed work.
    """
    courier = courier or template.route.default_courier
    run, _ = RouteRun.objects.get_or_create(
        route=template.route,
        run_date=run_date,
        defaults={'template':template,'assigned_courier':courier,'status':RouteRun.Status.READY},
    )
    run.template=template
    run.assigned_courier=courier
    if run.status == RouteRun.Status.DRAFT:
        run.status=RouteRun.Status.READY
    run.save(update_fields=['template','assigned_courier','status','updated_at'])

    items=list(template.items.select_related('point').order_by('route_order','id'))
    if enabled_item_ids is None:
        selected=[item for item in items if item.enabled_by_default]
    else:
        selected_ids={int(value) for value in enabled_item_ids}
        selected=[item for item in items if item.id in selected_ids]

    selected_point_ids={item.point_id for item in selected}
    pending=run.deliveries.exclude(status=Delivery.Status.DONE)
    pending.exclude(point_id__in=selected_point_ids).delete()

    for order,item in enumerate(selected,start=1):
        point=item.point
        delivery=run.deliveries.filter(point=point).first()
        if delivery and delivery.status == Delivery.Status.DONE:
            continue
        if not delivery:
            delivery=Delivery(route_run=run,delivery_date=run_date,point=point)
        delivery.delivery_date=run_date
        delivery.courier=courier
        delivery.route_order=order
        delivery.source_label=point.code or point.name
        delivery.address=point.address
        delivery.phone=point.phone
        delivery.time_window=item.time_window
        if delivery.status == Delivery.Status.NEW and courier:
            delivery.status=Delivery.Status.IN_PROGRESS
        elif delivery.status == Delivery.Status.IN_PROGRESS and not courier:
            delivery.status=Delivery.Status.NEW
        delivery.save()
    return run

@transaction.atomic
def reassign_route_run(run, courier):
    """Swap the courier for one day's route without changing its persistent template."""
    run.assigned_courier=courier
    run.save(update_fields=['assigned_courier','updated_at'])
    for delivery in run.deliveries.exclude(status=Delivery.Status.DONE):
        delivery.courier=courier
        if courier and delivery.status == Delivery.Status.NEW:
            delivery.status=Delivery.Status.IN_PROGRESS
        elif not courier and delivery.status == Delivery.Status.IN_PROGRESS:
            delivery.status=Delivery.Status.NEW
        delivery.save(update_fields=['courier','status','updated_at'])
    return run
