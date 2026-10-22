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

    def test_counts_unique_completed_submissions_and_only_their_awards(self):
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
            'month': '2026-06', 'bid_count': 3, 'win_count': 1, 'award_amount': 13_000_000,
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
        self.assertFalse(app.exception)
        return app

    def metrics(self, app):
        return {item.label: item.value for item in app.metric}

    def chart_frames(self, app):
        return [convert_arrow_bytes_to_pandas_df(item.proto.datasets[0].data.data)
                for item in app.get('vega_lite_chart')]

    def test_six_months_of_metrics_chart_data_and_table_agree(self):
        app = self.app()
        self.assertEqual(self.metrics(app), {'투찰 건수': '21건', '낙찰 건수': '8건', '낙찰금액': '116,500,000원'})
        table = app.dataframe[0].value
        self.assertEqual(list(table.columns), ['월', '투찰 건수', '낙찰 건수', '낙찰금액 (원)'])
        self.assertEqual(table.iloc[4:10][['투찰 건수', '낙찰 건수', '낙찰금액 (원)']].values.tolist(), [
            [2, 1, 8_400_000], [4, 2, 23_500_000], [3, 1, 15_800_000],
            [5, 2, 31_200_000], [4, 1, 24_600_000], [3, 1, 13_000_000],
        ])
        self.assertEqual(len(table), 12)
        counts, amounts = self.chart_frames(app)
        self.assertEqual(counts.groupby('구분')['건수'].sum().to_dict(), {'낙찰 건수': 8, '투찰 건수': 21})
        self.assertEqual(amounts['낙찰금액 (원)'].tolist(), table['낙찰금액 (원)'].tolist())
        self.assertEqual(app.download_button[0].label, '월별 실적 CSV 다운로드')
        self.assertTrue(any('가상' in item.value for item in app.caption))

    def test_category_and_changed_record_refresh_same_size_charts_without_writing(self):
        app = self.app()
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        originals = [item.proto.spec for item in app.get('vega_lite_chart')]
        app.selectbox(key='report_category').select('가상 시설').run()
        self.assertFalse(app.exception)
        self.assertEqual(self.metrics(app), {'투찰 건수': '8건', '낙찰 건수': '4건', '낙찰금액': '50,900,000원'})
        self.assertTrue(all(a != b for a, b in zip(originals, [item.proto.spec for item in app.get('vega_lite_chart')])) )
        app.selectbox(key='report_category').select('전체').run()
        store.save_result({**store.results()[0], 'amount': 15_000_000})
        app.run()
        self.assertEqual(self.metrics(app)['낙찰금액'], '118,500,000원')
        self.assertNotEqual(app.get('vega_lite_chart')[1].proto.spec, originals[1])
        self.assertEqual((store.notices(), store.submissions()), before[:2])

    def test_year_filter_and_empty_records_keep_twelve_month_rows(self):
        app = self.app()
        store = app.session_state['store']
        notice = store.get_notice(9)
        store.save_notice({**notice, 'deadline': '2025-12-31'}, notice_id=9)
        app.run()
        app.selectbox(key='report_year').set_value(2025).run()
        self.assertFalse(app.exception)
        self.assertEqual(self.metrics(app), {'투찰 건수': '1건', '낙찰 건수': '1건', '낙찰금액': '13,000,000원'})
        self.assertEqual(app.dataframe[0].value['월'].tolist(), [f'2025-{month:02d}' for month in range(1, 13)])
        for row in store.notices():
            store.delete_notice(row['id'])
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(self.metrics(app), {'투찰 건수': '0건', '낙찰 건수': '0건', '낙찰금액': '0원'})
        self.assertEqual(len(app.dataframe[0].value), 12)
        self.assertTrue(app.info)


if __name__ == '__main__':
    unittest.main()
