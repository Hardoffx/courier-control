from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.models import User
from .models import Delivery, DeliveryEvent, DeliveryPoint, Route, RouteOrderSuggestion, RouteRun, RouteTemplate, RouteTemplateItem
from .route_services import generate_route_run, reassign_route_run, learn_template_from_run, dissolve_route_run, suggestion_comparison
from .import_services import normalize_delivery_address


def dispatcher_required(view):
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_dispatcher:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def _couriers():
    return User.objects.filter(role=User.Role.COURIER, is_active=True, is_superuser=False).order_by('-is_reserve_courier', 'first_name', 'username')


def _ids(raw):
    result = []
    for value in (raw or '').split(','):
        try:
            result.append(int(value.strip()))
        except (TypeError, ValueError):
            pass
    return result


def _posted_point_ids(request):
    raw = request.POST.getlist('point_ids')
    if not raw and request.POST.get('point_id'):
        raw = [request.POST.get('point_id')]
    result = []
    for value in raw:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            pass
    return list(dict.fromkeys(result))


def _save_order(items):
    with transaction.atomic():
        for pos, item in enumerate(items, start=1):
            if item.route_order != pos:
                item.route_order = pos
                item.save(update_fields=['route_order'])


def _wants_json(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _point_from_post(request):
    kinds = {value for value, _ in DeliveryPoint.Kind.choices}
    kind = request.POST.get('kind', DeliveryPoint.Kind.UNKNOWN).strip()
    if kind not in kinds:
        kind = DeliveryPoint.Kind.UNKNOWN
    code = request.POST.get('code', '').strip()[:100]
    address = normalize_delivery_address(request.POST.get('address', ''))[:500]
    phone = request.POST.get('phone', '').strip()[:64]
    name = request.POST.get('name', '').strip()[:255]
    if not address:
        raise ValueError('Укажите адрес новой точки')
    if not name:
        if kind == DeliveryPoint.Kind.CMD:
            name = code or 'ЦМД'
        elif kind == DeliveryPoint.Kind.INVITRO:
            name = 'ИНВИТРО'
        elif kind == DeliveryPoint.Kind.SERVICE:
            name = 'Служебная точка'
        else:
            name = address[:255]

    exact = DeliveryPoint.objects.filter(address=address, is_active=True)
    if code:
        exact = exact.filter(code=code)
    else:
        exact = exact.filter(code='', kind=kind, name__iexact=name)
    point = exact.first()
    if point:
        return point, False

    point = DeliveryPoint.objects.create(
        name=name,
        code=code,
        address=address,
        kind=kind,
        phone=phone,
        is_active=True,
    )
    return point, True


@dispatcher_required
def route_list(request):
    return render(request, 'dispatcher/routes/list.html', {'routes': Route.objects.filter(is_active=True).select_related('default_courier').prefetch_related('templates')})


@dispatcher_required
def route_edit(request, pk=None):
    route = get_object_or_404(Route, pk=pk) if pk else None
    couriers = _couriers()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()[:120]
        if not name:
            messages.error(request, 'Укажите название маршрута')
        else:
            courier_id = request.POST.get('default_courier', '')
            courier = couriers.filter(pk=courier_id).first() if courier_id else None
            route = route or Route()
            route.name = name
            route.default_courier = courier
            route.notes = request.POST.get('notes', '').strip()
            route.save()
            if not route.templates.exists():
                RouteTemplate.objects.create(route=route, kind=RouteTemplate.Kind.WEEKDAY)
                RouteTemplate.objects.create(route=route, kind=RouteTemplate.Kind.WEEKEND)
            messages.success(request, 'Маршрут сохранён')
            return redirect('route_detail', pk=route.pk)
    return render(request, 'dispatcher/routes/route_form.html', {'route': route, 'couriers': couriers})


@dispatcher_required
def route_detail(request, pk):
    route = get_object_or_404(Route, pk=pk)
    templates = route.templates.filter(is_active=True)
    template_id = request.GET.get('template')
    template = templates.filter(pk=template_id).first() if template_id else templates.order_by('kind', 'id').first()
    points = DeliveryPoint.objects.filter(is_active=True).order_by('kind', 'name')
    return render(request, 'dispatcher/routes/detail.html', {'route': route, 'templates': templates, 'template': template, 'points': points, 'couriers': _couriers(), 'point_kinds': DeliveryPoint.Kind.choices})


@dispatcher_required
@require_POST
def template_add_point(request, pk):
    template = get_object_or_404(RouteTemplate, pk=pk)
    point_ids = _posted_point_ids(request)
    if not point_ids:
        messages.warning(request, 'Выберите хотя бы одну точку')
        return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')
    points = {point.pk: point for point in DeliveryPoint.objects.filter(pk__in=point_ids, is_active=True)}
    last = template.items.order_by('-route_order').first()
    next_order = last.route_order + 1 if last else 1
    added = 0
    enabled = 0
    with transaction.atomic():
        for point_id in point_ids:
            point = points.get(point_id)
            if not point:
                continue
            item, created = RouteTemplateItem.objects.get_or_create(template=template, point=point, defaults={'route_order': next_order})
            if created:
                next_order += 1
                added += 1
            elif not item.enabled_by_default:
                item.enabled_by_default = True
                item.save(update_fields=['enabled_by_default'])
                enabled += 1
    messages.success(request, f'Добавлено точек: {added}' + (f'; включено ранее добавленных: {enabled}' if enabled else ''))
    return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')


@dispatcher_required
@require_POST
def template_create_point(request, pk):
    template = get_object_or_404(RouteTemplate.objects.select_related('route'), pk=pk)
    try:
        with transaction.atomic():
            point, point_created = _point_from_post(request)
            item = template.items.filter(point=point).first()
            item_created = item is None
            if item is None:
                last = template.items.order_by('-route_order').first()
                item = RouteTemplateItem.objects.create(
                    template=template,
                    point=point,
                    route_order=(last.route_order + 1 if last else 1),
                )
            item.enabled_by_default = request.POST.get('enabled_by_default', '1') not in ('0', 'false', 'off', '')
            item.time_window = request.POST.get('time_window', '').strip()[:64]
            item.comment = request.POST.get('comment', '').strip()[:255]
            item.save(update_fields=['enabled_by_default', 'time_window', 'comment'])
        message = 'Новая точка создана и добавлена в шаблон' if point_created else ('Точка добавлена в шаблон' if item_created else 'Точка уже была в шаблоне — данные обновлены')
        if _wants_json(request):
            return JsonResponse({'ok': True, 'point_id': point.pk, 'item_id': item.pk, 'created': point_created, 'message': message})
        messages.success(request, message)
    except ValueError as exc:
        if _wants_json(request):
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
        messages.error(request, str(exc))
    return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')


@dispatcher_required
@require_POST
def template_item_update(request, pk):
    item = get_object_or_404(RouteTemplateItem.objects.select_related('template'), pk=pk)
    action = request.POST.get('action')
    route_id = item.template.route_id
    template_id = item.template_id
    payload = {'ok': True, 'item_id': item.pk, 'action': action}
    if action == 'toggle':
        item.enabled_by_default = not item.enabled_by_default
        item.save(update_fields=['enabled_by_default'])
        payload['enabled'] = item.enabled_by_default
    elif action in ('up', 'down'):
        items = list(item.template.items.order_by('route_order', 'id'))
        idx = items.index(item)
        target = idx - 1 if action == 'up' else idx + 1
        if 0 <= target < len(items):
            items[idx], items[target] = items[target], items[idx]
            _save_order(items)
    elif action == 'edit':
        item.time_window = request.POST.get('time_window', '').strip()[:64]
        item.comment = request.POST.get('comment', '').strip()[:255]
        item.save(update_fields=['time_window', 'comment'])
        payload.update({'time_window': item.time_window, 'comment': item.comment})
    elif action == 'remove':
        template = item.template
        item.delete()
        _save_order(list(template.items.order_by('route_order', 'id')))
    else:
        if _wants_json(request):
            return JsonResponse({'ok': False, 'error': 'Неизвестное действие'}, status=400)
        raise PermissionDenied
    if _wants_json(request):
        return JsonResponse(payload)
    return redirect(f'/dispatcher/routes/{route_id}/?template={template_id}')


@dispatcher_required
@require_POST
def template_reorder(request, pk):
    template = get_object_or_404(RouteTemplate, pk=pk)
    items = list(template.items.order_by('route_order', 'id'))
    by_id = {x.pk: x for x in items}
    requested = _ids(request.POST.get('order'))
    ordered = [by_id[x] for x in requested if x in by_id]
    ordered.extend(x for x in items if x.pk not in requested)
    _save_order(ordered)
    if _wants_json(request):
        return JsonResponse({'ok': True, 'order': [item.pk for item in ordered]})
    return redirect(f'/dispatcher/routes/{template.route_id}/?template={template.pk}')


@dispatcher_required
@require_POST
def route_generate(request, pk):
    route = get_object_or_404(Route, pk=pk)
    template = get_object_or_404(RouteTemplate, pk=request.POST.get('template_id'), route=route)
    try:
        run_date = date.fromisoformat(request.POST.get('run_date', ''))
    except ValueError:
        messages.error(request, 'Некорректная дата')
        return redirect('route_detail', pk=pk)
    courier_id = request.POST.get('courier_id', '')
    courier = _couriers().filter(pk=courier_id).first() if courier_id else route.default_courier
    run = generate_route_run(template, run_date, courier=courier, enabled_item_ids=request.POST.getlist('enabled_items'))
    messages.success(request, f'{route.name}: сформировано {run.deliveries.count()} точек на {run_date:%d.%m.%Y}')
    return redirect(f'/dispatcher/?date={run_date.isoformat()}')


@dispatcher_required
def run_detail(request, pk):
    run = get_object_or_404(RouteRun.objects.select_related('route', 'template', 'assigned_courier'), pk=pk)
    deliveries = run.deliveries.select_related('point', 'courier').prefetch_related('events__actor').order_by('route_order', 'id')
    points = DeliveryPoint.objects.filter(is_active=True).order_by('kind', 'name')
    previous = RouteRun.objects.filter(route=run.route, run_date__lt=run.run_date).order_by('-run_date').first()
    templates = run.route.templates.filter(is_active=True).order_by('kind', 'id')
    suggestion = RouteOrderSuggestion.objects.filter(run=run, status=RouteOrderSuggestion.Status.PENDING).select_related('courier').first()
    rows = list(deliveries)
    point_ids = {row.point_id for row in rows if row.point_id}
    history_by_point = {point_id: [] for point_id in point_ids}
    if point_ids:
        history_rows = (
            Delivery.objects.filter(point_id__in=point_ids)
            .exclude(route_run=run)
            .select_related('courier', 'route_run__route')
            .order_by('-delivery_date', '-id')
        )
        for old in history_rows:
            bucket = history_by_point.get(old.point_id)
            if bucket is not None and len(bucket) < 5:
                bucket.append(old)
    for row in rows:
        row.point_history = history_by_point.get(row.point_id, [])
    total = len(rows)
    done = sum(d.status == Delivery.Status.DONE for d in rows)
    problem = sum(d.status == Delivery.Status.PROBLEM for d in rows)
    problem_rows = [d for d in rows if d.status == Delivery.Status.PROBLEM]
    completed = [d for d in rows if d.status == Delivery.Status.DONE and d.completed_at]
    last_done = max(completed, key=lambda d: d.completed_at) if completed else None
    next_stop = next((d for d in rows if d.status != Delivery.Status.DONE), None)
    remaining = total - done
    percent = round(done * 100 / total) if total else 0
    before = after = []
    moved_count = 0
    if suggestion:
        before, after = suggestion_comparison(suggestion)
        before_pos = {point.pk: pos for pos, point in enumerate(before, start=1)}
        moved_count = sum(1 for pos, point in enumerate(after, start=1) if before_pos.get(point.pk) != pos)
    return render(request, 'dispatcher/route_run_detail.html', {
        'run': run,
        'deliveries': deliveries,
        'couriers': _couriers(),
        'points': points,
        'point_kinds': DeliveryPoint.Kind.choices,
        'previous_run': previous,
        'templates': templates,
        'order_suggestion': suggestion,
        'order_before': before,
        'order_after': after,
        'order_moved_count': moved_count,
        'route_kpis': {'total': total, 'done': done, 'remaining': remaining, 'problem': problem, 'percent': percent},
        'last_done': last_done,
        'next_stop': next_stop,
        'problem_rows': problem_rows,
        'recent_events': DeliveryEvent.objects.filter(delivery__route_run=run).select_related('delivery','actor').order_by('-created_at')[:20],
    })


def _add_point_to_run(run, point, requested_time, actor, order):
    delivery = (
        Delivery.objects.filter(delivery_date=run.run_date, point=point, route_run__isnull=True)
        .exclude(status=Delivery.Status.DONE)
        .order_by('id')
        .first()
    )
    if delivery:
        delivery.route_run = run
        delivery.courier = run.assigned_courier
        delivery.route_order = order
        if requested_time:
            delivery.time_window = requested_time
        if delivery.status == Delivery.Status.NEW and run.assigned_courier:
            delivery.status = Delivery.Status.IN_PROGRESS
        elif delivery.status == Delivery.Status.IN_PROGRESS and not run.assigned_courier:
            delivery.status = Delivery.Status.NEW
        delivery.save()
        note = f'Существующая точка дня добавлена в {run.route.name}'
    else:
        delivery = Delivery.objects.create(
            delivery_date=run.run_date,
            route_run=run,
            point=point,
            source_label=point.code or point.name,
            address=point.address,
            phone=point.phone,
            time_window=requested_time,
            courier=run.assigned_courier,
            route_order=order,
            status=Delivery.Status.IN_PROGRESS if run.assigned_courier else Delivery.Status.NEW,
        )
        note = f'Добавлено вручную в {run.route.name} только на {run.run_date:%d.%m.%Y}'
    DeliveryEvent.objects.create(delivery=delivery, actor=actor, action='run_point_added', note=note)
    return delivery


@dispatcher_required
@require_POST
def run_add_point(request, pk):
    run = get_object_or_404(RouteRun, pk=pk)
    point_ids = _posted_point_ids(request)
    if not point_ids:
        messages.warning(request, 'Выберите хотя бы одну точку')
        return redirect('run_detail', pk=pk)
    points = {point.pk: point for point in DeliveryPoint.objects.filter(pk__in=point_ids, is_active=True)}
    existing_ids = set(run.deliveries.values_list('point_id', flat=True))
    last = run.deliveries.order_by('-route_order').first()
    order = last.route_order + 1 if last else 1
    requested_time = request.POST.get('time_window', '').strip()[:64]
    added = 0
    with transaction.atomic():
        for point_id in point_ids:
            point = points.get(point_id)
            if not point or point_id in existing_ids:
                continue
            _add_point_to_run(run, point, requested_time, request.user, order)
            existing_ids.add(point_id)
            order += 1
            added += 1
    messages.success(request, f'Добавлено точек на сегодня: {added}')
    return redirect('run_detail', pk=pk)


@dispatcher_required
@require_POST
def run_create_point(request, pk):
    run = get_object_or_404(RouteRun.objects.select_related('route', 'template'), pk=pk)
    try:
        with transaction.atomic():
            point, point_created = _point_from_post(request)
            if run.deliveries.filter(point=point).exists():
                raise ValueError('Эта точка уже есть в сегодняшнем маршруте')
            last = run.deliveries.order_by('-route_order').first()
            order = last.route_order + 1 if last else 1
            delivery = _add_point_to_run(
                run,
                point,
                request.POST.get('time_window', '').strip()[:64],
                request.user,
                order,
            )
            delivery.comment = request.POST.get('comment', '').strip()
            delivery.save(update_fields=['comment', 'updated_at'])
            added_to_template = False
            if request.POST.get('add_to_template') and run.template_id:
                template_item, created = RouteTemplateItem.objects.get_or_create(
                    template=run.template,
                    point=point,
                    defaults={'route_order': (run.template.items.order_by('-route_order').values_list('route_order', flat=True).first() or 0) + 1},
                )
                template_item.enabled_by_default = True
                template_item.time_window = delivery.time_window
                template_item.comment = delivery.comment[:255]
                template_item.save(update_fields=['enabled_by_default', 'time_window', 'comment'])
                added_to_template = True
        message = 'Новая точка создана и добавлена на сегодня' if point_created else 'Точка добавлена на сегодня'
        if added_to_template:
            message += ' и в постоянный шаблон'
        if _wants_json(request):
            return JsonResponse({'ok': True, 'delivery_id': delivery.pk, 'point_id': point.pk, 'message': message})
        messages.success(request, message)
    except ValueError as exc:
        if _wants_json(request):
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
        messages.error(request, str(exc))
    return redirect('run_detail', pk=pk)


@dispatcher_required
@require_POST
def run_copy_previous(request, pk):
    run = get_object_or_404(RouteRun, pk=pk)
    previous = RouteRun.objects.filter(route=run.route, run_date__lt=run.run_date).order_by('-run_date').first()
    if not previous:
        messages.warning(request, 'Предыдущий маршрут не найден')
        return redirect('run_detail', pk=pk)
    if run.deliveries.filter(status=Delivery.Status.DONE).exists():
        messages.warning(request, 'Нельзя заменить состав: в этом дне уже есть выполненные точки')
        return redirect('run_detail', pk=pk)
    source = list(previous.deliveries.select_related('point').order_by('route_order', 'id'))
    with transaction.atomic():
        run.deliveries.all().delete()
        for order, old in enumerate(source, start=1):
            d = Delivery.objects.create(
                delivery_date=run.run_date, route_run=run, point=old.point, source_label=old.source_label,
                address=old.address, organization=old.organization, recipient=old.recipient, phone=old.phone,
                comment=old.comment, time_window=old.time_window, row_color=old.row_color, courier=run.assigned_courier,
                route_order=order, status=Delivery.Status.IN_PROGRESS if run.assigned_courier else Delivery.Status.NEW,
            )
            DeliveryEvent.objects.create(delivery=d, actor=request.user, action='copied_previous', note=f'Скопировано из маршрута {previous.run_date:%d.%m.%Y}')
    messages.success(request, f'Состав скопирован с {previous.run_date:%d.%m.%Y}: {len(source)} точек')
    return redirect('run_detail', pk=pk)


@dispatcher_required
@require_POST
def run_learn_template(request, pk):
    run = get_object_or_404(RouteRun, pk=pk)
    template = get_object_or_404(RouteTemplate, pk=request.POST.get('template_id'), route=run.route, is_active=True)
    try:
        count = learn_template_from_run(run, template)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('run_detail', pk=pk)
    messages.success(request, f'Шаблон «{template}» обновлён по этому дню: {count} точек. Другие шаблоны не изменены.')
    return redirect('run_detail', pk=pk)


@dispatcher_required
@require_POST
def run_reassign(request, pk):
    run = get_object_or_404(RouteRun, pk=pk)
    courier_id = request.POST.get('courier_id', '')
    courier = _couriers().filter(pk=courier_id).first() if courier_id else None
    reassign_route_run(run, courier)
    messages.success(request, f'{run.route.name}: ' + ('курьер изменён' if courier else 'назначение курьера снято'))
    return redirect(request.POST.get('next') or f'/dispatcher/?date={run.run_date.isoformat()}')


@dispatcher_required
@require_POST
def run_dissolve(request, pk):
    run = get_object_or_404(RouteRun.objects.select_related('route'), pk=pk)
    run_date = run.run_date
    route_name = run.route.name
    try:
        detached, duplicates = dissolve_route_run(run)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('run_detail', pk=pk)
    messages.success(request, f'{route_name}: маршрут на {run_date:%d.%m.%Y} расформирован. Точек возвращено в список дня: {detached}; старых дублей удалено: {duplicates}.')
    return redirect(f'/dispatcher/?date={run_date.isoformat()}')


@dispatcher_required
@require_POST
def run_delivery_move(request, pk, delivery_pk):
    run = get_object_or_404(RouteRun, pk=pk)
    delivery = get_object_or_404(Delivery, pk=delivery_pk, route_run=run)
    if delivery.status == Delivery.Status.DONE:
        if _wants_json(request):
            return JsonResponse({'ok': False, 'error': 'Выполненную точку изменять нельзя'}, status=409)
        messages.warning(request, 'Выполненную точку изменять нельзя')
        return redirect('run_detail', pk=pk)
    action = request.POST.get('action') or request.POST.get('direction')
    if action == 'edit':
        delivery.time_window = request.POST.get('time_window', '').strip()[:64]
        delivery.comment = request.POST.get('comment', '').strip()
        delivery.save(update_fields=['time_window', 'comment', 'updated_at'])
        DeliveryEvent.objects.create(delivery=delivery, actor=request.user, action='dispatcher_edited', note='Обновлены время/комментарий')
        if _wants_json(request):
            return JsonResponse({'ok': True, 'action': action, 'time_window': delivery.time_window, 'comment': delivery.comment})
        return redirect('run_detail', pk=pk)
    if action == 'remove':
        delivery.delete()
        _save_order(list(run.deliveries.order_by('route_order', 'id')))
        if _wants_json(request):
            return JsonResponse({'ok': True, 'action': action})
        messages.success(request, 'Точка убрана только из этого дня')
        return redirect('run_detail', pk=pk)
    if action == 'unassign':
        old = delivery.courier
        delivery.courier = None
        if delivery.status == Delivery.Status.IN_PROGRESS:
            delivery.status = Delivery.Status.NEW
        delivery.save(update_fields=['courier', 'status', 'updated_at'])
        DeliveryEvent.objects.create(delivery=delivery, actor=request.user, action='unassigned', note=f'Назначение снято: {old or "—"} → —')
        if _wants_json(request):
            return JsonResponse({'ok': True, 'action': action})
        messages.success(request, 'Точка снята с курьера')
        return redirect('run_detail', pk=pk)
    items = list(run.deliveries.exclude(status=Delivery.Status.DONE).order_by('route_order', 'id'))
    idx = items.index(delivery)
    target = idx - 1 if action == 'up' else idx + 1
    if 0 <= target < len(items):
        items[idx], items[target] = items[target], items[idx]
        _save_order(items)
    if _wants_json(request):
        return JsonResponse({'ok': True, 'action': action})
    return redirect('run_detail', pk=pk)


@dispatcher_required
@require_POST
def run_reorder(request, pk):
    run = get_object_or_404(RouteRun, pk=pk)
    items = list(run.deliveries.exclude(status=Delivery.Status.DONE).order_by('route_order', 'id'))
    slots = sorted(item.route_order for item in items)
    by_id = {x.pk: x for x in items}
    requested = _ids(request.POST.get('order'))
    ordered = [by_id[x] for x in requested if x in by_id]
    ordered.extend(x for x in items if x.pk not in requested)
    with transaction.atomic():
        for slot, item in zip(slots, ordered):
            if item.route_order != slot:
                item.route_order = slot
                item.save(update_fields=['route_order'])
    if _wants_json(request):
        return JsonResponse({'ok': True, 'order': [item.pk for item in ordered]})
    messages.success(request, 'Порядок маршрута сохранён')
    return redirect('run_detail', pk=pk)
