from functools import wraps
from datetime import datetime
from io import BytesIO
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import load_workbook
from accounts.models import User
from .forms import DeliveryForm
from .models import Delivery, DeliveryEvent

def dispatcher_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_dispatcher:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped

@login_required
def home(request):
    return redirect('dispatcher_dashboard' if request.user.is_dispatcher else 'courier_today')

@dispatcher_required
def dispatcher_dashboard(request):
    today = timezone.localdate()
    deliveries = Delivery.objects.filter(delivery_date=today).select_related('courier')
    counts = {key: deliveries.filter(status=key).count() for key, _ in Delivery.Status.choices}
    courier_stats = []
    for courier in User.objects.filter(role=User.Role.COURIER, is_active=True).order_by('first_name','username'):
        qs = deliveries.filter(courier=courier)
        courier_stats.append({'courier': courier, 'total': qs.count(), 'done': qs.filter(status=Delivery.Status.DONE).count(), 'problem': qs.filter(status=Delivery.Status.PROBLEM).count()})
    return render(request, 'dispatcher/dashboard.html', {'deliveries': deliveries, 'counts': counts, 'courier_stats': courier_stats, 'today': today})

@dispatcher_required
def delivery_create(request):
    form = DeliveryForm(request.POST or None, initial={'delivery_date': timezone.localdate()})
    if request.method == 'POST' and form.is_valid():
        delivery = form.save()
        DeliveryEvent.objects.create(delivery=delivery, actor=request.user, action='created')
        return redirect('dispatcher_dashboard')
    return render(request, 'dispatcher/delivery_form.html', {'form': form, 'title': 'Новая заявка'})

@dispatcher_required
def delivery_edit(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    form = DeliveryForm(request.POST or None, instance=delivery)
    if request.method == 'POST' and form.is_valid():
        form.save()
        DeliveryEvent.objects.create(delivery=delivery, actor=request.user, action='edited')
        return redirect('dispatcher_dashboard')
    return render(request, 'dispatcher/delivery_form.html', {'form': form, 'title': 'Редактирование заявки'})

@dispatcher_required
def import_excel(request):
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            wb = load_workbook(BytesIO(request.FILES['file'].read()), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                raise ValueError('Файл пуст')
            headers = [str(v or '').strip().lower() for v in rows[0]]
            aliases = {'адрес':'address','address':'address','организация':'organization','получатель':'recipient','телефон':'phone','комментарий':'comment','курьер':'courier','порядок':'route_order','дата':'delivery_date'}
            columns = {aliases[h]: i for i, h in enumerate(headers) if h in aliases}
            if 'address' not in columns:
                raise ValueError('Не найдена колонка «Адрес»')
            created = 0
            with transaction.atomic():
                for number, row in enumerate(rows[1:], start=1):
                    address = str(row[columns['address']] or '').strip()
                    if not address:
                        continue
                    courier = None
                    if 'courier' in columns and row[columns['courier']]:
                        name = str(row[columns['courier']]).strip()
                        courier = User.objects.filter(role=User.Role.COURIER, username__iexact=name).first()
                    date = timezone.localdate()
                    if 'delivery_date' in columns and row[columns['delivery_date']]:
                        raw = row[columns['delivery_date']]
                        if isinstance(raw, datetime): date = raw.date()
                        elif hasattr(raw, 'year'): date = raw
                    def value(key):
                        return str(row[columns[key]] or '').strip() if key in columns else ''
                    order = number
                    if 'route_order' in columns and row[columns['route_order']] is not None:
                        try: order = int(row[columns['route_order']])
                        except (TypeError, ValueError): pass
                    d = Delivery.objects.create(delivery_date=date,address=address,organization=value('organization'),recipient=value('recipient'),phone=value('phone'),comment=value('comment'),courier=courier,route_order=order)
                    DeliveryEvent.objects.create(delivery=d, actor=request.user, action='imported')
                    created += 1
            messages.success(request, f'Импортировано заявок: {created}')
            return redirect('dispatcher_dashboard')
        except Exception as exc:
            messages.error(request, f'Не удалось импортировать файл: {exc}')
    return render(request, 'dispatcher/import_excel.html')

@login_required
def courier_today(request):
    if request.user.is_dispatcher:
        return redirect('dispatcher_dashboard')
    today = timezone.localdate()
    deliveries = Delivery.objects.filter(delivery_date=today, courier=request.user).order_by('route_order','id')
    done = deliveries.filter(status=Delivery.Status.DONE).count()
    return render(request, 'courier/today.html', {'deliveries': deliveries, 'done': done, 'total': deliveries.count(), 'today': today})

@login_required
@require_POST
def courier_update(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk, courier=request.user)
    action = request.POST.get('action')
    if action == 'done':
        delivery.status = Delivery.Status.DONE
        delivery.completed_at = timezone.now()
        delivery.completed_latitude = request.POST.get('latitude') or None
        delivery.completed_longitude = request.POST.get('longitude') or None
    elif action == 'problem':
        delivery.status = Delivery.Status.PROBLEM
        delivery.problem_reason = request.POST.get('problem_reason','Другая проблема')[:255]
    elif action == 'phone':
        delivery.phone = request.POST.get('phone','')[:64]
    else:
        raise PermissionDenied
    delivery.save()
    DeliveryEvent.objects.create(delivery=delivery, actor=request.user, action=action)
    return redirect('courier_today')

@login_required
@require_POST
def courier_reorder(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk, courier=request.user, delivery_date=timezone.localdate())
    direction = request.POST.get('direction')
    qs = Delivery.objects.filter(courier=request.user, delivery_date=delivery.delivery_date).exclude(status=Delivery.Status.DONE).order_by('route_order','id')
    items = list(qs)
    try: index = items.index(delivery)
    except ValueError: return redirect('courier_today')
    target = index - 1 if direction == 'up' else index + 1
    if 0 <= target < len(items):
        other = items[target]
        delivery.route_order, other.route_order = other.route_order, delivery.route_order
        if delivery.route_order == other.route_order:
            delivery.route_order, other.route_order = target + 1, index + 1
        delivery.save(update_fields=['route_order'])
        other.save(update_fields=['route_order'])
        DeliveryEvent.objects.create(delivery=delivery, actor=request.user, action='reordered')
    return redirect('courier_today')
