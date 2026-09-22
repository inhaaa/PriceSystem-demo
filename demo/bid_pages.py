"""Original workflow layouts backed only by newly written demo data."""
from datetime import date

import pandas as pd
import streamlit as st

from demo.data_pages import _upload_panel
from demo.services import api_response, recommendation
from demo.store import RESULT_OUTCOMES, SUBMISSION_STATUSES
from demo.ui import csv_bytes as _csv, done, table


NOTICE_COLUMNS = ["code", "title", "agency", "category", "region", "base_amount", "deadline", "status"]
SCENARIOS = ["샘플 A", "샘플 B", "샘플 C"]
DEMO_NOTE = "고정 샘플 화면입니다. 입력값과 무관한 가상 표시값이며 실제 추천·분석·백테스트를 수행하지 않습니다."


def _notice_choice(label, rows, key):
    lookup = {row["id"]: row for row in rows}
    selected = st.selectbox(label, list(lookup), key=key,
                            format_func=lambda item: f"{lookup[item]['code']} · {lookup[item]['title']}")
    return lookup[selected]


def _matches(row, terms):
    return all(not value or value.strip().casefold() in str(row.get(field, "")).casefold()
               for field, value in terms.items())


def _sample_row(notice, scenario):
    sample = recommendation(scenario)
    return dict(notice_id=notice["id"], code=notice["code"], title=notice["title"],
                scenario=scenario, amount=sample["amount"], note=sample["note"])


def _remember(rows):
    saved = st.session_state.setdefault("demo_recommendations", {})
    for row in rows:
        saved[row["notice_id"]] = dict(row)


def _delete_result(store, notice_id):
    store.delete_result(notice_id)
    st.session_state.setdefault("demo_result_context", {}).pop(notice_id, None)
    for key in list(st.session_state):
        if key.startswith(f"result_{notice_id}_") or key == f"result_confirm_{notice_id}":
            del st.session_state[key]
    st.session_state["flash"] = "결과를 삭제했습니다."


def _date_range(rows, prefix, label):
    dates = [date.fromisoformat(row["deadline"]) for row in rows]
    start = st.date_input(label + " 시작", min(dates), key=prefix + "start")
    end = st.date_input(label + " 종료", max(dates), key=prefix + "end")
    return start.isoformat(), end.isoformat()


