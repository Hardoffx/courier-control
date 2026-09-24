from pathlib import Path
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]

class UIContractTests(SimpleTestCase):
    def test_shared_design_tokens_exist(self):
        css = (ROOT / "deliveries/static/css/tokens.css").read_text()
        for token in ("--ui-control-h", "--ui-control-radius", "--ui-card-radius", "--ui-space-4"):
            self.assertIn(token, css)

    def test_base_loads_tokens_before_app_css(self):
        html = (ROOT / "templates/base.html").read_text()
        self.assertIn("css/tokens.css", html)
        self.assertLess(html.index("css/tokens.css"), html.index("css/app.css"))

    def test_ui_preview_route_exists(self):
        urls = (ROOT / "deliveries/dispatcher_urls.py").read_text()
        self.assertIn("ui-preview/", urls)

    def test_stats_has_no_inline_style_block(self):
        html = (ROOT / "templates/dispatcher/stats.html").read_text()
        self.assertNotIn("<style>", html)

    def test_route_run_actions_use_no_reload_workspace(self):
        html = (ROOT / "templates/dispatcher/route_run_detail.html").read_text()
        js = (ROOT / "deliveries/static/js/dispatcher-route-editor.js").read_text()
        self.assertIn('id="run-live-workspace"', html)
        self.assertIn('class="ajax-run-form"', html)
        self.assertIn("refreshRunWorkspace", js)
        self.assertIn("document.addEventListener('submit'", js)

