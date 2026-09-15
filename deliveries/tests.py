from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from .models import Delivery, DeliveryEvent, DeliveryPoint


class DeliveryWorkflowTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(username='dispatcher', password='pass', role=User.Role.DISPATCHER)
        self.courier = User.objects.create_user(username='courier', password='pass', role=User.Role.COURIER)
        self.other = User.objects.create_user(username='other', password='pass', role=User.Role.COURIER)
        self.delivery = Delivery.objects.create(delivery_date=timezone.localdate(), address='Москва, Тестовая 1', route_order=1)

    def test_point_kind_fallback(self):
        self.assertEqual(Delivery.infer_point_kind('458'), DeliveryPoint.Kind.CMD)
        self.assertEqual(Delivery.infer_point_kind('ИНВИТРО Митино'), DeliveryPoint.Kind.INVITRO)
        self.assertEqual(Delivery.infer_point_kind('Склад'), DeliveryPoint.Kind.SERVICE)
        self.assertEqual(Delivery.infer_point_kind('ЛИТЕХ'), DeliveryPoint.Kind.EXTERNAL)

    def test_dispatcher_can_assign_courier(self):
        self.client.login(username='dispatcher', password='pass')
        response = self.client.post(reverse('dispatcher_assign', args=[self.delivery.pk]), {'courier_id': self.courier.pk})
        self.assertEqual(response.status_code, 302)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.courier, self.courier)
        self.assertEqual(self.delivery.status, Delivery.Status.IN_PROGRESS)
        self.assertTrue(DeliveryEvent.objects.filter(delivery=self.delivery, action='assigned').exists())

    def test_courier_cannot_complete_another_couriers_delivery(self):
        self.delivery.courier = self.other
        self.delivery.save()
        self.client.login(username='courier', password='pass')
        response = self.client.post(reverse('courier_update', args=[self.delivery.pk]), {'action': 'done'})
        self.assertEqual(response.status_code, 404)

    def test_completion_without_gps_is_allowed(self):
        self.delivery.courier = self.courier
        self.delivery.status = Delivery.Status.IN_PROGRESS
        self.delivery.save()
        self.client.login(username='courier', password='pass')
        response = self.client.post(reverse('courier_update', args=[self.delivery.pk]), {'action': 'done'})
        self.assertEqual(response.status_code, 302)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, Delivery.Status.DONE)
        self.assertIsNotNone(self.delivery.completed_at)
        self.assertIsNone(self.delivery.completed_latitude)

    def test_reorder_renumbers_remaining_route(self):
        first = self.delivery
        first.courier = self.courier
        first.save()
        second = Delivery.objects.create(delivery_date=timezone.localdate(), address='Москва, Тестовая 2', courier=self.courier, route_order=2)
        self.client.login(username='courier', password='pass')
        response = self.client.post(reverse('courier_reorder', args=[second.pk]), {'direction': 'up'})
        self.assertEqual(response.status_code, 302)
        first.refresh_from_db(); second.refresh_from_db()
        self.assertEqual(second.route_order, 1)
        self.assertEqual(first.route_order, 2)

    def test_courier_cannot_open_point_directory(self):
        self.client.login(username='courier', password='pass')
        response = self.client.get(reverse('point_list'))
        self.assertEqual(response.status_code, 403)
