from functools import wraps
from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.models import User
from .forms import DeliveryForm
from .models import Delivery, DeliveryEvent, DeliveryPoint, RouteOrderSuggestion, RouteRun
from .import_services import import_workbook, preview_workbook, validate_upload, normalize_delivery_address
from .import_staging import stage_upload, consume_upload
from .point_matching import canonical_delivery_values, resolve_point
from .route_services import record_courier_order_change

PROBLEM_REASONS=('Нет доступа','Не принимают','Получатель недоступен','Неверный адрес','Нужно вернуться позже','Другая проблема')

def _format_phone(phone):
    digits=''.join(ch for ch in (phone or '') if ch.isdigit())
    if len(digits)==11 and digits[0] in '78':
        digits='7'+digits[1:]
    elif len(digits)==10:
        digits='7'+digits
    if len(digits)==11 and digits[0]=='7':
        return f'+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}'
    return phone or ''

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


def _format_duration(delta):
    if delta is None:
        return ''
    seconds=max(0,int(delta.total_seconds()))
    hours,rest=divmod(seconds,3600)
    minutes=rest//60
    if hours:
        return f'{hours} ч {minutes:02d} мин' if minutes else f'{hours} ч'
    return f'{minutes} мин' if minutes else '< 1 мин'


def _run_timing(rows, now=None, live=True):
    completed=sorted(
        (d for d in rows if d.status==Delivery.Status.DONE and d.completed_at),
        key=lambda d:d.completed_at,
    )
    if not completed:
        return {'first_done':None,'last_done':None,'duration_label':'','avg_interval_label':'','is_completed':False}
    first_done=completed[0]
    last_done=completed[-1]
    is_completed=bool(rows) and all(d.status==Delivery.Status.DONE for d in rows)
    end_at=last_done.completed_at if is_completed or not live else (now or timezone.now())
    duration=end_at-first_done.completed_at
    avg_interval=(last_done.completed_at-first_done.completed_at)/(len(completed)-1) if len(completed)>1 else None
    return {
        'first_done':first_done,
        'last_done':last_done,
        'duration_label':_format_duration(duration),
        'avg_interval_label':_format_duration(avg_interval),
        'is_completed':is_completed,
    }

