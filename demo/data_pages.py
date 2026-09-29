"""공개 화면 구조를 재현하는 가상 자료 관리 화면. 운영 모듈과 연결하지 않는다."""
from datetime import date, datetime

import streamlit as st

from demo.ui import csv_bytes, done, table
from demo.workspace import open_tab


def _table(rows, columns=None):
    table(rows, columns or (list(rows[0]) if rows else []))


def _notice_display(rows):
    return [{"공고번호": row["code"], "공고명": row["title"], "발주기관": row["agency"],
             "카테고리": row["category"], "지역": row["region"], "기초금액": row["base_amount"],
             "개찰일": row["deadline"], "결과 상태": row["status"]} for row in rows]


def categories(store):
    descriptions = st.session_state.setdefault("category_descriptions", {})
    with st.form("create_category"):
        left, right = st.columns(2)
        name = left.text_input("새 카테고리명", key="category_name")
        description = right.text_input("설명", key="category_description")
        create = st.form_submit_button("생성", key="category_create")
    if create:
        try:
            store.add_category(name)
            descriptions[name.strip()] = description.strip()
            done("카테고리를 생성했습니다.")
        except ValueError as exc:
            st.error(str(exc))
    names = store.categories()
    counts = {name: len(store.notices(category=name)) for name in names}
    _table([{"카테고리명": name, "설명": descriptions.get(name, "가상 분류"), "공고 수": counts[name]}
            for name in names])
    for name in names:
        with st.expander(f"{name} ({counts[name]}건)"):
            with st.form(f"category_{name}"):
                edited = st.text_input("카테고리명", name, key=f"category_edit_{name}")
                detail = st.text_input("설명", descriptions.get(name, "가상 분류"), key=f"category_desc_{name}")
                left, right = st.columns(2)
                update = left.form_submit_button("수정", key=f"category_update_{name}")
                delete = right.form_submit_button("삭제", key=f"category_delete_{name}")
            try:
                if update:
                    store.rename_category(name, edited)
                    for archived in st.session_state.get("notice_archive", []):
                        if archived["notice"]["category"] == name:
                            archived["notice"]["category"] = edited.strip()
                    descriptions.pop(name, None)
                    descriptions[edited.strip()] = detail.strip()
                    done("카테고리를 수정했습니다.")
                if delete:
                    store.delete_category(name)
                    descriptions.pop(name, None)
                    done("비어 있는 카테고리를 삭제했습니다.")
            except ValueError as exc:
                st.error(str(exc))


