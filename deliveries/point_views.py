from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import DeliveryPointForm
from .models import DeliveryPoint


def dispatcher_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_dispatcher:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


@dispatcher_required
def point_list(request):
    q = request.GET.get('q', '').strip()
    kind = request.GET.get('kind', '').strip()
    points = DeliveryPoint.objects.all()
    if q:
        points = points.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(address__icontains=q) | Q(phone__icontains=q))
    if kind:
        points = points.filter(kind=kind)
    return render(request, 'dispatcher/points.html', {
        'points': points,
        'kinds': DeliveryPoint.Kind.choices,
        'q': q,
        'kind': kind,
    })


@dispatcher_required
def point_create(request):
    form = DeliveryPointForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Точка добавлена в справочник')
        return redirect('point_list')
    return render(request, 'dispatcher/point_form.html', {'form': form, 'title': 'Новая точка'})


@dispatcher_required
def point_edit(request, pk):
    point = get_object_or_404(DeliveryPoint, pk=pk)
    form = DeliveryPointForm(request.POST or None, instance=point)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Точка обновлена. Эти данные будут использоваться как канонические.')
        return redirect('point_list')
    return render(request, 'dispatcher/point_form.html', {'form': form, 'title': 'Редактирование точки', 'point': point})


@dispatcher_required
@require_POST
def point_toggle(request, pk):
    point = get_object_or_404(DeliveryPoint, pk=pk)
    point.is_active = not point.is_active
    point.save(update_fields=['is_active', 'updated_at'])
    message = 'Точка включена' if point.is_active else 'Точка отключена'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'point_id': point.pk, 'is_active': point.is_active, 'message': message})
    messages.success(request, message)
    return redirect('point_list')
