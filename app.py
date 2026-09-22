"""PriceSystem portfolio demo. All business data lives in this browser session."""
from datetime import date

import pandas as pd
import streamlit as st

from demo.services import api_response, authenticate, recommendation
from demo.store import DemoStore
from demo.ui import apply_theme, brand, card, done, header, hero, image_uri, table


PAGES = ["홈", "공고 관리", "자료 등록", "분석·추천", "투찰·결과", "분류 관리", "API 샘플"]
NOTICE_COLUMNS = ["code", "title", "agency", "category", "region", "base_amount", "deadline", "status"]
NOTICE_STATUSES = ["접수중", "마감", "완료"]


def restart(logout=False):
    store = st.session_state.get("store")
    if store:
        store.close()
    st.session_state.clear()
    if not logout:
        st.session_state["authenticated"] = True
        st.session_state["store"] = DemoStore()
        st.session_state["flash"] = "기본 샘플로 초기화했습니다."


def navigate(page):
    st.session_state["navigation"] = page


def login():
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.html('<div class="login-intro"><span class="eyebrow">PRICESYSTEM / PORTFOLIO</span>'
                '<h1>입찰 업무를 연결하는<br>하나의 시스템.</h1>'
                '<p>자료 등록부터 공고 관리, 분석 화면과 결과 기록까지.<br>'
                '실제 업무 시스템의 주요 흐름을 가상 데이터로 만나보세요.</p></div>')
        st.html(f'<img class="login-art" src="{image_uri("logo.svg")}" alt="PriceSystem 다이아몬드">')
    with right:
        with st.form("login_form"):
            brand()
            st.subheader("데모 체험 로그인")
            st.caption("공통 체험 계정으로 시작하세요.")
            username = st.text_input("아이디", key="login_username", placeholder="admin")
            password = st.text_input("비밀번호", type="password", key="login_password", placeholder="admin")
            submit = st.form_submit_button("체험 시작", type="primary", width="stretch", key="login_submit")
            st.caption("아이디 admin  ·  비밀번호 admin")
        if submit:
            if authenticate(username, password):
                st.session_state["authenticated"] = True
                st.session_state["store"] = DemoStore()
                st.rerun()
            st.error("체험 계정은 admin / admin 입니다.")
        st.info("운영 데이터가 없는 포트폴리오 데모입니다. 분석은 샘플이며, 변경 내용은 이번 세션에서만 유지됩니다.")
    st.html('<div class="footer-note">PriceSystem · Portfolio demonstration</div>')


def home(store):
    header("입찰 업무, 한눈에", "등록부터 결과 확인까지, 가상 데이터로 주요 기능을 둘러보세요.")
    hero()
    rows = store.notices()
    a, b, c, d = st.columns(4)
    a.metric("전체 공고", f"{len(rows)}건")
    b.metric("접수중", f"{sum(row['status'] == '접수중' for row in rows)}건")
    c.metric("내 투찰", f"{len(store.submissions())}건")
    d.metric("등록된 결과", f"{len(store.results())}건")
    st.write("")
    for column, number, title, desc, page in zip(
        st.columns(3), ["01 / ORGANIZE", "02 / EXPLORE", "03 / FOLLOW UP"],
        ["공고를 정리하세요", "분석 화면을 체험하세요", "투찰과 결과를 기록하세요"],
        ["조건을 검색하고, 공고를 등록·수정·삭제합니다.", "시나리오를 바꾸며 샘플 차트와 추천 표시를 확인합니다.", "가상 회사의 투찰과 결과를 한곳에서 관리합니다."],
        ["공고 관리", "분석·추천", "투찰·결과"],
    ):
        with column:
            with st.container(border=True):
                card(number, title, desc)
                st.button(f"{page} 열기", width="stretch", on_click=navigate, args=(page,))
    st.write("")
    st.subheader("공고 미리보기")
    table(rows[:5], NOTICE_COLUMNS)
    st.caption("표시된 기관·회사·금액은 모두 새로 작성한 가상 샘플입니다.")


