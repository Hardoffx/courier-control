from django.db import transaction
from .models import Delivery, RouteRun, RouteTemplateItem

@transaction.atomic
def generate_route_run(template, run_date, courier=None, enabled_item_ids=None):
    courier = courier or template.route.default_courier
    run, _ = RouteRun.objects.get_or_create(route=template.route,run_date=run_date,defaults={'template':template,'assigned_courier':courier,'status':RouteRun.Status.READY})
    run.template=template; run.assigned_courier=courier
    if run.status == RouteRun.Status.DRAFT: run.status=RouteRun.Status.READY
    run.save(update_fields=['template','assigned_courier','status','updated_at'])
    items=list(template.items.select_related('point').order_by('route_order','id'))
    selected=[item for item in items if item.enabled_by_default] if enabled_item_ids is None else [item for item in items if item.id in {int(v) for v in enabled_item_ids}]
    selected_point_ids={item.point_id for item in selected}; run.deliveries.exclude(status=Delivery.Status.DONE).exclude(point_id__in=selected_point_ids).delete()
    for order,item in enumerate(selected,start=1):
        point=item.point; delivery=run.deliveries.filter(point=point).first()
        if delivery and delivery.status == Delivery.Status.DONE: continue
        if not delivery: delivery=Delivery(route_run=run,delivery_date=run_date,point=point)
        delivery.delivery_date=run_date; delivery.courier=courier; delivery.route_order=order; delivery.source_label=point.code or point.name; delivery.address=point.address; delivery.phone=point.phone; delivery.time_window=item.time_window
        if delivery.status == Delivery.Status.NEW and courier: delivery.status=Delivery.Status.IN_PROGRESS
        elif delivery.status == Delivery.Status.IN_PROGRESS and not courier: delivery.status=Delivery.Status.NEW
        delivery.save()
    return run

@transaction.atomic
def reassign_route_run(run, courier):
    run.assigned_courier=courier; run.save(update_fields=['assigned_courier','updated_at'])
    for delivery in run.deliveries.exclude(status=Delivery.Status.DONE):
        delivery.courier=courier
        if courier and delivery.status == Delivery.Status.NEW: delivery.status=Delivery.Status.IN_PROGRESS
        elif not courier and delivery.status == Delivery.Status.IN_PROGRESS: delivery.status=Delivery.Status.NEW
        delivery.save(update_fields=['courier','status','updated_at'])
    return run

@transaction.atomic
def learn_template_from_run(run, template):
    """Explicitly replace one permanent template with the canonical composition/order of a real day."""
    if template.route_id != run.route_id:
        raise ValueError('Шаблон принадлежит другому маршруту')
    rows=list(run.deliveries.select_related('point').exclude(point__isnull=True).order_by('route_order','id'))
    if not rows:
        raise ValueError('В маршруте нет точек из справочника')
    seen=set(); learned=[]
    for row in rows:
        if row.point_id in seen: continue
        seen.add(row.point_id); learned.append(row)
    template.items.exclude(point_id__in=seen).delete()
    for order,row in enumerate(learned,start=1):
        item,_=RouteTemplateItem.objects.get_or_create(template=template,point=row.point,defaults={'route_order':order})
        item.route_order=order; item.enabled_by_default=True; item.time_window=row.time_window; item.comment=row.comment[:255]; item.save(update_fields=['route_order','enabled_by_default','time_window','comment'])
    return len(learned)
