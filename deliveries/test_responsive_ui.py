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

    def test_route_template_has_phone_editing_controls(self):
        response = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('template-mobile', html)
        self.assertIn('mobile-template-actions', html)
        self.assertIn('Сохранить время и комментарий', html)
        self.assertIn('↑ Раньше', html)
        self.assertIn('↓ Позже', html)
        self.assertIn('Убрать', html)

    def test_route_generation_controls_remain_on_same_screen(self):
        response = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertContains(response, 'Создать маршрут на конкретный день')
        self.assertContains(response, 'Что едет именно в этот день')
        self.assertContains(response, 'Загрузить Excel в шаблон')
        self.assertContains(response, 'Добавить точки вручную')
        self.assertContains(response, self.point.address)