def recommendation_page(store):
    st.info(DEMO_NOTE)
    terms = {}
    for column, field, label in zip(st.columns(5), ["code", "title", "agency", "region", "category"],
                                   ["공고번호", "공고명", "발주기관", "지역", "업종"]):
        terms[field] = column.text_input(label, key="recommendation_filter_" + field)
    rows = [row for row in store.notices() if _matches(row, terms)]
    if not rows:
        st.info("조회 조건에 맞는 공고가 없습니다. 공고를 등록하거나 조건을 바꿔 주세요.")
        return
    row = _notice_choice("분석할 공고", rows, "recommendation_notice")
    prefix = f"recommendation_{row['id']}_"
    with st.expander("선택 공고 주요 정보"):
        table([row], NOTICE_COLUMNS)
    with st.form(prefix + "form"):
        left, middle, right = st.columns(3)
        with left:
            st.text_input("공고명", row["title"], key=prefix + "title")
            st.text_input("발주기관", row["agency"], key=prefix + "agency")
            st.text_input("지역", row["region"], key=prefix + "region")
            st.text_input("공고종류", "가상 공고", key=prefix + "kind")
        with middle:
            st.text_input("업종/면허", row["category"], key=prefix + "license")
            st.text_input("계약방법", "가상 일반경쟁", key=prefix + "contract")
            st.text_input("적격심사 적용 여부", "데모 미적용", key=prefix + "qualification")
            st.text_input("예가변동폭", "데모 미적용", key=prefix + "price_range")
        with right:
            st.number_input("기초금액", min_value=0, max_value=10**12, value=row["base_amount"], key=prefix + "base")
            st.number_input("예정가격", min_value=0, max_value=10**12, value=0, key=prefix + "planned")
            st.number_input("추정가격", min_value=0, max_value=10**12, value=0, key=prefix + "estimated")
            st.number_input("낙찰하한율(%)", min_value=0.0, max_value=100.0, value=0.0, key=prefix + "rate")
            st.selectbox("A값 적용 여부", ["데모 미적용", "가상 입력"], key=prefix + "a_mode")
            st.number_input("A값", min_value=0, max_value=10**12, value=0, key=prefix + "a")
        a, b, c = st.columns(3)
        a.selectbox("분석 카테고리", store.categories(), key=prefix + "category")
        b.selectbox("반올림 단위", [100, 1000, 10000], key=prefix + "round")
        c.selectbox("처리 방식", ["round", "floor", "ceil"], key=prefix + "method")
        scenario = st.selectbox("표시 시나리오", SCENARIOS, key="analysis_scenario")
        with st.expander("분석 건수 설정"):
            st.selectbox("분석 범위", ["고정 가상 샘플"], disabled=True, key=prefix + "scope")
            st.checkbox("최종 분석 건수 자동 선택", disabled=True, key=prefix + "adaptive")
            st.caption("데모는 분석 건수나 유사도에 따라 결과를 계산하지 않습니다.")
        auto_save = st.checkbox("추천 결과 자동 저장", value=True, key="recommendation_auto_save")
        st.text_input("저장 시나리오명", "가상 추천 화면 체험", key=prefix + "scenario_name")
        st.checkbox("백테스트 사용", disabled=True, help="공개 데모에서는 실제 백테스트를 실행하지 않습니다.")
        st.caption("입력 폼과 저장 동선을 체험합니다. 입력값은 고정 샘플 금액을 변경하지 않습니다.")
        run = st.form_submit_button("분석 및 추천계산 시작", type="primary", key="recommendation_run")
    if run:
        st.session_state["recommendation_display"] = _sample_row(row, scenario)
        if auto_save:
            _remember([st.session_state["recommendation_display"]])
    display = st.session_state.get("recommendation_display")
    if not display or display["notice_id"] != row["id"]:
        return
    st.subheader("진행 상태")
    table([{"단계": label, "상태": state} for label, state in [
        ("공고 선택", "가상 공고 확인"), ("추천계산", "고정 샘플 표시"),
        ("결과 저장", "세션 저장됨" if st.session_state.get("demo_recommendations", {}).get(row["id"]) == display else "미저장"),
    ]], ["단계", "상태"])
    with st.expander("유사공고 · 고정 샘플"):
        st.caption("유사도 검색 없이 가상 목록의 앞 3건을 표시합니다. 실제 유사공고 선별 결과가 아닙니다.")
        table(store.notices()[:3], NOTICE_COLUMNS)
    st.subheader("추천 결과")
    a, b, c = st.columns(3)
    a.metric("최종 대표 추천투찰금액 · 가상", f"{display['amount']:,}원")
    b.metric("추천 기준", display["scenario"])
    c.metric("결과 유형", "고정 샘플")
    st.caption(display["note"])
    table([display], ["code", "title", "scenario", "amount", "note"])
    with st.expander("상세 추천 보기"):
        samples = [_sample_row(row, scenario) for scenario in SCENARIOS]
        table(samples, ["scenario", "amount", "note"])
        st.bar_chart(pd.DataFrame(recommendation(display["scenario"])["points"]), x="label", y="value")
        st.caption("차트도 새로 작성한 고정 표시값입니다.")
    a, b = st.columns(2)
    if a.button("추천 결과 다시 저장", key="recommendation_save", on_click=_remember, args=([display],)):
        st.success("가상 표시 결과를 현재 세션에 저장했습니다.")
    b.download_button("추천 결과 Excel용 CSV 다운로드", _csv([display]), "demo-recommendation.csv", "text/csv")


