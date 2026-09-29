"""Original workflow layouts backed only by newly written demo data."""
from datetime import date

import pandas as pd
import streamlit as st

from demo.data_pages import _upload_panel
from demo.services import api_response, backtest_sample, recommendation
from demo.store import RESULT_OUTCOMES, SUBMISSION_STATUSES
from demo.ui import csv_bytes as _csv, done, table


NOTICE_COLUMNS = ["code", "title", "agency", "category", "region", "base_amount", "deadline", "status"]
SCENARIOS = ["샘플 A", "샘플 B", "샘플 C"]
DEMO_NOTE = "고정 샘플을 표시하며 실제 추천 계산은 하지 않습니다."


def _notice_choice(label, rows, key):
    lookup = {row["id"]: row for row in rows}
    selected = st.selectbox(label, list(lookup), key=key,
                            format_func=lambda item: f"{lookup[item]['code']} · {lookup[item]['title']}")
    return lookup[selected]


def _matches(row, query):
    query = query.strip().casefold()
    return not query or any(query in str(row[field]).casefold() for field in ("code", "title"))


def _sample_row(notice, scenario):
    sample = recommendation(scenario)
    return dict(notice_id=notice["id"], code=notice["code"], title=notice["title"],
                scenario=scenario, amount=sample["amount"], note=sample["note"],
                bid_rate=sample["bid_rate"], confidence=sample["confidence"])


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
    left, right = st.columns(2)
    start = left.date_input(label + " 시작", min(dates), key=prefix + "start")
    end = right.date_input(label + " 종료", max(dates), key=prefix + "end")
    return start.isoformat(), end.isoformat()


def daily_page(store):
    user_tab, backtest_tab = st.tabs(["사용자용 추천계산", "백테스트"])
    with user_tab:
        _daily_recommendations(store)
    with backtest_tab:
        st.info(backtest_sample()["note"])
        if st.button("백테스트 샘플 보기", type="primary", key="backtest_show"):
            st.session_state["backtest_visible"] = True
        if st.session_state.get("backtest_visible"):
            view = backtest_sample()["rows"]
            won = sum(row["결과"] == "낙찰" for row in view)
            a, b, c = st.columns(3)
            a.metric("검증 공고 · 샘플", f"{len(view)}건")
            b.metric("낙찰 · 샘플", f"{won}건")
            c.metric("낙찰률 · 샘플", f"{won / len(view):.0%}")
            _recommendation_table(view)
            st.download_button("백테스트 샘플 다운로드", _csv(view), "demo-backtest.csv", "text/csv")


def _recommendation_table(view):
    frame = pd.DataFrame(view)
    styled = frame.style.set_properties(subset=["추천 금액 (원)"],
                                        **{"background-color": "#fff7cc", "color": "#292824", "font-weight": "700"})
    st.dataframe(styled, hide_index=True, width="stretch", column_config={
        "추천 금액 (원)": st.column_config.NumberColumn(format="localized"),
        "실투찰율 (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "신뢰도 (%)": st.column_config.NumberColumn(format="%.1f%%"),
    })


