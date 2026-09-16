from django.test import TestCase, override_settings

from accounts.models import User


@override_settings(
    DOMAIN_SPLIT_ENABLED=True,
    COURIER_HOST='courier.routecontrol.ru',
    CONTROL_HOST='control.routecontrol.ru',
    ALLOWED_HOSTS=['testserver', '127.0.0.1', 'localhost', 'courier.routecontrol.ru', 'control.routecontrol.ru'],
)
class PortalHostTests(TestCase):
    def setUp(self):
        self.dispatcher = User.objects.create_user(
            username='host-boss', password='pass12345', role=User.Role.DISPATCHER
        )
        self.courier = User.objects.create_user(
            username='host-driver', password='pass12345', role=User.Role.COURIER
        )

    def test_courier_host_hides_dispatcher_and_admin_paths(self):
        self.assertEqual(self.client.get('/dispatcher/', HTTP_HOST='courier.routecontrol.ru').status_code, 404)
        self.assertEqual(self.client.get('/admin/', HTTP_HOST='courier.routecontrol.ru').status_code, 404)

    def test_control_host_hides_courier_paths(self):
        self.assertEqual(self.client.get('/courier/', HTTP_HOST='control.routecontrol.ru').status_code, 404)

    def test_courier_login_rejects_dispatcher_account(self):
        response = self.client.post(
            '/login/',
            {'username': 'host-boss', 'password': 'pass12345'},
            HTTP_HOST='courier.routecontrol.ru',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)
        self.assertContains(response, 'панели управления')

    def test_control_login_rejects_courier_account(self):
        response = self.client.post(
            '/login/',
            {'username': 'host-driver', 'password': 'pass12345'},
            HTTP_HOST='control.routecontrol.ru',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)
        self.assertContains(response, 'курьерской панели')

    def test_correct_accounts_can_login_to_their_portals(self):
        response = self.client.post(
            '/login/',
            {'username': 'host-driver', 'password': 'pass12345'},
            HTTP_HOST='courier.routecontrol.ru',
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

        self.client.logout()
        response = self.client.post(
            '/login/',
            {'username': 'host-boss', 'password': 'pass12345'},
            HTTP_HOST='control.routecontrol.ru',
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_local_health_check_survives_strict_split(self):
        response = self.client.get('/healthz/', HTTP_HOST='127.0.0.1')
        self.assertEqual(response.status_code, 200)

    def test_unknown_public_host_is_hidden_in_strict_mode(self):
        with override_settings(ALLOWED_HOSTS=['legacy.example']):
            response = self.client.get('/login/', HTTP_HOST='legacy.example')
        self.assertEqual(response.status_code, 404)
