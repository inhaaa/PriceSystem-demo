"""Display helpers and reviewed visual assets; no business dependencies."""
import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from demo.visual_components import (
    home_action_card_html,
    login_cursor_glow_script,
    login_gem_webgl_script,
    login_panel_html,
    page_header_html,
    sidebar_brand_html,
    workspace_tab_scroll_script,
)
from demo.workspace_theme import (
    WORKSPACE_THEME_CSS,
    render_sheet_theme_bridge,
    workspace_theme_marker_html,
)


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def image_uri(name):
    return "data:image/svg+xml;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def apply_theme(login=False):
    tokens = (ASSETS / "tokens.css").read_text(encoding="utf-8")
    css = (ASSETS / ("login.css" if login else "demo.css")).read_text(encoding="utf-8")
    if login:
        st.markdown(f"<style>{tokens}\n{css}</style>", unsafe_allow_html=True)
        return
    st.markdown(
        f"<style>{tokens}\n{css}\n{WORKSPACE_THEME_CSS}</style>"
        + workspace_theme_marker_html(st.context.theme.type),
        unsafe_allow_html=True,
    )
    render_sheet_theme_bridge()


def brand():
    st.markdown(sidebar_brand_html(), unsafe_allow_html=True)


def header(title, description, eyebrow=""):
    st.markdown(page_header_html(title, description, eyebrow), unsafe_allow_html=True)


def hero():
    st.markdown(
        '<section class="home-launcher"><h2>입찰가격 분석</h2>'
        '<p>데이터의 여러 면을 읽고, 판단을 선명하게.</p></section>',
        unsafe_allow_html=True,
    )


def card(number, title, description):
    st.markdown(home_action_card_html(title, description, ":material/arrow_forward:"), unsafe_allow_html=True)


def render_login_page() -> tuple[str, str, bool]:
    """Render the original visual flow with public demo account guidance."""
    apply_theme(login=True)
    st.markdown(login_panel_html("PriceSystem", "입찰가격 분석 · DEMO", ""), unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown('<div id="login-card-root"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-brand"><span class="login-brand__eyebrow" '
            'draggable="false">PRECISION IN EVERY FACET</span></div>',
            unsafe_allow_html=True,
        )
        username = st.text_input("아이디", key="login_username")
        password = st.text_input("비밀번호", type="password", key="login_password")
        submitted = st.form_submit_button("로그인", key="login_submit", use_container_width=True)
    st.markdown(
        '<div class="login-access-footer"><span>데모 계정: admin / admin</span>'
        '<span>가상 데이터로 자유롭게 체험해 보세요.</span></div>',
        unsafe_allow_html=True,
    )
    st.html(login_cursor_glow_script(), unsafe_allow_javascript=True)
    st.html(login_gem_webgl_script(), unsafe_allow_javascript=True)
    return username, password, submitted


LABELS = {
    "code": "공고번호", "title": "공고명", "agency": "발주기관", "category": "분류",
    "region": "지역", "base_amount": "기초금액 (원)", "deadline": "마감일", "status": "상태",
    "memo": "메모", "notice_title": "공고명", "notice_code": "공고번호", "company": "가상 회사",
    "amount": "금액 (원)", "outcome": "샘플 결과", "note": "메모",
    "scenario": "샘플 구분",
}


def table(rows, columns, height="auto"):
    if not rows:
        st.info("표시할 데이터가 없습니다. 검색 조건을 바꾸거나 새 항목을 등록해 보세요.")
        return
    frame = pd.DataFrame(rows).reindex(columns=columns).rename(columns=LABELS)
    money = {LABELS[key]: st.column_config.NumberColumn(format="localized")
             for key in ["base_amount", "amount"] if key in columns}
    st.dataframe(frame, hide_index=True, width="stretch", height=height, column_config=money)


def done(message):
    st.session_state["flash"] = message
    st.rerun()


def csv_bytes(rows):
    """Export display data; spreadsheet applications must treat user text as text."""
    def safe(value):
        if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
            return "'" + value
        return value

    frame = pd.DataFrame(rows).map(safe).rename(columns=safe)
    return frame.to_csv(index=False).encode("utf-8-sig")