def notice_fields(store, prefix, current=None):
    current = current or {}
    categories = store.categories()
    left, right = st.columns(2)
    with left:
        code = st.text_input("공고번호", value=current.get("code", "DEMO-NEW-001"), key=prefix + "code")
        title = st.text_input("공고명", value=current.get("title", ""), key=prefix + "title")
        agency = st.text_input("가상 발주기관", value=current.get("agency", ""), key=prefix + "agency")
        selected = current.get("category", categories[0])
        category = st.selectbox("분류", categories, index=categories.index(selected), key=prefix + "category")
    with right:
        region = st.text_input("가상 지역", value=current.get("region", "가상 동부"), key=prefix + "region")
        amount = st.number_input("기초금액 (원)", min_value=0, max_value=10**12,
                                 value=int(current.get("base_amount", 100000000)), step=1000000, key=prefix + "amount")
        deadline = st.date_input("마감일", value=date.fromisoformat(current.get("deadline", "2026-10-15")),
                                 min_value=date(2000, 1, 1), max_value=date(2100, 12, 31), key=prefix + "deadline")
        status = st.selectbox("상태", NOTICE_STATUSES, index=NOTICE_STATUSES.index(current.get("status", "접수중")), key=prefix + "status")
    memo = st.text_area("메모", value=current.get("memo", ""), key=prefix + "memo", height=80)
    return dict(code=code, title=title, agency=agency, category=category, region=region,
                base_amount=amount, deadline=deadline.isoformat(), status=status, memo=memo)


def notices(store):
    header("공고 관리", "조건으로 찾아보고, 직접 등록하고 수정해 보세요. 변경은 이번 체험에만 적용됩니다.")
    left, middle, right = st.columns([2, 1, 1])
    query = left.text_input("공고 검색", placeholder="공고명 · 번호 · 기관", key="notice_search")
    category = middle.selectbox("분류 필터", ["전체", *store.categories()])
    status = right.selectbox("상태 필터", ["전체", *NOTICE_STATUSES])
    rows = store.notices(query=query, category=category, status=status)
    st.caption(f"검색 결과 {len(rows)}건")
    table(rows, NOTICE_COLUMNS)
    create, edit = st.tabs(["새 공고 등록", "상세 · 수정 · 삭제"])
    with create:
        if store.categories():
            with st.form("new_notice", clear_on_submit=True):
                data = notice_fields(store, "new_")
                save = st.form_submit_button("공고 등록", type="primary", key="create_notice")
            if save:
                try:
                    store.save_notice(data)
                    done("공고를 등록했습니다.")
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info("분류 관리에서 분류를 먼저 추가해 주세요.")
    with edit:
        if rows:
            lookup = {row["id"]: row for row in rows}
            selected = st.selectbox("편집할 공고", list(lookup), format_func=lambda x: f"{lookup[x]['code']} · {lookup[x]['title']}")
            with st.form(f"edit_notice_{selected}"):
                data = notice_fields(store, f"edit_{selected}_", lookup[selected])
                save = st.form_submit_button("수정 저장", type="primary", key="update_notice")
            if save:
                try:
                    store.save_notice(data, notice_id=selected)
                    done("공고를 수정했습니다.")
                except ValueError as exc:
                    st.error(str(exc))
            confirm = st.checkbox("연결된 투찰·결과를 포함하여 이 공고를 삭제합니다.", key=f"delete_confirm_{selected}")
            if st.button("공고 삭제", disabled=not confirm, key="delete_notice"):
                store.delete_notice(selected)
                done("공고와 연결된 체험 기록을 삭제했습니다.")


def uploads(store):
    header("자료 등록", "데모 CSV 양식을 내려받아 편집하고, 여러 공고를 한 번에 등록해 보세요.")
    st.info("가상 자료 전용입니다. 실제 공고·회사정보·개인정보를 업로드하지 마세요.")
    if not store.categories():
        st.info("분류 관리에서 분류를 먼저 추가하거나 샘플을 초기화해 주세요.")
        return
    with st.container(border=True):
        st.subheader("01. 샘플 양식 받기")
        st.write("UTF-8 CSV · 공고번호는 DEMO-로 시작 · 현재 등록된 분류 사용")
        st.caption("사용 가능한 분류: " + ", ".join(store.categories()))
        st.download_button("데모 CSV 다운로드", data=store.csv_template(), file_name="pricesystem-demo.csv", mime="text/csv")
    with st.container(border=True):
        st.subheader("02. 미리보기 후 등록")
        uploaded = st.file_uploader("데모 CSV 파일", type=["csv"], key="csv_upload")
        if uploaded:
            try:
                preview = pd.read_csv(uploaded, encoding="utf-8-sig", dtype=str, keep_default_na=False)
                st.dataframe(preview, hide_index=True, width="stretch")
            except (ValueError, UnicodeError, pd.errors.ParserError):
                st.error("UTF-8 CSV 양식을 확인해 주세요.")
            if st.button("일괄 등록", type="primary"):
                try:
                    count = store.import_csv(uploaded.getvalue())
                    st.success(f"가상 공고 {count}건을 등록했습니다.")
                except ValueError as exc:
                    st.error(str(exc))
    st.caption("이 공개 데모는 CSV 등록 흐름을 제공합니다. 운영 자료 파서와 자동 수집은 포함하지 않습니다.")


