from django.test import TestCase


class PwaSecurityTests(TestCase):
    def test_pages_do_not_register_service_worker(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('serviceWorker.register', html)
        self.assertNotIn('navigator.serviceWorker.register', html)

    def test_legacy_service_worker_self_destructs(self):
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        script = response.content.decode()
        self.assertIn('self.registration.unregister()', script)
        self.assertIn('caches.keys()', script)
        self.assertNotIn("addEventListener('fetch'", script)
        self.assertNotIn('caches.match(', script)

    def test_legacy_service_worker_is_never_cached(self):
        response = self.client.get('/service-worker.js')
        cache_control = response.get('Cache-Control', '')
        self.assertIn('no-store', cache_control)
        self.assertIn('no-cache', cache_control)
        self.assertEqual(response.get('Clear-Site-Data'), '"cache"')
