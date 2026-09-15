from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
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
    return render(request, 'dispatcher/dashboard.html', {'deliveries': deliveries, 'counts': counts, 'today': today})

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
