from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.models import User
from .models import Delivery, DeliveryEvent, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem
from .route_services import generate_route_run, reassign_route_run

def dispatcher_required(view):
    @login_required
    def wrapped(request,*args,**kwargs):
        if not request.user.is_dispatcher: raise PermissionDenied
        return view(request,*args,**kwargs)
    return wrapped

def _couriers(): return User.objects.filter(role=User.Role.COURIER,is_active=True).order_by('-is_reserve_courier','first_name','username')
def _ids(raw):
    result=[]
    for value in (raw or '').split(','):
        try: result.append(int(value.strip()))
        except (TypeError,ValueError): pass
    return result

def _save_order(items):
    with transaction.atomic():
        for pos,item in enumerate(items,start=1):
            if item.route_order!=pos: item.route_order=pos; item.save(update_fields=['route_order'])

@dispatcher_required
def route_list(request): return render(request,'dispatcher/routes/list.html',{'routes':Route.objects.filter(is_active=True).select_related('default_courier').prefetch_related('templates')})

@dispatcher_required
def route_edit(request,pk=None):
    route=get_object_or_404(Route,pk=pk) if pk else None; couriers=_couriers()
    if request.method=='POST':
        name=request.POST.get('name','').strip()[:120]
        if not name: messages.error(request,'Укажите название маршрута')
        else:
            courier_id=request.POST.get('default_courier',''); courier=couriers.filter(pk=courier_id).first() if courier_id else None; route=route or Route(); route.name=name; route.default_courier=courier; route.notes=request.POST.get('notes','').strip(); route.save()
            if not route.templates.exists(): RouteTemplate.objects.create(route=route,kind=RouteTemplate.Kind.WEEKDAY); RouteTemplate.objects.create(route=route,kind=RouteTemplate.Kind.WEEKEND)
            messages.success(request,'Маршрут сохранён'); return redirect('route_detail',pk=route.pk)
    return render(request,'dispatcher/routes/route_form.html',{'route':route,'couriers':couriers})

@dispatcher_required
def route_detail(request,pk):
    route=get_object_or_404(Route,pk=pk); templates=route.templates.filter(is_active=True); template_id=request.GET.get('template'); template=templates.filter(pk=template_id).first() if template_id else templates.order_by('kind','id').first(); points=DeliveryPoint.objects.filter(is_active=True).order_by('kind','name'); return render(request,'dispatcher/routes/detail.html',{'route':route,'templates':templates,'template':template,'points':points,'couriers':_couriers()})

@dispatcher_required
@require_POST
def template_add_point(request,pk):
    template=get_object_or_404(RouteTemplate,pk=pk); point=get_object_or_404(DeliveryPoint,pk=request.POST.get('point_id'),is_active=True); last=template.items.order_by('-route_order').first(); item,created=RouteTemplateItem.objects.get_or_create(template=template,point=point,defaults={'route_order':(last.route_order+1 if last else 1)})
    if not created: item.enabled_by_default=True; item.save(update_fields=['enabled_by_default'])
    return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')

@dispatcher_required
@require_POST
def template_item_update(request,pk):
    item=get_object_or_404(RouteTemplateItem.objects.select_related('template'),pk=pk); action=request.POST.get('action'); route_id=item.template.route_id; template_id=item.template_id
    if action=='toggle': item.enabled_by_default=not item.enabled_by_default; item.save(update_fields=['enabled_by_default'])
    elif action in ('up','down'):
        items=list(item.template.items.order_by('route_order','id')); idx=items.index(item); target=idx-1 if action=='up' else idx+1
        if 0<=target<len(items): items[idx],items[target]=items[target],items[idx]; _save_order(items)
    elif action=='edit': item.time_window=request.POST.get('time_window','').strip()[:64]; item.comment=request.POST.get('comment','').strip()[:255]; item.save(update_fields=['time_window','comment'])
    elif action=='remove': item.delete()
    return redirect(f'/dispatcher/routes/{route_id}/?template={template_id}')

@dispatcher_required
@require_POST
def template_reorder(request,pk):
    template=get_object_or_404(RouteTemplate,pk=pk); items=list(template.items.order_by('route_order','id')); by_id={x.pk:x for x in items}; requested=_ids(request.POST.get('order')); ordered=[by_id[x] for x in requested if x in by_id]; ordered.extend(x for x in items if x.pk not in requested); _save_order(ordered); return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')

@dispatcher_required
@require_POST
def route_generate(request,pk):
    route=get_object_or_404(Route,pk=pk); template=get_object_or_404(RouteTemplate,pk=request.POST.get('template_id'),route=route)
    try: run_date=date.fromisoformat(request.POST.get('run_date',''))
    except ValueError: messages.error(request,'Некорректная дата'); return redirect('route_detail',pk=pk)
    courier_id=request.POST.get('courier_id',''); courier=_couriers().filter(pk=courier_id).first() if courier_id else route.default_courier; run=generate_route_run(template,run_date,courier=courier,enabled_item_ids=request.POST.getlist('enabled_items')); messages.success(request,f'{route.name}: сформировано {run.deliveries.count()} точек на {run_date:%d.%m.%Y}'); return redirect(f'/dispatcher/?date={run_date.isoformat()}')

