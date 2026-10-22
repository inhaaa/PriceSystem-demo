"""브라우저 소유 디자인 설정의 공개 자산·팔레트·컴포넌트 계약."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo import preferences


ROOT = Path(__file__).resolve().parents[1]


def luminance(value):
    channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    channels = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(channels, (.2126, .7152, .0722)))


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


class PreferenceTests(unittest.TestCase):
    def test_palette_names_legacy_alias_and_unknown_input_are_safe(self):
        self.assertEqual(list(preferences.PALETTES), ['초록색', '파란색', '핑크색', '검정색'])
        self.assertEqual(preferences.theme_css('하늘색'), preferences.theme_css('파란색'))
        self.assertEqual(preferences.theme_css('} body {display:none}'), preferences.theme_css('초록색'))
        self.assertEqual(preferences.login_theme_css('} body {display:none}'), preferences.login_theme_css('초록색'))
        self.assertEqual(preferences.font_css('} body {display:none}'), '')

    def test_light_dark_actions_and_sidebar_colors_have_readable_contrast(self):
        for name, palette in preferences.PALETTES.items():
            for surface in ('action', 'hover'):
                self.assertGreaterEqual(contrast(palette[surface], palette['ink']), 4.5, (name, surface))
            for surface in ('dark_action', 'dark_hover'):
                self.assertGreaterEqual(contrast(palette[surface], palette['dark_ink']), 4.5, (name, surface))
            for ink in ('sidebar_ink', 'muted', 'sidebar_accent'):
                self.assertGreaterEqual(contrast(palette['sidebar'], palette[ink]), 4.5, (name, ink))

    def test_public_login_and_workspace_both_receive_saved_font_and_theme(self):
        for name in preferences.PALETTES:
            self.assertIn('--ps-primary:', preferences.theme_css(name))
            css = preferences.login_theme_css(name)
            self.assertIn('body:has(#login-card-root)', css)
            self.assertIn('--ps-login-forest:', css)
            self.assertIn(preferences.PALETTES[name]['hover'], css)
        self.assertEqual(preferences.font_css('default'), '')
        for name in ('pretendard', 'suit'):
            css = preferences.font_css(name)
            self.assertIn(f'body[data-ps-font="{name}"]', css)
            self.assertIn(':has(#login-card-root)', css)
            self.assertIn('.workspace-theme-marker', css)
            self.assertIn('stIconMaterial', css)
            self.assertNotIn('https://', css)

    def test_login_form_and_price_scene_inherit_the_same_selected_palette(self):
        for name, palette in preferences.PALETTES.items():
            css = preferences.login_theme_css(name)
            for variable, field in (('action', 'action'), ('hover', 'hover'),
                                    ('deep', 'sidebar'), ('accent', 'accent')):
                self.assertIn(f'--ps-login-{variable}: {palette[field]};', css, name)
            self.assertIn('body:has(#login-card-root)', css)

    def test_font_files_are_original_woff2_with_bundled_open_font_licenses(self):
        files = (
            ('PretendardVariable.woff2', 'Pretendard-OFL.txt',
             '9599f12fd42fc0bce1cd50b47a0c022e108d7aa64dd0d1bb0ed44f3282d900b4'),
            ('SUIT-Variable.woff2', 'SUIT-OFL.txt',
             'aa894a204d5a6fbae259dac6868d350cbd373a390caee0313f92946af741df23'),
        )
        for filename, license_name, digest in files:
            binary = (ROOT / 'static/fonts' / filename).read_bytes()
            self.assertEqual(binary[:4], b'wOF2')
            self.assertEqual(sha256(binary).hexdigest(), digest)
            license_text = (ROOT / 'static/fonts' / license_name).read_text(encoding='utf-8')
            self.assertIn('SIL OPEN FONT LICENSE Version 1.1', license_text)
            self.assertIn('Copyright', license_text)

    def test_render_registers_one_client_component_with_all_public_assets(self):
        with patch.object(preferences.st, 'markdown') as markdown, \
             patch.object(preferences.st.components.v2, 'component') as component:
            preferences.render_preferences()
        markdown.assert_called_once()
        styles = markdown.call_args.args[0]
        for name in preferences.PALETTES:
            self.assertIn(f'body[data-ps-color="{name}"]', styles)
        component.assert_called_once()
        declaration = component.call_args.kwargs
        self.assertIn('role="dialog"', declaration['html'])
        self.assertIn('max-width: calc(100vw - 24px)', declaration['css'])
        self.assertIn('localStorage.setItem', declaration['js'])
        data = component.return_value.call_args.kwargs['data']
        self.assertEqual(data['storageKey'], 'pricesystem.color-theme.v1')
        self.assertEqual(data['fontStorageKey'], 'pricesystem.font.v1')
        self.assertEqual(data['defaultTheme'], '초록색')
        self.assertEqual(data['defaultFont'], 'pretendard')
        self.assertEqual([font['id'] for font in data['fonts']], ['default', 'pretendard', 'suit'])
        self.assertEqual(data['themeAliases'], {'하늘색': '파란색'})
        self.assertTrue(all(value.startswith('/app/static/fonts/') for value in data['fontFaces'].values()))

    def test_rerun_keeps_one_menu_and_preserves_business_state(self):
        app = AppTest.from_string(
            'import streamlit as st\n'
            'from demo.store import DemoStore\n'
            'from demo.preferences import render_preferences\n'
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            'render_preferences()\n', default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results(), store.categories())
        for _ in range(2):
            app.run()
            self.assertFalse(app.exception)
            components = app.get('bidi_component')
            self.assertEqual(len(components), 1)
            data = json.loads(components[0].proto.json)
            self.assertEqual(len(data['themes']), 4)
            self.assertEqual(len(data['fonts']), 3)
            self.assertEqual(len([item for item in app.markdown if 'id="workbench-color-theme"' in item.value]), 1)
        self.assertEqual((store.notices(), store.submissions(), store.results(), store.categories()), before)

    def test_app_login_workspace_and_logout_each_keep_exactly_one_preferences_menu(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
        self.addCleanup(lambda: app.session_state['store'].close() if 'store' in app.session_state else None)

        def assert_components(scene_count):
            self.assertFalse(app.exception)
            components = app.get('bidi_component')
            menus = [item for item in components if item.proto.component_name.endswith('workbench_color_menu')]
            scenes = [item for item in components if item.proto.component_name.endswith('pricesystem_login_scene')]
            self.assertEqual(len(menus), 1)
            self.assertEqual(len(scenes), scene_count)

        assert_components(1)
        app.run()
        assert_components(1)
        app.text_input(key='login_username').set_value('admin')
        app.text_input(key='login_password').set_value('admin')
        app.button(key='login_submit').click().run()
        assert_components(0)
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results(), store.categories())
        app.run()
        assert_components(0)
        self.assertEqual((store.notices(), store.submissions(), store.results(), store.categories()), before)
        app.button(key='logout').click().run()
        assert_components(1)


if __name__ == '__main__':
    unittest.main()
