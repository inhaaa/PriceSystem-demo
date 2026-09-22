"""Display helpers and reviewed visual assets; no business dependencies."""
import base64
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def image_uri(name):
    return "data:image/svg+xml;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def apply_theme():
    tokens = (ASSETS / "tokens.css").read_text(encoding="utf-8")
    css = (ASSETS / "demo.css").read_text(encoding="utf-8")
    css = css.replace("__WORKSPACE__", image_uri("workspace.svg"))
    st.html(f"<style>{tokens}\n{css}</style>")


def brand():
    st.html(f'<div class="brand"><img src="{image_uri("logo.svg")}" alt="">'
            '<div><b>PriceSystem</b><small>PORTFOLIO DEMO</small></div></div>')


def header(title, description, eyebrow="PRICESYSTEM / DEMO WORKSPACE"):
    st.html(f'<header class="page-heading"><span class="eyebrow">{escape(eyebrow)}</span>'
            f'<h1>{escape(title)}</h1><p>{escape(description)}</p></header>')


def hero():
    st.html(f'<section class="hero"><div><span class="eyebrow">BID MANAGEMENT, IN ONE PLACE</span>'
            '<h2>입찰 업무의 흐름을,<br>하나의 작업 공간에서.</h2>'
            '<p>공고를 정리하고, 투찰을 기록하고, 결과를 살펴보세요.<br>'
            '새로운 가상 데이터로 자유롭게 체험할 수 있습니다.</p>'
            '<span class="pill">가상 데이터 전용</span><span class="pill">세션별 독립 체험</span>'
            f'</div><img src="{image_uri("logo.svg")}" alt="다이아몬드 그래픽"></section>')


def card(number, title, description):
    st.html(f'<article class="feature-card"><span class="card-index">{escape(number)}</span>'
            f'<h3>{escape(title)}</h3><p>{escape(description)}</p></article>')


LABELS = {
    "code": "공고번호", "title": "공고명", "agency": "발주기관", "category": "분류",
    "region": "지역", "base_amount": "기초금액 (원)", "deadline": "마감일", "status": "상태",
    "memo": "메모", "notice_title": "공고명", "notice_code": "공고번호", "company": "가상 회사",
    "amount": "금액 (원)", "outcome": "샘플 결과", "note": "메모",
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
