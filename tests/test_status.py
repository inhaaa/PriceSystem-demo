"""공개 데모의 가상 투찰 비교와 조회 카드 상호작용."""
from copy import deepcopy
import csv
from datetime import date
from decimal import Decimal
import importlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from demo.store import DemoStore
from demo.ui import csv_bytes


ROOT = Path(__file__).resolve().parents[1]


class StatusDataTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'demo/status.py').is_file(), '공개 투찰 비교 모듈이 필요합니다.')
        self.status = importlib.import_module('demo.status')
        self.store = DemoStore()
        self.addCleanup(self.store.close)

    def display(self):
        return self.status.status_display(self.store.notices(), self.store.submissions(), self.store.results())

    def test_seed_has_adjacent_amount_difference_rate_and_rank(self):
        display = self.display()
        columns = list(display.columns)
        start = columns.index('실제투찰금액')
        self.assertEqual(columns[start:start + 5], [
            '실제투찰금액', '1순위투찰금액', '1순위 대비 차이', '1순위 대비 차이율 (%)', '내 실제순위'])
        rows = display.set_index('공고번호')
        self.assertEqual(rows.loc['DEMO-009', ['실제투찰금액', '1순위투찰금액', '1순위 대비 차이',
                                              '1순위 대비 차이율 (%)', '내 실제순위']].tolist(),
                         ['13,000,000', '13,000,000', '0', '0.00%', '1위'])
        self.assertEqual(rows.loc['DEMO-010', ['실제투찰금액', '1순위투찰금액', '1순위 대비 차이',
                                              '1순위 대비 차이율 (%)', '내 실제순위']].tolist(),
                         ['29,000,000', '28,884,000', '+116,000', '+0.40%', '5위'])

    def test_draft_unsubmitted_and_pending_results_do_not_invent_comparisons(self):
        rows = self.display().set_index('공고번호')
        for code in ('DEMO-001', 'DEMO-007', 'DEMO-011', 'DEMO-012'):
            with self.subTest(code=code):
                self.assertEqual(rows.loc[code, ['내 낙찰상태', '1순위투찰금액', '1순위 대비 차이',
                                                 '1순위 대비 차이율 (%)', '내 실제순위']].tolist(), [''] * 5)
        self.assertEqual(rows.loc['DEMO-001', '실제투찰금액'], '')
        self.assertEqual(rows.loc['DEMO-007', '실제투찰금액'], '54,000,000')

    def test_completed_submission_wins_over_later_draft(self):
        self.store.save_submission(dict(notice_id=9, company='가상 초안', amount=1, status='작성중', memo=''))
        self.assertEqual(self.display().set_index('공고번호').loc['DEMO-009', '실제투찰금액'], '13,000,000')

    def test_zero_denominator_has_blank_rate(self):
        submissions = self.store.submissions()
        for row in submissions:
            if row['notice_id'] in (9, 10):
                row['amount'] = 0
        display = self.status.status_display(self.store.notices(), submissions, self.store.results())
        rows = display.set_index('공고번호')
        for code in ('DEMO-009', 'DEMO-010'):
            self.assertEqual(rows.loc[code, '1순위투찰금액'], '0')
            self.assertEqual(rows.loc[code, '1순위 대비 차이율 (%)'], '')

    def test_building_display_leaves_all_input_records_unchanged(self):
        inputs = (self.store.notices(), self.store.submissions(), self.store.results())
        original = deepcopy(inputs)
        self.status.status_display(*inputs)
        self.assertEqual(inputs, original)

    def test_empty_display_keeps_schema(self):
        empty = self.status.status_display([], [], [])
        self.assertTrue(empty.empty)
        self.assertEqual(list(empty.columns), list(self.display().columns))

    def test_averages_use_unrounded_row_rates_and_exclude_zero_denominator(self):
        display = pd.DataFrame([
            {'내 낙찰상태': '미낙찰', '개찰결과 상태': '개찰 완료', '실제투찰금액': '100,004', '1순위투찰금액': '100,000'},
            {'내 낙찰상태': '미낙찰', '개찰결과 상태': '개찰 완료', '실제투찰금액': '100,005', '1순위투찰금액': '100,000'},
        ])
        original = display.copy(deep=True)
        summary = self.status.comparison_averages(display)
        self.assertEqual(summary['미낙찰'], {'amount': Decimal('5'), 'rate': Decimal('0.00'),
                                             'amount_count': 2, 'rate_count': 2})
        pd.testing.assert_frame_equal(display, original)
        zero = pd.DataFrame([{'내 낙찰상태': '낙찰', '개찰결과 상태': '개찰 완료',
                              '실제투찰금액': '0', '1순위투찰금액': '0'}])
        self.assertEqual(self.status.comparison_averages(zero)['낙찰'],
                         {'amount': Decimal('0'), 'rate': None, 'amount_count': 1, 'rate_count': 0})

    def test_rates_are_arithmetic_mean_instead_of_ratio_of_totals(self):
        display = pd.DataFrame([
            {'내 낙찰상태': '미낙찰', '개찰결과 상태': '개찰 완료', '실제투찰금액': '200', '1순위투찰금액': '100'},
            {'내 낙찰상태': '미낙찰', '개찰결과 상태': '개찰 완료', '실제투찰금액': '10,001', '1순위투찰금액': '10,000'},
        ])
        self.assertEqual(self.status.comparison_averages(display)['미낙찰']['rate'], Decimal('50.01'))

    def test_missing_and_unfinished_rows_do_not_create_averages(self):
        empty = {'amount': None, 'rate': None, 'amount_count': 0, 'rate_count': 0}
        display = pd.DataFrame([
            {'내 낙찰상태': '낙찰', '개찰결과 상태': '결과 대기', '실제투찰금액': '100', '1순위투찰금액': '90'},
            {'내 낙찰상태': '미낙찰', '개찰결과 상태': '개찰 완료', '실제투찰금액': '', '1순위투찰금액': None},
        ])
        self.assertEqual(self.status.comparison_averages(display), {'낙찰': empty, '미낙찰': empty})


