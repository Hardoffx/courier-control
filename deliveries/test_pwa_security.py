from django.test import TestCase


class PwaSecurityTests(TestCase):
    """Regression tests for the retired PWA/service-worker architecture.

    Production uses hostname-based portal isolation, so requests in these
    tests must use a real portal hostname instead of Django's default
    ``testserver`` host.
    """

    CONTROL_HOST = 'control.routecontrol.ru'

    def get_control(self, path):
        return self.client.get(path, HTTP_HOST=self.CONTROL_HOST)

    def test_pages_do_not_register_service_worker(self):
        response = self.get_control('/login/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('serviceWorker.register', html)
        self.assertNotIn('navigator.serviceWorker.register', html)

    def test_legacy_service_worker_self_destructs(self):
        response = self.get_control('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        script = response.content.decode()
        self.assertIn('self.registration.unregister()', script)
        self.assertIn('caches.keys()', script)
        self.assertNotIn("addEventListener('fetch'", script)
        self.assertNotIn('caches.match(', script)

    def test_legacy_service_worker_is_never_cached(self):
        response = self.get_control('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        cache_control = response.get('Cache-Control', '')
        self.assertIn('no-store', cache_control)
        self.assertIn('no-cache', cache_control)
        self.assertEqual(response.get('Clear-Site-Data'), '"cache"')
