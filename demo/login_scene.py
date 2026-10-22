"""로컬 가격 밴드 장식. 로그인 폼과 업무 상태에는 접근하지 않는다."""
from pathlib import Path

import streamlit as st


STATIC = Path(__file__).resolve().parents[1] / "static"


def render_login_scene():
    """기존 native 폼 옆에 테마를 따르는 접근 불가 장식을 배치한다."""
    css = (STATIC / "login-scene.css").read_text(encoding="utf-8")
    st.markdown('<span class="ps-login-page-marker" hidden aria-hidden="true"></span>'
                f'<style id="login-scene-style">{css}</style>', unsafe_allow_html=True)
    scene = st.components.v2.component(
        "pricesystem_login_scene",
        html=(STATIC / "login-scene.html").read_text(encoding="utf-8"),
        js=(STATIC / "login-scene.js").read_text(encoding="utf-8"),
        isolate_styles=False,
    )
    scene(key="pricesystem_login_scene", height=0, data={})
