from django.test import TestCase, override_settings
from django.utils import timezone

from .geocoding import geocode_point, geocode_pending_points
from .map_data import delivery_map_items
from .models import Delivery, DeliveryPoint


class MapFoundationTests(TestCase):
    def setUp(self):
        self.point = DeliveryPoint.objects.create(name='Map point', address='Москва, Красная площадь, 1')

    @override_settings(YANDEX_GEOCODER_API_KEY='')
    def test_geocoder_without_key_is_safe_noop(self):
        self.assertFalse(geocode_point(self.point))
        self.point.refresh_from_db()
        self.assertEqual(self.point.geocode_status, DeliveryPoint.GeocodeStatus.PENDING)
        self.assertTrue(geocode_pending_points()['skipped_no_key'])

    def test_map_excludes_unresolved_points(self):
        delivery = Delivery.objects.create(delivery_date=timezone.localdate(), point=self.point, address=self.point.address)
        self.assertEqual(delivery_map_items([delivery]), [])

    def test_map_uses_yandex_longitude_latitude_order(self):
        self.point.longitude = '37.617700'
        self.point.latitude = '55.755800'
        self.point.geocode_status = DeliveryPoint.GeocodeStatus.OK
        self.point.save()
        delivery = Delivery.objects.create(delivery_date=timezone.localdate(), point=self.point, address=self.point.address, route_order=3)
        self.assertEqual(delivery_map_items([delivery])[0]['coordinates'], [37.6177, 55.7558])
