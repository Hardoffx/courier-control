from django.test import TestCase


class PwaSecurityTests(TestCase):
    def test_service_worker_does_not_intercept_application_requests(self):
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        script = response.content.decode()
        self.assertNotIn("addEventListener('fetch'", script)
        self.assertNotIn('respondWith', script)
        self.assertNotIn("/dispatcher/", script)
        self.assertNotIn("/courier/", script)
        self.assertIn('caches.keys()', script)
        self.assertIn('caches.delete', script)

    def test_service_worker_is_not_http_cached(self):
        response = self.client.get('/service-worker.js')
        self.assertIn('no-cache', response.get('Cache-Control', ''))
