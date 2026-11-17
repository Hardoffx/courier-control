"""Dispatcher-only, POST-only archive and restoration endpoints."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from accounts.models import User
from .archive_services import ArchiveConflict, archive_courier as perform_archive_courier
from .archive_services import archive_route as perform_archive_route
from .archive_services import restore_courier as perform_restore_courier
from .archive_services import restore_route as perform_restore_route
from .courier_admin_views import dispatcher_required
from .models import Route


@dispatcher_required
@require_POST
def route_archive(request, pk):
    get_object_or_404(Route, pk=pk)
    try:
        perform_archive_route(pk, request.user, request.POST.get('reason', ''))
    except ArchiveConflict as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, 'Маршрут перемещён в архив. История сохранена.')
    return redirect('route_list')


@dispatcher_required
@require_POST
def route_restore(request, pk):
    get_object_or_404(Route, pk=pk)
    try:
        perform_restore_route(pk, request.user)
    except ArchiveConflict as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, 'Маршрут восстановлен.')
    return redirect('/dispatcher/routes/?view=archive')


@dispatcher_required
@require_POST
def courier_archive(request, pk):
    get_object_or_404(User, pk=pk, role=User.Role.COURIER, is_superuser=False)
    try:
        perform_archive_courier(pk, request.user, request.POST.get('reason', ''))
    except ArchiveConflict as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, 'Курьер перемещён в архив. Доступ отключён, история сохранена.')
    return redirect('courier_manage_list')


@dispatcher_required
@require_POST
def courier_restore(request, pk):
    get_object_or_404(User, pk=pk, role=User.Role.COURIER, is_superuser=False)
    try:
        perform_restore_courier(pk, request.user)
    except ArchiveConflict as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, 'Курьер восстановлен.')
    return redirect('/dispatcher/couriers/?view=archive')
