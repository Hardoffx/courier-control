"""Courier-owned scheduling, bounded batch reads and durable assignment evidence."""
import calendar
from collections import defaultdict
from contextvars import ContextVar
from datetime import date, timedelta

from django.db import transaction
from django.db.models import F, Max, Count
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import CourierAssignment, CourierDayOff, CourierScheduleAudit, Delivery, Route, RouteRun

schedule_actor = ContextVar('schedule_actor', default=None)
LABELS = {'worked': 'Отработано', 'off': 'Выходной', 'shift': 'Смена', 'unplanned': 'Без плана',
          'outside': 'Вне учёта', 'conflict': 'Конфликт'}


class ScheduleConflict(ValueError):
    def __init__(self, message, courier=None, day=None):
        super().__init__(message)
        self.courier = courier
        self.day = day

    def payload(self):
        result = {'ok': False, 'error': str(self)}
        if self.courier:
            result['schedule_url'] = reverse('courier_schedule', args=[self.courier.pk]) + (f'?month={self.day:%Y-%m}&date={self.day}' if self.day else '')
        return result


def audit(courier_id, action, details, actor=None, request_id=None):
    return CourierScheduleAudit.objects.create(courier_id=courier_id, action=action,
        details=details, actor=actor or schedule_actor.get(), request_id=request_id)


def lock_courier(courier_id):
    # First write serializes SQLite writers; row lock alone is ineffective on SQLite.
    User.objects.filter(pk=courier_id).update(schedule_revision=F('schedule_revision') + 1)
    return User.objects.get(pk=courier_id)


def require_available(courier_id, day):
    if not courier_id:
        return
    courier = lock_courier(courier_id)
    if courier.role != User.Role.COURIER or courier.is_superuser:
        raise ScheduleConflict('Выберите курьера', courier, day)
    if courier.tracking_end_date and day > courier.tracking_end_date:
        raise ScheduleConflict('Дата за пределами периода работы курьера. Проверьте границы учёта.', courier, day)
    if CourierDayOff.objects.filter(courier_id=courier_id, date=day, active=True).exists():
        name = courier.get_full_name() or courier.username
        raise ScheduleConflict(f'У курьера {name} {day:%d.%m.%Y} запланирован выходной', courier, day)


def _evidence(run):
    if not run.assigned_courier_id:
        return
    row, created = CourierAssignment.objects.get_or_create(courier_id=run.assigned_courier_id,
        date=run.run_date, source_run_id=run.pk,
        defaults={'run': run, 'route_name': run.route.name, 'frozen': run.run_date < timezone.localdate()})
    if not created and not row.active and not row.frozen:
        row.active = True
        row.run = run
        row.save(update_fields=['active', 'run', 'updated_at'])
    if created:
        audit(run.assigned_courier_id, 'assignment', {'date': str(run.run_date), 'run_id': run.pk, 'route': run.route.name})


def retire_assignment(run):
    if not run.assigned_courier_id:
        return
    lock_courier(run.assigned_courier_id)
    _evidence(run)
    qs = CourierAssignment.objects.filter(courier_id=run.assigned_courier_id, date=run.run_date, source_run_id=run.pk)
    if run.run_date <= timezone.localdate():
        qs.update(frozen=True)
    else:
        qs.filter(frozen=False).update(active=False)
    audit(run.assigned_courier_id, 'assignment_removed', {'date': str(run.run_date), 'run_id': run.pk,
        'retained': run.run_date <= timezone.localdate()})


def save_run_assignment(run, save, update_fields=None):
    if update_fields is not None and not {'assigned_courier', 'assigned_courier_id', 'run_date'}.intersection(update_fields):
        return save()
    old = RouteRun.objects.select_related('route').filter(pk=run.pk).first() if run.pk else None
    changed = not old or (old.assigned_courier_id, old.run_date) != (run.assigned_courier_id, run.run_date)
    if changed:
        require_available(run.assigned_courier_id, run.run_date)
        if old:
            retire_assignment(old)
    result = save()
    if changed:
        _evidence(run)
    return result


