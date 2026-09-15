from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from accounts.models import User
from .models import DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem
from .route_services import generate_route_run, reassign_route_run


def dispatcher_required(view):
    @login_required
    def wrapped(request,*args,**kwargs):
        if not request.user.is_dispatcher: raise PermissionDenied
        return view(request,*args,**kwargs)
    return wrapped

@dispatcher_required
def route_list(request):
    routes=Route.objects.filter(is_active=True).select_related('default_courier').prefetch_related('templates')
    return render(request,'dispatcher/routes/list.html',{'routes':routes})

@dispatcher_required
def route_edit(request,pk=None):
    route=get_object_or_404(Route,pk=pk) if pk else None
    couriers=User.objects.filter(role=User.Role.COURIER,is_active=True).order_by('first_name','username')
    if request.method=='POST':
        name=request.POST.get('name','').strip()[:120]
        if not name:
            messages.error(request,'Укажите название маршрута')
        else:
            courier_id=request.POST.get('default_courier','')
            courier=couriers.filter(pk=courier_id).first() if courier_id else None
            route=route or Route()
            route.name=name; route.default_courier=courier; route.notes=request.POST.get('notes','').strip(); route.save()
            if not route.templates.exists():
                RouteTemplate.objects.create(route=route,kind=RouteTemplate.Kind.WEEKDAY)
                RouteTemplate.objects.create(route=route,kind=RouteTemplate.Kind.WEEKEND)
            messages.success(request,'Маршрут сохранён')
            return redirect('route_detail',pk=route.pk)
    return render(request,'dispatcher/routes/route_form.html',{'route':route,'couriers':couriers})

@dispatcher_required
def route_detail(request,pk):
    route=get_object_or_404(Route,pk=pk)
    templates=route.templates.filter(is_active=True)
    template_id=request.GET.get('template')
    template=templates.filter(pk=template_id).first() if template_id else templates.order_by('kind','id').first()
    points=DeliveryPoint.objects.filter(is_active=True).order_by('kind','name')
    couriers=User.objects.filter(role=User.Role.COURIER,is_active=True).order_by('first_name','username')
    return render(request,'dispatcher/routes/detail.html',{'route':route,'templates':templates,'template':template,'points':points,'couriers':couriers})

@dispatcher_required
@require_POST
def template_add_point(request,pk):
    template=get_object_or_404(RouteTemplate,pk=pk)
    point=get_object_or_404(DeliveryPoint,pk=request.POST.get('point_id'),is_active=True)
    last=template.items.order_by('-route_order').first()
    item,created=RouteTemplateItem.objects.get_or_create(template=template,point=point,defaults={'route_order':(last.route_order+1 if last else 1)})
    if not created: item.enabled_by_default=True; item.save(update_fields=['enabled_by_default'])
    return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')

@dispatcher_required
@require_POST
def template_item_update(request,pk):
    item=get_object_or_404(RouteTemplateItem.objects.select_related('template'),pk=pk)
    action=request.POST.get('action')
    if action=='toggle':
        item.enabled_by_default=not item.enabled_by_default; item.save(update_fields=['enabled_by_default'])
    elif action in ('up','down'):
        items=list(item.template.items.order_by('route_order','id')); idx=items.index(item); target=idx-1 if action=='up' else idx+1
        if 0<=target<len(items):
            items[idx],items[target]=items[target],items[idx]
            with transaction.atomic():
                for pos,current in enumerate(items,start=1):
                    if current.route_order!=pos: current.route_order=pos; current.save(update_fields=['route_order'])
    elif action=='edit':
        item.time_window=request.POST.get('time_window','').strip()[:64]; item.comment=request.POST.get('comment','').strip()[:255]; item.save(update_fields=['time_window','comment'])
    elif action=='remove':
        item.delete()
    return redirect(f'/dispatcher/routes/{item.template.route_id}/?template={item.template_id}')

@dispatcher_required
@require_POST
def route_generate(request,pk):
    route=get_object_or_404(Route,pk=pk)
    template=get_object_or_404(RouteTemplate,pk=request.POST.get('template_id'),route=route)
    try: run_date=date.fromisoformat(request.POST.get('run_date',''))
    except ValueError:
        messages.error(request,'Некорректная дата'); return redirect('route_detail',pk=pk)
    courier_id=request.POST.get('courier_id',''); courier=User.objects.filter(pk=courier_id,role=User.Role.COURIER,is_active=True).first() if courier_id else route.default_courier
    enabled=request.POST.getlist('enabled_items')
    run=generate_route_run(template,run_date,courier=courier,enabled_item_ids=enabled)
    messages.success(request,f'{route.name}: сформировано {run.deliveries.count()} точек на {run_date:%d.%m.%Y}')
    return redirect('dispatcher_dashboard')

@dispatcher_required
@require_POST
def run_reassign(request,pk):
    run=get_object_or_404(RouteRun,pk=pk)
    courier_id=request.POST.get('courier_id','')
    courier=User.objects.filter(pk=courier_id,role=User.Role.COURIER,is_active=True).first() if courier_id else None
    reassign_route_run(run,courier); messages.success(request,f'{run.route.name}: курьер изменён')
    return redirect('dispatcher_dashboard')
