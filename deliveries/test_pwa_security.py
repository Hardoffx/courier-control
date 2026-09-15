from django.test import TestCase


class PwaSecurityTests(TestCase):
    def test_service_worker_never_caches_login_or_operational_html(self):
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        script = response.content.decode()
        self.assertNotIn("addAll(['/login/'])", script)
        self.assertNotIn("caches.match(e.request)", script)
        self.assertIn("url.pathname.startsWith('/static/')", script)
        self.assertNotIn("/dispatcher/", script)
        self.assertNotIn("/courier/", script)

    def test_service_worker_is_not_http_cached(self):
        response = self.client.get('/service-worker.js')
        self.assertIn('no-cache', response.get('Cache-Control', ''))