def daily_page(store):
    st.info(DEMO_NOTE)
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    st.caption("데모 개찰일은 가상 공고의 날짜를 사용합니다. 실제 개찰 정보가 아닙니다.")
    with st.form("daily_search_form"):
        a, b, c, d = st.columns(4)
        opening = a.date_input("개찰일", date.fromisoformat(rows[0]["deadline"]), key="daily_date")
        category = b.selectbox("분석 카테고리", ["전체", *store.categories()], key="daily_category")
        title = c.text_input("공고명", key="daily_title")
        code = d.text_input("공고번호", key="daily_code")
        a, b, c, d = st.columns(4)
        license_name = a.text_input("업종", key="daily_license")
        region = b.text_input("지역", key="daily_region")
        agency = c.text_input("발주기관", key="daily_agency")
        contract = d.text_input("계약방법", key="daily_contract")
        search = st.form_submit_button("공고 조회", type="primary", key="daily_search")
    if search:
        st.session_state["daily_query"] = dict(deadline=opening.isoformat(), category=category, title=title,
                                               code=code, license=license_name, region=region, agency=agency, contract=contract)
        st.session_state["daily_query_revision"] = st.session_state.get("daily_query_revision", 0) + 1
        st.session_state.pop("daily_confirmed", None)
        st.session_state.pop("daily_results", None)
    query = st.session_state.get("daily_query")
    if not query:
        st.info("개찰일과 검색 조건을 선택한 뒤 공고 조회를 눌러 주세요.")
        return
    rows = [row for row in rows if row["deadline"] == query["deadline"]
            and (query["category"] == "전체" or row["category"] == query["category"])
            and _matches({**row, "license": row["category"], "contract": "가상 일반경쟁"},
                         {field: query[field] for field in ("title", "code", "license", "region", "agency", "contract")})]
    st.subheader(f"조회 공고 · {len(rows)}건")
    if not rows:
        st.info("조회 조건에 맞는 공고가 없습니다.")
        return
    all_selected = st.checkbox("전체 선택", value=True, key="daily_select_all")
    selection = pd.DataFrame([{"선택": all_selected, "id": row["id"], "공고번호": row["code"], "공고명": row["title"],
                               "발주기관": row["agency"], "업종": row["category"], "지역": row["region"],
                               "기초금액": row["base_amount"], "개찰일": row["deadline"], "자료 상태": "고정 가상 자료"} for row in rows])
    editor = st.data_editor(selection, hide_index=True, width="stretch",
                            disabled=[column for column in selection.columns if column != "선택"],
                            column_config={"id": None, "선택": st.column_config.CheckboxColumn()},
                            key=f"daily_editor_{st.session_state.get('daily_query_revision', 0)}_{all_selected}")
    selected_ids = tuple(int(value) for value in editor.loc[editor["선택"], "id"])
    selected_rows = [row for row in rows if row["id"] in selected_ids]
    st.caption(f"선택한 공고 {len(selected_rows)}건")
    if st.button("선택 공고 샘플 데이터 확인", disabled=not selected_rows, key="daily_check"):
        st.session_state["daily_confirmed"] = selected_ids
    confirmed = bool(selected_ids) and st.session_state.get("daily_confirmed") == selected_ids
    if confirmed:
        st.success("선택한 공고의 가상 샘플을 확인했습니다. 실제 API 보강은 수행하지 않습니다.")
    a, b, c = st.columns(3)
    a.selectbox("반올림 단위", [100, 1000, 10000], key="daily_round")
    b.selectbox("처리 방식", ["round", "floor", "ceil"], key="daily_method")
    scenario = c.selectbox("표시 시나리오", SCENARIOS, key="daily_scenario")
    auto_save = st.checkbox("계산 완료 후 자동 저장", value=True, key="daily_auto_save")
    st.checkbox("백테스트 사용", disabled=True, key="daily_backtest", help="실제 분석 대신 고정 샘플만 표시합니다.")
    if st.button("선택 공고 추천계산 · 고정 샘플", type="primary", disabled=not confirmed, key="daily_calculate"):
        results = [_sample_row(row, scenario) for row in selected_rows]
        st.session_state["daily_results"] = results
        st.session_state["daily_result_selection"] = selected_ids
        if auto_save:
            _remember(results)
    results = st.session_state.get("daily_results", [])
    if not results or st.session_state.get("daily_result_selection") != selected_ids:
        return
    st.subheader("추천 결과 요약")
    saved = st.session_state.get("demo_recommendations", {})
    for column, label, count in zip(st.columns(4), ["조회 공고", "선택 공고", "샘플 표시 완료", "저장 완료"],
                                     [len(rows), len(selected_rows), len(results), sum(saved.get(row["notice_id"]) == row for row in results)]):
        column.metric(label, f"{count}건")
    view = [{**row, "저장 상태": "저장 완료" if saved.get(row["notice_id"]) == row else "저장 가능"} for row in results]
    status = st.selectbox("저장 상태 필터", ["전체", "저장 가능", "저장 완료"], key="daily_saved_filter")
    table([row for row in view if status == "전체" or row["저장 상태"] == status], ["code", "title", "scenario", "amount", "저장 상태"])
    if st.button("저장 가능한 결과 일괄저장", key="daily_save_all"):
        _remember(results)
        done("고정 샘플 결과를 현재 세션에 저장했습니다.")
    st.download_button("개찰일별 추천투찰금액 Excel용 CSV 다운로드", _csv(view), "demo-daily.csv", "text/csv")


