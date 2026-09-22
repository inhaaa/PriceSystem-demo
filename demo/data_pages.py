"""공개 화면 구조를 재현하는 가상 자료 관리 화면. 운영 모듈과 연결하지 않는다."""
from datetime import date, datetime

import streamlit as st

from demo.store import NOTICE_STATUSES
from demo.ui import csv_bytes, done, table


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
    st.checkbox("업종·지역 기준 자동 카테고리 분류", value=True, key=f"{prefix}_classify")
    if not pdf:
        st.checkbox("선택한 카테고리를 대표 카테고리로 지정", disabled=category == "선택 안 함", key=f"{prefix}_primary")
    st.file_uploader("상세 PDF" if pdf else "Excel 파일 선택", type=["pdf"] if pdf else ["xlsx", "xls", "csv"],
                     accept_multiple_files=True, key=f"{prefix}_files")
    st.caption("데모 샘플 판독: 실제 파일 내용은 읽지 않습니다. 샘플을 불러와 미리보기와 등록 흐름을 체험하세요.")
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
    selected = st.multiselect("연결할 PDF 선택" if pdf else "업로드할 파일 선택", selectable,
                             default=selectable, key=f"{prefix}_selection")
    with st.expander(f"{filename} 미리보기/컬럼 매핑", expanded=True):
        _table(_notice_display(sample[:1] if pdf else sample))
        if not pdf:
            _table([{"엑셀 컬럼": label, "표준 컬럼": field}
                    for field, label in (("code", "공고번호"), ("title", "공고명"), ("agency", "발주기관"), ("base_amount", "기초금액"))])
            st.markdown("**주요 분석 컬럼 보유 현황**")
            _table([{"표준 컬럼": "공고번호", "의미": "공고 식별", "매핑된 원본 컬럼": "공고번호", "상태": "가상 샘플 확인"}])
            st.markdown("**카테고리 분류 미리보기**")
            _table([{"공고번호": row["code"], "카테고리": selected_category, "분류 근거": "데모에서 선택한 가상 분류"} for row in sample])
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
    label = "PDF 추출 및 공고 연결 — 선택 등록" if pdf else "선택한 Excel/CSV 파일 등록 — 선택 등록"
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
                    notice_id = store.save_notice(row)
                    if kind != "관심공고":
                        store.save_result({"notice_id": notice_id, "outcome": "샘플 낙찰", "amount": 21500000, "note": "판독 데모용 고정 결과"})
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


def _notice_form(store, row=None):
    prefix = f"edit_{row['id']}" if row else "new"
    with st.form(f"{prefix}_notice"):
        cols = st.columns(3)
        fields = {"code": cols[0].text_input("공고번호", row["code"] if row else "", key=f"{prefix}_code"),
                  "title": cols[1].text_input("공고명", row["title"] if row else "", key=f"{prefix}_title"),
                  "agency": cols[2].text_input("발주기관", row["agency"] if row else "", key=f"{prefix}_agency")}
        cols = st.columns(3)
        fields["region"] = cols[0].text_input("지역", row["region"] if row else "", key=f"{prefix}_region")
        options = store.categories()
        fields["category"] = cols[1].selectbox("카테고리", options, index=options.index(row["category"]) if row else 0, key=f"{prefix}_category")
        fields["base_amount"] = cols[2].number_input("기초금액", min_value=0, max_value=10**12,
                                                    value=row["base_amount"] if row else 24000000, key=f"{prefix}_amount")
        cols = st.columns(3)
        fields["deadline"] = cols[0].date_input("개찰일", date.fromisoformat(row["deadline"]) if row else date.today(), key=f"{prefix}_date").isoformat()
        fields["status"] = cols[1].selectbox("공고 상태", NOTICE_STATUSES, index=NOTICE_STATUSES.index(row["status"]) if row else 0, key=f"{prefix}_status")
        fields["memo"] = cols[2].text_input("메모", row["memo"] if row else "", key=f"{prefix}_memo")
        clicked = st.form_submit_button("공고 수정" if row else "가상 공고 등록", key="update_notice" if row else "create_notice")
    if clicked:
        try:
            store.save_notice(fields, row["id"] if row else None)
            done("가상 공고를 저장했습니다.")
        except ValueError as exc:
            st.error(str(exc))


