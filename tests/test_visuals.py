"""Visual structure and local-only dependencies for the restored demo shell."""
from pathlib import Path
import re
import unittest
from urllib.parse import urljoin

from streamlit.testing.v1 import AppTest

from demo import ui


ROOT = Path(__file__).resolve().parents[1]


def contrast_ratio(first, second):
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                  for value in channels]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class VisualStructureTests(unittest.TestCase):
    def test_mobile_sidebar_and_header_have_opaque_backgrounds(self):
        theme = (ROOT / "demo/workspace_theme.py").read_text(encoding="utf-8")
        mobile = theme.split('@media (max-width: 768px) {')
        for scope, color in (("__SCOPE__", "#111"), ("__LIGHT__", "#ffffff")):
            for surface in ("stSidebar", "stHeader"):
                rule = re.escape(scope + ' [data-testid="' + surface + '"]')
                matches = [re.search(rule + r'\s*\{([^}]+)\}', block) for block in mobile[1:]]
                styles = [match.group(1) for match in matches if match]
                self.assertTrue(any(f"background: {color};" in style for style in styles),
                                f"{scope} {surface} must cover content underneath on mobile")

    def test_primary_and_disabled_buttons_have_readable_text_in_both_themes(self):
        css = (ROOT / "assets/demo.css").read_text(encoding="utf-8")
        theme = (ROOT / "demo/workspace_theme.py").read_text(encoding="utf-8")
        disabled = re.search(r'\):disabled\s*\{([^}]+)\}', css).group(1)
        disabled_style = dict(re.findall(r'([\w-]+)\s*:\s*([^;]+);', disabled))
        for name, block in re.findall(r'__(SCOPE|LIGHT)__\s*\{([^}]+)\}', theme):
            palette = dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', block))
            for state, text, background in (
                ("primary", "#ffffff", palette["--ps-action"]),
                ("primary hover", "#ffffff", palette["--ps-action-hover"]),
                ("disabled", disabled_style["color"], disabled_style["background"]),
            ):
                with self.subTest(theme=name, state=state):
                    def resolve(value):
                        return palette[value[4:-1]] if value.startswith("var(") else value
                    self.assertGreaterEqual(contrast_ratio(resolve(text), resolve(background)), 4.5)
        self.assertEqual(disabled_style["opacity"], "1", "Opacity must not wash out disabled labels")
        self.assertEqual(disabled_style["cursor"], "not-allowed")

    def test_primary_theme_rules_cover_form_buttons_and_preserve_disabled_styles(self):
        theme = (ROOT / "demo/workspace_theme.py").read_text(encoding="utf-8")
        for scope in ("__SCOPE__", "__LIGHT__"):
            rule = re.search(re.escape(scope) + r' \[data-testid="stButton"\] button\[kind="primary"\][^{]+\{', theme).group()
            with self.subTest(scope=scope):
                self.assertIn('[kind="primaryFormSubmit"]', rule)
                self.assertEqual(rule.count(":not(:disabled)"), 2)

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
        urls = set(re.findall(r'(?:\./|/)?app/static/[A-Za-z0-9_./-]+', source))
        for base in ("https://example.invalid/", "https://example.invalid/~/+/"):
            for url in urls:
                self.assertTrue(urljoin(base, url).startswith(base + "app/static/"), url)
        assets = {url.split("app/static/", 1)[1] for url in urls}
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
