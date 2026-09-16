from datetime import timedelta
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from accounts.models import User
from .models import (
    CourierRouteOrderPreference,
    DeliveryPoint,
    Route,
    RouteOrderSuggestion,
    RouteTemplate,
    RouteTemplateItem,
)
from .route_import_services import apply_workbook_to_run, apply_workbook_to_template
from .route_services import decide_order_suggestion, generate_route_run, record_courier_order_change


class RouteWorkflowV2Tests(TestCase):
    def setUp(self):
        self.day = timezone.localdate()
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
        self.route = Route.objects.create(name='Митино V2', default_courier=self.courier)
        self.template = RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.WEEKDAY)
        self.p1 = DeliveryPoint.objects.create(name='Точка 1', code='101', address='Москва, Тестовая 1')
        self.p2 = DeliveryPoint.objects.create(name='Точка 2', code='102', address='Москва, Тестовая 2')
        self.p3 = DeliveryPoint.objects.create(name='Точка 3', code='103', address='Москва, Тестовая 3')
        self.i1 = RouteTemplateItem.objects.create(template=self.template, point=self.p1, route_order=1)
        self.i2 = RouteTemplateItem.objects.create(template=self.template, point=self.p2, route_order=2)

    def workbook(self, rows):
        wb = Workbook()
        ws = wb.active
        ws.append(['Код', 'Адрес', 'Время'])
        for row in rows:
            ws.append(row)
        stream = BytesIO()
        wb.save(stream)
        return stream.getvalue()

    def test_template_excel_replace_uses_file_order_and_adds_new_library_point(self):
        content = self.workbook([
            ['103', self.p3.address, '13:00-14:00'],
            ['101', self.p1.address, '10:00-11:00'],
            ['777', 'Москва, Совсем новая 77', '15:00-16:00'],
        ])

        summary = apply_workbook_to_template(content, self.template, mode='replace')

        items = list(self.template.items.select_related('point').order_by('route_order', 'id'))
        self.assertEqual([item.point.code for item in items], ['103', '101', '777'])
        self.assertEqual([item.route_order for item in items], [1, 2, 3])
        self.assertEqual([item.time_window for item in items], ['13:00-14:00', '10:00-11:00', '15:00-16:00'])
        self.assertEqual(summary.applied, 3)
        self.assertEqual(summary.created_points, 1)
        self.assertTrue(DeliveryPoint.objects.filter(code='777', address='Москва, Совсем новая 77').exists())

    def test_daily_excel_replace_changes_only_run_not_permanent_template(self):
        run = generate_route_run(self.template, self.day, courier=self.courier)
        content = self.workbook([
            ['102', self.p2.address, '12:00-13:00'],
            ['101', self.p1.address, '10:00-11:00'],
        ])

        apply_workbook_to_run(content, run, actor=self.dispatcher, mode='replace')

        daily = list(run.deliveries.select_related('point').order_by('route_order', 'id'))
        permanent = list(self.template.items.select_related('point').order_by('route_order', 'id'))
        self.assertEqual([row.point_id for row in daily], [self.p2.pk, self.p1.pk])
        self.assertEqual([item.point_id for item in permanent], [self.p1.pk, self.p2.pk])
        self.assertEqual(daily[0].time_window, '12:00-13:00')

    def test_manager_can_add_multiple_points_to_template_in_one_request(self):
        self.client.force_login(self.dispatcher)
        response = self.client.post(
            reverse('template_add_point', args=[self.template.pk]),
            {'point_ids': [str(self.p3.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.template.items.filter(point=self.p3).exists())

        p4 = DeliveryPoint.objects.create(name='Точка 4', code='104', address='Москва, Тестовая 4')
        p5 = DeliveryPoint.objects.create(name='Точка 5', code='105', address='Москва, Тестовая 5')
        self.client.post(
            reverse('template_add_point', args=[self.template.pk]),
            {'point_ids': [str(p4.pk), str(p5.pk)]},
        )
        appended = list(self.template.items.filter(point__in=[p4, p5]).order_by('route_order').values_list('point_id', flat=True))
        self.assertEqual(appended, [p4.pk, p5.pk])

    def test_courier_reorder_creates_manager_suggestion_without_changing_template(self):
        run = generate_route_run(self.template, self.day, courier=self.courier)
        rows = list(run.deliveries.order_by('route_order', 'id'))
        self.client.force_login(self.courier)

        response = self.client.post(
            reverse('courier_reorder', args=[rows[1].pk]),
            {'direction': 'up'},
        )

        self.assertRedirects(response, reverse('courier_today'))
        suggestion = RouteOrderSuggestion.objects.get(run=run)
        self.assertEqual(suggestion.status, RouteOrderSuggestion.Status.PENDING)
        self.assertEqual(suggestion.original_point_order, [self.p1.pk, self.p2.pk])
        self.assertEqual(suggestion.proposed_point_order, [self.p2.pk, self.p1.pk])
        self.assertEqual(
            list(self.template.items.order_by('route_order').values_list('point_id', flat=True)),
            [self.p1.pk, self.p2.pk],
        )

    def test_manager_can_save_reordered_route_as_personal_courier_order(self):
        run = generate_route_run(self.template, self.day, courier=self.courier)
        suggestion = record_courier_order_change(
            run,
            self.courier,
            [self.p1.pk, self.p2.pk],
            [self.p2.pk, self.p1.pk],
        )

        decide_order_suggestion(suggestion, 'courier', self.dispatcher)

        preference = CourierRouteOrderPreference.objects.get(template=self.template, courier=self.courier)
        self.assertEqual(preference.point_order, [self.p2.pk, self.p1.pk])
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, RouteOrderSuggestion.Status.APPLIED_COURIER)

        next_run = generate_route_run(self.template, self.day + timedelta(days=1), courier=self.courier)
        self.assertEqual(
            list(next_run.deliveries.order_by('route_order').values_list('point_id', flat=True)),
            [self.p2.pk, self.p1.pk],
        )

    def test_personal_order_keeps_new_template_points_after_known_sequence(self):
        CourierRouteOrderPreference.objects.create(
            template=self.template,
            courier=self.courier,
            point_order=[self.p2.pk, self.p1.pk],
        )
        RouteTemplateItem.objects.create(template=self.template, point=self.p3, route_order=3)

        run = generate_route_run(self.template, self.day, courier=self.courier)

        self.assertEqual(
            list(run.deliveries.order_by('route_order').values_list('point_id', flat=True)),
            [self.p2.pk, self.p1.pk, self.p3.pk],
        )

    def test_manager_can_promote_courier_order_to_template_standard(self):
        run = generate_route_run(self.template, self.day, courier=self.courier)
        suggestion = record_courier_order_change(
            run,
            self.courier,
            [self.p1.pk, self.p2.pk],
            [self.p2.pk, self.p1.pk],
        )

        decide_order_suggestion(suggestion, 'template', self.dispatcher)

        self.assertEqual(
            list(self.template.items.order_by('route_order').values_list('point_id', flat=True)),
            [self.p2.pk, self.p1.pk],
        )
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, RouteOrderSuggestion.Status.APPLIED_TEMPLATE)

    def test_dispatcher_courier_preview_does_not_switch_session(self):
        generate_route_run(self.template, self.day, courier=self.courier)
        self.client.force_login(self.dispatcher)

        response = self.client.get(reverse('courier_preview', args=[self.courier.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Просмотр как курьер — без переключения аккаунта')
        self.assertContains(response, self.p1.address)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.dispatcher.pk)
