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

    def test_quick_tunnel_uses_tcp_fallback_and_fresh_journal_entries(self):
        script = self.script()
        self.assertIn('tunnel --protocol http2 --url', script)
        self.assertIn('RestartSec=20', script)
        self.assertIn('--since "$TUNNEL_LOG_SINCE"', script)

    def test_quick_tunnel_reuses_the_existing_service_identity(self):
        script = self.script()
        self.assertNotIn('APP_USER=courierctl', script)
        self.assertNotIn('APP_GROUP=courierctl', script)
        self.assertIn('systemctl show "$APP_SERVICE" --property=User --value', script)
        self.assertIn("stat -c '%U' \"$APP_DIR\"", script)

    def test_quick_tunnel_trusts_its_external_csrf_origin(self):
        self.assertIn(
            "add_csv('DJANGO_CSRF_TRUSTED_ORIGINS','https://*.trycloudflare.com')",
            self.script(),
        )
