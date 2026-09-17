from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class QuickTunnelDeploymentTests(SimpleTestCase):
    def script(self):
        return (
            Path(settings.BASE_DIR) / 'deploy' / 'enable_cloudflare_quick_tunnel.sh'
        ).read_text(encoding='utf-8')

    def test_quick_tunnel_preserves_strict_control_portal_routing(self):
        script = self.script()
        self.assertIn('COURIER_CONTROL_TUNNEL_HOST', script)
        self.assertIn('--http-host-header $ORIGIN_HOST', script)

    def test_quick_tunnel_trusts_its_external_csrf_origin(self):
        self.assertIn(
            "add_csv('DJANGO_CSRF_TRUSTED_ORIGINS','https://*.trycloudflare.com')",
            self.script(),
        )