@dispatcher_required
def dispatcher_dashboard(request):
    selected_date=_dashboard_date(request)
    base=Delivery.objects.filter(delivery_date=selected_date).select_related('courier','point','route_run__route')
    couriers=User.objects.filter(role=User.Role.COURIER,is_active=True,is_superuser=False).order_by('first_name','username')
    counts={key:base.filter(status=key).count() for key,_ in Delivery.Status.choices}
    route_q=request.GET.get('route_q','').strip()
    route_state=request.GET.get('route_state','').strip()
    route_sort=request.GET.get('route_sort','name').strip()
    suggestions={s.run_id:s for s in RouteOrderSuggestion.objects.filter(run__run_date=selected_date,status=RouteOrderSuggestion.Status.PENDING).select_related('courier')}
    now=timezone.now()
    runs=[]
    for run in RouteRun.objects.filter(run_date=selected_date).select_related('route','template','assigned_courier').prefetch_related('deliveries').order_by('route__name'):
        rows=list(run.deliveries.all())
        total=len(rows)
        done=sum(d.status==Delivery.Status.DONE for d in rows)
        problem=sum(d.status==Delivery.Status.PROBLEM for d in rows)
        remaining=total-done
        ordered_remaining=[d for d in sorted(rows,key=lambda x:(x.route_order,x.id)) if d.status!=Delivery.Status.DONE]
        next_stop=next((d for d in ordered_remaining if d.status!=Delivery.Status.PROBLEM),None) or (ordered_remaining[0] if ordered_remaining else None)
        timing=_run_timing(rows,now,live=selected_date==timezone.localdate())
        suggestion=suggestions.get(run.pk)
        is_completed=bool(total) and done==total
        needs_attention=bool(problem or suggestion or (not is_completed and not run.assigned_courier))
        state='completed' if is_completed else ('attention' if needs_attention else ('active' if done else 'waiting'))
        runs.append({
            'run':run,'total':total,'done':done,'remaining':remaining,'problem':problem,
            'percent':round(done*100/total) if total else 0,'order_suggestion':suggestion,
            'last_done':timing['last_done'],'first_done':timing['first_done'],'next_stop':next_stop,
            'duration_label':timing['duration_label'],'avg_interval_label':timing['avg_interval_label'],
            'state':state,'needs_attention':needs_attention,
        })
    route_count=len(runs)
    completed_routes=sum(item['state']=='completed' for item in runs)
    attention_routes=sum(item['needs_attention'] for item in runs)
    total_count=base.count()
    done_count=counts.get(Delivery.Status.DONE,0)
    completion_percent=round(done_count*100/total_count) if total_count else 0
    unrouted_count=base.filter(route_run__isnull=True).count()
    route_without_courier_count=sum(1 for item in runs if item['state']!='completed' and not item['run'].assigned_courier_id)
    problem_count=counts.get(Delivery.Status.PROBLEM,0)
    pending_order_count=len(suggestions)
    attention_count=problem_count+unrouted_count+route_without_courier_count+pending_order_count
    active_courier_count=len({item['run'].assigned_courier_id for item in runs if item['run'].assigned_courier_id})

    visible_runs=runs
    if route_q:
        needle=route_q.casefold()
        visible_runs=[item for item in visible_runs if needle in item['run'].route.name.casefold() or (item['run'].assigned_courier and needle in (item['run'].assigned_courier.get_full_name() or item['run'].assigned_courier.username).casefold())]
    if route_state:
        visible_runs=[item for item in visible_runs if item['state']==route_state]
    if route_sort=='progress':
        visible_runs=sorted(visible_runs,key=lambda item:(item['percent'],item['run'].route.name))
    elif route_sort=='attention':
        visible_runs=sorted(visible_runs,key=lambda item:(item['state']!='attention',-item['problem'],item['run'].route.name))
    elif route_sort=='courier':
        visible_runs=sorted(visible_runs,key=lambda item:((item['run'].assigned_courier.get_full_name() or item['run'].assigned_courier.username) if item['run'].assigned_courier else 'яяя',item['run'].route.name))

    return render(request,'dispatcher/dashboard.html',{
        'total_count':total_count,'couriers':couriers,'counts':counts,'today':timezone.localdate(),
        'selected_date':selected_date,'prev_date':selected_date-timedelta(days=1),'next_date':selected_date+timedelta(days=1),
        'route_runs':visible_runs,'route_count':route_count,'completed_routes':completed_routes,
        'attention_routes':attention_routes,'completion_percent':completion_percent,
        'route_filters':{'q':route_q,'state':route_state,'sort':route_sort},
        'unrouted_count':unrouted_count,'route_without_courier_count':route_without_courier_count,
        'pending_order_count':pending_order_count,'problem_count':problem_count,'attention_count':attention_count,
        'active_courier_count':active_courier_count,
    })