def analysis(store):
    header("분석·추천", "분석 결과를 살펴보는 화면과 업무 흐름을 샘플 시나리오로 체험합니다.")
    st.info("데모용 샘플 결과입니다. 모든 금액과 차트는 표시를 위해 새로 작성했으며 실제 분석·추천을 수행하지 않습니다.")
    rows = store.notices()
    if not rows:
        st.warning("공고 관리에서 공고를 먼저 등록해 주세요.")
        return
    a, b = st.columns([2, 1])
    chosen = a.selectbox("체험할 공고", [r["id"] for r in rows],
                         format_func=lambda x: next(r["title"] for r in rows if r["id"] == x))
    scenario = b.selectbox("표시 시나리오", ["샘플 A", "샘플 B", "샘플 C"], key="analysis_scenario")
    sample = recommendation(scenario)
    row = store.get_notice(chosen)
    a, b, c = st.columns(3)
    a.metric("표시용 샘플 금액", f"{sample['amount']:,}원")
    b.metric("선택 시나리오", scenario)
    c.metric("결과 유형", "고정 샘플")
    st.write("")
    chart, detail = st.columns([1.7, 1], gap="large")
    with chart:
        with st.container(border=True):
            st.subheader("샘플 분포")
            st.caption("새로 작성한 표시용 점들입니다. 실제 데이터의 분포가 아닙니다.")
            frame = pd.DataFrame(sample["points"]).rename(columns={"label": "구간", "value": "샘플 수"})
            st.bar_chart(frame, x="구간", y="샘플 수", color="#5d78cf", height=280)
    with detail:
        with st.container(border=True):
            st.subheader("선택한 공고")
            st.write(row["title"])
            st.caption(f"{row['code']} · {row['category']}")
            st.divider()
            st.write("공고를 바꿔도 같은 시나리오는 같은 샘플을 표시합니다.")
            st.caption(sample["note"])
    st.caption("추천 금액은 투찰 입력에 자동 반영되지 않습니다. 투찰·결과 화면에서 별도로 체험할 수 있습니다.")


def bid_records(store):
    header("투찰·결과", "가상 회사의 투찰 금액과 결과를 등록하고 수정합니다.")
    notice_rows = store.notices()
    if not notice_rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    lookup = {r["id"]: r for r in notice_rows}
    tabs = st.tabs(["내 투찰", "결과 관리"])
    with tabs[0]:
        records = store.submissions()
        table(records, ["notice_code", "notice_title", "company", "amount", "status", "memo"])
        choices = {r["id"]: r for r in records}
        edit_id = st.selectbox("투찰 편집", [None, *choices],
                              format_func=lambda x: "새 투찰 등록" if x is None else f"{choices[x]['notice_code']} · {choices[x]['company']}")
        item = choices.get(edit_id, {})
        key = f"submission_{edit_id}_"
        with st.form(key + "form"):
            selected = item.get("notice_id", next(iter(lookup)))
            notice_id = st.selectbox("공고", list(lookup), index=list(lookup).index(selected), format_func=lambda x: lookup[x]["title"], key=key + "notice")
            a, b = st.columns(2)
            company = a.text_input("가상 회사명", value=item.get("company", "가상 데모회사"), key=key + "company")
            amount = b.number_input("투찰 금액 (원)", min_value=0, max_value=10**12, value=int(item.get("amount", 80000000)), step=1000000, key=key + "amount")
            status = st.selectbox("투찰 상태", ["작성중", "제출완료"], index=["작성중", "제출완료"].index(item.get("status", "작성중")), key=key + "status")
            memo = st.text_input("투찰 메모", value=item.get("memo", ""), key=key + "memo")
            save = st.form_submit_button("투찰 저장", type="primary", key="save_submission")
        if save:
            try:
                store.save_submission(dict(notice_id=notice_id, company=company, amount=amount, status=status, memo=memo), submission_id=edit_id)
                done("투찰 기록을 저장했습니다.")
            except ValueError as exc:
                st.error(str(exc))
        if edit_id is not None:
            confirm = st.checkbox("선택한 투찰을 삭제합니다.", key=f"submission_confirm_{edit_id}")
            if st.button("투찰 삭제", disabled=not confirm):
                store.delete_submission(edit_id)
                done("투찰 기록을 삭제했습니다.")
    with tabs[1]:
        records = store.results()
        table(records, ["notice_code", "notice_title", "outcome", "amount", "note"])
        selected = st.selectbox("결과를 기록할 공고", list(lookup), format_func=lambda x: lookup[x]["title"], key="result_notice")
        item = next((r for r in records if r["notice_id"] == selected), {})
        key = f"result_{selected}_"
        with st.form(key + "form"):
            outcomes = ["검토중", "샘플 낙찰", "샘플 미선정"]
            outcome = st.selectbox("샘플 결과", outcomes, index=outcomes.index(item.get("outcome", "검토중")), key=key + "outcome")
            amount = st.number_input("결과 금액 (원)", min_value=0, max_value=10**12, value=int(item.get("amount", 0)), step=1000000, key=key + "amount")
            note = st.text_input("결과 메모", value=item.get("note", ""), key=key + "note")
            save = st.form_submit_button("결과 저장", type="primary", key="save_result")
        if save:
            try:
                store.save_result(dict(notice_id=selected, outcome=outcome, amount=amount, note=note))
                done("결과를 저장했습니다.")
            except ValueError as exc:
                st.error(str(exc))
        if item:
            confirm = st.checkbox("선택한 결과를 삭제합니다.", key=f"result_confirm_{selected}")
            if st.button("결과 삭제", disabled=not confirm):
                store.delete_result(selected)
                for widget_key in list(st.session_state):
                    if widget_key.startswith(key):
                        del st.session_state[widget_key]
                done("결과를 삭제했습니다.")