def _detail(store, row, tabs=False):
    frames = [
        [{"카테고리": row["category"], "대표 여부": "Y"}],
        [{"자료 유형": "가상 체험 자료", "공고번호": row["code"]}],
        [{"파일명": name, "구분": "데모 샘플 연결"} for name in st.session_state.get("pdf_links", {}).get(row["id"], [])],
        [{"공고번호": row["code"], "추천 유형": "표준", "추천 투찰금액": 22100000, "표시 구분": "계산 없는 고정 가상 값"}],
    ]
    labels = ["카테고리", "업로드 출처", "연결 PDF", "추천 결과"]
    if tabs:
        for target, frame in zip(st.tabs(labels), frames):
            with target:
                _table(frame)
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("**데이터 출처**")
            _table(frames[1])
        with right:
            st.markdown("**상세 PDF**")
            _table(frames[2])
        st.markdown("**연결 카테고리**")
        _table(frames[0])


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
    st.session_state["flash"] = "가상 공고를 삭제 보관함으로 옮겼습니다."


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
    left, middle, right = st.columns(3)
    search = left.text_input("공고번호 또는 공고명", key="notice_search")
    category = middle.selectbox("카테고리", ["전체", *store.categories()], key="notice_category")
    status = right.selectbox("결과 상태", ["전체", "INTEREST", "RESULT_REGISTERED", "HISTORICAL"], key="notice_status")
    results = {row["notice_id"] for row in store.results()}
    rows = [row for row in store.notices(category=category)
            if (not search or search.casefold() in f"{row['code']} {row['title']}".casefold())
            and (status == "전체" or (status == "INTEREST" and row["id"] not in results)
                 or (status == "RESULT_REGISTERED" and row["id"] in results)
                 or (status == "HISTORICAL" and row["status"] == "완료"))]
    _table(_notice_display(rows))
    if store.categories():
        with st.expander("가상 공고 등록"):
            _notice_form(store)
    else:
        st.info("공고를 등록하려면 카테고리를 먼저 생성하세요.")
    if rows:
        target = st.selectbox("상세 확인 공고", [row["id"] for row in rows],
                              format_func=lambda item: next(f"{row['code']} | {row['title']}" for row in rows if row['id'] == item),
                              key="notice_detail")
        row = store.get_notice(target)
        st.json(_notice_display([row])[0], expanded=False)
        _detail(store, row)
        with st.expander("가상 공고 수정"):
            _notice_form(store, row)
        names = store.categories()
        new_category = st.selectbox("카테고리 수동 변경", names, index=names.index(row["category"]), key=f"notice_move_{target}")
        if st.button("카테고리 변경", key="notice_move"):
            store.save_notice({**row, "category": new_category}, target)
            done("대표 카테고리를 변경했습니다.")
        with st.expander("안전 삭제: 백업 후 논리삭제"):
            st.caption("가상 자료는 현재 체험 세션의 삭제 보관함에 보관됩니다.")
            st.text_input("공고번호 확인", value=row["code"], disabled=True, key=f"archive_code_{target}")
            acknowledged = st.checkbox("가상 공고와 연결 기록을 삭제 보관함에 보관합니다.", key=f"delete_confirm_{target}")
            st.button("백업 후 논리삭제", key="delete_notice", disabled=not acknowledged,
                      on_click=_archive_notice, args=(store, row))
    with st.expander("삭제 보관함 / 복원"):
        archives = st.session_state.setdefault("notice_archive", [])
        _table(_notice_display([item["notice"] for item in archives]))
        if archives:
            index = st.selectbox("복원할 공고", range(len(archives)), format_func=lambda i: archives[i]["notice"]["code"], key="archive_selection")
            restore_category = archives[index]["notice"]["category"]
            names = store.categories()
            if restore_category not in names:
                st.warning("보관 당시 카테고리가 삭제되었습니다. 복원할 카테고리를 선택해 주세요.")
                restore_category = st.selectbox("복원 카테고리", names, key="restore_category") if names else None
                if not names:
                    st.info("카테고리 관리에서 카테고리를 먼저 생성해 주세요.")
            acknowledged = st.checkbox("보관된 가상 공고를 다시 활성화합니다.", key="restore_acknowledged")
            st.button("공고 복원", key="restore_notice", disabled=not acknowledged or not restore_category,
                      on_click=_restore_notice, args=(store, index, restore_category))
        if st.session_state.get("archive_error"):
            st.error(st.session_state.pop("archive_error"))
    st.divider()
    st.markdown("**값 및 카테고리 충돌 목록**")
    st.info("현재 체험 세션에 등록된 충돌이 없습니다.")


