"""운영 조회 조건과 목록 제한을 가상 메모리 데이터로 검증한다."""
from datetime import date, timedelta
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class ProductionDataParityTests(unittest.TestCase):
    def page(self, name):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.store import DemoStore\n"
            "from demo import data_pages\n"
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            f"if st.session_state.get('parity_visible', True): data_pages.{name}(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def test_integrated_status_and_trimmed_keyword_filters_work_together(self):
        app = self.page('integrated')
        store = app.session_state['store']
        app.selectbox(key='notice_status').set_value('완료').run()
        self.assertEqual(set(app.dataframe[0].value['결과 상태']), {'완료'})
        row = store.notices(status='완료')[0]
        app.text_input(key='notice_search').set_value(f"  {row['code'].lower()}  ").run()
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), [row['code']])
        self.assertEqual(len(store.notices()), 12)

    def test_query_agency_region_and_industry_filters_are_combined_on_submit(self):
        app = self.page('query')
        app.text_input(key='query_agency').set_value('  데모 운영  ')
        app.text_input(key='query_region').set_value('동부')
        app.text_input(key='query_license').set_value('물품')
        app.button(key='query_submit').click().run()
        expected = [row['code'] for row in app.session_state['store'].notices()
                    if '동부' in row['region'] and '물품' in row['category']]
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), expected)
        self.assertTrue(all('가상 물품업' == value for value in app.dataframe[0].value['업종']))
        app.text_input(key='query_agency').set_value('일치하지 않는 기관')
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 0건')
        self.assertEqual(len(app.dataframe), 0)
        self.assertFalse(app.exception)

    def test_query_limits_rows_counts_all_matches_and_includes_recommendation_only_on_request(self):
        app = self.page('query')
        self.assertFalse(app.checkbox(key='query_include_recommendation').value)
        self.assertEqual(app.number_input(key='query_limit').value, 1000)
        self.assertNotIn('추천 투찰금액', app.dataframe[0].value.columns)
        row = app.session_state['store'].notices()[0]
        app.session_state['demo_recommendations'] = {row['id']: {'amount': 22000000}}
        app.number_input(key='query_limit').set_value(1)
        app.checkbox(key='query_include_recommendation').set_value(True)
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 12건')
        self.assertEqual(len(app.dataframe[0].value), 1)
        self.assertEqual(app.dataframe[0].value.iloc[0]['추천 투찰금액'], 22000000)
        self.assertEqual(app.dataframe[0].value.iloc[0]['추천 여부'], 'Y')
        self.assertEqual(len(app.session_state['store'].notices()), 12)
        self.assertFalse(app.exception)

    def test_invalid_date_range_preserves_last_valid_query_and_inclusive_boundaries(self):
        app = self.page('query')
        opening = date.fromisoformat(app.session_state['store'].notices()[0]['deadline'])
        app.date_input(key='query_date_from').set_value(opening)
        app.date_input(key='query_date_to').set_value(opening)
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 1건')
        previous = app.dataframe[0].value.copy()
        app.date_input(key='query_date_from').set_value(opening + timedelta(days=1))
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 1건')
        self.assertTrue(previous.equals(app.dataframe[0].value))
        self.assertTrue(any('시작일' in error.value for error in app.error))
        self.assertFalse(app.exception)

    def test_query_controls_and_results_stay_in_sync_after_leaving_and_returning(self):
        app = self.page('query')
        row = app.session_state['store'].notices()[0]
        opening = date.fromisoformat(row['deadline'])
        text_filters = {'query_title': row['title'], 'query_bid_no': row['code'],
                        'query_agency': '일치하지 않는 기관', 'query_region': row['region'],
                        'query_license': '가상 시설업'}
        for key, value in text_filters.items():
            app.text_input(key=key).set_value(value)
        app.selectbox(key='query_category').set_value(row['category'])
        app.date_input(key='query_date_from').set_value(opening)
        app.date_input(key='query_date_to').set_value(opening)
        app.checkbox(key='query_include_recommendation').set_value(True)
        app.number_input(key='query_limit').set_value(5)
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 0건')
        app.session_state['parity_visible'] = False
        app.run()
        self.assertEqual(len(app.text_input), 0)
        app.session_state['parity_visible'] = True
        with patch('streamlit.elements.lib.policies._shown_default_value_warning', False):
            with self.assertNoLogs('streamlit.elements.lib.policies', level='WARNING'):
                app.run()
        self.assertEqual({widget.key: widget.value for widget in app.text_input}, text_filters)
        self.assertEqual(app.selectbox(key='query_category').value, row['category'])
        self.assertEqual(app.date_input(key='query_date_from').value, opening)
        self.assertEqual(app.date_input(key='query_date_to').value, opening)
        self.assertTrue(app.checkbox(key='query_include_recommendation').value)
        self.assertEqual(app.number_input(key='query_limit').value, 5)
        self.assertEqual(app.metric[0].value, '총 0건')
        self.assertFalse(app.exception)

    def test_daily_pages_are_bounded_and_selection_is_cleared_between_pages(self):
        app = self.page('daily_notices')
        store = app.session_state['store']
        row = store.notices()[0]
        for number in range(100):
            store.save_notice({**row, 'code': f'DEMO-PAGE-{number:03d}'})
        app.button(key='daily_notices_search').click().run()
        self.assertEqual(len(app.dataframe[0].value), 100)
        self.assertIn('투찰기록', app.dataframe[0].value.columns)
        self.assertEqual(app.dataframe[0].value.iloc[0]['투찰기록'], '있음')
        self.assertTrue(app.button(key='daily_notices_previous').disabled)
        app.checkbox(key='daily_notices_select_all').set_value(True).run()
        app.button(key='daily_notices_delete').click().run()
        app.button(key='daily_notices_next').click().run()
        self.assertEqual(len(app.dataframe[0].value), 1)
        self.assertFalse(app.checkbox(key='daily_notices_select_all').value)
        self.assertTrue(app.button(key='daily_notices_delete').disabled)
        self.assertTrue(app.button(key='daily_notices_next').disabled)
        self.assertFalse(any(button.key == 'daily_notices_confirm' for button in app.button))
        app.date_input(key='daily_notices_date').set_value(opening := date.fromisoformat(row['deadline']) + timedelta(days=2)).run()
        app.button(key='daily_notices_search').click().run()
        self.assertEqual(app.session_state['daily_notices_page'], 0)
        self.assertEqual(set(app.dataframe[0].value['개찰일']), {opening.isoformat()})
        self.assertEqual(len(store.notices()), 112)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
