"""현재 데모 세션의 투찰·낙찰 기록을 개찰월별로 집계한다."""
from datetime import date
from hashlib import sha256

import pandas as pd
import streamlit as st

from demo.ui import csv_bytes, money_columns


def monthly_performance(notices, submissions, results, *, year, category='전체'):
    """DemoStore의 dict 행으로 선택 연도 12개월의 건수와 정수 원 금액을 반환한다."""
    if type(year) is not int or not 2000 <= year <= 2100:
        raise ValueError('연도는 2000~2100 범위의 정수여야 합니다.')
    months = {
        f'{year}-{month:02d}': {
            'month': f'{year}-{month:02d}', 'bid_count': 0, 'win_count': 0, 'award_amount': 0,
        }
        for month in range(1, 13)
    }
    submitted_ids = {row['notice_id'] for row in submissions if row['status'] == '제출완료'}
    winning_amounts = {row['notice_id']: row['amount'] for row in results if row['outcome'] == '샘플 낙찰'}
    for notice in notices:
        notice_id = notice['id']
        if notice_id not in submitted_ids or (category != '전체' and notice['category'] != category):
            continue
        month = months.get(notice['deadline'][:7])
        if month is None:
            continue
        month['bid_count'] += 1
        if notice_id in winning_amounts:
            month['win_count'] += 1
            month['award_amount'] += winning_amounts[notice_id]
    return list(months.values())


def _chart_source(frame):
    # 같은 크기의 Arrow 데이터도 값이 바뀌면 차트를 다시 그리도록 이름에 내용을 반영한다.
    name = 'data-' + sha256(frame.to_json(orient='records').encode()).hexdigest()
    return {'data': {'name': name}, 'datasets': {name: frame}}


def performance_page(store):
    """집계·그래프·다운로드를 같은 조회 연도와 카테고리에 맞춰 표시한다."""
    notices = store.notices()
    years = sorted({int(row['deadline'][:4]) for row in notices} or {date.today().year}, reverse=True)
    with st.container(key='performance_report'):
        year_column, category_column = st.columns([1, 2])
        if st.session_state.get('report_year') not in years:
            st.session_state.pop('report_year', None)
        categories = ['전체', *store.categories()]
        if st.session_state.get('report_category') not in categories:
            st.session_state.pop('report_category', None)
        year = year_column.selectbox('조회 연도', years, format_func=lambda value: f'{value}년', key='report_year')
        category = category_column.selectbox('카테고리', categories, key='report_category')
        monthly = monthly_performance(notices, store.submissions(), store.results(), year=year, category=category)
        totals = {key: sum(row[key] for row in monthly) for key in ('bid_count', 'win_count', 'award_amount')}
        with st.container(key='report_summary'):
            bids, wins, amount = st.columns(3)
            bids.metric('투찰 건수', f"{totals['bid_count']:,}건")
            wins.metric('낙찰 건수', f"{totals['win_count']:,}건")
            amount.metric('낙찰금액', f"{totals['award_amount']:,}원")
        st.caption('개찰월 기준 · 제출완료 공고는 중복 없이 1건으로 집계합니다. '
                   '낙찰금액은 해당 공고에 연결된 낙찰 결과의 금액 합계입니다.')
        if not any(row['bid_count'] for row in monthly):
            st.info('선택한 조건에 제출완료 투찰 기록이 없습니다. 기록이 없는 달은 0으로 표시합니다.')
        frame = pd.DataFrame(monthly).rename(columns={
            'month': '월', 'bid_count': '투찰 건수', 'win_count': '낙찰 건수', 'award_amount': '낙찰금액 (원)',
        })
        x_axis = {'field': '월', 'type': 'ordinal', 'title': None,
                  'axis': {'labelAngle': 0, 'labelOverlap': 'greedy',
                           'labelExpr': "toNumber(slice(datum.label, 5)) + '월'"}}
        counts, amounts = st.columns(2, gap='medium')
        with counts, st.container(key='report_count_panel'):
            st.markdown('<h2 class="workbench-section-title">월별 투찰·낙찰 건수</h2>', unsafe_allow_html=True)
            st.caption('제출완료 공고와 연결된 낙찰 결과 · 단위: 건')
            counts_frame = frame.melt(id_vars='월', value_vars=['투찰 건수', '낙찰 건수'],
                                      var_name='구분', value_name='건수')
            st.vega_lite_chart(spec={
                **_chart_source(counts_frame),
                'mark': {'type': 'bar', 'cornerRadiusEnd': 3},
                'encoding': {
                    'x': x_axis, 'xOffset': {'field': '구분'},
                    'y': {'field': '건수', 'type': 'quantitative', 'title': '건',
                          'axis': {'tickMinStep': 1, 'format': 'd'}, 'scale': {'zero': True}},
                    'color': {'field': '구분', 'type': 'nominal', 'legend': {'title': None, 'orient': 'top'},
                              'scale': {'domain': ['투찰 건수', '낙찰 건수'], 'range': ['#718178', '#18794e']}},
                    'tooltip': [{'field': '월'}, {'field': '구분'}, {'field': '건수', 'type': 'quantitative', 'format': ',d'}],
                },
            }, height=280, width='stretch', key='report_counts_chart')
        with amounts, st.container(key='report_amount_panel'):
            st.markdown('<h2 class="workbench-section-title">낙찰금액 추이</h2>', unsafe_allow_html=True)
            st.caption('월별 낙찰금액 합계 · 단위: 백만원')
            amounts_frame = frame[['월', '낙찰금액 (원)']].copy()
            amounts_frame['낙찰금액 (백만원)'] = amounts_frame['낙찰금액 (원)'] / 1_000_000
            st.vega_lite_chart(spec={
                **_chart_source(amounts_frame),
                'mark': {'type': 'line', 'point': True, 'strokeWidth': 2, 'color': '#18794e'},
                'encoding': {
                    'x': x_axis,
                    'y': {'field': '낙찰금액 (백만원)', 'type': 'quantitative', 'title': '백만원', 'scale': {'zero': True}},
                    'tooltip': [{'field': '월'}, {'field': '낙찰금액 (원)', 'type': 'quantitative', 'format': ',.0f'}],
                },
            }, height=280, width='stretch', key='report_amount_chart')
        with st.container(key='report_detail_panel'):
            st.markdown('<h2 class="workbench-section-title">월별 상세 실적</h2>', unsafe_allow_html=True)
            st.caption(f'{year}년 1월–12월 · {category} · 금액 단위: 원')
            st.dataframe(frame, hide_index=True, width='stretch', column_config=money_columns(frame.columns))
            st.download_button('월별 실적 CSV 다운로드', csv_bytes(frame.to_dict('records')),
                               f'demo-performance-{year}.csv', 'text/csv', key='report_download')
        st.caption('DEMO · 현재 세션에 등록된 가상 기록을 집계합니다.')
