import json
from urllib.error import URLError
from django.test import TestCase, override_settings
from django.utils import timezone

from .geocoding import geocode_point, geocode_pending_points
from .map_data import delivery_map_items
from .models import Delivery, DeliveryPoint


class FakeResponse:
    def __init__(self,payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return json.dumps(self.payload).encode('utf-8')


class MapFoundationTests(TestCase):
    def setUp(self):
        self.point = DeliveryPoint.objects.create(name='Map point', address='Москва, Красная площадь, 1')

    @override_settings(YANDEX_GEOCODER_API_KEY='')
    def test_geocoder_without_key_is_safe_noop(self):
        self.assertFalse(geocode_point(self.point))
        self.point.refresh_from_db()
        self.assertEqual(self.point.geocode_status, DeliveryPoint.GeocodeStatus.PENDING)
        self.assertTrue(geocode_pending_points()['skipped_no_key'])

    @override_settings(YANDEX_GEOCODER_API_KEY='test-key')
    def test_geocoder_success_saves_yandex_coordinate_order(self):
        payload={'response':{'GeoObjectCollection':{'featureMember':[{'GeoObject':{'Point':{'pos':'37.617700 55.755800'},'metaDataProperty':{'GeocoderMetaData':{'text':'Россия, Москва, Красная площадь, 1'}}}}]}}}
        self.assertTrue(geocode_point(self.point,opener=lambda request,timeout: FakeResponse(payload)))
        self.point.refresh_from_db()
        self.assertEqual(str(self.point.longitude),'37.617700'); self.assertEqual(str(self.point.latitude),'55.755800'); self.assertEqual(self.point.geocode_status,DeliveryPoint.GeocodeStatus.OK); self.assertTrue(self.point.geocoded_at)

    @override_settings(YANDEX_GEOCODER_API_KEY='test-key')
    def test_transient_geocoder_failure_stays_retryable(self):
        def fail(request,timeout): raise URLError('temporary')
        self.assertFalse(geocode_point(self.point,opener=fail))
        self.point.refresh_from_db()
        self.assertEqual(self.point.geocode_status,DeliveryPoint.GeocodeStatus.PENDING); self.assertIsNone(self.point.latitude); self.assertIsNone(self.point.geocoded_at)

    @override_settings(YANDEX_GEOCODER_API_KEY='test-key')
    def test_no_result_is_recorded_as_failed(self):
        payload={'response':{'GeoObjectCollection':{'featureMember':[]}}}
        self.assertFalse(geocode_point(self.point,opener=lambda request,timeout: FakeResponse(payload)))
        self.point.refresh_from_db()
        self.assertEqual(self.point.geocode_status,DeliveryPoint.GeocodeStatus.FAILED); self.assertTrue(self.point.geocoded_at)

    @override_settings(YANDEX_GEOCODER_API_KEY='test-key')
    def test_forced_transient_failure_preserves_existing_good_coordinates(self):
        self.point.longitude='37.617700'; self.point.latitude='55.755800'; self.point.geocode_status=DeliveryPoint.GeocodeStatus.OK; self.point.geocoded_address=self.point.address; self.point.geocoded_at=timezone.now(); self.point.save()
        def fail(request,timeout): raise URLError('temporary')
        self.assertFalse(geocode_point(self.point,force=True,opener=fail))
        self.point.refresh_from_db()
        self.assertEqual(self.point.geocode_status,DeliveryPoint.GeocodeStatus.OK); self.assertEqual(str(self.point.longitude),'37.617700'); self.assertEqual(str(self.point.latitude),'55.755800')

    def test_address_change_invalidates_stale_destination_coordinates(self):
        self.point.longitude='37.617700'; self.point.latitude='55.755800'; self.point.geocode_status=DeliveryPoint.GeocodeStatus.OK; self.point.geocoded_address=self.point.address; self.point.geocoded_at=timezone.now(); self.point.save()
        self.point.address='Москва, Новый адрес, 2'; self.point.save(update_fields=['address'])
        self.point.refresh_from_db()
        self.assertEqual(self.point.geocode_status,DeliveryPoint.GeocodeStatus.PENDING); self.assertIsNone(self.point.longitude); self.assertIsNone(self.point.latitude); self.assertEqual(self.point.geocoded_address,''); self.assertIsNone(self.point.geocoded_at)

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