@dispatcher_required
def dispatcher_deliveries(request):
    selected_date=_dashboard_date(request)
    base=Delivery.objects.filter(delivery_date=selected_date).select_related('courier','point','route_run__route')
    deliveries=base
    q=request.GET.get('q','').strip()
    kind=request.GET.get('kind','').strip()
    status=request.GET.get('status','').strip()
    courier_filter=request.GET.get('courier','').strip()
    unrouted=request.GET.get('unrouted','')=='1'
    route_filter=request.GET.get('route','').strip()
    if q:
        deliveries=deliveries.filter(Q(source_label__icontains=q)|Q(address__icontains=q)|Q(phone__icontains=q)|Q(organization__icontains=q)|Q(recipient__icontains=q))
    if kind:
        deliveries=deliveries.filter(point__kind=kind)
    if status:
        deliveries=deliveries.filter(status=status)
    if unrouted:
        deliveries=deliveries.filter(route_run__isnull=True)
    if courier_filter=='unassigned':
        deliveries=deliveries.filter(courier__isnull=True)
    elif courier_filter.isdigit():
        deliveries=deliveries.filter(courier_id=int(courier_filter))
    if route_filter.isdigit():
        deliveries=deliveries.filter(route_run_id=int(route_filter))
    deliveries=list(deliveries.order_by('route_run__route__name','courier_id','route_order','id'))
    couriers=User.objects.filter(role=User.Role.COURIER,is_active=True,is_superuser=False).order_by('first_name','username')
    runs=RouteRun.objects.filter(run_date=selected_date).select_related('route','assigned_courier').order_by('route__name')
    return render(request,'dispatcher/deliveries.html',{
        'deliveries':deliveries,'total_count':base.count(),'couriers':couriers,'runs':runs,
        'row_colors':Delivery.RowColor.choices,'point_kinds':DeliveryPoint.Kind.choices,'statuses':Delivery.Status.choices,
        'today':timezone.localdate(),'selected_date':selected_date,'prev_date':selected_date-timedelta(days=1),'next_date':selected_date+timedelta(days=1),
        'filters':{'q':q,'kind':kind,'status':status,'courier':courier_filter,'unrouted':unrouted,'route':route_filter},
    })


def _resolve_courier(courier_id):
    if not courier_id: return None
    return get_object_or_404(User,pk=courier_id,role=User.Role.COURIER,is_active=True,is_superuser=False)

def _assign(delivery,courier,actor,action='assigned'):
    old=delivery.courier; delivery.courier=courier
    if courier and delivery.status==Delivery.Status.NEW: delivery.status=Delivery.Status.IN_PROGRESS
    elif not courier and delivery.status==Delivery.Status.IN_PROGRESS: delivery.status=Delivery.Status.NEW
    delivery.save(update_fields=['courier','status','updated_at']); DeliveryEvent.objects.create(delivery=delivery,actor=actor,action=action,note=f'{old or "—"} → {courier or "—"}')

@dispatcher_required
@require_POST
def dispatcher_assign(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk)
    courier=_resolve_courier(request.POST.get('courier_id',''))
    _assign(delivery,courier,request.user)
    if request.headers.get('x-requested-with')=='XMLHttpRequest':
        return JsonResponse({'ok':True,'delivery_id':delivery.pk,'courier':(courier.get_full_name() or courier.username) if courier else ''})
    return redirect(f'/dispatcher/deliveries/?date={delivery.delivery_date.isoformat()}')


@dispatcher_required
@require_POST
def dispatcher_bulk_assign(request):
    ids=request.POST.getlist('delivery_ids')
    courier=_resolve_courier(request.POST.get('courier_id',''))
    deliveries=list(Delivery.objects.filter(pk__in=ids).exclude(status=Delivery.Status.DONE))
    with transaction.atomic():
        for delivery in deliveries:
            _assign(delivery,courier,request.user,'bulk_assigned')
    if request.headers.get('x-requested-with')=='XMLHttpRequest':
        return JsonResponse({'ok':True,'updated':len(deliveries)})
    if ids:
        messages.success(request,f'Обновлено точек: {len(deliveries)}')
    else:
        messages.warning(request,'Сначала отметьте точки')
    day=request.POST.get('date','').strip()
    return redirect(f'/dispatcher/deliveries/?date={day}' if day else 'dispatcher_deliveries')