def guard_delivery_assignment(delivery, update_fields=None):
    if update_fields is not None and not {'courier', 'courier_id', 'delivery_date'}.intersection(update_fields):
        return
    old = Delivery.objects.filter(pk=delivery.pk).values('courier_id', 'delivery_date').first() if delivery.pk else None
    if not old or (old['courier_id'], old['delivery_date']) != (delivery.courier_id, delivery.delivery_date):
        require_available(delivery.courier_id, delivery.delivery_date)


def month_bounds(raw):
    try:
        first = date.fromisoformat(raw + '-01') if raw else timezone.localdate().replace(day=1)
        if not 1901 <= first.year <= 2198:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError('Укажите месяц в формате ГГГГ-ММ (1901–2198)')
    return first, first.replace(day=calendar.monthrange(first.year, first.month)[1])


def month_data(couriers, first, last):
    couriers = list(couriers)
    ids = [c.pk for c in couriers]
    today = timezone.localdate()
    off = {(r.courier_id, r.date): r for r in CourierDayOff.objects.filter(courier_id__in=ids, date__range=(first, last), active=True)}
    evidence = defaultdict(list)
    for r in CourierAssignment.objects.filter(courier_id__in=ids, date__range=(first, last), active=True):
        evidence[(r.courier_id, r.date)].append(r)
    runs = defaultdict(list)
    for run in RouteRun.objects.filter(assigned_courier_id__in=ids, run_date__range=(first, last)).select_related('route'):
        runs[(run.assigned_courier_id, run.run_date)].append(run)
    activity = {(r['courier_id'], r['delivery_date']): r['last'] for r in Delivery.objects.filter(
        courier_id__in=ids, delivery_date__range=(first, last), completed_at__isnull=False
    ).values('courier_id', 'delivery_date').annotate(last=Max('completed_at'))}
    loose = {(r['courier_id'], r['delivery_date']): r['count'] for r in Delivery.objects.filter(courier_id__in=ids, delivery_date__range=(first, last), route_run__isnull=True).values('courier_id', 'delivery_date').annotate(count=Count('id'))}
    rows = []
    for c in couriers:
        days, counts = [], {'worked': 0, 'off': 0, 'shifts': 0, 'planned_off': 0, 'conflicts': 0}
        for n in range(1, last.day + 1):
            day = first.replace(day=n)
            key = (c.pk, day)
            assignments = evidence[key]
            planned = runs[key]
            worked = day < today and bool(assignments)
            in_period = bool(c.tracking_start_date and day >= c.tracking_start_date and (not c.tracking_end_date or day <= c.tracking_end_date))
            # Explicit historical evidence remains visible even outside conservative tracking boundaries.
            status = 'worked' if worked else ('off' if day < today and in_period else 'unplanned')
            if not in_period and not worked:
                status = 'outside'
            if day >= today and in_period:
                status = 'shift' if planned else ('off' if key in off else 'unplanned')
            if key in off and ((planned or key in loose) if day >= today else assignments):
                status = 'conflict'
                counts['conflicts'] += 1
            counts['worked'] += int(worked)
            counts['off'] += int(day < today and in_period and not worked)
            counts['shifts'] += int(day >= today and bool(planned))
            counts['planned_off'] += int(day >= today and key in off)
            route_items = []
            seen = set()
            sources = assignments if day < today else planned
            for r in sources:
                run_id = r.run_id if day < today else r.pk
                source_id = r.source_run_id if day < today else r.pk
                if source_id in seen:
                    continue
                seen.add(source_id)
                route_items.append({'id': source_id, 'name': r.route_name if day < today else r.route.name,
                    'url': reverse('run_detail', args=[run_id]) if run_id else None})
            days.append({'date': str(day), 'number': n, 'status': status, 'label': LABELS[status],
                'today': day == today, 'past': day < today, 'in_period': in_period, 'routes': route_items,
                'run_count': len(route_items), 'loose_deliveries': loose.get(key, 0), 'last_activity': activity[key].isoformat() if key in activity else None,
                'day_off': key in off, 'comment': off[key].comment if key in off else ''})
        rows.append({'id': c.pk, 'name': c.get_full_name() or c.username, 'active': c.is_active,
            'revision': c.schedule_revision, 'start': str(c.tracking_start_date or ''), 'end': str(c.tracking_end_date or ''),
            'url': reverse('courier_schedule', args=[c.pk]), 'days': days, 'counts': counts})
    return {'month': first.strftime('%Y-%m'), 'title': first.strftime('%m.%Y'), 'weekday': first.weekday(), 'rows': rows,
        'previous': (first-timedelta(days=1)).strftime('%Y-%m'), 'next': (last+timedelta(days=1)).strftime('%Y-%m')}


