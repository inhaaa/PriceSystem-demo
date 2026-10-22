"""공고·추천·투찰 업무를 연결하는 공개 데모 작업 공간."""
from datetime import date
from html import escape

import streamlit as st

from demo.schedule import render_schedule
from demo.ui import brand, header, workspace_tab_scroll_script


PAGES = [
    dict(key="category", label="카테고리 관리", description="분류 기준을 만들고 연결된 공고를 관리합니다.", group="기준 정보", icon=":material/category:"),
    dict(key="data_upload", label="데이터 등록", description="관심공고를 등록하고 개찰일별 조회로 이어가세요.", group="데이터 업무", icon=":material/upload_file:"),
    dict(key="integrated_bids", label="통합 공고 조회", description="등록한 공고를 공고명과 번호로 검색합니다.", group="데이터 업무", icon=":material/list_alt:"),
    dict(key="bid_award_search", label="입찰/낙찰 데이터 조회", description="입찰과 낙찰 데이터를 조건별로 검색하고 상세 정보를 조회합니다.", group="데이터 업무", icon=":material/search:"),
    dict(key="daily_notices", label="개찰일별 공고관리", description="개찰일로 조회하고 계산할 공고를 선택하세요.", group="추천 업무", icon=":material/edit_calendar:"),
    dict(key="daily_recommend", label="개찰일별 추천계산", description="공고를 선택하고 계산 결과를 확인·저장하세요.", group="추천 업무", icon=":material/calendar_month:"),
    dict(key="my_bid_manage", label="나의 투찰관리", description="추천금액과 투찰 결과를 가상 공고별로 기록하고 관리합니다.", group="투찰 업무", icon=":material/work:"),
    dict(key="my_bid_status", label="내 투찰현황", description="나의 투찰 결과와 낙찰상태를 샘플로 확인합니다.", group="투찰 업무", icon=":material/monitoring:"),
    dict(key="g2b_api", label="나라장터 API 연동", description="공고와 개찰 데이터 조회 흐름을 외부 호출 없는 샘플로 체험합니다.", group="시스템 연동", icon=":material/api:"),
    dict(key="result_manage", label="결과 관리", description="가상 개찰결과를 등록하고 표시용 추천 결과와 함께 관리합니다.", group="결과 업무", icon=":material/task_alt:"),
    dict(key="bid_review", label="투찰 검토함", description="공고별 준비 항목을 확인하고 투찰 전 검토 상태를 관리하세요.", group="업무 관리", icon=":material/checklist:"),
    dict(key="performance_report", label="성과 리포트", description="월별 투찰·낙찰 건수와 낙찰금액 추이를 가상 기록으로 확인하세요.", group="성과 분석", icon=":material/bar_chart:"),
]
PAGE_BY_KEY = {page["key"]: page for page in PAGES}
SIDEBAR_GROUPS = (
    ("입찰 업무", ("integrated_bids", "daily_notices", "daily_recommend", "my_bid_manage", "my_bid_status", "result_manage")),
    ("업무 관리", ("bid_review",)),
    ("성과 분석", ("performance_report",)),
    ("자료 관리", ("data_upload", "bid_award_search", "category")),
    ("시스템", ("g2b_api",)),
)


def open_tab(key):
    if key not in PAGE_BY_KEY:
        raise ValueError("등록된 데모 메뉴를 선택해 주세요.")
    tabs = st.session_state.setdefault("open_tabs", [])
    if key not in tabs:
        tabs.append(key)
    st.session_state["active_tab"] = key


def close_tab(key):
    tabs = st.session_state.setdefault("open_tabs", [])
    if key not in tabs:
        return
    index = tabs.index(key)
    tabs.remove(key)
    if key == "data_upload":
        for widget_key in list(st.session_state):
            if widget_key.startswith(("historical_", "current_excel_", "current_pdf_", "result_excel_", "result_pdf_")):
                del st.session_state[widget_key]
    if st.session_state.get("active_tab") == key:
        st.session_state["active_tab"] = tabs[max(0, index - 1)] if tabs else ""