def management_page(store):
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    with st.expander("내 회사 정보"):
        st.caption("회사 식별자 DEMO-COMPANY-001 · 사용자 admin · 실제 사업자정보를 사용하지 않습니다.")
        with st.form("demo_company_form"):
            company = st.text_input("가상 회사명", st.session_state.get("demo_company", "가상 데모회사"), key="demo_company_name")
            save_company = st.form_submit_button("가상 회사 정보 저장")
        if save_company:
            if not company.strip():
                st.error("가상 회사명을 입력해 주세요.")
            else:
                previous = st.session_state.get("demo_company", "가상 데모회사")
                if st.session_state.get("submission_None_company", previous) == previous:
                    st.session_state["submission_None_company"] = company.strip()
                st.session_state["demo_company"] = company.strip()
                st.success("가상 회사 정보를 현재 세션에 저장했습니다.")
    with st.form("management_search_form"):
        a, b, c = st.columns(3)
        with a:
            start, end = _date_range(rows, "management_", "참가마감일")
        category = b.selectbox("카테고리", ["전체", *store.categories()], key="management_category")
        recommendation_filter = b.selectbox("추천결과 저장 여부", ["전체", "있음", "없음"], key="management_recommended")
        submission_filter = c.selectbox("내 투찰 기록 여부", ["전체", "있음", "없음"], key="management_submitted")
        result_filter = c.selectbox("낙찰결과 존재 여부", ["전체", "있음", "없음"], key="management_result")
        terms = {}
        for column, field, label in zip(st.columns(5), ["code", "title", "agency", "region", "category"], ["공고번호", "공고명", "발주기관", "지역", "업종"]):
            terms[field] = column.text_input(label, key="management_filter_" + field)
        missing_only = st.checkbox("미입력 공고만 보기", key="management_missing")
        st.form_submit_button("조회", type="primary", key="management_search")
    submissions = {row["notice_id"]: row for row in store.submissions()}
    results = {row["notice_id"]: row for row in store.results()}
    saved = st.session_state.get("demo_recommendations", {})
    filtered = [row for row in rows if start <= row["deadline"] <= end
                and (category == "전체" or category == row["category"]) and _matches(row, terms)
                and (not missing_only or row["id"] not in submissions)
                and all(mode == "전체" or (row["id"] in source) == (mode == "있음")
                        for mode, source in [(recommendation_filter, saved), (submission_filter, submissions), (result_filter, results)])]
    a, b, c = st.columns(3)
    a.metric("조회 공고", f"{len(filtered)}건")
    b.metric("투찰 기록", f"{sum(row['id'] in submissions for row in filtered)}건")
    c.metric("결과 등록", f"{sum(row['id'] in results for row in filtered)}건")
    st.caption("가상 공고의 투찰금액·상태·메모를 직접 편집하고 저장할 수 있습니다.")
    if filtered:
        baseline = [{"id": row["id"], "공고번호": row["code"], "공고명": row["title"], "발주기관": row["agency"],
                     "카테고리": row["category"], "참가마감일": row["deadline"], "샘플 추천금액": saved.get(row["id"], {}).get("amount", 0),
                     "내 투찰금액": submissions.get(row["id"], {}).get("amount", 0),
                     "내 투찰상태": submissions.get(row["id"], {}).get("status", "작성중"),
                     "메모": submissions.get(row["id"], {}).get("memo", "")} for row in filtered]
        editable = ["내 투찰금액", "내 투찰상태", "메모"]
        edited = st.data_editor(pd.DataFrame(baseline), hide_index=True, width="stretch",
                                disabled=[key for key in baseline[0] if key not in editable],
                                column_config={"id": None, "내 투찰금액": st.column_config.NumberColumn(min_value=0, max_value=10**12, step=1),
                                               "내 투찰상태": st.column_config.SelectboxColumn(options=list(SUBMISSION_STATUSES), required=True)},
                                key=f"management_editor_{st.session_state.get('management_revision', 0)}")
        selected = _notice_choice("선택 저장 공고", filtered, "management_selected")
        a, b = st.columns(2)
        save_all = a.button("전체 변경사항 저장", key="management_save_all")
        save_selected = b.button("선택 공고 저장", key="management_save_selected")
        if save_all or save_selected:
            count = 0
            try:
                for current, before in zip(edited.to_dict("records"), baseline):
                    changed = any(current[field] != before[field] for field in editable)
                    if (save_all and changed) or (save_selected and current["id"] == selected["id"]):
                        existing = submissions.get(current["id"], {})
                        store.save_submission(dict(notice_id=int(current["id"]), company=existing.get("company", st.session_state.get("demo_company", "가상 데모회사")),
                                                   amount=int(current["내 투찰금액"]), status=current["내 투찰상태"], memo=current["메모"] or ""),
                                              submission_id=existing.get("id"))
                        count += 1
                st.session_state["management_revision"] = st.session_state.get("management_revision", 0) + 1
                done(f"투찰 기록 {count}건을 저장했습니다.")
            except (ValueError, TypeError) as exc:
                st.error(f"저장한 기록 {count}건. 나머지 입력값을 확인해 주세요: {exc}")
        st.download_button("나의 투찰관리 Excel용 CSV 다운로드", _csv(baseline), "demo-my-bids.csv", "text/csv")
    else:
        st.info("조회 조건에 맞는 공고가 없습니다.")
    with st.expander("투찰 상세 등록·수정·삭제", expanded=True):
        records = {row["id"]: row for row in store.submissions()}
        edit_id = st.selectbox("투찰 편집", [None, *records], key="submission_edit",
                               format_func=lambda value: "새 투찰 등록" if value is None else f"{records[value]['notice_code']} · {records[value]['company']}")
        item = records.get(edit_id, {})
        prefix = f"submission_{edit_id}_"
        lookup = {row["id"]: row for row in rows}
        with st.container(border=True):
            selected_id = item.get("notice_id", rows[0]["id"])
            notice_id = st.selectbox("공고", list(lookup), index=list(lookup).index(selected_id), format_func=lambda value: lookup[value]["title"], key=prefix + "notice")
            a, b = st.columns(2)
            st.session_state.setdefault(prefix + "company", item.get("company", st.session_state.get("demo_company", "가상 데모회사")))
            company = a.text_input("가상 회사명", key=prefix + "company")
            amount = b.number_input("투찰 금액 (원)", min_value=0, max_value=10**12, value=item.get("amount", 0), key=prefix + "amount")
            status = st.selectbox("투찰 상태", list(SUBMISSION_STATUSES), index=list(SUBMISSION_STATUSES).index(item.get("status", "작성중")), key=prefix + "status")
            memo = st.text_input("투찰 메모", item.get("memo", ""), key=prefix + "memo")
            submit = st.button("투찰 저장", type="primary", key="save_submission")
        if submit:
            try:
                store.save_submission(dict(notice_id=notice_id, company=company, amount=amount, status=status, memo=memo), submission_id=edit_id)
                st.session_state["management_revision"] = st.session_state.get("management_revision", 0) + 1
                done("투찰 기록을 저장했습니다.")
            except ValueError as exc:
                st.error(str(exc))
        if edit_id is not None:
            confirm = st.checkbox("선택한 투찰을 삭제합니다.", key=f"submission_confirm_{edit_id}")
            if st.button("투찰 삭제", disabled=not confirm, key="delete_submission"):
                store.delete_submission(edit_id)
                del st.session_state["submission_edit"]
                st.session_state["management_revision"] = st.session_state.get("management_revision", 0) + 1
                done("투찰 기록을 삭제했습니다.")


