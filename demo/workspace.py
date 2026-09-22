"""원본의 공개 가능한 메뉴·업무 탭 구조. 계정별 운영 권한 규칙은 포함하지 않는다."""
import streamlit as st

from demo.ui import brand, header, home_action_card_html, workspace_tab_scroll_script


PAGES = [
    dict(key="category", label="카테고리 관리", description="분류 기준을 만들고 연결된 공고를 관리합니다.", group="기준 정보", icon=":material/category:"),
    dict(key="data_upload", label="데이터 등록", description="입찰·낙찰 데이터를 등록하고 처리 결과를 확인합니다.", group="데이터 업무", icon=":material/upload_file:"),
    dict(key="integrated_bids", label="통합 공고 관리", description="통합된 공고 정보와 출처, 상세 자료를 함께 관리합니다.", group="데이터 업무", icon=":material/list_alt:"),
    dict(key="bid_award_search", label="입찰/낙찰 데이터 조회", description="입찰과 낙찰 데이터를 조건별로 검색하고 상세 정보를 조회합니다.", group="데이터 업무", icon=":material/search:"),
    dict(key="recommend_price", label="추천투찰금액 계산", description="관심공고의 추천 결과를 표시용 샘플로 확인합니다.", group="추천 업무", icon=":material/calculate:"),
    dict(key="daily_recommend", label="개찰일별 추천계산", description="개찰일별로 관심공고를 모아 샘플 추천 결과를 확인합니다.", group="추천 업무", icon=":material/calendar_month:"),
    dict(key="my_bid_manage", label="나의 투찰관리", description="추천금액과 투찰 결과를 가상 공고별로 기록하고 관리합니다.", group="투찰 업무", icon=":material/work:"),
    dict(key="my_bid_status", label="내 투찰현황", description="나의 투찰 결과와 낙찰상태를 샘플로 확인합니다.", group="투찰 업무", icon=":material/monitoring:"),
    dict(key="g2b_api", label="나라장터 API 연동", description="공고와 개찰 데이터 조회 흐름을 외부 호출 없는 샘플로 체험합니다.", group="시스템 연동", icon=":material/api:"),
    dict(key="result_manage", label="결과 관리", description="가상 개찰결과를 등록하고 표시용 추천 결과와 함께 관리합니다.", group="결과 업무", icon=":material/task_alt:"),
]
PAGE_BY_KEY = {page["key"]: page for page in PAGES}


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


def sidebar(restart):
    active = st.session_state.get("active_tab", "")
    with st.sidebar:
        brand()
        st.button("Home", key="sidebar_home", type="primary" if not active else "secondary",
                  icon=":material/home:", width="stretch", on_click=home)
        st.markdown('<div class="sidebar-home-divider"></div>', unsafe_allow_html=True)
        group = ""
        for page in PAGES:
            if page["group"] != group:
                group = page["group"]
                st.markdown(f'<div class="sidebar-nav-title">{group}</div>', unsafe_allow_html=True)
            st.button(page["label"], key=f"menu_open_{page['key']}",
                      type="primary" if active == page["key"] else "secondary",
                      icon=page["icon"], width="stretch", on_click=open_tab, args=(page["key"],))
        with st.container(key="sidebar_account_area"):
            st.markdown('<div class="sidebar-account-label">현재 계정</div>'
                        '<div class="sidebar-account-name">admin <small>· DEMO</small></div>', unsafe_allow_html=True)
            st.button("샘플 초기화", key="reset_samples", on_click=restart, width="stretch")
            st.button("로그아웃", key="logout", on_click=restart, args=(True,), width="stretch")


def masthead(active):
    with st.container(key="workspace_masthead"):
        st.markdown('<div class="workspace-tabbar-spacer"></div>', unsafe_allow_html=True)
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
        header(page["label"], page["description"], page["group"])


def render_home():
    with st.container(key="workspace_home"):
        st.markdown('<section class="home-launcher"><h2>입찰가격 분석</h2>'
                    '<p>데이터의 여러 면을 읽고, 판단을 선명하게.</p></section>', unsafe_allow_html=True)
        page = PAGE_BY_KEY["daily_recommend"]
        with st.container(key="home_featured_daily_recommend"):
            st.markdown(home_action_card_html(page["label"], page["description"], page["icon"], featured=True), unsafe_allow_html=True)
            st.button("추천계산 시작하기", key="home_open_daily_recommend", type="primary",
                      icon=":material/arrow_forward:", icon_position="right", width="stretch",
                      on_click=open_tab, args=("daily_recommend",))
        page = PAGE_BY_KEY["data_upload"]
        with st.container(key="home_secondary_grid_1"):
            with st.container(key="home_secondary_data_upload"):
                st.markdown(home_action_card_html(page["label"], page["description"], page["icon"]), unsafe_allow_html=True)
                st.button("데이터 등록하기", key="home_open_data_upload", type="tertiary",
                          icon=":material/arrow_forward:", icon_position="right", width="stretch",
                          on_click=open_tab, args=("data_upload",))
        st.caption("DEMO · 가상 데이터로 체험합니다. 변경 내용은 현재 세션에만 유지됩니다.")