def home():
    st.session_state["active_tab"] = ""
    st.session_state["open_tabs"] = []


def open_daily_notices(opening):
    opening = date.fromisoformat(str(opening))
    for key in ("daily_notices_select_all", "daily_notices_pending", "daily_notices_reason",
                "daily_notices_other_reason", "daily_notices_ack"):
        st.session_state.pop(key, None)
    st.session_state["daily_notices_date"] = opening
    st.session_state["daily_notices_query"] = opening.isoformat()
    st.session_state["daily_notices_revision"] = st.session_state.get("daily_notices_revision", 0) + 1
    open_tab("daily_notices")


def open_daily_calculation(opening):
    st.session_state["daily_requested_date"] = date.fromisoformat(str(opening))
    open_tab("daily_recommend")


def sidebar(restart):
    active = st.session_state.get("active_tab", "")
    with st.sidebar:
        brand()
        st.button("업무 홈", key="sidebar_home", type="primary" if not active else "secondary",
                  icon=":material/home:", width="stretch", on_click=home)
        st.markdown('<div class="sidebar-home-divider"></div>', unsafe_allow_html=True)
        for group, keys in SIDEBAR_GROUPS:
            st.markdown(f'<div class="sidebar-nav-title">{group}</div>', unsafe_allow_html=True)
            for key in keys:
                page = PAGE_BY_KEY[key]
                st.button(page["label"], key=f"menu_open_{key}",
                          type="primary" if active == key else "secondary",
                          icon=page["icon"], width="stretch", on_click=open_tab, args=(key,))
        with st.container(key="sidebar_account_area"):
            st.markdown('<div class="sidebar-account-label">현재 계정</div>'
                        '<div class="sidebar-account-name">admin <small>· DEMO</small></div>', unsafe_allow_html=True)
            st.button("샘플 초기화", key="reset_samples", on_click=restart, width="stretch")
            st.button("로그아웃", key="logout", on_click=restart, args=(True,), width="stretch")


def masthead(active):
    with st.container(key="workspace_masthead"):
        st.markdown('<div class="workspace-utility"><span class="workspace-utility__label">'
                    '업무 홈 <span aria-hidden="true">/</span> '
                    f'{escape(PAGE_BY_KEY[active]["label"])}</span>'
                    '<span class="workspace-utility__status">DEMO · 가상 데이터</span></div>', unsafe_allow_html=True)
        with st.container(key="internal_tab_bar", horizontal=True, vertical_alignment="center", gap="small"):
            for index, key in enumerate(st.session_state.get("open_tabs", [])):
                with st.container(key=f"workspace_tab_{index}_{key}", horizontal=True,
                                  vertical_alignment="center", gap=None, width="content"):
                    kind = "primary" if key == active else "secondary"
                    st.button(PAGE_BY_KEY[key]["label"], key=f"tab_activate_{key}", type=kind,
                              width="content", on_click=open_tab, args=(key,))
                    st.button("x", key=f"tab_close_{key}", type=kind, width="content",
                              help=f"{PAGE_BY_KEY[key]['label']} 닫기", on_click=close_tab, args=(key,))
        st.html(workspace_tab_scroll_script(active), unsafe_allow_javascript=True)
        page = PAGE_BY_KEY[active]
        header("관심공고 등록" if active == "data_upload" else page["label"], page["description"])


def home_summary(store):
    """집계는 현재 세션의 기록만 사용하며 대기 공고는 중복 없이 센다."""
    notices = store.notices()
    submissions = store.submissions()
    completed = {row["notice_id"] for row in store.results() if row["outcome"] != "검토중"}
    awaiting = {row["notice_id"] for row in submissions
                if row["status"] == "제출완료" and row["notice_id"] not in completed}
    return dict(notices=len(notices), submissions=len(submissions), awaiting_results=len(awaiting))


