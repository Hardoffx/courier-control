from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from deliveries.models import Delivery, DeliveryPoint, Route, RouteRun, RouteTemplate


class UnassignedDispatcherDashboardTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(
            username='dispatcher-unassigned',
            password='pass',
            role=User.Role.DISPATCHER,
        )
        self.route = Route.objects.create(name='Маршрут без курьера')
        self.template = RouteTemplate.objects.create(
            route=self.route,
            kind=RouteTemplate.Kind.WEEKDAY,
        )
        self.point = DeliveryPoint.objects.create(
            name='Точка без курьера',
            address='Москва, Тестовая 1',
        )
        self.run = RouteRun.objects.create(
            route=self.route,
            template=self.template,
            run_date=timezone.localdate(),
            assigned_courier=None,
            status=RouteRun.Status.READY,
        )
        Delivery.objects.create(
            delivery_date=self.run.run_date,
            route_run=self.run,
            point=self.point,
            address=self.point.address,
            source_label=self.point.name,
            route_order=1,
            courier=None,
        )

    def test_dashboard_renders_unassigned_route_and_delivery(self):
        self.client.login(username='dispatcher-unassigned', password='pass')
        response = self.client.get(
            reverse('dispatcher_dashboard'),
            {'date': self.run.run_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Маршрут без курьера')
        self.assertContains(response, 'Курьер не назначен')
        self.assertContains(response, 'Требует внимания')

        deliveries_response = self.client.get(
            reverse('dispatcher_deliveries'),
            {'date': self.run.run_date.isoformat(), 'courier': 'unassigned'},
        )
        self.assertEqual(deliveries_response.status_code, 200)
        self.assertContains(deliveries_response, self.point.address)
        self.assertContains(deliveries_response, 'Без курьера')