def _upload_panel(store, prefix, kind, pdf=False):
    category = st.selectbox("업로드 카테고리 (선택사항)", ["선택 안 함", *store.categories()], key=f"{prefix}_category")
    st.file_uploader("상세 PDF" if pdf else "Excel 파일 선택", type=["pdf"] if pdf else ["xlsx", "xls", "csv"],
                     accept_multiple_files=True, key=f"{prefix}_files")
    st.caption("실제 파일은 읽지 않습니다. 샘플 자료로 등록을 체험하세요.")
    if st.button("샘플 불러오기", key=f"{prefix}_load_sample"):
        st.session_state[f"{prefix}_preview"] = True
    if not st.session_state.get(f"{prefix}_preview"):
        return
    names = store.categories()
    if not names:
        st.info("카테고리를 먼저 생성해 주세요.")
        return
    selected_category = category if category in names else names[0]
    status = {"과거데이터": "완료", "개찰결과": "마감"}.get(kind, "접수중")
    sample = [{"code": f"DEMO-{prefix.upper()}-{index:03d}", "title": f"가상 {kind} 체험 공고 {index}",
               "agency": "가상 자료체험센터", "category": selected_category, "region": "가상 동부",
               "base_amount": amount, "deadline": date.today().isoformat(), "status": status, "memo": "화면 체험용 가상 자료"}
              for index, amount in enumerate((24000000, 37000000), 1)]
    filename = f"가상_{prefix}.{'pdf' if pdf else 'xlsx'}"
    _table([{"번호": 1, "파일명": filename, "파일 유형": "PDF" if pdf else "Excel", "자료 구분": "데모 샘플"}])
    selectable = [filename] if pdf else [row["code"] for row in sample]
    selected = st.multiselect("연결할 PDF 선택" if pdf else "등록할 공고 선택", selectable,
                             default=selectable, key=f"{prefix}_selection")
    with st.expander(f"{filename} 미리보기", expanded=True):
        _table(_notice_display(sample[:1] if pdf else sample))
    target = None
    if pdf:
        st.markdown("**PDF 수기 연결**")
        options = store.notices()
        if not options:
            st.info("연결할 공고를 먼저 등록해 주세요.")
            return
        target = st.selectbox("연결할 공고", [row["id"] for row in options],
                              format_func=lambda item: next(f"{row['code']} | {row['title']}" for row in options if row['id'] == item),
                              key=f"{prefix}_target")
        st.checkbox("PDF 샘플과 선택 공고를 확인했습니다.", key=f"{prefix}_link_confirm")
    label = "선택한 PDF 연결 — 선택 등록" if pdf else "선택한 공고 등록 — 선택 등록"
    if st.button(label, key=f"{prefix}_register", disabled=not selected or (pdf and not st.session_state.get(f"{prefix}_link_confirm"))):
        inserted = 0
        skipped = 0
        if pdf:
            links = st.session_state.setdefault("pdf_links", {}).setdefault(target, [])
            for selected_file in selected:
                if selected_file not in links:
                    links.append(selected_file)
                    inserted += 1
                else:
                    skipped += 1
        else:
            for row in sample:
                if row["code"] not in selected:
                    continue
                if any(saved["code"] == row["code"] for saved in store.notices()):
                    skipped += 1
                else:
                    archived = next((index for index, bundle in enumerate(st.session_state.get("notice_archive", []))
                                     if bundle["notice"]["code"] == row["code"]), None)
                    if archived is not None:
                        _restore_notice(store, archived, selected_category)
                    else:
                        notice_id = store.save_notice(row)
                        if kind != "관심공고":
                            store.save_result({"notice_id": notice_id, "outcome": "샘플 낙찰", "amount": 21500000, "note": "가상 개찰결과"})
                    inserted += 1
        result = {"업로드 유형": kind, "파일명": filename, "카테고리": selected_category,
                  "전체 행 수": len(selected), "신규 등록": inserted, "중복 스킵": skipped, "오류": 0,
                  "완료 일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        st.session_state.setdefault("upload_history", []).insert(0, result)
        st.success(f"가상 자료 {inserted}건 등록, 중복 {skipped}건 건너뜀")
        _table([result])


def uploads(store):
    historical, current, result = st.tabs(["과거데이터", "관심공고", "개찰결과"])
    with historical:
        st.caption("낙찰정보 엑셀을 과거 분석 데이터로 등록합니다.")
        _upload_panel(store, "historical", "과거데이터")
    with current:
        excel, pdf = st.tabs(["입찰서류함 엑셀", "상세 PDF"])
        with excel:
            _upload_panel(store, "current_excel", "관심공고")
        with pdf:
            _upload_panel(store, "current_pdf", "관심공고", pdf=True)
    with result:
        excel, pdf = st.tabs(["낙찰정보 엑셀", "결과 상세 PDF"])
        with excel:
            _upload_panel(store, "result_excel", "개찰결과")
        with pdf:
            _upload_panel(store, "result_pdf", "개찰결과", pdf=True)
    with st.expander("최근 업로드 이력"):
        _table(st.session_state.get("upload_history", []))


def _detail(store, row, tabs=False):
    saved = st.session_state.get("demo_recommendations", {}).get(row["id"])
    frames = [
        [{**_notice_display([row])[0], "메모": row["memo"]}],
        [{"파일명": name} for name in st.session_state.get("pdf_links", {}).get(row["id"], [])],
        [{"추천 유형": saved.get("scenario", "표준"), "추천 투찰금액": saved["amount"]}] if saved else [],
    ]
    labels = ["공고 정보", "연결 PDF", "추천 결과"]
    if tabs:
        for target, frame in zip(st.tabs(labels), frames):
            with target:
                _table(frame)
    else:
        _table(frames[0])
        if frames[1]:
            st.markdown("**연결 PDF**")
            _table(frames[1])
        if frames[2]:
            st.markdown("**추천 결과**")
            _table(frames[2])


def _archive_notice(store, row):
    target = row["id"]
    bundle = {"notice": row, "submissions": [item for item in store.submissions() if item["notice_id"] == target],
              "results": [item for item in store.results() if item["notice_id"] == target],
              "pdfs": st.session_state.get("pdf_links", {}).pop(target, [])}
    bundle["session_metadata"] = {
        key: st.session_state[key].pop(target)
        for key in ("demo_recommendations", "demo_primary", "demo_result_context")
        if target in st.session_state.get(key, {})
    }
    st.session_state.setdefault("notice_archive", []).append(bundle)
    store.delete_notice(target)
    if (st.session_state.get("recommendation_display") or {}).get("notice_id") == target:
        st.session_state.pop("recommendation_display", None)
    if "daily_results" in st.session_state:
        st.session_state["daily_results"] = [item for item in st.session_state["daily_results"] if item["notice_id"] != target]
    if "daily_result_selection" in st.session_state:
        st.session_state["daily_result_selection"] = tuple(item for item in st.session_state["daily_result_selection"] if item != target)
    st.session_state.pop("daily_confirmed", None)
    st.session_state["daily_query_revision"] = st.session_state.get("daily_query_revision", 0) + 1
    st.session_state["management_revision"] = st.session_state.get("management_revision", 0) + 1
    prefixes = (f"recommendation_{target}_", f"result_{target}_", f"edit_{target}_", "daily_editor_", "management_editor_")
    prefixes += tuple(f"submission_{item['id']}_" for item in bundle["submissions"])
    for key in list(st.session_state):
        if key.startswith(prefixes) or key in (f"result_confirm_{target}", f"delete_confirm_{target}", f"archive_code_{target}", f"notice_move_{target}"):
            st.session_state.pop(key, None)
    st.session_state["flash"] = "공고를 삭제했습니다."


def _restore_notice(store, index, category):
    archives = st.session_state["notice_archive"]
    bundle = archives[index]
    try:
        restored = store.save_notice({**bundle["notice"], "category": category})
        for item in bundle["submissions"]:
            store.save_submission({**item, "notice_id": restored})
        for item in bundle["results"]:
            store.save_result({**item, "notice_id": restored})
        st.session_state.setdefault("pdf_links", {})[restored] = bundle["pdfs"]
        for key, value in bundle.get("session_metadata", {}).items():
            if key == "demo_recommendations":
                value = {**value, "notice_id": restored}
            st.session_state.setdefault(key, {})[restored] = value
        archives.pop(index)
        st.session_state["flash"] = "가상 공고와 연결 기록을 복원했습니다."
    except ValueError as exc:
        st.session_state["archive_error"] = str(exc)


def integrated(store):
    left, right = st.columns([3, 1])
    search = left.text_input("공고번호 또는 공고명", key="notice_search")
    category = right.selectbox("카테고리", ["전체", *store.categories()], key="notice_category")
    rows = [row for row in store.notices(category=category)
            if not search or search.casefold() in f"{row['code']} {row['title']}".casefold()]
    _table(_notice_display(rows))
    if rows:
        target = st.selectbox("상세 확인 공고", [row["id"] for row in rows],
                              format_func=lambda item: next(f"{row['code']} | {row['title']}" for row in rows if row['id'] == item),
                              key="notice_detail")
        with st.expander("선택 공고 상세", expanded=True):
            _detail(store, store.get_notice(target))


def _clear_delete_confirmation():
    for key in ("daily_notices_pending", "daily_notices_reason", "daily_notices_other_reason", "daily_notices_ack"):
        st.session_state.pop(key, None)


def _reset_daily_notices():
    _clear_delete_confirmation()
    st.session_state.pop("daily_notices_query", None)
    st.session_state.pop("daily_notices_select_all", None)
    st.session_state["daily_notices_revision"] = st.session_state.get("daily_notices_revision", 0) + 1


def _open_daily_recommendations(opening):
    st.session_state["daily_requested_date"] = opening
    open_tab("daily_recommend")


def _delete_daily_notices(store, targets, reason):
    for target in targets:
        row = store.get_notice(target)
        if row:
            _archive_notice(store, row)
            st.session_state["notice_archive"][-1]["reason"] = reason
    _clear_delete_confirmation()
    st.session_state.pop("daily_notices_select_all", None)
    st.session_state["daily_notices_revision"] = st.session_state.get("daily_notices_revision", 0) + 1
    st.session_state["flash"] = f"공고 {len(targets)}건을 삭제했습니다."


def daily_notices(store):
    all_rows = store.notices()
    default_date = date.fromisoformat(all_rows[0]["deadline"]) if all_rows else date.today()
    left, right = st.columns([2, 1], vertical_alignment="bottom")
    opening = left.date_input("개찰일", default_date, key="daily_notices_date", on_change=_reset_daily_notices)
    if right.button("공고 조회", key="daily_notices_search", type="primary"):
        _clear_delete_confirmation()
        st.session_state["daily_notices_query"] = opening.isoformat()
        st.session_state["daily_notices_revision"] = st.session_state.get("daily_notices_revision", 0) + 1
    requested = st.session_state.get("daily_notices_query")
    if not requested:
        st.info("개찰일을 선택한 뒤 공고 조회를 누르세요.")
        return
    rows = [row for row in all_rows if row["deadline"] == requested]
    st.caption(f"총 {len(rows):,}건")
    if not rows:
        st.info("조회 조건에 맞는 공고가 없습니다.")
        return
    saved = st.session_state.get("demo_recommendations", {})
    unsaved = {row["notice_id"] for row in st.session_state.get("daily_results", [])}
    current = st.session_state.get("recommendation_display") or {}
    if current.get("notice_id"):
        unsaved.add(current["notice_id"])
    submissions = {row["notice_id"] for row in store.submissions()}
    select_all = st.checkbox("전체 선택", key="daily_notices_select_all")
    display = [{"선택": select_all, "공고번호": row["code"], "공고명": row["title"], "개찰일": row["deadline"],
                "발주기관": row["agency"], "업종": row["category"], "기초금액": row["base_amount"], "업무 상태": row["status"],
                "계산 이력": "저장된 계산 있음" if row["id"] in saved else "미저장 계산 있음" if row["id"] in unsaved else "없음",
                "투찰기록": "있음" if row["id"] in submissions else "없음"} for row in rows]
    edited = st.data_editor(display, hide_index=True, width="stretch", disabled=[key for key in display[0] if key != "선택"],
                            key=f"daily_notices_editor_{st.session_state.get('daily_notices_revision', 0)}_{select_all}")
    targets = tuple(row["id"] for row, edit in zip(rows, edited) if edit["선택"])
    if st.session_state.get("daily_notices_pending") != targets:
        _clear_delete_confirmation()
    left, right = st.columns(2)
    if left.button("선택 공고 삭제", key="daily_notices_delete", disabled=not targets):
        st.session_state["daily_notices_pending"] = targets
    right.button("이 날짜 추천계산으로 이동", key="daily_notices_recommend",
                 on_click=_open_daily_recommendations, args=(opening,))
    if not targets or st.session_state.get("daily_notices_pending") != targets:
        return
    selected = [row for row in rows if row["id"] in targets]
    calculated = any(target in saved or target in unsaved for target in targets)
    with st.container(border=True):
        st.markdown("**공고 삭제 확인**")
        _table(_notice_display(selected))
        st.caption("삭제하면 관심공고와 추천계산 목록에서 제외됩니다. 저장된 추천·투찰·결과 이력은 보관됩니다.")
        if calculated:
            st.warning("이미 계산된 공고가 포함되어 있습니다. 삭제할 공고를 확인해 주세요.")
        if any(target in unsaved and target not in saved for target in targets):
            st.caption("저장하지 않은 계산 결과는 삭제됩니다.")
        reason = st.selectbox("삭제 사유", ["사유 선택", "나라장터에서 취소·삭제됨", "중복 등록", "참여하지 않음", "기타"],
                              key="daily_notices_reason")
        if reason == "기타":
            reason = st.text_input("기타 사유", key="daily_notices_other_reason").strip()
        acknowledged = st.checkbox("계산 이력이 있는 공고의 삭제에 동의합니다.", key="daily_notices_ack") if calculated else True
        left, right = st.columns(2)
        left.button(f"{len(targets)}건 삭제 확정", key="daily_notices_confirm",
                    disabled=not acknowledged or not reason or reason == "사유 선택",
                    on_click=_delete_daily_notices, args=(store, targets, reason))
        right.button("취소", key="daily_notices_cancel", on_click=_clear_delete_confirmation)


def query(store):
    with st.form("bid_data_query_form"):
        left, right = st.columns(2)
        title = left.text_input("공고명", key="query_title")
        code = right.text_input("공고번호", key="query_bid_no")
        left, middle, right = st.columns(3)
        category = left.selectbox("카테고리", ["전체", *store.categories()], key="query_category")
        date_from = middle.date_input("개찰일 시작", value=None, key="query_date_from")
        date_to = right.date_input("개찰일 종료", value=None, key="query_date_to")
        submitted = st.form_submit_button("조회", key="query_submit", type="primary")
    if submitted or "query_filters" not in st.session_state:
        if date_from and date_to and date_from > date_to:
            st.error("개찰일 시작일은 종료일보다 늦을 수 없습니다.")
        else:
            st.session_state["query_filters"] = (title, code, category, date_from, date_to)
    title, code, category, date_from, date_to = st.session_state.get("query_filters", ("", "", "전체", None, None))
    rows = [row for row in store.notices(category=category)
            if (not title or title.casefold() in row["title"].casefold())
            and (not code or code.casefold() in row["code"].casefold())
            and (not date_from or row["deadline"] >= date_from.isoformat())
            and (not date_to or row["deadline"] <= date_to.isoformat())]
    st.metric("현재 조회 조건 기준", f"총 {len(rows):,}건")
    actual = {row["notice_id"]: row for row in store.results()}
    saved = st.session_state.get("demo_recommendations", {})
    display = [{"번호(No)": number, **_notice_display([row])[0],
                "1순위투찰금액": actual.get(row["id"], {}).get("amount"),
                "추천 투찰금액": saved.get(row["id"], {}).get("amount")}
               for number, row in enumerate(rows, 1)]
    _table(display)
    if rows:
        st.download_button("조회 결과 CSV 다운로드", csv_bytes(display),
                           file_name="가상_입찰낙찰데이터.csv", mime="text/csv")
        target = st.selectbox("상세 보기 공고", [row["id"] for row in rows],
                              format_func=lambda item: next(f"{row['code']} | {row['title']}" for row in rows if row['id'] == item), key="query_detail")
        with st.expander("선택 공고 상세"):
            _detail(store, store.get_notice(target), tabs=True)