def status_page(store):
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    with st.form("status_search_form"):
        a, b, c = st.columns(3)
        with a:
            start, end = _date_range(rows, "status_", "개찰일")
        code = b.text_input("공고번호", key="status_code")
        title = b.text_input("공고명", key="status_title")
        region = c.text_input("지역", key="status_region")
        outcome = c.selectbox("결과 상태", ["전체", "결과 미등록", *RESULT_OUTCOMES], key="status_outcome")
        st.form_submit_button("조회", type="primary", key="status_search")
    a, b = st.columns(2)
    if a.button("저장된 개찰결과 재매칭", key="status_rematch"):
        st.info("현재 세션에 저장된 가상 공고·투찰·결과를 공고 ID로 다시 표시했습니다.")
    if b.button("개찰결과/실제순위 조회 · 샘플", key="status_lookup"):
        st.session_state["status_response"] = api_response()
    if "status_response" in st.session_state:
        st.info("고정 API 샘플을 확인했습니다. 실제 개찰결과나 순위를 수집하지 않습니다.")
        with st.expander("샘플 응답 구조"):
            st.json(st.session_state["status_response"])
    submissions = {row["notice_id"]: row for row in store.submissions()}
    results = {row["notice_id"]: row for row in store.results()}
    view = [{**row, "내 투찰금액": submissions.get(row["id"], {}).get("amount", 0),
             "내 투찰상태": submissions.get(row["id"], {}).get("status", "미입력"),
             "결과 상태": results.get(row["id"], {}).get("outcome", "결과 미등록"),
             "개찰결과 금액": results.get(row["id"], {}).get("amount", 0)}
            for row in rows if start <= row["deadline"] <= end and _matches(row, {"code": code, "title": title, "region": region})]
    view = [row for row in view if outcome == "전체" or outcome == row["결과 상태"]]
    for column, label, count in zip(st.columns(5), ["관심공고", "표시 공고", "샘플 낙찰", "샘플 미선정", "순위 확인 불가"],
                                     [len(rows), len(view), sum(row["결과 상태"] == "샘플 낙찰" for row in view),
                                      sum(row["결과 상태"] == "샘플 미선정" for row in view), len(view)]):
        column.metric(label, f"{count}건")
    table(view, ["code", "title", "region", "deadline", "내 투찰금액", "내 투찰상태", "결과 상태", "개찰결과 금액"])
    with st.expander("추천 후보 상세보기"):
        selected = _notice_choice("공고번호", rows, "status_detail")
        st.caption(DEMO_NOTE)
        table([_sample_row(selected, scenario) for scenario in SCENARIOS], ["scenario", "amount", "note"])
    st.download_button("내 투찰현황 Excel용 CSV 다운로드", _csv(view), "demo-bid-status.csv", "text/csv")


