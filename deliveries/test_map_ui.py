from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import Delivery, DeliveryPoint


class LazyMapUiTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(username='map-dispatcher', password='pass', role=User.Role.DISPATCHER)
        self.courier = User.objects.create_user(username='map-courier', password='pass', role=User.Role.COURIER)
        self.point = DeliveryPoint.objects.create(
            name='Map point',
            address='Москва, Красная площадь, 1',
            latitude='55.755800',
            longitude='37.617700',
            geocode_status=DeliveryPoint.GeocodeStatus.OK,
        )
        self.delivery = Delivery.objects.create(
            delivery_date=timezone.localdate(),
            point=self.point,
            address=self.point.address,
            courier=self.courier,
            route_order=1,
            status=Delivery.Status.IN_PROGRESS,
        )

    @override_settings(YANDEX_MAPS_JS_API_KEY='browser-key', YANDEX_MAPS_LANG='en_US')
    def test_dispatcher_map_api_is_not_eager_script(self):
        self.client.login(username='map-dispatcher', password='pass')
        response = self.client.get(reverse('dispatcher_dashboard'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('data-map-instance="dispatcher-map-points"', html)
        self.assertIn('lang=en_US', html)
        self.assertIn('cc:map-visible', html)
        self.assertNotIn('<script src="https://api-maps.yandex.ru/v3/', html)

    @override_settings(YANDEX_MAPS_JS_API_KEY='browser-key', YANDEX_MAPS_LANG='ru_RU')
    def test_courier_map_stays_secondary_and_lazy(self):
        self.client.login(username='map-courier', password='pass')
        response = self.client.get(reverse('courier_today'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('data-map-instance="courier-map-points"', html)
        self.assertIn('Загрузится только при открытии этого блока', html)
        self.assertIn('IntersectionObserver', html)
        self.assertNotIn('<script src="https://api-maps.yandex.ru/v3/', html)

    @override_settings(YANDEX_MAPS_JS_API_KEY='')
    def test_missing_browser_key_keeps_list_working(self):
        self.client.login(username='map-courier', password='pass')
        response = self.client.get(reverse('courier_today'))
        self.assertContains(response, 'Карта готова к подключению')
        self.assertContains(response, self.point.address)
