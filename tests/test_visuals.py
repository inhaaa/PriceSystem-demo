"""Visual structure and local-only dependencies for the restored demo shell."""
from pathlib import Path
import re
import unittest

from streamlit.testing.v1 import AppTest

from demo import ui


ROOT = Path(__file__).resolve().parents[1]


class VisualStructureTests(unittest.TestCase):
    def test_login_preserves_the_single_diamond_and_form_flow(self):
        self.assertTrue(callable(getattr(ui, "render_login_page", None)), "Login renderer is missing")
        app = AppTest.from_string(
            "from demo.ui import render_login_page\nrender_login_page()"
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key="login_username").label, "아이디")
        self.assertEqual(app.text_input(key="login_password").label, "비밀번호")
        self.assertEqual(app.button(key="login_submit").label, "로그인")
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn('class="login-panel"', markup)
        self.assertIn('id="login-card-root"', markup)
        self.assertIn("admin / admin", markup)
        self.assertLess(markup.index('class="login-panel"'), markup.index('id="login-card-root"'))

    def test_workspace_keeps_both_palettes_and_original_layout_hooks(self):
        theme_file = ROOT / "demo/workspace_theme.py"
        self.assertTrue(theme_file.is_file(), "Workspace theme is missing")
        theme = theme_file.read_text(encoding="utf-8")
        for hook in ("workspace-theme-marker", "workspace_masthead", "workspace_surface",
                     "internal_tab_bar", "data-ps-theme", "workspace-crystal.svg", "diamond-chamber.svg"):
            self.assertIn(hook, theme)
        app = AppTest.from_string(
            "from demo.ui import apply_theme, brand, header\n"
            "apply_theme()\nbrand()\nheader('샘플 제목', '샘플 설명', '데이터 업무')"
        ).run()
        self.assertFalse(app.exception)

    def test_visual_dependencies_are_local_and_complete(self):
        components = ROOT / "demo/visual_components.py"
        self.assertTrue(components.is_file(), "Visual components are missing")
        sources = [components, ROOT / "demo/workspace_theme.py", ROOT / "assets/demo.css", ROOT / "assets/login.css"]
        source = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        assets = set(re.findall(r'/app/static/([A-Za-z0-9_./-]+)', source))
        self.assertGreaterEqual(len(assets), 6)
        for relative in assets:
            self.assertTrue((ROOT / "static" / relative).is_file(), relative)
        for name in ("login-atmosphere.js", "diamond-optics.js"):
            script = (ROOT / "static" / name).read_text(encoding="utf-8")
            self.assertNotRegex(script, r"\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(")
        vendor = (ROOT / "static/vendor/three.module.min.js").read_text(encoding="utf-8")
        self.assertIn("Copyright 2010-2024 Three.js Authors", vendor[:200])
        self.assertIn("SPDX-License-Identifier: MIT", vendor[:200])


if __name__ == "__main__":
    unittest.main()