def api_page(store):
    st.info("데모용 샘플 응답입니다. 실제 외부 API를 호출하거나 API 키를 사용하지 않습니다.")
    with st.expander("ServiceKey 설정"):
        st.text_input("ServiceKey", "데모는 키 불필요", disabled=True, key="api_key_placeholder")
    a, b, c = st.columns(3)
    a.metric("오늘 API 호출 횟수", "0회")
    b.metric("실행 방식", "고정 샘플")
    c.metric("반영 위치", "현재 세션")
    a, b, c = st.columns(3)
    a.selectbox("조회 대상", ["입찰공고 샘플", "개찰결과 샘플", "낙찰결과 샘플"], key="api_target")
    start = b.date_input("조회 시작일", date(2026, 10, 1), key="api_start")
    end = c.date_input("조회 종료일", date(2026, 10, 31), key="api_end")
    a, b = st.columns(2)
    categories = a.multiselect("업종 키워드", ["가상 시설", "가상 물품", "가상 용역"], key="api_categories")
    regions = b.multiselect("지역", ["가상 동부", "가상 서부"], key="api_regions")
    a, b, c = st.columns(3)
    a.number_input("최대 페이지", min_value=1, max_value=10, value=1, key="api_pages")
    b.number_input("페이지당 요청 행 수(numOfRows)", min_value=1, max_value=100, value=20, key="api_rows")
    scenario = c.selectbox("응답 시나리오", ["정상", "빈 결과", "오류"], key="api_scenario")
    st.caption("조회 대상과 페이지 옵션은 입력 화면 체험용입니다. 기간·업종·지역·키워드는 고정 샘플 목록에만 적용됩니다.")
    a, b = st.columns(2)
    title = a.text_input("공고명 키워드", key="api_title")
    code = b.text_input("공고번호 직접 조회", key="api_code")
    if st.button("API 조회", type="primary", key="api_preview"):
        if start > end:
            st.error("조회 종료일은 시작일 이후여야 합니다.")
            st.session_state.pop("api_response", None)
        else:
            response = api_response(scenario)
            response["items"] = [row for row in response["items"] if start.isoformat() <= row["deadline"] <= end.isoformat()
                                 and (not categories or row["category"] in categories) and (not regions or row["region"] in regions)
                                 and _matches(row, {"code": code, "title": title})]
            response["total"] = len(response["items"])
            st.session_state["api_response"] = response
    response = st.session_state.get("api_response")
    if not response:
        return
    if response["status"] == "error":
        st.warning(response["message"])
    elif not response["items"]:
        st.info("샘플 조회 결과가 없습니다.")
    else:
        st.subheader(f"API 조회 결과 · 고정 샘플 {response['total']}건")
        table(response["items"], NOTICE_COLUMNS)
        a, b, c = st.columns(3)
        if a.button("공사기초금액조회 보강 · 샘플", key="api_enrich"):
            st.info("표의 기초금액은 고정 가상 샘플입니다. 외부 조회나 추가 보강은 수행하지 않습니다.")
        if b.button("인포21C 데이터와 비교 · 샘플", key="api_compare"):
            existing = {row["code"] for row in store.notices()}
            table([{**row, "데모 저장 여부": "있음" if row["code"] in existing else "없음"} for row in response["items"]], ["code", "title", "base_amount", "데모 저장 여부"])
        if c.button("API 기준으로 DB 반영", key="api_apply"):
            missing = {row["category"] for row in response["items"]} - set(store.categories())
            if missing:
                st.error("샘플 분류를 먼저 등록해 주세요: " + ", ".join(sorted(missing)))
            else:
                existing = {row["code"]: row["id"] for row in store.notices()}
                try:
                    for item in response["items"]:
                        store.save_notice(item, notice_id=existing.get(item["code"]))
                    done("고정 API 샘플을 현재 세션의 가상 공고에 반영했습니다.")
                except ValueError as exc:
                    st.error(str(exc))
    with st.expander("샘플 응답 구조", expanded=True):
        st.json(response)


