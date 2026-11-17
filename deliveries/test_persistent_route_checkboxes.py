"""Persistent template checkboxes: no session-only selection or lost delivery history."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import Delivery, DeliveryEvent, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem
from .route_services import generate_route_run


class PersistentRouteCheckboxTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.dispatcher = User.objects.create_user(
            username='checkbox-dispatcher', password='test-password', role=User.Role.DISPATCHER,
        )
        self.courier = User.objects.create_user(
            username='checkbox-courier', password='test-password', role=User.Role.COURIER,
        )
        self.route = Route.objects.create(name='Checkbox route', default_courier=self.courier)
        self.template = RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.WEEKDAY)
        self.point = DeliveryPoint.objects.create(name='Point', address='Москва, Тестовая, 1')
        self.item = RouteTemplateItem.objects.create(template=self.template, point=self.point)
        self.url = reverse('template_item_day_toggle', args=[self.item.pk])
        self.client.force_login(self.dispatcher)

    def toggle(self, enabled):
        return self.client.post(self.url, {'enabled': '1' if enabled else '0'},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_checkbox_persists_in_db_across_sessions_and_future_generation(self):
        response = self.toggle(False)
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertFalse(self.item.enabled_by_default)
        self.client.logout()
        self.client.force_login(self.dispatcher)
        detail = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertContains(detail, 'Исключена')
        self.assertNotContains(detail, 'В этот день')
        future = generate_route_run(self.template, self.today + timedelta(days=2), courier=self.courier)
        self.assertFalse(future.deliveries.filter(point=self.point).exists())
        self.assertEqual(self.toggle(True).status_code, 200)
        self.item.refresh_from_db()
        self.assertTrue(self.item.enabled_by_default)
        next_run = generate_route_run(self.template, self.today + timedelta(days=3), courier=self.courier)
        self.assertTrue(next_run.deliveries.filter(point=self.point).exists())

    def test_today_open_run_detaches_delivery_but_keeps_events(self):
        run = generate_route_run(self.template, self.today, courier=self.courier)
        delivery = run.deliveries.get(point=self.point)
        event = DeliveryEvent.objects.create(delivery=delivery, actor=self.dispatcher,
                                             action='note', note='Сохранить историю')
        self.assertEqual(self.toggle(False).status_code, 200)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.route_run_id)
        self.assertTrue(DeliveryEvent.objects.filter(pk=event.pk, delivery=delivery).exists())
        self.assertTrue(DeliveryEvent.objects.filter(
            delivery=delivery, action='template_point_excluded',
        ).exists())

    def test_completed_today_is_not_deleted_when_future_template_excluded(self):
        run = generate_route_run(self.template, self.today, courier=self.courier)
        delivery = run.deliveries.get(point=self.point)
        delivery.status = Delivery.Status.DONE
        delivery.completed_at = timezone.now()
        delivery.save(update_fields=['status', 'completed_at'])
        self.assertEqual(self.toggle(False).status_code, 200)
        delivery.refresh_from_db()
        self.assertEqual(delivery.route_run_id, run.pk)
        self.assertEqual(delivery.status, Delivery.Status.DONE)
        self.item.refresh_from_db()
        self.assertFalse(self.item.enabled_by_default)

    def test_archived_route_and_courier_cannot_change_template(self):
        from .archive_services import archive_route
        archive_route(self.route.pk, self.dispatcher)
        self.assertEqual(self.toggle(False).status_code, 403)
        self.client.force_login(self.courier)
        self.assertEqual(self.toggle(False).status_code, 403)

    def test_bad_state_does_not_mutate_template(self):
        response = self.client.post(self.url, {'enabled': 'sometimes'})
        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertTrue(self.item.enabled_by_default)
