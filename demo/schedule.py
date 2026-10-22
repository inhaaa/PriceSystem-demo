"""공개 데모 홈의 읽기 전용 개찰 일정과 브라우저 표시 설정."""
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

import streamlit as st


STORAGE_KEY = 'pricesystem.demo.schedule.v1'
COMPONENT_KEY = 'schedule_browser_preferences'


def normalize_preferences(value, groups):
    result = {'version': 1, 'showAll': False, 'expandedDates': [], 'month': None}
    if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1:
        return result
    dates = {group['date'] for group in groups}
    result['showAll'] = value.get('showAll') is True
    expanded = value.get('expandedDates')
    if isinstance(expanded, list):
        result['expandedDates'] = sorted({day for day in expanded if isinstance(day, str) and day in dates})
    month = value.get('month')
    if isinstance(month, str) and month in {day[:7] for day in dates}:
        result['month'] = month
    return result


def _mark_ready():
    st.session_state['schedule_preferences_loaded'] = True


def restore_preferences(value, groups):
    if st.session_state.get('schedule_preferences_loaded'):
        return
    saved = normalize_preferences(value, groups)
    st.session_state['schedule_show_all'] = saved['showAll']
    st.session_state['schedule_expanded_dates'] = set(saved['expandedDates'])
    if saved['month']:
        st.session_state['schedule_month'] = saved['month']
    _mark_ready()


def render_preferences(groups):
    def on_restored():
        envelope = st.session_state.get(COMPONENT_KEY, {}).get('restored')
        restore_preferences(envelope.get('preferences') if isinstance(envelope, dict) else None, groups)

    preferences = normalize_preferences({
        'version': 1, 'showAll': st.session_state.get('schedule_show_all', False),
        'expandedDates': sorted(st.session_state.get('schedule_expanded_dates', set())),
        'month': st.session_state.get('schedule_month'),
    }, groups)
    bridge = st.components.v2.component('demo_schedule_preferences', html='<span hidden aria-hidden="true"></span>',
        js=(Path(__file__).resolve().parents[1] / 'static/schedule-preferences.js').read_text(encoding='utf-8'))
    bridge(key=COMPONENT_KEY, height=0, default={'restored': None}, on_restored_change=on_restored,
           data={'storageKey': STORAGE_KEY, 'ready': st.session_state.get('schedule_preferences_loaded', False),
                 'preferences': preferences})


def visible_groups(groups, month, today, show_all):
    end = today + timedelta(days=6)
    return sorted((group for group in groups if group['date'].startswith(month)
        and (show_all or today.isoformat() <= group['date'] <= end.isoformat())), key=lambda group: group['date'])


def set_expanded(days, expanded):
    _mark_ready()
    selected = set(st.session_state.get('schedule_expanded_dates', set()))
    if expanded:
        selected.update(days)
    else:
        selected.difference_update(days)
    st.session_state['schedule_expanded_dates'] = selected


def _toggle_day(day):
    set_expanded((day,), day not in st.session_state.get('schedule_expanded_dates', set()))


def _toggle_scope():
    _mark_ready()
    st.session_state['schedule_show_all'] = not st.session_state.get('schedule_show_all', False)


def _today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def _bulk_actions(days):
    expanded = set(days).intersection(st.session_state.get('schedule_expanded_dates', set()))
    with st.container(key='schedule_bulk_actions', horizontal=True, horizontal_alignment='right', gap='small'):
        st.button('모두 펼치기', key='schedule_expand_all', icon=':material/unfold_more:',
                  disabled=len(expanded) == len(days), on_click=set_expanded, args=(days, True))
        st.button('모두 접기', key='schedule_collapse_all', icon=':material/unfold_less:',
                  disabled=not expanded, on_click=set_expanded, args=(days, False))