def schedule_groups(rows, saved):
    groups = {}
    for row in rows:
        group = groups.setdefault(row["deadline"], dict(date=row["deadline"], notices=[], calculated=0))
        group["notices"].append(row)
        group["calculated"] += row["id"] in saved
    return [groups[opening] for opening in sorted(groups)]


def render_home(store):
    rows = store.notices()
    saved = st.session_state.get("demo_recommendations", {})
    groups = schedule_groups(rows, saved)
    with st.container(key="workspace_home"):
        st.markdown('<div class="workspace-utility"><span class="workspace-utility__label">업무 홈</span>'
                    '<span class="workspace-utility__status">DEMO · 가상 데이터</span></div>', unsafe_allow_html=True)
        with st.container(key="home_heading"):
            title, action = st.columns([3, 1], vertical_alignment="center")
            title.markdown('<header class="workbench-heading"><h1>업무 홈</h1>'
                           '<p>개찰 일정을 확인하고, 필요한 공고의 계산을 이어가세요.</p></header>', unsafe_allow_html=True)
            action.button("관심공고 등록", key="home_open_data_upload", type="primary", icon=":material/add:",
                          width="stretch", on_click=open_tab, args=("data_upload",))
        if not rows:
            st.info("등록된 공고가 없습니다. 관심공고를 등록해 주세요.")
            return
        today = date.today()
        upcoming = [group for group in groups if group["date"] >= today.isoformat()]
        default_date = date.fromisoformat((upcoming or groups)[0]["date"])
        with st.container(key="home_workbench"):
            schedule, tasks = st.columns([2.4, 1], gap="medium")
            with schedule, st.container(key="home_schedule"):
                render_schedule(groups, saved, open_notices=open_daily_notices,
                                open_calculation=open_daily_calculation)
            with tasks, st.container(key="home_action_panel"):
                st.markdown('<h2 class="workbench-section-title">계산 작업</h2>'
                            '<p class="workbench-section-note">개찰일을 고르고 계산을 시작하세요.</p>', unsafe_allow_html=True)
                opening = st.date_input("계산할 개찰일", default_date, key="home_calculation_date")
                selected = next((group for group in groups if group["date"] == opening.isoformat()), None)
                count = len(selected["notices"]) if selected else 0
                calculated = selected["calculated"] if selected else 0
                st.markdown('<dl class="workbench-facts">'
                            f'<div><dt>등록 공고</dt><dd>{count}건</dd></div>'
                            f'<div><dt>계산 저장</dt><dd>{calculated}건</dd></div></dl>', unsafe_allow_html=True)
                if not count:
                    st.caption("선택한 날짜에 등록된 공고가 없습니다.")
                st.button("공고 조회하고 계산", key="home_open_daily_recommend", type="primary", width="stretch",
                          disabled=not count, on_click=open_daily_calculation, args=(opening,))
                st.button("날짜별 공고 조회", key="home_open_daily_notices", width="stretch",
                          on_click=open_daily_notices, args=(opening,))
                st.markdown('<div class="workbench-panel-divider"></div><h3 class="workbench-panel-subtitle">저장한 계산</h3>',
                            unsafe_allow_html=True)
                recent = [row for row in rows if row["id"] in saved][-3:]
                if not recent:
                    st.caption("저장한 계산 결과가 없습니다.")
                for row in reversed(recent):
                    result = saved[row["id"]]
                    st.markdown('<div class="saved-calculation">'
                                f'<span>{escape(row["code"])}</span><strong>{escape(row["title"])}</strong>'
                                f'<p>{result["amount"]:,}원 <small>샘플</small></p></div>', unsafe_allow_html=True)
                st.caption("계산 결과는 고정 샘플입니다.")
        st.caption("DEMO · 가상 데이터이며 변경 내용은 현재 세션에만 유지됩니다.")
