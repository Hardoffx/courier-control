from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class PwaSecurityTests(SimpleTestCase):
    """Regression tests for the retired PWA/service-worker architecture.

    Keep these checks independent from the production staticfiles manifest:
    their purpose is to prevent service-worker registration from returning,
    not to test collectstatic/WhiteNoise.
    """

    def test_base_template_does_not_register_service_worker(self):
        template = (Path(settings.BASE_DIR) / 'templates' / 'base.html').read_text(encoding='utf-8')
        self.assertNotIn('serviceWorker.register', template)
        self.assertNotIn('navigator.serviceWorker.register', template)

    def test_legacy_service_worker_self_destructs(self):
        from config.pilot_views import service_worker

        response = service_worker(None)
        self.assertEqual(response.status_code, 200)
        script = response.content.decode()
        self.assertIn('self.registration.unregister()', script)
        self.assertIn('caches.keys()', script)
        self.assertNotIn("addEventListener('fetch'", script)
        self.assertNotIn('caches.match(', script)

    def test_legacy_service_worker_is_never_cached(self):
        from config.pilot_views import service_worker

        response = service_worker(None)
        cache_control = response.get('Cache-Control', '')
        self.assertIn('no-store', cache_control)
        self.assertIn('no-cache', cache_control)
        self.assertEqual(response.get('Clear-Site-Data'), '"cache"')
