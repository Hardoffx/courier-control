"""Reversible archiving must retain history and reject unsafe operations."""
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .archive_services import ArchiveConflict, archive_courier, archive_route, restore_courier, restore_route
from .models import (
    ArchiveEvent, CourierAssignment, CourierDayOff, CourierScheduleAudit,
    Delivery, DeliveryEvent, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem,
)
from .route_services import generate_route_run, reassign_route_run


class ArchiveLifecycleTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.dispatcher = User.objects.create_user(
            username='archive-dispatcher', password='pass', role=User.Role.DISPATCHER,
        )
        self.courier = User.objects.create_user(
            username='archive-courier', password='pass', role=User.Role.COURIER,
            tracking_start_date=self.today-timedelta(days=60),
        )
        self.other = User.objects.create_user(username='archive-other', password='pass', role=User.Role.COURIER)
        self.route = Route.objects.create(name='Archive route', default_courier=self.courier)
        self.template = RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.WEEKDAY)
        self.point = DeliveryPoint.objects.create(name='Точка', code='AR1', address='Москва, Тестовая, 10')
        self.item = RouteTemplateItem.objects.create(template=self.template, point=self.point, route_order=1)
        self.client.force_login(self.dispatcher)

    def past_run(self):
        past = self.today-timedelta(days=3)
        run = RouteRun.objects.create(route=self.route, template=self.template, assigned_courier=self.courier,
                                      status=RouteRun.Status.DONE, run_date=past)
        delivery = Delivery.objects.create(route_run=run, point=self.point, courier=self.courier,
                                           delivery_date=past, address=self.point.address, status=Delivery.Status.DONE,
                                           completed_at=timezone.now())
        event = DeliveryEvent.objects.create(delivery=delivery, actor=self.dispatcher, action='done', note='История')
        return run, delivery, event

    def test_route_archived_without_deleting_related_history_and_restored(self):
        run, delivery, event = self.past_run()
        response = self.client.post(reverse('route_archive', args=[self.route.pk]), {'reason': 'Больше не используется'})
        self.assertEqual(response.status_code, 302)
        self.route.refresh_from_db()
        self.assertFalse(self.route.is_active)
        self.assertIsNotNone(self.route.archived_at)
        self.assertEqual(self.route.archive_reason, 'Больше не используется')
        self.assertEqual(self.route.archived_by, self.dispatcher)
        self.assertEqual(RouteRun.objects.get(pk=run.pk).route_id, self.route.pk)
        self.assertTrue(RouteTemplate.objects.filter(pk=self.template.pk).exists())
        self.assertTrue(Delivery.objects.filter(pk=delivery.pk, route_run_id=run.pk).exists())
        self.assertTrue(DeliveryEvent.objects.filter(pk=event.pk, delivery_id=delivery.pk).exists())
        self.assertTrue(CourierAssignment.objects.filter(courier=self.courier, source_run_id=run.pk).exists())
        self.assertContains(self.client.get(reverse('route_list')+'?view=archive'), self.route.name)
        self.assertNotContains(self.client.get(reverse('route_list')), self.route.name)
        self.assertContains(self.client.get(reverse('route_detail', args=[self.route.pk])), 'История рейсов')
        self.assertContains(self.client.get(reverse('run_detail', args=[run.pk])), 'Архивный рейс')
        self.assertEqual(ArchiveEvent.objects.filter(kind='route', object_id=self.route.pk, action='archive').count(), 1)
        restore = self.client.post(reverse('route_restore', args=[self.route.pk]))
        self.assertEqual(restore.status_code, 302)
        self.route.refresh_from_db()
        self.assertTrue(self.route.is_active)
        self.assertIsNone(self.route.archived_at)
        self.assertEqual(ArchiveEvent.objects.filter(kind='route', object_id=self.route.pk).count(), 2)
        self.assertTrue(DeliveryEvent.objects.filter(pk=event.pk).exists())

    def test_route_archiving_rejects_unfinished_today_and_future(self):
        run = RouteRun.objects.create(route=self.route, template=self.template, run_date=self.today + timedelta(days=1),
                                      assigned_courier=self.courier)
        with self.assertRaisesRegex(ArchiveConflict, 'незавершённые'):
            archive_route(self.route.pk, self.dispatcher)
        self.route.refresh_from_db()
        self.assertIsNone(self.route.archived_at)
        self.assertEqual(ArchiveEvent.objects.filter(kind='route').count(), 0)
        run.status = RouteRun.Status.DONE
        run.save(update_fields=['status'])
        archive_route(self.route.pk, self.dispatcher)
        self.assertFalse(Route.objects.get(pk=self.route.pk).is_active)

    def test_archived_route_mutations_rejected_even_by_direct_endpoints(self):
        archive_route(self.route.pk, self.dispatcher)
        for name, pk in [
            ('template_add_point', self.template.pk),
            ('template_item_update', self.item.pk),
            ('template_item_day_toggle', self.item.pk),
            ('template_reorder', self.template.pk),
            ('route_generate', self.route.pk),
            ('template_import_excel', self.template.pk),
        ]:
            response = self.client.post(reverse(name, args=[pk]), {})
            self.assertEqual(response.status_code, 403, name)
        with self.assertRaisesRegex(ValueError, 'Архивный'):
            generate_route_run(self.template, self.today)
        self.assertEqual(self.client.get(reverse('route_edit', args=[self.route.pk])).status_code, 404)

    def test_courier_needs_default_route_reassigned_before_archive(self):
        with self.assertRaisesRegex(ArchiveConflict, 'закреплён'):
            archive_courier(self.courier.pk, self.dispatcher)
        self.route.default_courier = self.other
        self.route.save(update_fields=['default_courier'])
        archive_courier(self.courier.pk, self.dispatcher, 'Уволен')
        self.courier.refresh_from_db()
        self.assertFalse(self.courier.is_active)
        self.assertIsNotNone(self.courier.archived_at)
        self.assertEqual(self.courier.archive_reason, 'Уволен')
        self.assertEqual(self.courier.tracking_end_date, self.today)
        self.assertFalse(self.client.login(username='archive-courier', password='pass'))
        self.client.force_login(self.dispatcher)
        self.assertContains(self.client.get(reverse('courier_manage_list')+'?view=archive'), self.courier.username)
        self.assertNotContains(self.client.get(reverse('courier_manage_list')), self.courier.username)
        self.assertEqual(self.client.get(reverse('courier_manage_edit',args=[self.courier.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('courier_manage_toggle',args=[self.courier.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('courier_schedule_change',args=[self.courier.pk]), data='{}',
                                          content_type='application/json').status_code, 409)
        self.assertContains(self.client.get(reverse('courier_schedule',args=[self.courier.pk])), 'только для просмотра')
        with self.assertRaisesRegex(ValueError, 'курьера'):
            reassign_route_run(RouteRun.objects.create(route=self.route, run_date=self.today), self.courier)
        restore_courier(self.courier.pk, self.dispatcher)
        self.courier.refresh_from_db()
        self.assertTrue(self.courier.is_active)
        self.assertIsNone(self.courier.archived_at)
        self.assertIsNone(self.courier.tracking_end_date)
        self.assertEqual(ArchiveEvent.objects.filter(kind='courier', object_id=self.courier.pk).count(), 2)

    def test_courier_archiving_rejects_future_assignment_and_retains_old_evidence(self):
        self.route.default_courier = None
        self.route.save(update_fields=['default_courier'])
        past_run, delivery, event = self.past_run()
        CourierDayOff.objects.create(courier=self.courier, date=self.today-timedelta(days=2))
        pending = RouteRun.objects.create(route=self.route, run_date=self.today+timedelta(days=1),
                                          assigned_courier=self.courier)
        with self.assertRaisesRegex(ArchiveConflict, 'назначения'):
            archive_courier(self.courier.pk, self.dispatcher)
        pending.assigned_courier = self.other
        pending.save(update_fields=['assigned_courier'])
        archive_courier(self.courier.pk, self.dispatcher)
        self.assertTrue(CourierAssignment.objects.filter(courier=self.courier, source_run_id=past_run.pk).exists())
        self.assertTrue(CourierScheduleAudit.objects.filter(courier=self.courier).exists())
        self.assertTrue(CourierDayOff.objects.filter(courier=self.courier).exists())
        self.assertEqual(Delivery.objects.get(pk=delivery.pk).courier_id, self.courier.pk)
        self.assertTrue(DeliveryEvent.objects.filter(pk=event.pk).exists())

    def test_courier_previously_disabled_restored_disabled_and_original_end_preserved(self):
        self.route.default_courier = None
        self.route.save(update_fields=['default_courier'])
        previous = self.today-timedelta(days=1)
        self.courier.is_active = False
        self.courier.tracking_end_date = previous
        self.courier.save(update_fields=['is_active', 'tracking_end_date'])
        archive_courier(self.courier.pk, self.dispatcher)
        restore_courier(self.courier.pk, self.dispatcher)
        self.courier.refresh_from_db()
        self.assertFalse(self.courier.is_active)
        self.assertEqual(self.courier.tracking_end_date, previous)

    def test_restoring_route_requires_available_original_courier(self):
        archive_route(self.route.pk, self.dispatcher)
        archive_courier(self.courier.pk, self.dispatcher)
        with self.assertRaisesRegex(ArchiveConflict, 'курьера'):
            restore_route(self.route.pk, self.dispatcher)
        restore_courier(self.courier.pk, self.dispatcher)
        restore_route(self.route.pk, self.dispatcher)
        self.assertTrue(Route.objects.get(pk=self.route.pk).is_active)

    def test_editing_disabled_courier_does_not_reenable_access(self):
        self.courier.is_active = False
        self.courier.save(update_fields=['is_active'])
        response = self.client.post(reverse('courier_manage_edit', args=[self.courier.pk]), {
            'username': self.courier.username,
            'first_name': 'Исправлено',
            'last_name': 'Имя',
            'phone': '',
            'password': '',
        })
        self.assertEqual(response.status_code, 302)
        self.courier.refresh_from_db()
        self.assertFalse(self.courier.is_active)
        self.assertEqual(self.courier.first_name, 'Исправлено')

    def test_settings_pages_own_archiving_controls_not_list_cards(self):
        route_list = self.client.get(reverse('route_list'))
        self.assertNotContains(route_list, 'name="reason"')
        self.assertContains(self.client.get(reverse('route_edit',args=[self.route.pk])), 'route-archive-dialog')
        courier_list = self.client.get(reverse('courier_manage_list'))
        self.assertNotContains(courier_list, 'name="reason"')
        self.assertContains(self.client.get(reverse('courier_manage_edit',args=[self.courier.pk])), 'courier-archive-dialog')

    def test_permissions_and_methods_on_archive_actions(self):
        self.assertEqual(self.client.get(reverse('route_archive', args=[self.route.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('courier_restore', args=[self.courier.pk])).status_code, 405)
        self.client.force_login(self.courier)
        self.assertEqual(self.client.post(reverse('route_archive',args=[self.route.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('courier_archive',args=[self.courier.pk])).status_code, 403)
        self.client.force_login(self.dispatcher)
        self.assertEqual(self.client.post(reverse('courier_archive',args=[self.dispatcher.pk])).status_code, 404)
