from functools import wraps
from datetime import date, timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.models import User
from .forms import DeliveryForm
from .models import Delivery, DeliveryEvent, DeliveryPoint, RouteRun
from .import_services import import_workbook, preview_workbook, validate_upload
from .import_staging import stage_upload, consume_upload
from .point_matching import canonical_delivery_values, resolve_point
from .map_data import delivery_map_items

PROBLEM_REASONS=('Нет доступа','Не принимают','Получатель недоступен','Неверный адрес','Нужно вернуться позже','Другая проблема')

def dispatcher_required(view):
    @wraps(view)
    @login_required
    def wrapped(request,*args,**kwargs):
        if not request.user.is_dispatcher: raise PermissionDenied
        return view(request,*args,**kwargs)
    return wrapped

@login_required
def home(request): return redirect('dispatcher_dashboard' if request.user.is_dispatcher else 'courier_today')

def _dashboard_date(request):
    raw=request.GET.get('date','').strip()
    if raw:
        try: return date.fromisoformat(raw)
        except ValueError: pass
    return timezone.localdate()

@dispatcher_required
def dispatcher_dashboard(request):
    selected_date=_dashboard_date(request); base=Delivery.objects.filter(delivery_date=selected_date).select_related('courier','point','route_run__route'); deliveries=base
    q=request.GET.get('q','').strip(); kind=request.GET.get('kind','').strip(); status=request.GET.get('status','').strip(); courier_filter=request.GET.get('courier','').strip()
    if q: deliveries=deliveries.filter(Q(source_label__icontains=q)|Q(address__icontains=q)|Q(phone__icontains=q)|Q(organization__icontains=q)|Q(recipient__icontains=q))
    if kind: deliveries=deliveries.filter(point__kind=kind)
    if status: deliveries=deliveries.filter(status=status)
    if courier_filter=='unassigned': deliveries=deliveries.filter(courier__isnull=True)
    elif courier_filter.isdigit(): deliveries=deliveries.filter(courier_id=int(courier_filter))
    deliveries=list(deliveries.order_by('route_run__route__name','courier_id','route_order','id')); couriers=User.objects.filter(role=User.Role.COURIER,is_active=True).order_by('first_name','username'); counts={key:base.filter(status=key).count() for key,_ in Delivery.Status.choices}; courier_stats=[]
    for courier in couriers:
        qs=base.filter(courier=courier); courier_stats.append({'courier':courier,'total':qs.count(),'done':qs.filter(status=Delivery.Status.DONE).count(),'problem':qs.filter(status=Delivery.Status.PROBLEM).count()})
    runs=[]
    for run in RouteRun.objects.filter(run_date=selected_date).select_related('route','template','assigned_courier').prefetch_related('deliveries').order_by('route__name'):
        rows=list(run.deliveries.all()); total=len(rows); done=sum(d.status==Delivery.Status.DONE for d in rows); problem=sum(d.status==Delivery.Status.PROBLEM for d in rows); runs.append({'run':run,'total':total,'done':done,'problem':problem,'percent':round(done*100/total) if total else 0})
    return render(request,'dispatcher/dashboard.html',{'deliveries':deliveries,'total_count':base.count(),'couriers':couriers,'row_colors':Delivery.RowColor.choices,'point_kinds':DeliveryPoint.Kind.choices,'statuses':Delivery.Status.choices,'counts':counts,'courier_stats':courier_stats,'today':timezone.localdate(),'selected_date':selected_date,'prev_date':selected_date-timedelta(days=1),'next_date':selected_date+timedelta(days=1),'route_runs':runs,'filters':{'q':q,'kind':kind,'status':status,'courier':courier_filter},'map_points':delivery_map_items(deliveries),'yandex_maps_api_key':settings.YANDEX_MAPS_JS_API_KEY})

def _resolve_courier(courier_id):
    if not courier_id: return None
    return get_object_or_404(User,pk=courier_id,role=User.Role.COURIER,is_active=True)

def _assign(delivery,courier,actor,action='assigned'):
    old=delivery.courier; delivery.courier=courier
    if courier and delivery.status==Delivery.Status.NEW: delivery.status=Delivery.Status.IN_PROGRESS
    elif not courier and delivery.status==Delivery.Status.IN_PROGRESS: delivery.status=Delivery.Status.NEW
    delivery.save(update_fields=['courier','status','updated_at']); DeliveryEvent.objects.create(delivery=delivery,actor=actor,action=action,note=f'{old or "—"} → {courier or "—"}')

@dispatcher_required
@require_POST
def dispatcher_assign(request,pk): _assign(get_object_or_404(Delivery,pk=pk),_resolve_courier(request.POST.get('courier_id','')),request.user); return redirect('dispatcher_dashboard')

@dispatcher_required
@require_POST
def dispatcher_bulk_assign(request):
    ids=request.POST.getlist('delivery_ids'); courier=_resolve_courier(request.POST.get('courier_id','')); deliveries=Delivery.objects.filter(pk__in=ids).exclude(status=Delivery.Status.DONE)
    with transaction.atomic():
        for delivery in deliveries: _assign(delivery,courier,request.user,'bulk_assigned')
    messages.success(request,f'Обновлено точек: {deliveries.count()}') if ids else messages.warning(request,'Сначала отметьте точки'); return redirect('dispatcher_dashboard')

