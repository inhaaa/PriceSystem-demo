"""공개 로그인 장식의 로컬 자산·비간섭·모바일 대체 화면 계약."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class LoginSceneTests(unittest.TestCase):
    def read_asset(self, name):
        path = ROOT / "static" / name
        self.assertTrue(path.is_file(), f"공개 로그인 자산이 필요합니다: {name}")
        return path.read_text(encoding="utf-8")

    def test_renderer_is_a_client_only_component_without_business_state(self):
        self.assertTrue((ROOT / "demo/login_scene.py").is_file(), "공개 장식 렌더러가 필요합니다")
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.login_scene import render_login_scene\n"
            "st.session_state.setdefault('kept_value', '보존')\n"
            "render_login_scene()\n"
            "with st.form('native_form'):\n"
            "    st.markdown('<div id=\"login-card-root\"></div>', unsafe_allow_html=True)\n"
            "    username = st.text_input('아이디', key='login_username')\n"
            "    submitted = st.form_submit_button('로그인', key='login_submit')\n"
            "if submitted: st.session_state['received_username'] = username\n"
        ).run()
        self.assertFalse(app.exception)
        scene = [item for item in app.get("bidi_component")
                 if item.proto.component_name.endswith("pricesystem_login_scene")]
        self.assertEqual(len(scene), 1)
        self.assertIn("ps-login-page-marker", "\n".join(item.value for item in app.markdown))
        app.text_input(key="login_username").set_value("admin")
        app.button(key="login_submit").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["received_username"], "admin")
        self.assertEqual(app.session_state["kept_value"], "보존")

    def test_local_scene_has_a_static_price_band_fallback_and_no_focusable_controls(self):
        html = self.read_asset("login-scene.html")
        self.assertIn('class="ps-login-fallback"', html)
        self.assertIn('class="ps-login-visual" aria-hidden="true"', html)
        self.assertIn("선정 기준", html)
        self.assertIn("선정 가격", html)
        for control in ("<button", "<input", "<iframe", "tabindex="):
            self.assertNotIn(control, html)
        self.assertNotIn("http", html)

    def test_scene_stops_motion_and_disposes_gpu_resources_without_network_assets(self):
        js = self.read_asset("login-scene.js")
        self.assertIn("/app/static/vendor/three.module.min.js", js)
        self.assertIn("prefers-reduced-motion: reduce", js)
        self.assertIn("!document.hidden", js)
        self.assertIn("!mobile.matches", js)
        self.assertIn("1000 / 30", js)
        self.assertIn("webglcontextlost", js)
        self.assertIn("renderer?.forceContextLoss()", js)
        self.assertIn("resizeObserver.disconnect()", js)
        self.assertIn("return dispose", js)
        self.assertNotIn("fetch(", js)
        self.assertNotIn("https://", js)
        self.assertNotIn("localStorage", js)
        self.assertNotIn("PriceSys", js)

    def test_layout_preserves_native_form_and_safely_stacks_the_artwork_on_mobile(self):
        css = self.read_asset("login-scene.css")
        self.assertIn("#login-card-root", css)
        self.assertIn("pointer-events: none", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        self.assertIn("@media (max-width: 900px)", css)
        self.assertIn(".st-key-pricesystem_login_scene", css)
        self.assertIn("--ps-login-action: #204e3e", css)
        self.assertNotIn(".ps-theme-tools", css)

    def test_public_login_page_mounts_one_scene_and_keeps_native_form_return_values(self):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.ui import render_login_page\n"
            "st.session_state['login_result'] = render_login_page()\n"
        ).run()
        self.assertFalse(app.exception)
        scenes = [item for item in app.get("bidi_component")
                  if item.proto.component_name.endswith("pricesystem_login_scene")]
        self.assertEqual(len(scenes), 1)
        self.assertEqual([item.key for item in app.text_input], ["login_username", "login_password"])
        app.text_input(key="login_username").set_value("admin")
        app.text_input(key="login_password").set_value("password")
        app.button(key="login_submit").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["login_result"], ("admin", "password", True))


if __name__ == "__main__":
    unittest.main()
