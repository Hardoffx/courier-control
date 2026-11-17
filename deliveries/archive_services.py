"""Reversible route/courier archive with intact historical foreign keys."""
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import User
from .models import ArchiveEvent, Delivery, Route, RouteRun


class ArchiveConflict(ValueError):
    """Archive/restore is unsafe until live assignments are resolved."""


def _unfinished_runs(**filters):
    today = timezone.localdate()
    return RouteRun.objects.filter(**filters).filter(
        Q(run_date__gte=today) | Q(status=RouteRun.Status.IN_PROGRESS)
    ).exclude(status=RouteRun.Status.DONE).exists()


def _unfinished_deliveries(**filters):
    today = timezone.localdate()
    return Delivery.objects.filter(**filters).filter(
        Q(delivery_date__gte=today) | Q(status=Delivery.Status.IN_PROGRESS)
    ).exclude(status=Delivery.Status.DONE).exists()


def _record(kind, obj, action, actor, reason=''):
    ArchiveEvent.objects.create(
        kind=kind, object_id=obj.pk,
        object_label=(obj.get_full_name() or obj.username) if kind == ArchiveEvent.Kind.COURIER else obj.name,
        action=action, actor=actor, reason=reason[:500],
    )


@transaction.atomic
def archive_route(route_id, actor, reason=''):
    route = Route.objects.select_for_update().get(pk=route_id)
    if route.archived_at:
        raise ArchiveConflict('Маршрут уже находится в архиве.')
    if _unfinished_runs(route=route) or _unfinished_deliveries(route_run__route=route):
        raise ArchiveConflict('Есть незавершённые или будущие рейсы и доставки. Завершите или переназначьте их перед архивированием.')
    route.archived_was_active = route.is_active
    route.archived_at = timezone.now()
    route.archived_by = actor
    route.archive_reason = (reason or '').strip()[:500]
    route.is_active = False
    route.save(update_fields=['archived_was_active', 'archived_at', 'archived_by', 'archive_reason', 'is_active', 'updated_at'])
    _record(ArchiveEvent.Kind.ROUTE, route, ArchiveEvent.Action.ARCHIVE, actor, route.archive_reason)
    return route


@transaction.atomic
def restore_route(route_id, actor):
    route = Route.objects.select_for_update().select_related('default_courier').get(pk=route_id)
    if not route.archived_at:
        raise ArchiveConflict('Маршрут не находится в архиве.')
    if route.archived_was_active and route.default_courier and (
        route.default_courier.archived_at or not route.default_courier.is_active
    ):
        raise ArchiveConflict('Закреплённый курьер недоступен. Сначала восстановите курьера.')
    route.is_active = route.archived_was_active
    route.archived_at = None
    route.archived_by = None
    route.archive_reason = ''
    route.archived_was_active = False
    route.save(update_fields=['is_active', 'archived_at', 'archived_by', 'archive_reason', 'archived_was_active', 'updated_at'])
    _record(ArchiveEvent.Kind.ROUTE, route, ArchiveEvent.Action.RESTORE, actor)
    return route


@transaction.atomic
def archive_courier(courier_id, actor, reason=''):
    courier = User.objects.select_for_update().get(pk=courier_id, role=User.Role.COURIER, is_superuser=False)
    if courier.archived_at:
        raise ArchiveConflict('Курьер уже находится в архиве.')
    if Route.objects.filter(default_courier=courier, is_active=True, archived_at__isnull=True).exists():
        raise ArchiveConflict('Курьер закреплён за активным маршрутом. Сначала назначьте другого курьера в настройках маршрута.')
    if _unfinished_runs(assigned_courier=courier) or _unfinished_deliveries(courier=courier):
        raise ArchiveConflict('Есть незавершённые или будущие назначения. Сначала передайте их другому курьеру либо завершите.')
    courier.archived_was_active = courier.is_active
    courier.archived_previous_tracking_end_date = courier.tracking_end_date
    courier.archived_at = timezone.now()
    courier.archived_by = actor
    courier.archive_reason = (reason or '').strip()[:500]
    courier.is_active = False
    if courier.tracking_end_date is None:
        courier.tracking_end_date = timezone.localdate()
    # Use a direct atomic update: User.save() normally changes tracking boundaries
    # on deactivation; archive must preserve exact pre-archive values for restoration.
    User.objects.filter(pk=courier.pk).update(
        archived_was_active=courier.archived_was_active,
        archived_previous_tracking_end_date=courier.archived_previous_tracking_end_date,
        archived_at=courier.archived_at, archived_by=actor,
        archive_reason=courier.archive_reason, is_active=False,
        tracking_end_date=courier.tracking_end_date,
        schedule_revision=F('schedule_revision') + 1,
    )
    _record(ArchiveEvent.Kind.COURIER, courier, ArchiveEvent.Action.ARCHIVE, actor, courier.archive_reason)
    return courier


@transaction.atomic
def restore_courier(courier_id, actor):
    courier = User.objects.select_for_update().get(pk=courier_id, role=User.Role.COURIER, is_superuser=False)
    if not courier.archived_at:
        raise ArchiveConflict('Курьер не находится в архиве.')
    original_active = courier.archived_was_active
    original_end = courier.archived_previous_tracking_end_date
    User.objects.filter(pk=courier.pk).update(
        archived_at=None, archived_by=None, archive_reason='',
        archived_was_active=False, archived_previous_tracking_end_date=None,
        is_active=original_active, tracking_end_date=original_end,
        schedule_revision=F('schedule_revision') + 1,
    )
    _record(ArchiveEvent.Kind.COURIER, courier, ArchiveEvent.Action.RESTORE, actor)
    return courier