@dispatcher_required
@require_POST
def dispatcher_quick_edit(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk); changed=[]; label=request.POST.get('source_label','').strip()[:255]; address=normalize_delivery_address(request.POST.get('address',''))[:500]; phone=request.POST.get('phone','').strip()[:64]
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
    today=timezone.localdate()
    deliveries=list(Delivery.objects.filter(delivery_date=today,courier=request.user).select_related('point','route_run__route','route_run__template').order_by('route_run__created_at','route_order','id'))
    # Keep each RouteRun contiguous. Active/new trips come first, while fully
    # completed trips remain below as today's history instead of blocking work.
    run_active={}
    for d in deliveries:
        key=d.route_run_id or 0
        run_active[key]=run_active.get(key,False) or d.status!=Delivery.Status.DONE
    deliveries.sort(key=lambda d:(0 if run_active.get(d.route_run_id or 0) else 1, -(d.route_run.created_at.timestamp() if d.route_run_id else 0), d.route_order, d.id))
    for d in deliveries:
        d.phone_display=_format_phone(d.phone)
    done=sum(d.status==Delivery.Status.DONE for d in deliveries)
    unfinished=[d for d in deliveries if d.status!=Delivery.Status.DONE]
    selected_id=request.GET.get('selected','').strip()
    selected_delivery=next((d for d in unfinished if str(d.pk)==selected_id),None)
    if not selected_delivery:
        selected_delivery=next((d for d in unfinished if d.status!=Delivery.Status.PROBLEM),None) or (unfinished[0] if unfinished else None)

    # The selected workspace belongs to one concrete trip. Do not mix progress
    # or previous/next navigation with an earlier RouteRun from the same day.
    selected_run_id=selected_delivery.route_run_id if selected_delivery else None
    current_run_deliveries=[d for d in deliveries if d.route_run_id==selected_run_id] if selected_run_id else ([d for d in deliveries if not d.route_run_id] if selected_delivery else [])
    current_run_unfinished=[d for d in current_run_deliveries if d.status!=Delivery.Status.DONE]
    current_run_done=sum(d.status==Delivery.Status.DONE for d in current_run_deliveries)
    current_run_total=len(current_run_deliveries)
    selectable=current_run_unfinished
    selected_index=selectable.index(selected_delivery) if selected_delivery in selectable else -1
    previous_delivery=selectable[selected_index-1] if selected_index>0 else None
    next_delivery=selectable[selected_index+1] if 0<=selected_index<len(selectable)-1 else None
    route_runs=[]
    seen=set()
    for delivery in deliveries:
        if delivery.route_run_id and delivery.route_run_id not in seen:
            seen.add(delivery.route_run_id); route_runs.append(delivery.route_run)
    active_deliveries=[d for d in deliveries if run_active.get(d.route_run_id or 0)]
    completed_deliveries=[d for d in deliveries if not run_active.get(d.route_run_id or 0)]
    completed_run_ids={d.route_run_id for d in completed_deliveries if d.route_run_id}
    completed_runs_count=len(completed_run_ids)
    active_runs=[run for run in route_runs if run.pk not in completed_run_ids]
    route_name=' + '.join(run.route.name for run in active_runs) if active_runs else ('Мой маршрут' if completed_deliveries else ('Без маршрута' if deliveries else ''))
    return render(request,'courier/today.html',{'deliveries':deliveries,'active_deliveries':active_deliveries,'completed_deliveries':completed_deliveries,'completed_runs_count':completed_runs_count,'done':done,'total':len(deliveries),'current_run_done':current_run_done,'current_run_total':current_run_total,'today':today,'selected_delivery':selected_delivery,'previous_delivery':previous_delivery,'next_delivery':next_delivery,'route_name':route_name,'route_runs':route_runs,'problem_reasons':PROBLEM_REASONS})

