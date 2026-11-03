"""운영 리포트의 기간·독립 집계·지연 다운로드를 가상 데이터로 검증한다."""
from copy import deepcopy
import csv
import io
import unittest
from unittest.mock import patch

from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from streamlit.testing.v1 import AppTest

from demo import performance


class ProductionReportParityTests(unittest.TestCase):
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

    def test_month_filter_controls_metrics_charts_table_and_download_snapshot(self):
        downloads = []
        original = performance.st.download_button

        def capture(*args, **kwargs):
            downloads.append((args[1], args[2]))
            return original(*args, **kwargs)

        with patch.object(performance.st, 'download_button', side_effect=capture):
            app = self.app()
            self.assertEqual(app.number_input(key='report_year').value, 2026)
            before = deepcopy((app.session_state['store'].notices(),
                               app.session_state['store'].submissions(),
                               app.session_state['store'].results()))
            notice_ids = {row['id'] for row in before[0] if row['deadline'].startswith('2026-06')}
            bid_count = len({row['notice_id'] for row in before[1]
                             if row['notice_id'] in notice_ids and row['status'] == '제출완료'})
            wins = [row for row in before[2]
                    if row['notice_id'] in notice_ids and row['outcome'] == '샘플 낙찰']
            award_amount = sum(row['amount'] for row in wins
                               if type(row['amount']) is int and row['amount'] > 0)
            expected = {'월': '2026-06', '투찰 건수': bid_count,
                        '낙찰 건수': len(wins), '낙찰금액 (원)': award_amount}
            app.selectbox(key='report_month').set_value(6).run()
            self.assertFalse(app.exception)
            self.assertEqual({item.label: item.value for item in app.metric}, {
                '투찰 기록 건수': f'{bid_count:,}건', '기록상 낙찰 건수': f'{len(wins):,}건',
                '확정 낙찰금액': f'{award_amount:,}원',
            })
            frame = app.dataframe[0].value
            self.assertEqual(frame.to_dict('records'), [expected])
            chart_frames = [convert_arrow_bytes_to_pandas_df(item.proto.datasets[0].data.data)
                            for item in app.get('vega_lite_chart')]
            self.assertEqual(set(chart_frames[0]['월']), {'2026-06'})
            self.assertEqual(chart_frames[0].set_index('구분')['건수'].to_dict(),
                             {'투찰 건수': bid_count, '낙찰 건수': len(wins)})
            self.assertEqual(chart_frames[1]['월'].tolist(), ['2026-06'])
            self.assertEqual(chart_frames[1]['낙찰금액 (원)'].tolist(), [award_amount])
            download, filename = downloads[-1]
            self.assertTrue(callable(download))
            self.assertEqual(filename, 'demo-performance-2026-06.csv')
            app.selectbox(key='report_month').set_value(7).run()
            snapshot = list(csv.DictReader(io.StringIO(download().decode('utf-8-sig'))))
            self.assertEqual(snapshot, [{key: str(value) for key, value in expected.items()}])
            app.button(key='report_refresh').click().run()
            self.assertEqual((app.session_state['store'].notices(),
                              app.session_state['store'].submissions(),
                              app.session_state['store'].results()), before)

    def test_missing_or_invalid_final_amount_never_borrows_a_submission_amount(self):
        invalid = (None, 0, -1, True, 1.5, '1000000')
        notices = [{'id': index, 'deadline': '2026-06-01', 'category': '가상 시설'}
                   for index in range(len(invalid) + 1)]
        submissions = [{'notice_id': row['id'], 'status': '제출완료', 'amount': 999_999}
                       for row in notices]
        results = [{'notice_id': index, 'outcome': '샘플 낙찰', 'amount': value}
                   for index, value in enumerate((*invalid, 123))]
        before = deepcopy((notices, submissions, results))
        row = performance.monthly_performance(notices, submissions, results, year=2026)[5]
        self.assertEqual(row, {'month': '2026-06', 'bid_count': 7, 'win_count': 7, 'award_amount': 123})
        self.assertEqual((notices, submissions, results), before)

    def test_month_contract_rejects_invalid_values_and_returns_one_selected_month(self):
        for month in (True, False, 0, 13, '6', 6.0):
            with self.subTest(month=month), self.assertRaises(ValueError):
                performance.monthly_performance([], [], [], year=2026, month=month)
        self.assertEqual(performance.monthly_performance([], [], [], year=2026, month=6),
                         [{'month': '2026-06', 'bid_count': 0, 'win_count': 0, 'award_amount': 0}])


if __name__ == '__main__':
    unittest.main()