def results_page(store):
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    st.caption("가상 결과 관리입니다. 실제 금액 비교 계산과 자동 대표 추천 판단은 포함하지 않습니다.")
    pending, excel, pdf, manual, compare = st.tabs(["결과 미회수 공고", "개찰결과 엑셀", "개찰결과 PDF", "수기 입력 및 비교", "추천 결과 비교/대표 지정"])
    records = store.results()
    result_ids = {row["notice_id"] for row in records}
    with pending:
        unresolved = [row for row in rows if row["id"] not in result_ids]
        st.metric("결과 미회수 공고", f"{len(unresolved)}건")
        table(unresolved, NOTICE_COLUMNS)
        if unresolved:
            row = _notice_choice("결과를 입력할 공고", unresolved, "result_unresolved_notice")
            if st.button("이 공고를 수기 입력 대상으로 선택", key="result_choose_manual"):
                st.session_state["result_notice"] = row["id"]
                st.success("수기 입력 및 비교 탭에서 선택한 공고를 확인해 주세요.")
    with excel:
        _upload_panel(store, "results_tab_excel", "개찰결과")
    with pdf:
        _upload_panel(store, "results_tab_pdf", "개찰결과", pdf=True)
    with manual:
        table(records, ["notice_code", "notice_title", "outcome", "amount", "note"])
        row = _notice_choice("결과를 기록할 공고", rows, "result_notice")
        selected = row["id"]
        item = next((record for record in records if record["notice_id"] == selected), {})
        context = st.session_state.get("demo_result_context", {}).get(selected, {})
        prefix = f"result_{selected}_"
        with st.form(prefix + "form"):
            st.text_input("공고번호", row["code"], disabled=True, key=prefix + "code")
            a, b, c = st.columns(3)
            planned = a.number_input("실제 예정가격 · 가상 입력", min_value=0, max_value=10**12, value=context.get("planned", 0), key=prefix + "planned")
            award = b.number_input("실제 낙찰금액 · 가상 입력", min_value=0, max_value=10**12, value=context.get("award", 0), key=prefix + "award")
            amount = c.number_input("실제 1순위 투찰금액 · 가상 입력", min_value=0, max_value=10**12, value=item.get("amount", 0), key=prefix + "amount")
            outcome = st.selectbox("샘플 결과", list(RESULT_OUTCOMES), index=list(RESULT_OUTCOMES).index(item.get("outcome", "검토중")), key=prefix + "outcome")
            note = st.text_input("결과 메모", item.get("note", ""), key=prefix + "note")
            save = st.form_submit_button("실제 결과 저장", type="primary", key="save_result")
        if save:
            try:
                store.save_result(dict(notice_id=selected, outcome=outcome, amount=amount, note=note))
                st.session_state.setdefault("demo_result_context", {})[selected] = dict(planned=planned, award=award)
                done("가상 결과를 현재 세션에 저장했습니다.")
            except ValueError as exc:
                st.error(str(exc))
        if item:
            confirm = st.checkbox("선택한 결과를 삭제합니다.", key=f"result_confirm_{selected}")
            st.button("결과 삭제", disabled=not confirm, key="delete_result", on_click=_delete_result, args=(store, selected))
    with compare:
        row = _notice_choice("비교할 공고번호", rows, "result_compare_notice")
        comparison = [_sample_row(row, scenario) for scenario in SCENARIOS]
        table(comparison, ["code", "scenario", "amount", "note"])
        st.caption("대표 표시는 사용자가 선택한 샘플만 저장합니다. 금액·성과에 따른 자동 선정은 없습니다.")
        choice = st.selectbox("대표로 표시할 샘플", SCENARIOS, key="result_sample_choice")
        confirm = st.checkbox("선택한 샘플을 이 공고의 대표로 표시합니다.", key="result_primary_confirm")
        a, b, c = st.columns(3)
        if a.button("대표 추천 지정 · 샘플 선택", disabled=not confirm, key="result_set_primary"):
            st.session_state.setdefault("demo_primary", {})[row["id"]] = choice
            _remember([_sample_row(row, choice)])
            st.success("사용자가 선택한 고정 샘플을 대표로 표시했습니다.")
        if b.button("대표 추천 해제", key="result_clear_primary"):
            st.session_state.setdefault("demo_primary", {}).pop(row["id"], None)
            st.success("대표 샘플 표시를 해제했습니다.")
        c.download_button("비교 결과 Excel용 CSV 다운로드", _csv(comparison), "demo-comparison.csv", "text/csv")
        primary = st.session_state.get("demo_primary", {}).get(row["id"])
        if primary:
            st.caption("현재 대표 샘플: " + primary)
