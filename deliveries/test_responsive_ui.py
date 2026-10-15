from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import DeliveryPoint, Route, RouteTemplate, RouteTemplateItem


class ResponsiveOperationalUiTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(username='ui-dispatcher', password='pass', role=User.Role.DISPATCHER)
        self.courier = User.objects.create_user(username='ui-courier', role=User.Role.COURIER)
        self.route = Route.objects.create(name='UI route', default_courier=self.courier)
        self.template = RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.WEEKDAY)
        self.point = DeliveryPoint.objects.create(name='UI point', address='Москва, Очень длинный тестовый адрес 123')
        RouteTemplateItem.objects.create(template=self.template, point=self.point, route_order=1, time_window='09:00')
        self.client.login(username='ui-dispatcher', password='pass')

    def test_route_template_has_compact_mobile_editor_controls(self):
        response = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('admin-route-editor', html)
        self.assertIn('inline-edit-form', html)
        self.assertIn('Переместить', html)
        self.assertIn('На позицию', html)
        self.assertIn('Убрать', html)
        self.assertIn('Создать новую точку', html)
        self.assertIn('name="phone"', html)

    def test_template_picker_places_weekday_before_weekend_options(self):
        RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.SATURDAY)
        RouteTemplate.objects.create(route=self.route, kind=RouteTemplate.Kind.SUNDAY)

        response = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('class="variant-picker-grid"', html)
        for kind in ('weekday', 'saturday', 'sunday'):
            self.assertIn(f'data-template-kind="{kind}"', html)
        self.assertIn('data-template-kind="weekday"]{grid-column:1/-1;order:0}', html)
        self.assertIn('data-template-kind="saturday"]{order:1}', html)
        self.assertIn('data-template-kind="sunday"]{order:2}', html)

    def test_courier_names_have_no_role_prefixes_in_route_picker(self):
        self.courier.first_name = 'Кирилл'
        self.courier.is_reserve_courier = True
        self.courier.save(update_fields=['first_name', 'is_reserve_courier'])
        response = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertContains(response, '<option value="">Кирилл</option>', html=False)
        self.assertContains(response, f'<option value="{self.courier.pk}">Кирилл · Доступен</option>', html=False)
        html = response.content.decode()
        for unwanted in ('Обычный курьер:', 'Обычный:', ' · РЕЗЕРВ', ' · Резерв'):
            self.assertNotIn(unwanted, html)

    def test_route_generation_controls_remain_on_same_screen(self):
        response = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertContains(response, 'Создать маршрут на день')
        self.assertContains(response, 'В этот день')
        self.assertContains(response, 'Excel')
        self.assertContains(response, 'Добавить из базы')
        self.assertContains(response, self.point.address)

    def test_new_point_can_be_created_directly_in_template(self):
        response = self.client.post(reverse('template_create_point', args=[self.template.pk]), {
            'kind': DeliveryPoint.Kind.CMD,
            'code': '1370/4628/5180',
            'name': 'Новая точка',
            'address': 'Москва г, Митинская ул, дом № 17, корпус 4',
            'phone': '+79990000000',
            'time_window': '12:00-15:00',
            'comment': 'Тест',
            'enabled_by_default': '1',
        })
        self.assertEqual(response.status_code, 302)
        point = DeliveryPoint.objects.get(code='1370/4628/5180')
        self.assertEqual(point.address, 'Москва, ул Митинская 17к4')
        item = RouteTemplateItem.objects.get(template=self.template, point=point)
        self.assertEqual(item.time_window, '12:00-15:00')
        self.assertEqual(item.comment, 'Тест')

