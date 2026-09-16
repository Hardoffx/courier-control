from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Delivery, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem
from .route_services import dissolve_route_run, generate_route_run


class RouteRunSafetyTests(TestCase):
    def setUp(self):
        self.day = date(2026, 9, 16)
        self.dispatcher = User.objects.create_user(
            username='dispatcher',
            password='pass',
            role=User.Role.DISPATCHER,
        )
        self.courier = User.objects.create_user(
            username='courier',
            password='pass',
            role=User.Role.COURIER,
        )
        self.point = DeliveryPoint.objects.create(
            name='Митино 1',
            code='458',
            address='Москва, Дубравная ул., 46',
            kind=DeliveryPoint.Kind.CMD,
        )
        self.route = Route.objects.create(name='Митино')
        self.template = RouteTemplate.objects.create(
            route=self.route,
            kind=RouteTemplate.Kind.WEEKDAY,
        )
        self.item = RouteTemplateItem.objects.create(
            template=self.template,
            point=self.point,
            route_order=1,
            time_window='11:00-13:00',
        )

    def test_generate_route_adopts_existing_day_delivery_instead_of_duplicating(self):
        existing = Delivery.objects.create(
            delivery_date=self.day,
            point=self.point,
            source_label='458 из Excel',
            address=self.point.address,
            time_window='10:30-12:30',
            courier=self.courier,
            status=Delivery.Status.IN_PROGRESS,
            route_order=7,
        )

        run = generate_route_run(
            self.template,
            self.day,
            courier=self.courier,
            enabled_item_ids=[str(self.item.pk)],
        )

        self.assertEqual(Delivery.objects.filter(delivery_date=self.day, point=self.point).count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.pk, run.deliveries.get().pk)
        self.assertEqual(existing.route_run_id, run.pk)
        self.assertEqual(existing.courier_id, self.courier.pk)
        self.assertEqual(existing.route_order, 1)
        self.assertEqual(existing.source_label, '458 из Excel')
        self.assertEqual(existing.time_window, '10:30-12:30')

    def test_dissolve_route_removes_legacy_duplicate_and_unassigns_retained_row(self):
        direct = Delivery.objects.create(
            delivery_date=self.day,
            point=self.point,
            source_label='458',
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.IN_PROGRESS,
            route_order=1,
        )
        run = RouteRun.objects.create(
            route=self.route,
            template=self.template,
            run_date=self.day,
            assigned_courier=self.courier,
            status=RouteRun.Status.READY,
        )
        Delivery.objects.create(
            delivery_date=self.day,
            route_run=run,
            point=self.point,
            source_label='458',
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.IN_PROGRESS,
            route_order=1,
        )

        detached, duplicates = dissolve_route_run(run)

        self.assertEqual(detached, 0)
        self.assertEqual(duplicates, 1)
        self.assertFalse(RouteRun.objects.filter(pk=run.pk).exists())
        self.assertEqual(Delivery.objects.filter(delivery_date=self.day, point=self.point).count(), 1)
        direct.refresh_from_db()
        self.assertIsNone(direct.route_run_id)
        self.assertIsNone(direct.courier_id)
        self.assertEqual(direct.status, Delivery.Status.NEW)

    def test_dissolve_route_returns_unique_delivery_to_unassigned_day_pool(self):
        run = RouteRun.objects.create(
            route=self.route,
            template=self.template,
            run_date=self.day,
            assigned_courier=self.courier,
            status=RouteRun.Status.READY,
        )
        delivery = Delivery.objects.create(
            delivery_date=self.day,
            route_run=run,
            point=self.point,
            source_label='458',
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.IN_PROGRESS,
            route_order=1,
        )

        detached, duplicates = dissolve_route_run(run)

        self.assertEqual((detached, duplicates), (1, 0))
        delivery.refresh_from_db()
        self.assertIsNone(delivery.route_run_id)
        self.assertIsNone(delivery.courier_id)
        self.assertEqual(delivery.status, Delivery.Status.NEW)

    def test_dissolve_route_is_blocked_after_completed_delivery(self):
        run = RouteRun.objects.create(
            route=self.route,
            template=self.template,
            run_date=self.day,
            assigned_courier=self.courier,
            status=RouteRun.Status.READY,
        )
        Delivery.objects.create(
            delivery_date=self.day,
            route_run=run,
            point=self.point,
            source_label='458',
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.DONE,
            route_order=1,
        )

        with self.assertRaisesMessage(ValueError, 'выполненные точки'):
            dissolve_route_run(run)

        self.assertTrue(RouteRun.objects.filter(pk=run.pk).exists())

    def test_dispatcher_can_unassign_one_route_point(self):
        run = RouteRun.objects.create(
            route=self.route,
            template=self.template,
            run_date=self.day,
            assigned_courier=self.courier,
            status=RouteRun.Status.READY,
        )
        delivery = Delivery.objects.create(
            delivery_date=self.day,
            route_run=run,
            point=self.point,
            source_label='458',
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.IN_PROGRESS,
            route_order=1,
        )
        self.client.force_login(self.dispatcher)

        response = self.client.post(
            reverse('run_delivery_move', args=[run.pk, delivery.pk]),
            {'direction': 'unassign'},
        )

        self.assertRedirects(response, reverse('run_detail', args=[run.pk]))
        delivery.refresh_from_db()
        self.assertIsNone(delivery.courier_id)
        self.assertEqual(delivery.status, Delivery.Status.NEW)
        self.assertEqual(delivery.events.filter(action='unassigned').count(), 1)
