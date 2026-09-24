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

    def test_template_editor_actions_use_no_reload_workspace(self):
        html = (ROOT / "templates/dispatcher/routes/detail.html").read_text()
        js = (ROOT / "deliveries/static/js/dispatcher-route-editor.js").read_text()
        self.assertIn('id="template-route-editor-workspace"', html)
        self.assertIn('class="ajax-template-form"', html)
        self.assertIn("refreshTemplateWorkspace", js)
        self.assertIn("bindDayToggles", js)

    def test_delivery_filters_update_without_page_reload(self):
        js = (ROOT / "deliveries/static/js/dispatcher-deliveries.js").read_text()
        self.assertIn("refreshDeliveries", js)
        self.assertIn("window.history.replaceState", js)
        self.assertIn("window.addEventListener('popstate'", js)