@transaction.atomic
def mutate_schedule(courier, payload, actor):
    import uuid
    try:
        request_id = uuid.UUID(payload['request_id'])
        revision = int(payload['revision'])
    except (KeyError, ValueError, TypeError, AttributeError):
        raise ValueError('Нужны идентификатор запроса и версия графика')
    previous = CourierScheduleAudit.objects.filter(courier=courier, request_id=request_id).first()
    if previous:
        if previous.details.get('request') != payload:
            raise ScheduleConflict('Идентификатор запроса уже использован для другого действия')
        return
    # Optimistic CAS is a write before any reads of mutable scheduling state.
    if not User.objects.filter(pk=courier.pk, schedule_revision=revision).update(schedule_revision=F('schedule_revision')+1):
        raise ScheduleConflict('График изменён другим диспетчером. Обновите данные и повторите действие.')
    courier.refresh_from_db()
    action = payload.get('action')
    details = {'request': payload}
    if action == 'period':
        try:
            start = date.fromisoformat(payload['start'])
            end = date.fromisoformat(payload['end']) if payload.get('end') else None
        except (KeyError, TypeError, ValueError):
            raise ValueError('Некорректные границы учёта')
        if end and end < start:
            raise ValueError('Окончание учёта раньше начала')
        details['before'] = {'start': str(courier.tracking_start_date), 'end': str(courier.tracking_end_date)}
        User.objects.filter(pk=courier.pk).update(tracking_start_date=start, tracking_end_date=end)
    elif action in ('off', 'cancel', 'correct'):
        try:
            dates = sorted({date.fromisoformat(v) for v in payload['dates']})
        except (KeyError, TypeError, ValueError):
            raise ValueError('Некорректные даты')
        if not 1 <= len(dates) <= 62 or (dates[-1]-dates[0]).days > 92:
            raise ValueError('Выберите от 1 до 62 дат в пределах 93 дней')
        comment = str(payload.get('comment', '')).strip()
        if len(comment) > 500:
            raise ValueError('Комментарий: не более 500 символов')
        today = timezone.localdate()
        if action == 'correct':
            if any(d >= today for d in dates) or not comment or payload.get('worked') not in (True, False):
                raise ValueError('Исправление истории требует прошедшей даты, статуса и причины')
            details['before'] = list(CourierAssignment.objects.filter(courier=courier, date__in=dates).values('date', 'source_run_id', 'active'))
            details['before'] = [{**r, 'date': str(r['date'])} for r in details['before']]
            details['previous_days_off'] = [{**r, 'date': str(r['date'])} for r in CourierDayOff.objects.filter(courier=courier, date__in=dates).values('date', 'active', 'comment')]
            if payload['worked']:
                CourierDayOff.objects.filter(courier=courier, date__in=dates, active=True).update(active=False, updated_by=actor, updated_at=timezone.now())
            for day in dates:
                CourierAssignment.objects.filter(courier=courier, date=day).update(active=False, frozen=True)
                if payload['worked']:
                    CourierAssignment.objects.update_or_create(courier=courier, date=day, source_run_id=0,
                        defaults={'active': True, 'frozen': True, 'route_name': 'Корректировка диспетчера'})
        else:
            if any(d < today for d in dates):
                raise ValueError('Прошедшие даты меняются через исправление истории')
            if action == 'off':
                if any(d < courier.tracking_start_date or (courier.tracking_end_date and d > courier.tracking_end_date) for d in dates):
                    raise ValueError('Выходной за пределами периода учёта')
                conflict = RouteRun.objects.filter(assigned_courier=courier, run_date__in=dates).first()
                # Loose deliveries also occupy availability, but do not invent a RouteRun shift.
                loose = Delivery.objects.filter(courier=courier, delivery_date__in=dates, route_run__isnull=True).first()
                if (conflict or loose) and payload.get('allow_conflict') is not True:
                    raise ScheduleConflict('На эти даты уже есть назначения. Отмените действие или явно сохраните конфликт для последующей замены.', courier, conflict.run_date if conflict else loose.delivery_date)
            details['before'] = list(CourierDayOff.objects.filter(courier=courier, date__in=dates).values('date', 'active', 'comment'))
            details['before'] = [{**r, 'date': str(r['date'])} for r in details['before']]
            for day in dates:
                row, _ = CourierDayOff.objects.get_or_create(courier=courier, date=day, defaults={'created_by': actor})
                row.active = action == 'off'
                row.comment = comment
                row.updated_by = actor
                row.save()
    else:
        raise ValueError('Неизвестное действие')
    audit(courier.pk, action, details, actor, request_id)


