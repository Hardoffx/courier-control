"""Manual route address edits must not be rewritten by Excel import normalization."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import DeliveryPoint, Route, RouteTemplate, RouteTemplateItem
from .point_matching import match_point, normalize_address


class RouteAddressEditingTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(
            username='address-editor-dispatcher', password='test-password',
            role=User.Role.DISPATCHER,
        )
        self.client.force_login(self.dispatcher)
        self.route = Route.objects.create(name='Тест адресов')
        self.template = RouteTemplate.objects.create(
            route=self.route, kind=RouteTemplate.Kind.WEEKDAY,
        )
        self.point = DeliveryPoint.objects.create(
            name='ИНВИТРО Пятницкое', kind=DeliveryPoint.Kind.INVITRO,
            address='Москва, ш Пятницкое 15к3',
        )
        self.item = RouteTemplateItem.objects.create(
            template=self.template, point=self.point, route_order=1,
        )

    def test_manual_address_update_keeps_written_highway_suffix(self):
        address = 'Москва, Пятницкое шоссе 15к3'
        response = self.client.post(
            reverse('template_item_update', args=[self.item.pk]),
            {'action': 'point_address', 'address': address},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['address'], address)
        self.point.refresh_from_db()
        self.assertEqual(self.point.address, address)
        page = self.client.get(reverse('route_detail', args=[self.route.pk]))
        self.assertContains(page, address)

    def test_manual_update_compacts_whitespace_only(self):
        response = self.client.post(
            reverse('template_item_update', args=[self.item.pk]),
            {'action': 'point_address', 'address': '  Москва,  Пятницкое\nшоссе 15к3  '},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.json()['address'], 'Москва, Пятницкое шоссе 15к3')

    def test_legacy_highway_prefix_and_suffix_match_same_point(self):
        for address in (
            'Москва, ш Пятницкое 15к3',
            'Москва, шоссе Пятницкое 15к3',
            'Москва, Пятницкое ш 15к3',
            'Москва, Пятницкое шоссе 15к3',
        ):
            with self.subTest(address=address):
                self.assertEqual(normalize_address(address),
                                 'москва пятницкое шоссе 15к3')
                self.assertEqual(match_point(address=address).point, self.point)