def _daily_recommendations(store):
    requested_date = st.session_state.pop("daily_requested_date", None)
    if requested_date is not None:
        if isinstance(requested_date, str):
            requested_date = date.fromisoformat(requested_date)
        st.session_state["daily_date"] = requested_date
        st.session_state["daily_category"] = "전체"
        st.session_state["daily_keyword"] = ""
        st.session_state["daily_select_all"] = True
    st.info(DEMO_NOTE)
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    st.session_state.setdefault("daily_date", date.fromisoformat(rows[0]["deadline"]))
    with st.form("daily_search_form"):
        a, b, c = st.columns([1, 1, 2])
        opening = a.date_input("개찰일", key="daily_date")
        category = b.selectbox("카테고리", ["전체", *store.categories()], key="daily_category")
        keyword = c.text_input("공고명 또는 번호", key="daily_keyword")
        search = st.form_submit_button("공고 조회", type="primary", key="daily_search")
    if search or requested_date is not None:
        st.session_state["daily_query"] = dict(deadline=opening.isoformat(), category=category, keyword=keyword)
        st.session_state["daily_query_revision"] = st.session_state.get("daily_query_revision", 0) + 1
        for key in ("daily_confirmed", "daily_results", "daily_result_selection"):
            st.session_state.pop(key, None)
    query = st.session_state.get("daily_query")
    if not query:
        st.info("개찰일을 선택하고 공고를 조회해 주세요.")
        return
    rows = [row for row in rows if row["deadline"] == query["deadline"]
            and (query["category"] == "전체" or row["category"] == query["category"])
            and _matches(row, query.get("keyword", ""))]
    st.subheader(f"조회 공고 · {len(rows)}건")
    if not rows:
        st.info("조회 조건에 맞는 공고가 없습니다.")
        return
    st.session_state.setdefault("daily_select_all", True)
    all_selected = st.checkbox("전체 선택", key="daily_select_all")
    selection = pd.DataFrame([{"선택": all_selected, "id": row["id"], "공고번호": row["code"], "공고명": row["title"],
                               "발주기관": row["agency"], "카테고리": row["category"], "지역": row["region"],
                               "기초금액": row["base_amount"], "개찰일": row["deadline"]} for row in rows])
    editor = st.data_editor(selection, hide_index=True, width="stretch",
                            disabled=[column for column in selection.columns if column != "선택"],
                            column_config={"id": None, "선택": st.column_config.CheckboxColumn()},
                            key=f"daily_editor_{st.session_state.get('daily_query_revision', 0)}_{all_selected}")
    selected_ids = tuple(int(value) for value in editor.loc[editor["선택"], "id"])
    selected_rows = [row for row in rows if row["id"] in selected_ids]
    st.caption(f"선택한 공고 {len(selected_rows)}건")
    if st.button("선택 공고 샘플 확인", disabled=not selected_rows, key="daily_check"):
        st.session_state["daily_confirmed"] = selected_ids
    confirmed = bool(selected_ids) and st.session_state.get("daily_confirmed") == selected_ids
    if confirmed:
        st.success("선택한 공고를 확인했습니다.")
    scenario = st.selectbox("표시할 샘플", SCENARIOS, key="daily_scenario")
    auto_save = st.checkbox("결과 자동 저장", value=True, key="daily_auto_save")
    if st.button("선택 공고 추천계산", type="primary", disabled=not confirmed, key="daily_calculate"):
        results = [_sample_row(row, scenario) for row in selected_rows]
        st.session_state["daily_results"] = results
        st.session_state["daily_result_selection"] = selected_ids
        if auto_save:
            _remember(results)
    results = st.session_state.get("daily_results", [])
    if not results or st.session_state.get("daily_result_selection") != selected_ids:
        return
    st.subheader("추천 결과")
    saved = st.session_state.get("demo_recommendations", {})
    for column, label, count in zip(st.columns(3), ["조회 공고", "샘플 결과", "저장 완료"],
                                     [len(rows), len(results), sum(saved.get(row["notice_id"]) == row for row in results)]):
        column.metric(label, f"{count}건")
    view = [{"공고번호": row["code"], "공고명": row["title"], "샘플": row["scenario"], "추천 금액 (원)": row["amount"],
             "실투찰율 (%)": recommendation(row["scenario"])["bid_rate"],
             "신뢰도 (%)": recommendation(row["scenario"])["confidence"],
             "저장 상태": "저장 완료" if saved.get(row["notice_id"]) == row else "저장 가능"} for row in results]
    selected = results[0]
    if len(results) > 1:
        lookup = {row["notice_id"]: row for row in results}
        selected_id = st.selectbox("추천 결과 공고", list(lookup), key="daily_result_notice",
                                   format_func=lambda value: f'{lookup[value]["code"]} · {lookup[value]["title"]}')
        selected = lookup[selected_id]
    sample = recommendation(selected["scenario"])
    a, b, c = st.columns([2, 1, 1])
    with a:
        st.markdown(f'<div class="recommendation-amount"><span>추천금액 · 샘플</span>'
                    f'<strong>{selected["amount"]:,}원</strong></div>', unsafe_allow_html=True)
    b.metric("실투찰율 · 샘플", f'{sample["bid_rate"]:.2f}%')
    c.metric("신뢰도 · 샘플", f'{sample["confidence"]:.1f}%')
    st.caption("금액·실투찰율·신뢰도는 서로 독립적인 가상 표시값이며 실제 계산·평가 결과가 아닙니다.")
    _recommendation_table(view)
    if st.button("결과 저장", key="daily_save_all"):
        _remember(results)
        done("샘플 결과를 저장했습니다.")
    st.download_button("추천 결과 다운로드", _csv(view), "demo-daily.csv", "text/csv")


