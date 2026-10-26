"""오늘 포함 7일을 우선 표시하는 개찰 일정 표."""

from datetime import date, datetime, timedelta, timezone
from html import escape

import streamlit as st


def query_periods(period, today):
    """선택 기간과 주간을 포함하는 기존 월/연 조회 인자만 중복 없이 반환한다."""
    queries = [(int(period[:4]), int(period[5:]) if len(period) == 7 else None)]
    for opening in (today, today + timedelta(days=6)):
        query = (opening.year, opening.month)
        if not opening.isoformat().startswith(period) and query not in queries:
            queries.append(query)
    return queries


def split_schedule_groups(groups, period, today):
    start, end = today.isoformat(), (today + timedelta(days=6)).isoformat()
    ordered = sorted(groups, key=lambda group: group["date"])
    weekly = [group for group in ordered if start <= group["date"] <= end]
    remaining = [group for group in ordered
                 if group["date"].startswith(period) and not start <= group["date"] <= end]
    return weekly, remaining


def _toggle_scope():
    st.session_state["home_schedule_all_visible"] = not st.session_state.get("home_schedule_all_visible", False)


def reset_scope():
    st.session_state["home_schedule_all_visible"] = False


def _today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def _schedule_day(group, saved, open_notices, open_calculation):
    opening = date.fromisoformat(group["date"])
    weekday = ("월", "화", "수", "목", "금", "토", "일")[opening.weekday()]
    with st.container(key=f'home_schedule_day_{group["date"]}'):
        with st.container(key=f'home_schedule_header_{group["date"]}'):
            label, actions = st.columns([3, 2], vertical_alignment="center")
            label.markdown('<div class="schedule-day-heading" role="heading" aria-level="3">'
                           f'<time datetime="{opening.isoformat()}"><strong>{opening.month}월 {opening.day}일</strong>'
                           f'<span>{weekday}요일</span></time>'
                           f'<span class="schedule-count">공고 {len(group["notices"]):,}건</span></div>',
                           unsafe_allow_html=True)
            with actions, st.container(key=f'home_schedule_actions_{group["date"]}', horizontal=True,
                                       horizontal_alignment="right", gap="small"):
                st.button("공고 조회", key=f'home_day_notices_{group["date"]}', type="tertiary",
                          disabled=open_notices is None, on_click=open_notices, args=(opening,))
                st.button("계산", key=f'home_day_calculate_{group["date"]}', type="primary",
                          icon=":material/arrow_forward:", icon_position="right", disabled=open_calculation is None,
                          on_click=open_calculation, args=(opening,))
        rows = []
        for row in group["notices"]:
            calculated = row["id"] in saved
            amount = f'{row["base_amount"]:,}<small>원</small>' if row["base_amount"] is not None else "금액 미확인"
            rows.append('<tr class="schedule-notice"><td class="schedule-notice__body">'
                        f'<h3>{escape(row["title"])}</h3><span>{escape(row["code"])}</span></td>'
                        f'<td class="schedule-notice__amount">{amount}</td><td class="schedule-notice__status">'
                        f'<span class="schedule-status{" schedule-status--saved" if calculated else ""}">'
                        f'{"계산 저장됨" if calculated else "미확인"}</span></td></tr>')
        st.markdown(f'<table class="schedule-notices" aria-label="{opening.month}월 {opening.day}일 개찰 공고">'
                    '<thead><tr><th scope="col">공고</th><th scope="col">기초금액</th>'
                    '<th scope="col">계산상태</th></tr></thead><tbody>'
                    + ''.join(rows) + '</tbody></table>', unsafe_allow_html=True)


def render_schedule(groups, saved, *, period, open_notices, open_calculation, today=None):
    """주간은 항상 표시하고, 선택 기간의 나머지 일정만 추가로 연다."""
    for key in ("schedule_month", "schedule_show_all", "schedule_expanded_dates",
                "schedule_preferences_loaded", "schedule_browser_preferences"):
        st.session_state.pop(key, None)
    st.session_state.setdefault("home_schedule_all_visible", False)
    st.markdown('<h2 class="workbench-section-title">개찰 일정</h2>'
                '<p class="workbench-section-note">등록 공고 기준</p>', unsafe_allow_html=True)
    today = today or _today()
    weekly, remaining = split_schedule_groups(groups, period, today)
    st.caption(f'오늘부터 7일 · {today:%m.%d}–{today + timedelta(days=6):%m.%d}'
               f' · 공고 {sum(len(group["notices"]) for group in weekly):,}건')
    if not weekly:
        st.info("오늘부터 7일 이내 개찰 일정이 없습니다.")
    for group in weekly:
        _schedule_day(group, saved, open_notices, open_calculation)
    label = f"{period}년 전체" if len(period) == 4 else f"{period[:4]}년 {int(period[5:])}월"
    show_all = st.session_state["home_schedule_all_visible"]
    st.button(f'{label} 나머지 일정 접기' if show_all else f'{label} 전체 일정 열기',
              key="schedule_scope_toggle", width="stretch", disabled=not remaining,
              icon=":material/expand_less:" if show_all else ":material/calendar_month:", on_click=_toggle_scope)
    if show_all and remaining:
        st.markdown(f'<h3 class="schedule-section-heading">{label} 나머지 일정</h3>', unsafe_allow_html=True)
        st.caption("상단의 주간 일정과 합쳐 선택한 기간의 전체 일정입니다.")
        for group in remaining:
            _schedule_day(group, saved, open_notices, open_calculation)
    count = sum(len(group["notices"]) for group in groups if group["date"].startswith(period))
    st.caption(f'{label} 공고 {count:,}건')