@dispatcher_required
def run_detail(request,pk):
    run=get_object_or_404(RouteRun.objects.select_related('route','template','assigned_courier'),pk=pk); deliveries=run.deliveries.select_related('point').prefetch_related('events__actor').order_by('route_order','id'); points=DeliveryPoint.objects.filter(is_active=True).order_by('kind','name'); previous=RouteRun.objects.filter(route=run.route,run_date__lt=run.run_date).order_by('-run_date').first(); return render(request,'dispatcher/route_run_detail.html',{'run':run,'deliveries':deliveries,'couriers':_couriers(),'points':points,'previous_run':previous})

@dispatcher_required
@require_POST
def run_add_point(request,pk):
    run=get_object_or_404(RouteRun,pk=pk); point=get_object_or_404(DeliveryPoint,pk=request.POST.get('point_id'),is_active=True); last=run.deliveries.order_by('-route_order').first(); delivery=Delivery.objects.create(delivery_date=run.run_date,route_run=run,point=point,source_label=point.code or point.name,address=point.address,phone=point.phone,time_window=request.POST.get('time_window','').strip()[:64],courier=run.assigned_courier,route_order=(last.route_order+1 if last else 1),status=Delivery.Status.IN_PROGRESS if run.assigned_courier else Delivery.Status.NEW); DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action='run_point_added',note=f'Добавлено вручную в {run.route.name} только на {run.run_date:%d.%m.%Y}'); messages.success(request,f'Добавлено: {point.name}'); return redirect('run_detail',pk=pk)

@dispatcher_required
@require_POST
def run_copy_previous(request,pk):
    run=get_object_or_404(RouteRun,pk=pk); previous=RouteRun.objects.filter(route=run.route,run_date__lt=run.run_date).order_by('-run_date').first()
    if not previous: messages.warning(request,'Предыдущий маршрут не найден'); return redirect('run_detail',pk=pk)
    if run.deliveries.filter(status=Delivery.Status.DONE).exists(): messages.warning(request,'Нельзя заменить состав: в этом дне уже есть выполненные точки'); return redirect('run_detail',pk=pk)
    source=list(previous.deliveries.select_related('point').order_by('route_order','id'))
    with transaction.atomic():
        run.deliveries.all().delete()
        for order,old in enumerate(source,start=1):
            d=Delivery.objects.create(delivery_date=run.run_date,route_run=run,point=old.point,source_label=old.source_label,address=old.address,organization=old.organization,recipient=old.recipient,phone=old.phone,comment=old.comment,time_window=old.time_window,row_color=old.row_color,courier=run.assigned_courier,route_order=order,status=Delivery.Status.IN_PROGRESS if run.assigned_courier else Delivery.Status.NEW); DeliveryEvent.objects.create(delivery=d,actor=request.user,action='copied_previous',note=f'Скопировано из маршрута {previous.run_date:%d.%m.%Y}')
    messages.success(request,f'Состав скопирован с {previous.run_date:%d.%m.%Y}: {len(source)} точек'); return redirect('run_detail',pk=pk)

@dispatcher_required
@require_POST
def run_reassign(request,pk):
    run=get_object_or_404(RouteRun,pk=pk); courier_id=request.POST.get('courier_id',''); courier=_couriers().filter(pk=courier_id).first() if courier_id else None; reassign_route_run(run,courier); messages.success(request,f'{run.route.name}: курьер изменён'); return redirect(request.POST.get('next') or f'/dispatcher/?date={run.run_date.isoformat()}')

@dispatcher_required
@require_POST
def run_delivery_move(request,pk,delivery_pk):
    run=get_object_or_404(RouteRun,pk=pk); delivery=get_object_or_404(Delivery,pk=delivery_pk,route_run=run)
    if delivery.status==Delivery.Status.DONE: messages.warning(request,'Выполненную точку изменять нельзя'); return redirect('run_detail',pk=pk)
    action=request.POST.get('direction')
    if action=='remove': delivery.delete(); messages.success(request,'Точка убрана только из этого дня'); return redirect('run_detail',pk=pk)
    items=list(run.deliveries.exclude(status=Delivery.Status.DONE).order_by('route_order','id')); idx=items.index(delivery); target=idx-1 if action=='up' else idx+1
    if 0<=target<len(items): items[idx],items[target]=items[target],items[idx]; _save_order(items)
    return redirect('run_detail',pk=pk)

@dispatcher_required
@require_POST
def run_reorder(request,pk):
    run=get_object_or_404(RouteRun,pk=pk); items=list(run.deliveries.exclude(status=Delivery.Status.DONE).order_by('route_order','id')); by_id={x.pk:x for x in items}; requested=_ids(request.POST.get('order')); ordered=[by_id[x] for x in requested if x in by_id]; ordered.extend(x for x in items if x.pk not in requested); _save_order(ordered); messages.success(request,'Порядок маршрута сохранён'); return redirect('run_detail',pk=pk)