def management_page(store):
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
    with st.expander("내 회사 정보"):
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
                st.success("가상 회사 정보를 저장했습니다.")
    with st.form("management_search_form"):
        a, b, c = st.columns([2, 1, 1])
        keyword = a.text_input("공고명 또는 번호", key="management_keyword")
        category = b.selectbox("카테고리", ["전체", *store.categories()], key="management_category")
        status = c.selectbox("투찰 상태", ["전체", "미입력", *SUBMISSION_STATUSES], key="management_status")
        st.form_submit_button("조회", type="primary", key="management_search")
    submissions = {row["notice_id"]: row for row in store.submissions()}
    results = {row["notice_id"]: row for row in store.results()}
    saved = st.session_state.get("demo_recommendations", {})
    filtered = [row for row in rows if _matches(row, keyword)
                and (category == "전체" or category == row["category"])
                and (status == "전체" or submissions.get(row["id"], {}).get("status", "미입력") == status)]
    a, b, c = st.columns(3)
    a.metric("조회 공고", f"{len(filtered)}건")
    b.metric("투찰 기록", f"{sum(row['id'] in submissions for row in filtered)}건")
    c.metric("결과 등록", f"{sum(row['id'] in results for row in filtered)}건")
    st.caption("투찰금액·상태·메모를 표에서 편집할 수 있습니다.")
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
        st.download_button("투찰관리 다운로드", _csv(pd.DataFrame(baseline).drop(columns="id")), "demo-my-bids.csv", "text/csv")
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
        start, end = _date_range(rows, "status_", "개찰일")
        left, right = st.columns([2, 1])
        keyword = left.text_input("공고명 또는 번호", key="status_keyword")
        outcome = right.selectbox("결과 상태", ["전체", "낙찰", "미낙찰", "결과 대기", "작성중", "미투찰"], key="status_outcome")
        st.form_submit_button("조회", type="primary", key="status_search")
    if start > end:
        st.error("종료일은 시작일 이후여야 합니다.")
        return
    submissions = {}
    for submission in store.submissions():
        previous = submissions.get(submission["notice_id"], {})
        if submission["status"] == "제출완료" or previous.get("status") != "제출완료":
            submissions[submission["notice_id"]] = submission
    results = {row["notice_id"]: row for row in store.results()}
    outcome_labels = {"샘플 낙찰": "낙찰", "샘플 미선정": "미낙찰", "검토중": "결과 대기"}
    view = []
    for row in rows:
        if not (start <= row["deadline"] <= end and _matches(row, keyword)):
            continue
        submission = submissions.get(row["id"], {})
        result = results.get(row["id"], {})
        status = submission.get("status", "미투찰")
        result_status = outcome_labels.get(result.get("outcome"), "결과 대기") if status == "제출완료" else status
        view.append({"공고번호": row["code"], "공고명": row["title"], "개찰일": row["deadline"],
                     "최종 제출금액": submission.get("amount", 0) if status == "제출완료" else 0, "내 투찰상태": status,
                     "결과 상태": result_status, "개찰결과 금액": result.get("amount", 0)})
    view = [row for row in view if outcome == "전체" or outcome == row["결과 상태"]]
    counts = [len(view), sum(row["내 투찰상태"] == "제출완료" for row in view)]
    counts.extend(sum(row["결과 상태"] == result for row in view) for result in ("낙찰", "미낙찰", "결과 대기"))
    for column, label, count in zip(st.columns(5), ["조회 공고", "제출완료", "낙찰", "미낙찰", "결과 대기"], counts):
        column.metric(label, f"{count}건")
    st.caption("완료한 투찰 기록을 기준으로 낙찰 결과를 표시합니다.")
    columns = ["공고번호", "공고명", "개찰일", "최종 제출금액", "내 투찰상태", "결과 상태", "개찰결과 금액"]
    table(view, columns)
    if view:
        st.download_button("투찰현황 다운로드", _csv(view), "demo-bid-status.csv", "text/csv")


