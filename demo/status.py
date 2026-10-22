"""외부 시스템과 연결하지 않는 가상 투찰 결과 비교 화면."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import streamlit as st

from demo.ui import csv_bytes


STATUS_COLUMNS = [
    '공고번호', '공고명', '내 낙찰상태', '실제투찰금액', '1순위투찰금액',
    '1순위 대비 차이', '1순위 대비 차이율 (%)', '내 실제순위', '개찰일',
    '발주기관', '지역', '투찰상태', '개찰결과 상태', '비교 기준',
]
RESULT_OPTIONS = ['전체', '개찰 완료', '낙찰', '미낙찰', '결과 대기', '작성중', '미투찰']


def status_display(notices, submissions, results):
    """가상 기록을 표시용 표로 변환하며 완료된 투찰에만 비교 샘플을 만든다."""
    selected = {}
    for submission in submissions:
        previous = selected.get(submission['notice_id'], {})
        if submission['status'] == '제출완료' or previous.get('status') != '제출완료':
            selected[submission['notice_id']] = submission
    outcomes = {row['notice_id']: row['outcome'] for row in results}
    rows = []
    for notice in notices:
        submission = selected.get(notice['id'], {})
        submitted = submission.get('status') == '제출완료'
        outcome = {'샘플 낙찰': '낙찰', '샘플 미선정': '미낙찰'}.get(outcomes.get(notice['id']), '') if submitted else ''
        actual = submission['amount'] if submitted else None
        row = dict.fromkeys(STATUS_COLUMNS, '')
        row.update({
            '공고번호': notice['code'], '공고명': notice['title'], '내 낙찰상태': outcome,
            '실제투찰금액': f'{actual:,}' if actual is not None else '',
            '개찰일': notice['deadline'], '발주기관': notice['agency'], '지역': notice['region'],
            '투찰상태': submission.get('status', '미투찰'),
            '개찰결과 상태': '개찰 완료' if outcome else '결과 대기' if submitted else submission.get('status', '미투찰'),
            '비교 기준': 'DEMO · 가상 기록',
        })
        if outcome:
            rank = 1 if outcome == '낙찰' else 2 + notice['id'] % 7
            first = actual if rank == 1 else max(0, actual - max(1, actual * (rank - 1) // 1000))
            difference = actual - first
            row.update({
                '1순위투찰금액': f'{first:,}', '내 실제순위': f'{rank}위',
                '1순위 대비 차이': f'{difference:+,}' if difference else '0',
                '비교 기준': 'DEMO · 제출액 기반 가상 1순위 금액·순위',
            })
            if first > 0:
                rate = (Decimal(difference) * 100 / Decimal(first)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                row['1순위 대비 차이율 (%)'] = f'{rate:+.2f}%' if rate else '0.00%'
        rows.append(row)
    return pd.DataFrame(rows, columns=STATUS_COLUMNS).sort_values('개찰일', ascending=False).reset_index(drop=True)


def comparison_averages(display):
    """현재 표의 상태별 금액/건별 차이율 평균과 유효 건수를 반환한다."""
    values = {outcome: {'amounts': [], 'rates': []} for outcome in ('낙찰', '미낙찰')}
    for row in display.to_dict('records'):
        outcome = row.get('내 낙찰상태')
        if outcome not in values or row.get('개찰결과 상태') != '개찰 완료':
            continue
        try:
            actual = int(str(row.get('실제투찰금액')).replace(',', ''))
            first = int(str(row.get('1순위투찰금액')).replace(',', ''))
        except ValueError:
            continue
        difference = actual - first
        values[outcome]['amounts'].append(difference)
        if first > 0:
            values[outcome]['rates'].append(Decimal(difference) * 100 / Decimal(first))
    summary = {}
    for outcome, group in values.items():
        amounts, rates = group['amounts'], group['rates']
        summary[outcome] = {
            'amount': (Decimal(sum(amounts)) / len(amounts)).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if amounts else None,
            'rate': (sum(rates) / len(rates)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if rates else None,
            'amount_count': len(amounts), 'rate_count': len(rates),
        }
    return summary


def _toggle_result(outcome):
    params = st.session_state['status_query']
    selected = '전체' if params['outcome'] == outcome else outcome
    st.session_state['status_outcome'] = selected
    st.session_state['status_query'] = {**params, 'outcome': selected}


def _query_source(source, params):
    if params['start'] > params['end']:
        return source.iloc[:0]
    no_keyword = params['number'].strip().casefold()
    name_keyword = params['name'].strip().casefold()
    return source.loc[
        source['개찰일'].between(params['start'].isoformat(), params['end'].isoformat())
        & source['공고번호'].str.casefold().str.contains(no_keyword, regex=False)
        & source['공고명'].str.casefold().str.contains(name_keyword, regex=False)
    ].reset_index(drop=True)


def _result_colors(row):
    colors = {
        '낙찰': 'color: #17613b; background-color: #edf7f0; font-weight: 600',
        '미낙찰': 'color: #9b3d35; background-color: #fff1ef; font-weight: 600',
    }
    style = colors.get(row['내 낙찰상태'], '')
    return [style if column in {'내 낙찰상태', '1순위 대비 차이', '1순위 대비 차이율 (%)'} else '' for column in row.index]


def status_page(store):
    with st.container(key='my_bid_status'):
        if 'status_source' not in st.session_state:
            source = status_display(store.notices(), store.submissions(), store.results())
            st.session_state['status_source'] = source
            days = [date.fromisoformat(value) for value in source['개찰일']]
            st.session_state['status_query'] = {
                'start': min(days) if days else date.today(), 'end': max(days) if days else date.today(),
                'number': '', 'name': '', 'outcome': '전체',
            }
        params = st.session_state['status_query']
        with st.form('status_search_form'):
            start_column, end_column, number_column, name_column = st.columns(4)
            start = start_column.date_input('개찰일 시작', params['start'], key='status_start')
            end = end_column.date_input('개찰일 종료', params['end'], key='status_end')
            number = number_column.text_input('공고번호', key='status_no_keyword')
            name = name_column.text_input('공고명', key='status_name_keyword')
            result_column, action_column = st.columns([1, 3], vertical_alignment='bottom')
            outcome = result_column.selectbox('결과 상태', RESULT_OPTIONS, key='status_outcome')
            with action_column, st.container(key='status_search_action', horizontal=True, horizontal_alignment='right'):
                submitted = st.form_submit_button('조회', icon=':material/search:', type='primary', width=112, key='status_search')
        if submitted:
            st.session_state['status_source'] = status_display(store.notices(), store.submissions(), store.results())
            params = {'start': start, 'end': end, 'number': number, 'name': name, 'outcome': outcome}
            st.session_state['status_query'] = params
        if params['start'] > params['end']:
            st.error('종료일은 시작일 이후여야 합니다.')
        base = _query_source(st.session_state['status_source'], params)
        outcome = params['outcome']
        if outcome in ('낙찰', '미낙찰'):
            display = base.loc[base['내 낙찰상태'].eq(outcome)].reset_index(drop=True)
        elif outcome != '전체':
            display = base.loc[base['개찰결과 상태'].eq(outcome)].reset_index(drop=True)
        else:
            display = base
        st.session_state['status_display'] = display
        with st.container(key='status_result_cards'):
            count, submitted_count, wins, losses, waiting = st.columns(5)
            count.metric('조회 공고', f'{len(display):,}건')
            submitted_count.metric('제출완료', f"{display['투찰상태'].eq('제출완료').sum():,}건")
            for column, result, key in ((wins, '낙찰', 'win'), (losses, '미낙찰', 'loss')):
                selected = outcome == result
                column.button(
                    f"{result}\n\n**{base['내 낙찰상태'].eq(result).sum():,}건**", key=f'status_card_{key}',
                    type='primary' if selected else 'secondary', icon=':material/check_circle:' if selected else None,
                    width='stretch', on_click=_toggle_result, args=(result,),
                    help=f'{result}만 바로 표시합니다. 다시 누르면 전체로 돌아갑니다.',
                )
            waiting.metric('결과 대기', f"{display['개찰결과 상태'].eq('결과 대기').sum():,}건")
        st.caption('낙찰·미낙찰 카드는 조회 기간과 검색어 기준 건수입니다. 카드를 누르면 해당 결과만 표시됩니다.')
        summary = comparison_averages(display)
        with st.container(key='status_averages'):
            columns = st.columns(4)
            for index, result in enumerate(('낙찰', '미낙찰')):
                group = summary[result]
                amount, rate = group['amount'], group['rate']
                columns[index * 2].metric(f'{result} 평균 금액 차이',
                    '—' if amount is None else f'{amount:+,}원' if amount else '0원',
                    help=f"현재 표시 결과 중 금액 비교 가능한 {group['amount_count']:,}건의 평균입니다.")
                columns[index * 2 + 1].metric(f'{result} 평균 차이율',
                    '—' if rate is None else f'{rate:+.2f}%' if rate else '0.00%',
                    help=f"현재 표시 결과 중 1순위 금액이 0원보다 큰 {group['rate_count']:,}건의 건별 차이율 평균입니다.")
        st.caption('현재 표시 결과의 건별 단순평균 · 금액은 원, 차이율은 소수 둘째 자리 반올림 · 1순위 0원·미확인 차이율 제외')
        st.caption('DEMO · 제출완료·개찰완료 기록에만 가상 1순위 금액과 순위를 표시합니다. 낙찰은 1위, 미낙찰은 2~8위인 비교용 샘플입니다.')
        st.caption('금액 차이 = 내 투찰금액 − 1순위 금액(원) · 차이율 = 금액 차이 ÷ 1순위 금액 × 100 · +는 1순위보다 높은 금액입니다.')
        if display.empty:
            st.info('조회 조건에 맞는 투찰 기록이 없습니다. 날짜·검색어·결과 상태를 바꿔 주세요.')
            return
        st.caption(':green[● 낙찰] · :red[● 미낙찰] — 상태·금액 차이·차이율을 같은 색으로 표시합니다.')
        st.dataframe(display.style.apply(_result_colors, axis=1), hide_index=True, width='stretch',
            column_config={
                '1순위 대비 차이': st.column_config.TextColumn('금액 차이 (원)', help='내 투찰금액 − 가상 1순위 금액'),
                '1순위 대비 차이율 (%)': st.column_config.TextColumn('차이율 (%)', width='small',
                    help='(내 투찰금액 − 가상 1순위 금액) ÷ 1순위 금액 × 100. 1순위 금액이 0원 또는 미확인이면 공백입니다.'),
            }, key='status_table')
        st.download_button('내 투찰현황 CSV 다운로드', csv_bytes(display.to_dict('records')),
                           'demo-bid-status.csv', 'text/csv', key='status_download')
