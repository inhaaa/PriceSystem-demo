"""성과 집계와 화면 필터가 같은 월별 기록을 표시하는지 검증한다."""
from copy import deepcopy
import unittest

from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from streamlit.testing.v1 import AppTest

from demo.performance import monthly_performance


class MonthlyPerformanceTests(unittest.TestCase):
    def aggregate(self, notices=(), submissions=(), results=(), **filters):
        return monthly_performance(notices, submissions, results, **{'year': 2026, **filters})

    def test_empty_inputs_return_twelve_zero_months_and_validate_year(self):
        rows = self.aggregate()
        self.assertEqual([row['month'] for row in rows], [f'2026-{month:02d}' for month in range(1, 13)])
        self.assertTrue(all(row['bid_count'] == row['win_count'] == row['award_amount'] == 0 for row in rows))
        for value in (True, False, None, '2026', 2026.0, 1999, 2101):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.aggregate(year=value)

    def test_counts_completed_submissions_and_recorded_awards_independently(self):
        notices = [{'id': i, 'deadline': '2026-06-04', 'category': '가상 시설'} for i in range(1, 6)]
        submissions = [
            {'notice_id': 1, 'status': '제출완료'}, {'notice_id': 1, 'status': '제출완료'},
            {'notice_id': 2, 'status': '제출완료'}, {'notice_id': 3, 'status': '작성중'},
            {'notice_id': 4, 'status': '제출완료'}, {'notice_id': 99, 'status': '제출완료'},
        ]
        results = [
            {'notice_id': 1, 'outcome': '샘플 낙찰', 'amount': 13_000_000},
            {'notice_id': 2, 'outcome': '샘플 미선정', 'amount': 28_000_000},
            {'notice_id': 3, 'outcome': '샘플 낙찰', 'amount': 7_000_000},
            {'notice_id': 5, 'outcome': '샘플 낙찰', 'amount': 7_000_000},
            {'notice_id': 99, 'outcome': '샘플 낙찰', 'amount': 7_000_000},
        ]
        before = deepcopy((notices, submissions, results))
        self.assertEqual(self.aggregate(notices, submissions, results)[5], {
            'month': '2026-06', 'bid_count': 3, 'win_count': 3, 'award_amount': 27_000_000,
        })
        self.assertEqual((notices, submissions, results), before)

    def test_category_and_year_filters_keep_exact_integer_award_amounts(self):
        notices = [
            {'id': 1, 'deadline': '2026-01-01', 'category': '가상 시설'},
            {'id': 2, 'deadline': '2026-01-21', 'category': '가상 시설'},
            {'id': 3, 'deadline': '2026-01-24', 'category': '가상 물품'},
            {'id': 4, 'deadline': '2025-12-31', 'category': '가상 시설'},
        ]
        submissions = [{'notice_id': i, 'status': '제출완료'} for i in range(1, 5)]
        amounts = [9_007_199_254_740_993, 8_000_000_000_000_011, 11, 29]
        results = [{'notice_id': i, 'outcome': '샘플 낙찰', 'amount': amount}
                   for i, amount in enumerate(amounts, 1)]
        row = self.aggregate(notices, submissions, results, category='가상 시설')[0]
        self.assertEqual(row, {'month': '2026-01', 'bid_count': 2, 'win_count': 2,
                               'award_amount': 17_007_199_254_741_004})
        self.assertIs(type(row['award_amount']), int)
        self.assertEqual(self.aggregate(notices, submissions, results, year=2025)[11]['award_amount'], 29)
        self.assertEqual(self.aggregate(notices, submissions, results, category='없는 분류'), self.aggregate())


class PerformancePageTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_string(
            'import streamlit as st\n'
            'from demo.fixtures import create_demo_store\n'
            'from demo.performance import performance_page\n'
            "if 'store' not in st.session_state: st.session_state['store'] = create_demo_store()\n"
            "performance_page(st.session_state['store'])\n", default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        app.number_input(key='report_year').set_value(2026).run()
        self.assertFalse(app.exception)
        return app

    def metrics(self, app):
        return {item.label: item.value for item in app.metric}

    def chart_frames(self, app):
        return [convert_arrow_bytes_to_pandas_df(item.proto.datasets[0].data.data)
                for item in app.get('vega_lite_chart')]

    def assert_report_matches_records(self, app, year=2026, category='전체'):
        self.assertFalse(app.exception)
        store = app.session_state['store']
        notices, submissions, results = store.notices(), store.submissions(), store.results()
        expected = []
        for month in range(1, 13):
            period = f'{year}-{month:02d}'
            notice_ids = {row['id'] for row in notices
                          if row['deadline'].startswith(period)
                          and (category == '전체' or row['category'] == category)}
            bids = {row['notice_id'] for row in submissions
                    if row['notice_id'] in notice_ids and row['status'] == '제출완료'}
            wins = [row for row in results
                    if row['notice_id'] in notice_ids and row['outcome'] == '샘플 낙찰']
            expected.append({'월': period, '투찰 건수': len(bids), '낙찰 건수': len(wins),
                             '낙찰금액 (원)': sum(row['amount'] for row in wins
                                              if type(row['amount']) is int and row['amount'] > 0)})
        self.assertEqual(self.metrics(app), {
            '투찰 기록 건수': f"{sum(row['투찰 건수'] for row in expected):,}건",
            '기록상 낙찰 건수': f"{sum(row['낙찰 건수'] for row in expected):,}건",
            '확정 낙찰금액': f"{sum(row['낙찰금액 (원)'] for row in expected):,}원",
        })
        table = app.dataframe[0].value
        self.assertEqual(list(table.columns), ['월', '투찰 건수', '낙찰 건수', '낙찰금액 (원)'])
        self.assertEqual(table.to_dict('records'), expected)
        counts, amounts = self.chart_frames(app)
        self.assertEqual(counts.pivot(index='월', columns='구분', values='건수').reset_index().to_dict('records'),
                         [{key: row[key] for key in ('월', '투찰 건수', '낙찰 건수')} for row in expected])
        self.assertEqual(amounts[['월', '낙찰금액 (원)']].to_dict('records'),
                         [{key: row[key] for key in ('월', '낙찰금액 (원)')} for row in expected])
        return expected

    def test_twelve_months_of_metrics_chart_data_and_table_agree_with_records(self):
        app = self.app()
        expected = self.assert_report_matches_records(app)
        self.assertTrue(all(row['투찰 건수'] > 0 and row['낙찰 건수'] > 0 for row in expected))
        self.assertEqual(app.download_button[0].label, '월별 실적 CSV 다운로드')
        self.assertTrue(any('가상' in item.value for item in app.caption))

    def test_category_and_changed_record_refresh_same_size_charts_without_writing(self):
        app = self.app()
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        before_amount = sum(row['낙찰금액 (원)'] for row in self.assert_report_matches_records(app))
        originals = [item.proto.spec for item in app.get('vega_lite_chart')]
        app.selectbox(key='report_category').select('가상 시설').run()
        self.assert_report_matches_records(app, category='가상 시설')
        self.assertTrue(all(a != b for a, b in zip(originals, [item.proto.spec for item in app.get('vega_lite_chart')])) )
        app.selectbox(key='report_category').select('전체').run()
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)
        winning_result = next(row for row in before[2] if row['outcome'] == '샘플 낙찰'
                              and store.get_notice(row['notice_id'])['deadline'].startswith('2026-'))
        store.save_result({**winning_result, 'amount': winning_result['amount'] + 2_000_000})
        app.run()
        self.assert_report_matches_records(app)
        self.assertEqual(self.metrics(app)['확정 낙찰금액'], f'{before_amount + 2_000_000:,}원')
        self.assertNotEqual(app.get('vega_lite_chart')[1].proto.spec, originals[1])
        self.assertEqual((store.notices(), store.submissions()), before[:2])

    def test_all_years_and_categories_and_empty_year_keep_twelve_month_rows(self):
        app = self.app()
        store = app.session_state['store']
        for year in (2025, 2026, 2027):
            app.number_input(key='report_year').set_value(year).run()
            for category in ['전체', *store.categories()]:
                with self.subTest(year=year, category=category):
                    app.selectbox(key='report_category').select(category).run()
                    expected = self.assert_report_matches_records(app, year, category)
                    self.assertTrue(all(row['투찰 건수'] > 0 and row['낙찰 건수'] > 0 for row in expected))
        app.selectbox(key='report_category').select('전체').run()
        app.number_input(key='report_year').set_value(2024).run()
        self.assert_report_matches_records(app, year=2024)
        self.assertEqual(self.metrics(app), {'투찰 기록 건수': '0건', '기록상 낙찰 건수': '0건', '확정 낙찰금액': '0원'})
        self.assertTrue(app.info)


if __name__ == '__main__':
    unittest.main()
