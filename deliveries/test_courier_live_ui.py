from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


class CourierLiveUIContracts(SimpleTestCase):
    def test_courier_today_uses_live_module(self):
        html = (ROOT / "templates/courier/today.html").read_text()
        live = (ROOT / "deliveries/static/js/courier-live.js").read_text()
        bindings = (ROOT / "deliveries/static/js/courier-bindings.js").read_text()
        self.assertIn("courier-live.js", html)
        self.assertNotIn("<script type=\"module\">", html)
        self.assertIn("courierActions", live)
        self.assertIn("refreshCourierShell", live)
        self.assertIn("courier:reopen", live)
        self.assertIn("courier-bindings.js", live)
        self.assertIn("SingleAccordion", bindings)
        self.assertIn("hold-done", bindings)

    def test_live_module_covers_all_courier_update_actions(self):
        live = (ROOT / "deliveries/static/js/courier-live.js").read_text()
        for action in ("done", "problem", "phone", "daily_note", "reopen"):
            self.assertIn(f"'{action}'", live)
        self.assertIn("X-Requested-With", live)
        self.assertIn("XMLHttpRequest", live)