class StatusPageJourneys(unittest.TestCase):
    def page(self):
        self.assertTrue((ROOT / 'demo/status.py').is_file(), '공개 투찰 비교 모듈이 필요합니다.')
        app = AppTest.from_string(
            'import streamlit as st\n'
            'from demo.store import DemoStore\n'
            'from demo.status import status_page\n'
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            "status_page(st.session_state['store'])\n", default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def test_cards_filter_immediately_toggle_restore_and_sync_dropdown(self):
        app = self.page()
        self.assertEqual(len(app.session_state['status_display']), 12)
        app.button(key='status_card_win').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['status_display']['공고번호'].tolist(), ['DEMO-009'])
        self.assertEqual(app.selectbox(key='status_outcome').value, '낙찰')
        self.assertEqual(app.button(key='status_card_win').proto.type, 'primary')
        self.assertIn('check_circle', app.button(key='status_card_win').proto.icon)
        app.button(key='status_card_loss').click().run()
        self.assertEqual(app.session_state['status_display']['공고번호'].tolist(), ['DEMO-010'])
        self.assertEqual(app.button(key='status_card_loss').proto.type, 'primary')
        self.assertEqual(app.button(key='status_card_win').proto.type, 'secondary')
        values = {item.label: item.value for item in app.metric}
        self.assertEqual(values['낙찰 평균 금액 차이'], '—')
        self.assertEqual(values['미낙찰 평균 금액 차이'], '+116,000원')
        self.assertEqual(values['미낙찰 평균 차이율'], '+0.40%')
        app.button(key='status_card_loss').click().run()
        self.assertEqual(len(app.session_state['status_display']), 12)
        self.assertEqual(app.selectbox(key='status_outcome').value, '전체')

    def test_cards_preserve_query_and_use_cached_results_without_store_requery(self):
        app = self.page()
        app.text_input(key='status_no_keyword').set_value('DEMO-010')
        app.text_input(key='status_name_keyword').set_value('커뮤니티실')
        app.date_input(key='status_start').set_value(date(2026, 10, 20))
        app.date_input(key='status_end').set_value(date(2026, 10, 22))
        app.button(key='status_search').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['status_display']['공고번호'].tolist(), ['DEMO-010'])
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        with patch.object(store, 'notices', side_effect=AssertionError('카드는 재조회하지 않습니다.')), \
                patch.object(store, 'submissions', side_effect=AssertionError('카드는 재조회하지 않습니다.')), \
                patch.object(store, 'results', side_effect=AssertionError('카드는 재조회하지 않습니다.')):
            app.button(key='status_card_win').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.session_state['status_display'].empty)
            app.button(key='status_card_loss').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['status_display']['공고번호'].tolist(), ['DEMO-010'])
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)
        self.assertEqual(app.text_input(key='status_no_keyword').value, 'DEMO-010')
        self.assertEqual(app.date_input(key='status_start').value, date(2026, 10, 20))

    def test_dropdown_query_updates_selection_and_export_matches_visible_rows(self):
        app = self.page()
        app.selectbox(key='status_outcome').set_value('미낙찰')
        with patch('demo.status.csv_bytes', wraps=csv_bytes) as exporter:
            app.button(key='status_search').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.button(key='status_card_loss').proto.type, 'primary')
        display = app.session_state['status_display']
        self.assertEqual(exporter.call_args.args[0], display.to_dict('records'))
        exported = list(csv.DictReader(io.StringIO(csv_bytes(exporter.call_args.args[0]).decode('utf-8-sig'))))
        self.assertEqual([row['공고번호'] for row in exported], ['DEMO-010'])
        self.assertEqual(exported[0]['1순위 대비 차이율 (%)'], "'+0.40%")
        self.assertIn('CSV', app.get('download_button')[0].proto.label)
        app.selectbox(key='status_outcome').set_value('개찰 완료')
        app.button(key='status_search').click().run()
        self.assertEqual(len(app.session_state['status_display']), 2)
        self.assertEqual(app.button(key='status_card_loss').proto.type, 'secondary')

    def test_empty_search_and_invalid_dates_do_not_retain_old_comparisons(self):
        app = self.page()
        app.text_input(key='status_no_keyword').set_value('없는공고')
        app.button(key='status_search').click().run()
        self.assertTrue(app.session_state['status_display'].empty)
        self.assertEqual({item.value for item in app.metric if '평균' in item.label}, {'—'})
        self.assertFalse(app.get('download_button'))
        app.date_input(key='status_start').set_value(date(2026, 10, 31))
        app.date_input(key='status_end').set_value(date(2026, 10, 1))
        app.button(key='status_search').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertTrue(app.session_state['status_display'].empty)

    def test_native_table_colors_outcomes_and_search_excludes_region(self):
        app = self.page()
        self.assertEqual([item.label for item in app.text_input], ['공고번호', '공고명'])
        grid = app.dataframe[0]
        self.assertIn('#17613b', grid.proto.arrow_data.styler.styles)
        self.assertIn('#9b3d35', grid.proto.arrow_data.styler.styles)
        self.assertTrue(any('가상' in item.value and '1순위' in item.value for item in app.caption))
        self.assertEqual(len([item for item in app.metric if '평균' in item.label]), 4)


if __name__ == '__main__':
    unittest.main()
