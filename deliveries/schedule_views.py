import json
from datetime import date
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.models import User
from .courier_admin_views import dispatcher_required, _courier_users
from .models import CourierScheduleAudit
from .schedule_services import (availability, month_bounds, month_data, mutate_schedule, replacement_warnings)


@dispatcher_required
def schedule_page(request, pk=None):
    courier = get_object_or_404(_courier_users(), pk=pk) if pk else None
    return render(request, 'dispatcher/couriers/schedule.html', {'courier': courier})


@dispatcher_required
def schedule_data(request, pk=None):
    try:
        first, last = month_bounds(request.GET.get('month'))
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    couriers = _courier_users().order_by('first_name', 'username')
    if pk:
        couriers = [get_object_or_404(couriers, pk=pk)]
    elif request.GET.get('active') == '1':
        couriers = couriers.filter(is_active=True)
    data = month_data(couriers, first, last)
    if pk:
        data['audit'] = [{'action': a.action, 'actor': (a.actor.get_full_name() or a.actor.username) if a.actor else 'Система',
            'at': a.created_at.isoformat(), 'details': a.details} for a in
            CourierScheduleAudit.objects.filter(courier_id=pk).select_related('actor').order_by('-id')[:30]]
    return JsonResponse({'ok': True, **data})


@dispatcher_required
@require_POST
def schedule_change(request, pk):
    courier = get_object_or_404(_courier_users(), pk=pk)
    if len(request.body) > 20000:
        return JsonResponse({'ok': False, 'error': 'Слишком большой запрос'}, status=400)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError('Ожидается объект запроса')
        mutate_schedule(courier, payload, request.user)
    except (ValueError, TypeError, KeyError) as exc:
        from .schedule_services import ScheduleConflict
        if isinstance(exc, ScheduleConflict):
            raise
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    return JsonResponse({'ok': True})


@dispatcher_required
def schedule_availability(request):
    try:
        day = date.fromisoformat(request.GET.get('date', str(timezone.localdate())))
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Некорректная дата'}, status=400)
    couriers = availability(_courier_users().filter(is_active=True), day)
    return JsonResponse({'ok': True, 'couriers': [{'id': c.pk, 'name': c.get_full_name() or c.username,
        'label': c.schedule_label, 'unavailable': c.schedule_unavailable} for c in couriers]})


@dispatcher_required
def schedule_warnings(request):
    return JsonResponse({'ok': True, 'warnings': replacement_warnings()})
