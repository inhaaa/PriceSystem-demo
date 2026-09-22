"""PriceSystem: 원본의 업무 화면과 독립적인 가상 데이터 체험."""
import streamlit as st

from demo import bid_pages, data_pages, workspace
from demo.services import authenticate
from demo.store import DemoStore
from demo.ui import apply_theme, render_login_page


HANDLERS = {
    "category": data_pages.categories,
    "data_upload": data_pages.uploads,
    "integrated_bids": data_pages.integrated,
    "bid_award_search": data_pages.query,
    "recommend_price": bid_pages.recommendation_page,
    "daily_recommend": bid_pages.daily_page,
    "my_bid_manage": bid_pages.management_page,
    "my_bid_status": bid_pages.status_page,
    "g2b_api": bid_pages.api_page,
    "result_manage": bid_pages.results_page,
}


def restart(logout=False):
    store = st.session_state.get("store")
    if store:
        store.close()
    st.session_state.clear()
    if not logout:
        st.session_state["authenticated"] = True
        st.session_state["store"] = DemoStore()
        st.session_state["flash"] = "기본 샘플로 초기화했습니다."


def main():
    st.set_page_config(page_title="PriceSystem · Demo", page_icon="💎", layout="wide")
    if not st.session_state.get("authenticated"):
        username, password, submitted = render_login_page()
        if submitted:
            if authenticate(username, password):
                st.session_state["authenticated"] = True
                st.session_state["store"] = DemoStore()
                st.rerun()
            st.error("체험 계정은 admin / admin 입니다.")
        return
    apply_theme()
    workspace.sidebar(restart)
    active = st.session_state.get("active_tab", "")
    if not active:
        workspace.render_home()
        if message := st.session_state.pop("flash", None):
            st.success(message)
        return
    workspace.masthead(active)
    with st.container(key="workspace_surface"):
        st.caption("DEMO · 가상 데이터 · 분석과 외부 조회는 고정 샘플 · 변경은 현재 세션에만 유지")
        if message := st.session_state.pop("flash", None):
            st.success(message)
        HANDLERS[active](st.session_state["store"])


if __name__ == "__main__":
    main()