def api_page(store):
    st.info("외부 연결 없이 고정 샘플을 조회합니다.")
    with st.form("api_search_form"):
        a, b, c = st.columns([2, 1, 1])
        keyword = a.text_input("공고명 또는 번호", key="api_keyword")
        category = b.selectbox("카테고리", ["전체", "가상 시설", "가상 물품"], key="api_category")
        scenario = c.selectbox("샘플 응답", ["정상", "빈 결과", "오류"], key="api_scenario")
        search = st.form_submit_button("API 조회", type="primary", key="api_preview")
    if search:
        response = api_response(scenario)
        response["items"] = [row for row in response["items"] if _matches(row, keyword)
                             and (category == "전체" or row["category"] == category)]
        response["total"] = len(response["items"])
        st.session_state["api_response"] = response
    response = st.session_state.get("api_response")
    if not response:
        return
    if response["status"] == "error":
        st.warning("오류 응답 샘플입니다. 다른 응답을 선택해 주세요.")
    elif not response["items"]:
        st.info("조회 결과가 없습니다.")
    else:
        st.subheader(f"조회 결과 · {response['total']}건")
        existing = {row["code"]: row["id"] for row in store.notices()}
        view = [{**row, "등록 상태": "등록됨" if row["code"] in existing else "미등록"} for row in response["items"]]
        table(view, [*NOTICE_COLUMNS, "등록 상태"])
        if st.button("공고에 반영", key="api_apply"):
            missing = {row["category"] for row in response["items"]} - set(store.categories())
            if missing:
                st.error("샘플 분류를 먼저 등록해 주세요: " + ", ".join(sorted(missing)))
            else:
                try:
                    for item in response["items"]:
                        store.save_notice(item, notice_id=existing.get(item["code"]))
                    done("조회한 샘플을 공고에 반영했습니다.")
                except ValueError as exc:
                    st.error(str(exc))


def results_page(store):
    rows = store.notices()
    if not rows:
        st.info("공고를 먼저 등록해 주세요.")
        return
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
        prefix = f"result_{selected}_"
        with st.form(prefix + "form"):
            amount = st.number_input("결과 금액 (원)", min_value=0, max_value=10**12, value=item.get("amount", 0), key=prefix + "amount")
            outcome = st.selectbox("샘플 결과", list(RESULT_OUTCOMES), index=list(RESULT_OUTCOMES).index(item.get("outcome", "검토중")), key=prefix + "outcome")
            note = st.text_input("결과 메모", item.get("note", ""), key=prefix + "note")
            save = st.form_submit_button("결과 저장", type="primary", key="save_result")
        if save:
            try:
                store.save_result(dict(notice_id=selected, outcome=outcome, amount=amount, note=note))
                done("결과를 저장했습니다.")
            except ValueError as exc:
                st.error(str(exc))
        if item:
            confirm = st.checkbox("선택한 결과를 삭제합니다.", key=f"result_confirm_{selected}")
            st.button("결과 삭제", disabled=not confirm, key="delete_result", on_click=_delete_result, args=(store, selected))
    with compare:
        row = _notice_choice("비교할 공고번호", rows, "result_compare_notice")
        comparison = [{"공고번호": row["code"], "샘플": scenario, "추천 금액 (원)": recommendation(scenario)["amount"]} for scenario in SCENARIOS]
        table(comparison, ["공고번호", "샘플", "추천 금액 (원)"])
        st.caption("고정 샘플 중 대표로 표시할 항목을 선택합니다.")
        choice = st.selectbox("대표로 표시할 샘플", SCENARIOS, key="result_sample_choice")
        confirm = st.checkbox("선택한 샘플을 이 공고의 대표로 표시합니다.", key="result_primary_confirm")
        a, b, c = st.columns(3)
        if a.button("대표 추천 지정 · 샘플 선택", disabled=not confirm, key="result_set_primary"):
            st.session_state.setdefault("demo_primary", {})[row["id"]] = choice
            _remember([_sample_row(row, choice)])
            st.success("선택한 샘플을 대표로 지정했습니다.")
        if b.button("대표 추천 해제", key="result_clear_primary"):
            st.session_state.setdefault("demo_primary", {}).pop(row["id"], None)
            st.success("대표 샘플 표시를 해제했습니다.")
        c.download_button("비교 결과 다운로드", _csv(comparison), "demo-comparison.csv", "text/csv")
        primary = st.session_state.get("demo_primary", {}).get(row["id"])
        if primary:
            st.caption("현재 대표 샘플: " + primary)
