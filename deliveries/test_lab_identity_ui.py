from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .lab_catalog import resolve_known_lab
from .models import Delivery, DeliveryPoint
from .point_matching import resolve_point


class LabIdentityUiTests(TestCase):
    def setUp(self):
        self.courier = User.objects.create_user(username='lab-courier', password='pass', role=User.Role.COURIER)
        self.dispatcher = User.objects.create_user(username='lab-dispatcher', password='pass', role=User.Role.DISPATCHER)

    def test_known_cmd_address_carries_lpu_from_bot_catalog(self):
        known = resolve_known_lab('Москва, ул. Дубравная, д. 46')
        self.assertIsNotNone(known)
        self.assertEqual(known.kind, DeliveryPoint.Kind.CMD)
        self.assertEqual(known.facility_code, '458')

    def test_point_creation_is_enriched_with_cmd_lpu(self):
        match = resolve_point('', 'Москва, ул. Дубравная, д. 46', create=True)
        self.assertTrue(match.created)
        self.assertEqual(match.point.kind, DeliveryPoint.Kind.CMD)
        self.assertEqual(match.point.code, '458')

    def test_courier_screen_shows_badge_lpu_and_external_yandex_link(self):
        delivery = Delivery.objects.create(
            delivery_date=timezone.localdate(), courier=self.courier, route_order=1,
            address='Москва, ул. Дубравная, д. 46', status=Delivery.Status.IN_PROGRESS,
        )
        self.client.login(username='lab-courier', password='pass')
        response = self.client.get(reverse('courier_today'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lab-badge--cmd')
        self.assertContains(response, 'ЛПУ 458')
        self.assertContains(response, 'Открыть в Яндекс.Картах')
        self.assertContains(response, 'https://yandex.ru/maps/?text=')
        self.assertNotContains(response, 'route-map')
        self.assertEqual(delivery.lab_kind, DeliveryPoint.Kind.CMD)

    def test_courier_uses_one_expandable_route_item_per_delivery(self):
        delivery = Delivery.objects.create(
            delivery_date=timezone.localdate(), courier=self.courier, route_order=7,
            address='Москва г, ул Митинская 27', status=Delivery.Status.IN_PROGRESS,
        )
        self.client.login(username='lab-courier', password='pass')
        response = self.client.get(reverse('courier_today'))
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(html.count(f'id="delivery-{delivery.pk}"'), 1)
        self.assertContains(response, 'class="route-item')
        self.assertContains(response, 'class="route-detail-body compact-route-detail"')
        self.assertNotContains(response, 'class="card delivery-detail"')
        # ManifestStaticFilesStorage fingerprints production assets, so assert
        # the stable asset stem rather than the unhashed development filename.
        self.assertContains(response, 'route-accordion.')
        self.assertContains(response, '.css')

    def test_dispatcher_screen_shows_lab_identity(self):
        Delivery.objects.create(
            delivery_date=timezone.localdate(), courier=self.courier, route_order=1,
            address='Москва г, ул Митинская 27', status=Delivery.Status.NEW,
        )
        self.client.login(username='lab-dispatcher', password='pass')
        response = self.client.get(reverse('dispatcher_deliveries'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lab-badge--invitro')
        self.assertContains(response, 'ИНВИТРО')
        self.assertNotContains(response, 'Список + карта')
