"""Login keeps native form behavior within the compact product entry surface."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

from demo.visual_components import login_panel_html


ROOT = Path(__file__).resolve().parents[1]


class AccessDesignTests(unittest.TestCase):
    def test_login_uses_a_compact_heading_and_native_submit_values(self):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.ui import render_login_page\n"
            "username, password, submitted = render_login_page()\n"
            "st.session_state['login_result'] = (username, password, submitted)\n"
        ).run()
        self.assertFalse(app.exception)
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn('<h2>로그인</h2>', markup)
        self.assertIn('계정 정보를 입력해 주세요.', markup)
        self.assertIn('admin / admin', markup)
        self.assertNotIn('WORKSPACE ACCESS', markup)
        app.text_input(key='login_username').set_value('admin')
        app.text_input(key='login_password').set_value('admin')
        app.button(key='login_submit').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['login_result'], ('admin', 'admin', True))

    def test_description_stays_explicit_and_escaped(self):
        markup = login_panel_html('PriceSystem', '입찰가격선정시스템', '<계정 안내>')
        self.assertIn('&lt;계정 안내&gt;', markup)
        self.assertNotIn('<계정 안내>', markup)

    def test_access_surface_accounts_for_focus_errors_and_small_screens(self):
        css = (ROOT / 'assets/login.css').read_text(encoding='utf-8')
        self.assertIn(':focus-within', css)
        self.assertIn(':focus-visible', css)
        self.assertIn('[data-testid="stAlert"]', css)
        self.assertIn('@media (max-width: 768px)', css)
        self.assertNotIn('grid-template-columns', css)
        self.assertNotIn('login-panel__headline', css)


if __name__ == '__main__':
    unittest.main()
