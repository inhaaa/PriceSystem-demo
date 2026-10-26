"""운영 UI의 기간·조회 계약을 독립 데모 데이터에서 검증한다."""
from datetime import date, timedelta
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo import bid_pages, status


class ProductionBidParityTests(unittest.TestCase):
    def page(self, name, module='bid_pages'):
        app = AppTest.from_string(
            'import streamlit as st\n'
            'from demo.store import DemoStore\n'
            f'from demo.{module} import {name}\n'
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            f"{name}(st.session_state['store'])\n", default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def test_daily_detailed_filters_use_display_metadata_without_changing_store(self):
        app = self.page('daily_page')
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        details = next(item for item in app.expander if item.label == '상세 조회 조건')
        self.assertFalse(details.proto.expanded)
        self.assertEqual({'daily_keyword', 'daily_no_keyword', 'daily_license', 'daily_region',
                          'daily_agency', 'daily_contract'}, {item.key for item in details.text_input})
        for key, value in {'daily_no_keyword': 'DEMO-001', 'daily_license': '시설',
                           'daily_region': '동부', 'daily_agency': '운영센터',
                           'daily_contract': '제한경쟁'}.items():
            app.text_input(key=key).set_value(value)
        app.button(key='daily_search').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), ['DEMO-001'])
        app.text_input(key='daily_region').set_value('없는지역')
        app.button(key='daily_search').click().run()
        self.assertFalse(app.dataframe)
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)

    def test_management_defaults_to_today_and_filters_saved_record_presence(self):
        today = date(2026, 10, 21)
        with patch.object(bid_pages, '_today_kst', return_value=today, create=True):
            app = self.page('management_page')
        self.assertEqual([item.value for item in app.date_input], [today, today])
        app.button(key='management_search').click().run()
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), ['DEMO-010'])
        app.selectbox(key='management_result_filter').set_value('없음')
        app.button(key='management_search').click().run()
        self.assertFalse(app.dataframe)
        app.selectbox(key='management_result_filter').set_value('전체')
        app.selectbox(key='management_recommendation_filter').set_value('있음')
        app.button(key='management_search').click().run()
        self.assertFalse(app.dataframe)

    def test_review_queries_year_and_month_directly_and_refresh_keeps_checklist(self):
        app = self.page('review_page')
        app.selectbox(key='review_1_status').set_value('보류')
        app.button(key='review_save_1').click().run()
        app.selectbox(key='review_month').set_value(9).run()
        self.assertFalse(app.dataframe)
        self.assertEqual(app.session_state['demo_reviews'][1]['status'], '보류')
        app.selectbox(key='review_month').set_value(10).run()
        app.button(key='review_refresh').click().run()
        self.assertEqual(len(app.dataframe[0].value), 12)
        self.assertEqual(app.selectbox(key='review_1_status').value, '보류')
        app.number_input(key='review_year').set_value(2025).run()
        self.assertFalse(app.dataframe)

    def test_management_restores_submitted_filters_after_widget_cleanup(self):
        app = AppTest.from_string(
            'import streamlit as st\n'
            'from demo.store import DemoStore\n'
            'from demo.bid_pages import management_page\n'
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            "if st.session_state.get('show_management', True): management_page(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        app.date_input(key='management_start').set_value(date(2026, 10, 1))
        app.date_input(key='management_end').set_value(date(2026, 10, 31))
        app.selectbox(key='management_category').set_value('가상 시설')
        app.text_input(key='management_agency').set_value('운영센터')
        app.button(key='management_search').click().run()
        app.session_state['show_management'] = False
        app.run()
        app.session_state['show_management'] = True
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='management_category').value, '가상 시설')
        self.assertEqual(app.text_input(key='management_agency').value, '운영센터')

    def test_status_defaults_to_korean_today_plus_minus_fifteen_days(self):
        today = date(2026, 10, 26)
        with patch.object(status, '_today_kst', return_value=today, create=True):
            app = self.page('status_page', module='status')
        self.assertEqual(app.date_input(key='status_start').value, today - timedelta(days=15))
        self.assertEqual(app.date_input(key='status_end').value, today + timedelta(days=15))
        self.assertTrue(all('2026-10-11' <= value <= '2026-11-10'
                            for value in app.session_state['status_source']['개찰일']))
        self.assertIn('낙찰 판정 정보', [item.label for item in app.expander])

    def test_status_download_is_deferred_and_evidence_does_not_query_or_write(self):
        today = date(2026, 10, 20)
        with patch.object(status, '_today_kst', return_value=today, create=True), \
                patch.object(status, 'csv_bytes', side_effect=AssertionError('다운로드 전 생성 금지')):
            app = self.page('status_page', module='status')
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        self.assertIn('status_download', [item.key for item in app.get('download_button')])
        evidence = getattr(status, 'award_evidence', None)
        self.assertTrue(callable(evidence))
        rows = evidence(app.session_state['status_source'], app.session_state['status_context'], 'DEMO-009')
        self.assertIn('샘플 낙찰', str(rows))
        self.assertIn('가상', str(rows))
        with patch.object(store, 'notices', side_effect=AssertionError('상세 펼침은 재조회하지 않습니다.')), \
                patch.object(store, 'submissions', side_effect=AssertionError('상세 펼침은 재조회하지 않습니다.')), \
                patch.object(store, 'results', side_effect=AssertionError('상세 펼침은 재조회하지 않습니다.')):
            app.session_state['status_evidence'] = True
            app.session_state['status_evidence_notice'] = 'DEMO-009'
            app.run()
            self.assertFalse(app.exception)
            self.assertIn('status_evidence_notice', [item.key for item in app.selectbox])
            self.assertIn('샘플 낙찰', app.dataframe[-1].value['조회값'].tolist())
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)


if __name__ == '__main__':
    unittest.main()