@login_required
@require_POST
def courier_update(request,pk):
    delivery=get_object_or_404(Delivery,pk=pk,courier=request.user); action=request.POST.get('action')
    if action=='done' and delivery.status==Delivery.Status.DONE: return redirect('courier_today')
    if action=='done': delivery.status=Delivery.Status.DONE; delivery.completed_at=timezone.now(); delivery.completed_latitude=request.POST.get('latitude') or None; delivery.completed_longitude=request.POST.get('longitude') or None; delivery.problem_reason=''; note='Выполнено' + (' · GPS получен' if delivery.completed_latitude and delivery.completed_longitude else ' · без GPS')
    elif action=='reopen':
        if delivery.status!=Delivery.Status.DONE: return redirect('courier_today')
        delivery.status=Delivery.Status.IN_PROGRESS; delivery.completed_at=None; delivery.completed_latitude=None; delivery.completed_longitude=None; delivery.problem_reason=''; note='Возвращено в работу'
    elif action=='problem': reason=request.POST.get('problem_reason','').strip(); comment=request.POST.get('problem_comment','').strip()[:255]; reason=reason if reason in PROBLEM_REASONS else 'Другая проблема'; delivery.status=Delivery.Status.PROBLEM; delivery.problem_reason=(f'{reason}: {comment}' if comment else reason)[:255]; note=delivery.problem_reason
    elif action=='phone':
        delivery.phone=request.POST.get('phone','').strip()[:64]
        if delivery.point_id:
            now=timezone.now()
            DeliveryPoint.objects.filter(pk=delivery.point_id).update(phone=delivery.phone,updated_at=now)
            Delivery.objects.filter(point_id=delivery.point_id).exclude(pk=delivery.pk).update(phone=delivery.phone,updated_at=now)
        note=f'Телефон точки: {delivery.phone or "удалён"}'
    elif action=='daily_note': delivery.courier_daily_note=request.POST.get('courier_daily_note','').strip()[:500]; note=('Заметка на сегодня: '+delivery.courier_daily_note) if delivery.courier_daily_note else 'Заметка на сегодня удалена'
    else: raise PermissionDenied
    delivery.save(); DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action=action,note=note)
    if request.headers.get('x-requested-with')=='XMLHttpRequest': return JsonResponse({'ok':True,'delivery_id':delivery.pk,'action':action,'status':delivery.status})
    return redirect('courier_today')

@login_required
@require_POST
def courier_reorder(request,pk):
    delivery=get_object_or_404(Delivery.objects.select_related('route_run__template'),pk=pk,courier=request.user,delivery_date=timezone.localdate()); direction=request.POST.get('direction')
    wants_json=request.headers.get('x-requested-with')=='XMLHttpRequest'
    if delivery.route_run_id:
        full_items=list(Delivery.objects.filter(route_run_id=delivery.route_run_id,courier=request.user,delivery_date=delivery.delivery_date).order_by('route_order','id')); run=delivery.route_run
    else:
        full_items=list(Delivery.objects.filter(route_run__isnull=True,courier=request.user,delivery_date=delivery.delivery_date).order_by('route_order','id')); run=None
    items=[item for item in full_items if item.status!=Delivery.Status.DONE]
    try: index=items.index(delivery)
    except ValueError: return redirect('courier_today')
    target=index-1 if direction=='up' else index+1
    if direction not in ('up','down'): return redirect('courier_today')
    if 0<=target<len(items):
        other=items[target]
        before=[item.point_id for item in full_items if item.point_id]
        old_order,other_order=delivery.route_order,other.route_order
        with transaction.atomic():
            # Swap only the two unfinished positions. Completed rows and every unrelated
            # delivery keep their exact route_order, so the route cannot "shuffle".
            delivery.route_order,other.route_order=other_order,old_order
            delivery.save(update_fields=['route_order'])
            other.save(update_fields=['route_order'])
            if run:
                after_rows=Delivery.objects.filter(route_run_id=run.pk,courier=request.user,delivery_date=delivery.delivery_date).order_by('route_order','id')
                after=[item.point_id for item in after_rows if item.point_id]
                record_courier_order_change(run,request.user,before,after)
        DeliveryEvent.objects.create(delivery=delivery,actor=request.user,action='reordered',note=f'Позиция {old_order} → {other_order}')
        if wants_json:
            return JsonResponse({'ok':True,'moved_id':delivery.pk,'other_id':other.pk,'direction':direction,'moved_order':delivery.route_order,'other_order':other.route_order})
    if wants_json:
        return JsonResponse({'ok':False,'error':'Точку нельзя переместить дальше'},status=409)
    return redirect(f"{redirect('courier_today').url}?selected={delivery.pk}")