def query(store):
    with st.form("bid_data_query_form"):
        cols = st.columns(4)
        filters = {field: cols[index].text_input(label, key=f"query_{field}")
                   for index, (field, label) in enumerate((("title", "공고명"), ("bid_no", "공고번호"), ("agency", "발주기관"), ("region", "지역")))}
        cols = st.columns(4)
        license_type = cols[0].text_input("업종", key="query_license")
        category = cols[1].selectbox("카테고리", ["전체", *store.categories()], key="query_category")
        date_from = cols[2].date_input("개찰일 시작", value=None, key="query_date_from")
        date_to = cols[3].date_input("개찰일 종료", value=None, key="query_date_to")
        cols = st.columns([2, 2, 1])
        include = cols[0].checkbox("추천 결과 포함", key="query_recommendations")
        limit = cols[1].number_input("최대 조회 건수", 1, 10000, 1000, step=100, key="query_limit")
        submitted = cols[2].form_submit_button("조회", key="query_submit")
    if submitted or "query_filters" not in st.session_state:
        if date_from and date_to and date_from > date_to:
            st.error("개찰일 시작일은 종료일보다 늦을 수 없습니다.")
        else:
            st.session_state["query_filters"] = (filters, license_type, category, date_from, date_to, include, limit)
    filters, license_type, category, date_from, date_to, include, limit = st.session_state.get("query_filters", ({}, "", "전체", None, None, False, 1000))
    matches = [row for row in store.notices(category=category)
               if all(not text or text.casefold() in str(row["code" if field == "bid_no" else field]).casefold() for field, text in filters.items())
               and (not license_type or license_type.casefold() in row["category"].casefold())
               and (not date_from or row["deadline"] >= date_from.isoformat())
               and (not date_to or row["deadline"] <= date_to.isoformat())]
    st.metric("현재 조회 조건 기준", f"총 {len(matches):,}건")
    rows = matches[:int(limit)]
    actual = {row["notice_id"]: row for row in store.results()}
    display = []
    for number, row in enumerate(rows, 1):
        result = actual.get(row["id"], {})
        item = {"번호(No)": number, "공고번호": row["code"], "공고명": row["title"], "발주기관": row["agency"], "지역": row["region"],
                "기초금액": row["base_amount"], "예정가격": "가상 24,000,000", "1순위투찰금액": result.get("amount"),
                "1순위기초대비": "샘플", "1순위업체": "가상 체험기업" if result else "", "예가/기초(100%)": "샘플",
                "예가/기초(0%)": "샘플", "개찰일": row["deadline"], "업종": row["category"], "업체수": 12,
                "대표 카테고리": row["category"], "연결 카테고리 목록": row["category"], "자동분류 여부": "N", "분류 근거": "가상 분류"}
        if include:
            item.update({"추천 여부": "Y", "추천일시": "데모 고정 값", "추천 투찰금액": 22100000,
                         "예상 예가율": "샘플", "차이금액": "샘플", "오차율": "샘플", "가장 근접한 추천순위": "샘플"})
        display.append(item)
    _table(display)
    if rows:
        st.caption("가격·비율·추천 항목은 계산하지 않는 가상 표시값입니다.")
        st.download_button("조회 결과 Excel 호환 CSV 다운로드", csv_bytes(display),
                           file_name="가상_입찰낙찰데이터.csv", mime="text/csv")
        target = st.selectbox("상세 보기 공고", [row["id"] for row in rows],
                              format_func=lambda item: next(f"{row['code']} | {row['title']}" for row in rows if row['id'] == item), key="query_detail")
        with st.expander("선택 공고 상세"):
            row = store.get_notice(target)
            st.json(_notice_display([row])[0], expanded=False)
            _detail(store, row, tabs=True)