@dispatcher_required
@require_POST
def dispatcher_quick_edit(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk); changed=[]; label=request.POST.get('source_label','').strip()[:255]; address=request.POST.get('address','').strip()[:500]; phone=request.POST.get('phone','').strip()[:64]
    if not address: messages.error(request,'Адрес не может быть пустым'); return redirect('dispatcher_dashboard')
    match=resolve_point(label,address,phone,create=True); canonical=canonical_delivery_values(match.point,label,address,phone); values={'point':match.point,'source_label':canonical['source_label'],'address':canonical['address'],'time_window':request.POST.get('time_window','').strip()[:64],'phone':canonical['phone'],'row_color':request.POST.get('row_color','')}; allowed_colors={v for v,_ in Delivery.RowColor.choices}
    if values['row_color'] not in allowed_colors: values['row_color']=''
    for field,value in values.items():
        if getattr(delivery,field)!=value: setattr(delivery,field,value); changed.append(field)
    if changed: delivery.save(update_fields=changed+['updated_at']); DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action='quick_edited',note=', '.join(changed))
    return redirect(f'/dispatcher/?date={delivery.delivery_date.isoformat()}')

@dispatcher_required
def delivery_create(request):
    form=DeliveryForm(request.POST or None,initial={'delivery_date':timezone.localdate()})
    if request.method=='POST' and form.is_valid(): delivery=form.save(); DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action='created'); return redirect('dispatcher_dashboard')
    return render(request,'dispatcher/delivery_form.html',{'form':form,'title':'Новая заявка'})

@dispatcher_required
def delivery_edit(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk); form=DeliveryForm(request.POST or None,instance=delivery)
    if request.method=='POST' and form.is_valid(): form.save(); DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action='edited'); return redirect('dispatcher_dashboard')
    return render(request,'dispatcher/delivery_form.html',{'form':form,'title':'Редактирование заявки'})

@dispatcher_required
def delivery_history(request,pk): delivery=get_object_or_404(Delivery.objects.select_related('courier','point','route_run__route'),pk=pk); events=delivery.events.select_related('actor').order_by('-created_at'); return render(request,'dispatcher/delivery_history.html',{'delivery':delivery,'events':events})

@dispatcher_required
def import_excel(request):
    summary=None; preview_token=''; filename=''
    if request.method=='POST':
        try:
            if request.POST.get('action')=='commit':
                filename,content=consume_upload(request.POST.get('token',''),request.user.pk); validate_upload(filename,content); summary=import_workbook(content,request.user); messages.success(request,f'Импорт завершён: создано {summary.created}; распознано {summary.matched}; новых точек {summary.new_points}; пропущено {summary.skipped}')
            elif request.FILES.get('file'):
                uploaded=request.FILES['file']; content=uploaded.read(); filename=uploaded.name; validate_upload(filename,content); summary=preview_workbook(content); preview_token=stage_upload(content,request.user.pk,filename)
            else: messages.error(request,'Выберите XLSX-файл')
        except Exception as exc: messages.error(request,f'Не удалось обработать файл: {exc}')
    return render(request,'dispatcher/import_excel.html',{'summary':summary,'preview_token':preview_token,'filename':filename})

@login_required
def courier_today(request):
    if request.user.is_dispatcher: return redirect('dispatcher_dashboard')
    today=timezone.localdate(); deliveries=list(Delivery.objects.filter(delivery_date=today,courier=request.user).select_related('point','route_run__route').order_by('route_order','id')); done=sum(d.status==Delivery.Status.DONE for d in deliveries); next_delivery=next((d for d in deliveries if d.status not in (Delivery.Status.DONE,Delivery.Status.PROBLEM)),None) or next((d for d in deliveries if d.status!=Delivery.Status.DONE),None); return render(request,'courier/today.html',{'deliveries':deliveries,'done':done,'total':len(deliveries),'today':today,'next_delivery':next_delivery,'problem_reasons':PROBLEM_REASONS,'map_points':delivery_map_items(deliveries),'yandex_maps_api_key':settings.YANDEX_MAPS_JS_API_KEY})

@login_required
@require_POST
def courier_update(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk,courier=request.user); action=request.POST.get('action')
    if action=='done': delivery.status=Delivery.Status.DONE; delivery.completed_at=timezone.now(); delivery.completed_latitude=request.POST.get('latitude') or None; delivery.completed_longitude=request.POST.get('longitude') or None; delivery.problem_reason=''; note='Выполнено' + (' · GPS получен' if delivery.completed_latitude and delivery.completed_longitude else ' · без GPS')
    elif action=='problem': reason=request.POST.get('problem_reason','').strip(); comment=request.POST.get('problem_comment','').strip()[:255]; reason=reason if reason in PROBLEM_REASONS else 'Другая проблема'; delivery.status=Delivery.Status.PROBLEM; delivery.problem_reason=(f'{reason}: {comment}' if comment else reason)[:255]; note=delivery.problem_reason
    elif action=='phone': delivery.phone=request.POST.get('phone','').strip()[:64]; note=f'Телефон: {delivery.phone}'
    else: raise PermissionDenied
    delivery.save(); DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action=action,note=note); return redirect('courier_today')

@login_required
@require_POST
def courier_reorder(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk,courier=request.user,delivery_date=timezone.localdate()); direction=request.POST.get('direction'); items=list(Delivery.objects.filter(courier=request.user,delivery_date=delivery.delivery_date).exclude(status=Delivery.Status.DONE).order_by('route_order','id'))
    try: index=items.index(delivery)
    except ValueError: return redirect('courier_today')
    target=index-1 if direction=='up' else index+1
    if 0<=target<len(items):
        items[index],items[target]=items[target],items[index]
        with transaction.atomic():
            for pos,item in enumerate(items,start=1):
                if item.route_order!=pos: item.route_order=pos; item.save(update_fields=['route_order'])
        DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action='reordered',note=f'{index+1} → {target+1}')
    return redirect('courier_today')