def _schedule_day(group, saved, open_notices, open_calculation):
    opening = date.fromisoformat(group['date'])
    weekday = ('월', '화', '수', '목', '금', '토', '일')[opening.weekday()]
    expanded = group['date'] in st.session_state.get('schedule_expanded_dates', set())
    with st.container(key=f'home_schedule_day_{group["date"]}'):
        label, actions = st.columns([3, 2], vertical_alignment='center')
        label.button(f'{opening.month}월 {opening.day}일 ({weekday}) · 공고 {len(group["notices"])}건',
                     key=f'home_day_toggle_{group["date"]}', type='tertiary', width='stretch',
                     icon=':material/expand_more:' if expanded else ':material/chevron_right:',
                     help='공고 목록 접기' if expanded else '공고 목록 펼치기', on_click=_toggle_day, args=(group['date'],))
        with actions, st.container(key=f'home_schedule_actions_{group["date"]}', horizontal=True,
                                   horizontal_alignment='right', gap='small'):
            st.button('공고 조회', key=f'home_day_notices_{group["date"]}', type='tertiary',
                      on_click=open_notices, args=(opening,))
            st.button('계산', key=f'home_day_calculate_{group["date"]}', type='primary',
                      icon=':material/arrow_forward:', icon_position='right', on_click=open_calculation, args=(opening,))
        if expanded:
            for row in group['notices']:
                calculated = row['id'] in saved
                st.markdown('<article class="schedule-notice"><div class="schedule-notice__body">'
                    f'<h3>{escape(row["title"])}</h3><span>{escape(row["code"])}</span></div>'
                    f'<div class="schedule-notice__amount">{row["base_amount"]:,}<small>원</small></div>'
                    f'<span class="schedule-status{" schedule-status--saved" if calculated else ""}">'
                    f'{"계산 저장됨" if calculated else "계산 전"}</span></article>', unsafe_allow_html=True)


def render_schedule(groups, saved, *, open_notices, open_calculation):
    """workspace.schedule_groups 결과와 기존 날짜별 이동 콜백을 받아 표시한다."""
    render_preferences(groups)
    heading, picker = st.columns([2, 1], vertical_alignment='center')
    heading.markdown('<h2 class="workbench-section-title">개찰 일정</h2>'
                     '<p class="workbench-section-note">등록 공고 기준</p>', unsafe_allow_html=True)
    if not groups:
        _bulk_actions(())
        st.info('등록된 개찰 일정이 없습니다. 관심공고를 등록해 주세요.')
        return
    today = _today()
    months = sorted({group['date'][:7] for group in groups}, reverse=True)
    if st.session_state.get('schedule_month') not in months:
        st.session_state.pop('schedule_month', None)
    default_month = today.strftime('%Y-%m')
    month = picker.selectbox('개찰 월', months, index=months.index(default_month) if default_month in months else 0,
        format_func=lambda value: f'{value[:4]}년 {int(value[5:])}월', key='schedule_month',
        label_visibility='collapsed', on_change=_mark_ready)
    show_all = st.session_state.get('schedule_show_all', False)
    visible = visible_groups(groups, month, today, show_all)
    scope = '전체 일정' if show_all else f'오늘부터 7일 · {today:%m.%d}–{today + timedelta(days=6):%m.%d}'
    st.caption(f'{scope} · 공고 {sum(len(group["notices"]) for group in visible):,}건')
    _bulk_actions(tuple(group['date'] for group in visible))
    if not visible:
        st.info('해당 기간에 개찰 일정이 없습니다. 전체 일정 보기로 다른 날짜를 확인하세요.')
    for group in visible:
        _schedule_day(group, saved, open_notices, open_calculation)
    st.button('일주일만 보기' if show_all else '전체 일정 보기', key='schedule_scope_toggle', type='tertiary',
        width='stretch', icon=':material/expand_less:' if show_all else ':material/expand_more:', on_click=_toggle_scope)
    count = sum(len(group['notices']) for group in groups if group['date'].startswith(month))
    st.caption(f'{int(month[5:])}월 등록 공고 {count:,}건')