def availability(couriers, day):
    couriers = list(couriers)
    ids = [c.pk for c in couriers]
    off = set(CourierDayOff.objects.filter(courier_id__in=ids, date=day, active=True).values_list('courier_id', flat=True))
    busy = set(RouteRun.objects.filter(assigned_courier_id__in=ids, run_date=day).values_list('assigned_courier_id', flat=True))
    for c in couriers:
        c.schedule_unavailable = c.pk in off or bool(c.tracking_end_date and day > c.tracking_end_date)
        c.schedule_label = ' · Выходной' if c.pk in off else (' · Вне периода' if c.schedule_unavailable else (' · Есть рейсы' if c.pk in busy else ' · Доступен'))
    return sorted(couriers, key=lambda c: c.schedule_unavailable)


def replacement_warnings(day=None):
    tomorrow = (day or timezone.localdate()) + timedelta(days=1)
    off = set(CourierDayOff.objects.filter(date=tomorrow, active=True).values_list('courier_id', flat=True))
    warnings = []
    by_route = defaultdict(list)
    for run in RouteRun.objects.filter(run_date=tomorrow):
        by_route[run.route_id].append(run)
    kind = 'weekday' if tomorrow.weekday() < 5 else ('saturday' if tomorrow.weekday() == 5 else 'sunday')
    for route in Route.objects.filter(is_active=True, default_courier_id__in=off).select_related('default_courier').prefetch_related('templates__items'):
        runs = by_route[route.pk]
        unresolved = [r for r in runs if not r.assigned_courier_id or r.assigned_courier_id in off]
        if runs and not unresolved:
            continue
        expected = any(t.is_active and t.kind == kind and any(i.enabled_by_default for i in t.items.all()) for t in route.templates.all())
        if not runs and not expected:
            continue
        name = route.default_courier.get_full_name() or route.default_courier.username
        warnings.append({'text': f'Завтра у {name} выходной. Маршруту «{route.name}» ' + ('нужен другой курьер.' if runs else 'может потребоваться подмена; рейс ещё не создан.'),
            'url': reverse('run_detail', args=[unresolved[0].pk]) if unresolved else reverse('route_detail', args=[route.pk]) + f'?date={tomorrow}',
            'confirmed': bool(runs)})
    return warnings