def categories(store):
    header("분류 관리", "공고를 정리할 분류를 추가하거나 이름을 변경합니다.")
    rows = store.categories()
    st.dataframe(pd.DataFrame({"분류명": rows}), hide_index=True, width="stretch")
    a, b = st.columns(2)
    with a:
        with st.form("new_category", clear_on_submit=True):
            name = st.text_input("새 분류명")
            add = st.form_submit_button("분류 추가", type="primary")
        if add:
            try:
                store.add_category(name)
                done("분류를 추가했습니다.")
            except ValueError as exc:
                st.error(str(exc))
    with b:
        if rows:
            selected = st.selectbox("관리할 분류", rows)
            with st.form(f"rename_category_{selected}"):
                name = st.text_input("변경할 분류명", value=selected)
                rename = st.form_submit_button("이름 변경")
            if rename:
                try:
                    store.rename_category(selected, name)
                    done("분류 이름을 변경했습니다.")
                except ValueError as exc:
                    st.error(str(exc))
            st.caption("공고가 사용 중인 분류는 삭제할 수 없습니다.")
            confirm = st.checkbox("이 분류를 삭제합니다.", key=f"category_confirm_{selected}")
            if st.button("분류 삭제", disabled=not confirm):
                try:
                    store.delete_category(selected)
                    done("분류를 삭제했습니다.")
                except ValueError as exc:
                    st.error(str(exc))


def api_samples(store):
    header("API 샘플", "외부 조회와 응답 확인 흐름을 네트워크 호출 없이 체험합니다.")
    st.info("데모용 샘플 응답입니다. 실제 외부 API를 호출하거나 API 키를 사용하지 않습니다.")
    scenario = st.selectbox("응답 시나리오", ["정상", "빈 결과", "오류"], key="api_scenario")
    if st.button("샘플 조회", type="primary", key="api_preview"):
        st.session_state["api_response"] = api_response(scenario)
    response = st.session_state.get("api_response")
    if response:
        if response["status"] == "error":
            st.warning(response["message"])
        elif not response["items"]:
            st.info("샘플 조회 결과가 없습니다.")
        else:
            table(response["items"], NOTICE_COLUMNS)
            for item in response["items"]:
                if st.button(f"{item['code']} 데모 공고로 등록", key="api_save_" + item["code"]):
                    try:
                        store.save_notice(item)
                        done("샘플 응답을 데모 공고로 등록했습니다.")
                    except ValueError as exc:
                        st.error(str(exc))
        with st.expander("샘플 응답 구조", expanded=True):
            st.json(response)


def main():
    st.set_page_config(page_title="PriceSystem · Portfolio Demo", page_icon="💎", layout="wide")
    apply_theme()
    if not st.session_state.get("authenticated"):
        login()
        return
    with st.sidebar:
        brand()
        page = st.radio("작업 공간", PAGES, key="navigation", label_visibility="collapsed")
        st.html('<div class="session-chip"><b>admin</b> · 체험 계정<br>현재 세션에만 저장됩니다.</div>')
        st.button("샘플 초기화", on_click=restart, key="reset_samples", width="stretch")
        st.button("로그아웃", on_click=restart, args=(True,), key="logout", width="stretch")
        st.divider()
        st.caption("PORTFOLIO DEMO\n\n가상 데이터 · 샘플 분석\n\n개인정보와 실제 업무 자료를 입력하지 마세요.")
    if message := st.session_state.pop("flash", None):
        st.success(message)
    handlers = dict(zip(PAGES, [home, notices, uploads, analysis, bid_records, categories, api_samples]))
    handlers[page](st.session_state["store"])


if __name__ == "__main__":
    main()
