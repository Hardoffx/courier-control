from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import Delivery, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem


class RouteWorkflowPolishTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(
            username='workflow-dispatcher',
            password='pass',
            role=User.Role.DISPATCHER,
        )
        self.courier = User.objects.create_user(
            username='workflow-courier',
            password='pass',
            role=User.Role.COURIER,
        )
        self.route = Route.objects.create(name='Workflow route', default_courier=self.courier)
        self.template = RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.WEEKDAY)
        self.point_a = DeliveryPoint.objects.create(
            name='1001',
            code='1001',
            address='Москва, ул. Первая, д. 1',
            kind=DeliveryPoint.Kind.CMD,
        )
        self.point_b = DeliveryPoint.objects.create(
            name='ИНВИТРО Митино',
            address='Москва, ул. Вторая, д. 2',
            kind=DeliveryPoint.Kind.INVITRO,
        )
        self.item_a = RouteTemplateItem.objects.create(
            template=self.template,
            point=self.point_a,
            route_order=1,
            enabled_by_default=True,
        )
        self.item_b = RouteTemplateItem.objects.create(
            template=self.template,
            point=self.point_b,
            route_order=2,
            enabled_by_default=True,
        )
        self.client.force_login(self.dispatcher)

    def test_pending_day_toggle_survives_adding_another_template_point(self):
        run_date = timezone.localdate()
        response = self.client.post(
            reverse('template_item_day_toggle', args=[self.item_a.pk]),
            {'run_date': run_date.isoformat(), 'enabled': '0'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['pending'])

        extra = DeliveryPoint.objects.create(
            name='Сторонняя лаборатория',
            address='Москва, ул. Третья, д. 3',
            kind=DeliveryPoint.Kind.EXTERNAL,
        )
        response = self.client.post(
            reverse('template_add_point', args=[self.template.pk]),
            {'point_id': extra.pk},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('route_detail', args=[self.route.pk]),
            {'template': self.template.pk, 'date': run_date.isoformat()},
        )
        enabled = response.context['day_enabled_item_ids']
        self.assertNotIn(self.item_a.pk, enabled)
        self.assertIn(self.item_b.pk, enabled)
        self.assertIn(self.template.items.get(point=extra).pk, enabled)

    def test_new_route_gets_independent_saturday_and_sunday_templates(self):
        response = self.client.post(reverse('route_create'), {'name': 'Weekend split route'})
        self.assertEqual(response.status_code, 302)
        route = Route.objects.get(name='Weekend split route')
        self.assertEqual(
            set(route.templates.values_list('kind', flat=True)),
            {
                RouteTemplate.Kind.WEEKDAY,
                RouteTemplate.Kind.SATURDAY,
                RouteTemplate.Kind.SUNDAY,
            },
        )

    def test_inline_point_address_update_changes_canonical_address(self):
        response = self.client.post(
            reverse('template_item_update', args=[self.item_a.pk]),
            {'action': 'point_address', 'address': 'Москва, ул. Новая, д. 10'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.point_a.refresh_from_db()
        self.assertEqual(self.point_a.address, 'Москва, ул Новая 10')
        self.assertEqual(response.json()['address'], self.point_a.address)

    def test_create_external_point_ignores_stale_cmd_code_and_uses_generic_name(self):
        response = self.client.post(
            reverse('template_create_point', args=[self.template.pk]),
            {
                'kind': DeliveryPoint.Kind.EXTERNAL,
                'code': 'SHOULD-NOT-SAVE',
                'name': '',
                'address': 'Москва, ул. Лабораторная, д. 5',
                'enabled_by_default': '1',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        point = DeliveryPoint.objects.get(pk=response.json()['point_id'])
        self.assertEqual(point.code, '')
        self.assertEqual(point.name, 'Сторонняя лаборатория')

    def test_create_invitro_point_uses_name_and_never_cmd_code(self):
        response = self.client.post(
            reverse('template_create_point', args=[self.template.pk]),
            {
                'kind': DeliveryPoint.Kind.INVITRO,
                'code': 'OLD-CMD',
                'name': 'ИНВИТРО Север',
                'address': 'Москва, ул. Инвитро, д. 7',
                'enabled_by_default': '1',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        point = DeliveryPoint.objects.get(pk=response.json()['point_id'])
        self.assertEqual(point.code, '')
        self.assertEqual(point.name, 'ИНВИТРО Север')

    def test_cmd_point_requires_cmd_code(self):
        response = self.client.post(
            reverse('template_create_point', args=[self.template.pk]),
            {
                'kind': DeliveryPoint.Kind.CMD,
                'code': '',
                'name': 'stale name',
                'address': 'Москва, ул. ЦМД, д. 8',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('код ЦМД', response.json()['error'])


class CourierCompletedBarrierReorderTests(TestCase):
    def setUp(self):
        self.courier = User.objects.create_user(
            username='reorder-courier',
            password='pass',
            role=User.Role.COURIER,
        )
        self.route = Route.objects.create(name='Reorder route', default_courier=self.courier)
        self.template = RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.WEEKDAY)
        self.run = RouteRun.objects.create(
            route=self.route,
            template=self.template,
            run_date=timezone.localdate(),
            assigned_courier=self.courier,
            status=RouteRun.Status.IN_PROGRESS,
        )
        self.points = [
            DeliveryPoint.objects.create(name=f'P{i}', address=f'Москва, адрес {i}')
            for i in range(1, 4)
        ]
        self.done = Delivery.objects.create(
            delivery_date=self.run.run_date,
            route_run=self.run,
            point=self.points[0],
            address=self.points[0].address,
            courier=self.courier,
            route_order=1,
            status=Delivery.Status.DONE,
        )
        self.active = Delivery.objects.create(
            delivery_date=self.run.run_date,
            route_run=self.run,
            point=self.points[1],
            address=self.points[1].address,
            courier=self.courier,
            route_order=2,
            status=Delivery.Status.IN_PROGRESS,
        )
        self.tail = Delivery.objects.create(
            delivery_date=self.run.run_date,
            route_run=self.run,
            point=self.points[2],
            address=self.points[2].address,
            courier=self.courier,
            route_order=3,
            status=Delivery.Status.IN_PROGRESS,
        )
        self.client.force_login(self.courier)

    def test_unfinished_stop_can_swap_with_completed_neighbor(self):
        response = self.client.post(
            reverse('courier_reorder', args=[self.active.pk]),
            {'direction': 'up'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.active.refresh_from_db()
        self.done.refresh_from_db()
        self.assertEqual(self.active.route_order, 1)
        self.assertEqual(self.done.route_order, 2)

    def test_completed_stop_cannot_be_directly_reordered(self):
        response = self.client.post(
            reverse('courier_reorder', args=[self.done.pk]),
            {'direction': 'down'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 409)
