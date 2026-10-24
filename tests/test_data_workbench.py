"""관심공고 등록 → 개찰일 조회 → 계산 이동 계약."""
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class DataWorkbenchJourneys(unittest.TestCase):
    def page(self, name):
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.store import DemoStore\n"
            "from demo import data_pages\n"
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            f"page = '{name}'\n"
            "if st.session_state.get('active_tab') == 'daily_notices': page = 'daily_notices'\n"
            "getattr(data_pages, page)(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def test_interest_upload_is_first_and_sample_keeps_duplicate_guard(self):
        app = self.page('uploads')
        self.assertEqual([tab.label for tab in app.tabs], [
            '관심공고', '입찰서류함 엑셀', '상세 PDF', '과거데이터', '개찰결과',
            '낙찰정보 엑셀', '결과 상세 PDF',
        ])
        count = len(app.session_state['store'].notices())
        app.button(key='current_excel_load_sample').click().run()
        app.button(key='current_excel_register').click().run()
        self.assertEqual(len(app.session_state['store'].notices()), count + 2)
        app.button(key='current_excel_register').click().run()
        history = app.session_state['upload_history'][0]
        self.assertEqual((history['신규 등록'], history['중복 스킵']), (0, 2))
        self.assertFalse(app.exception)

    def test_registered_interest_opens_its_opening_date_without_extra_search(self):
        app = self.page('uploads')
        self.assertFalse(any(button.label == '등록 공고 조회' for button in app.button))
        app.button(key='current_excel_load_sample').click().run()
        app.button(key='current_excel_register').click().run()
        self.assertIn('current_excel_open_notices', [button.key for button in app.button])
        button = app.button(key='current_excel_open_notices')
        self.assertEqual(button.label, '등록 공고 조회')
        with patch('streamlit.elements.lib.policies._shown_default_value_warning', False):
            with self.assertNoLogs('streamlit.elements.lib.policies', level='WARNING'):
                button.click().run()
        self.assertEqual(app.session_state['active_tab'], 'daily_notices')
        self.assertEqual(app.date_input(key='daily_notices_date').value, date.today())
        self.assertEqual(app.session_state['daily_notices_query'], date.today().isoformat())
        codes = set(app.dataframe[0].value['공고번호'])
        self.assertTrue({'DEMO-CURRENT_EXCEL-001', 'DEMO-CURRENT_EXCEL-002'} <= codes)
        self.assertFalse(app.exception)

    def test_daily_list_and_execution_panel_keep_only_work_fields(self):
        app = self.page('daily_notices')
        row = app.session_state['store'].notices()[0]
        app.session_state['demo_recommendations'] = {row['id']: {'amount': 22000000}}
        app.button(key='daily_notices_search').click().run()
        self.assertEqual(list(app.dataframe[0].value.columns), [
            '선택', '공고번호', '공고명', '기초금액', '개찰일', '계산 이력',
        ])
        self.assertEqual(app.dataframe[0].value.iloc[0]['계산 이력'], '저장된 계산 있음')
        list_columns = [column for column in app.get('column') if len(column.dataframe)]
        action_columns = [column for column in app.get('column')
                          if any(button.key == 'daily_notices_recommend' for button in column.button)]
        self.assertEqual(len(list_columns), 1)
        self.assertEqual(len(action_columns), 1)
        self.assertGreater(list_columns[0].weight, action_columns[0].weight)
        self.assertTrue(app.button(key='daily_notices_delete').disabled)
        app.checkbox(key='daily_notices_select_all').set_value(True).run()
        self.assertTrue(any(caption.value == '선택 1건' for caption in app.caption))
        self.assertFalse(app.button(key='daily_notices_delete').disabled)
        app.button(key='daily_notices_recommend').click().run()
        self.assertEqual(app.session_state['active_tab'], 'daily_recommend')
        self.assertEqual(app.session_state['daily_requested_date'], date.fromisoformat(row['deadline']))
        self.assertFalse(app.exception)

    def test_daily_query_date_survives_calculation_round_trip_in_main_app(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'),
                                default_timeout=20).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        app.text_input(key='login_username').set_value('admin')
        app.text_input(key='login_password').set_value('admin')
        app.session_state['schedule_show_all'] = True
        app.button(key='login_submit').click().run()
        opening = date(2026, 10, 23)
        app.button(key=f'home_day_notices_{opening.isoformat()}').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.date_input(key='daily_notices_date').value, opening)
        codes = set(app.dataframe[0].value['공고번호'])
        app.button(key='daily_notices_recommend').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['active_tab'], 'daily_recommend')
        self.assertNotIn('daily_notices_date', app.session_state)
        self.assertEqual(app.session_state['daily_notices_query'], opening.isoformat())
        with patch('streamlit.elements.lib.policies._shown_default_value_warning', False):
            with self.assertNoLogs('streamlit.elements.lib.policies', level='WARNING'):
                app.button(key='menu_open_daily_notices').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.date_input(key='daily_notices_date').value, opening)
        self.assertEqual(app.session_state['daily_notices_query'], opening.isoformat())
        self.assertEqual(set(app.dataframe[0].value['공고번호']), codes)
        self.assertEqual(set(app.dataframe[0].value['개찰일']), {opening.isoformat()})

    def test_integrated_details_start_collapsed(self):
        app = self.page('integrated')
        self.assertFalse(app.expander[0].proto.expanded)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
