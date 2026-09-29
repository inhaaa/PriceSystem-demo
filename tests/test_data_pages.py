"""자료 등록·조회와 개찰일별 공고관리의 가상 세션 회귀 확인."""
import csv
import io
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo import data_pages
from demo.store import DemoStore


class DataPageJourneys(unittest.TestCase):
    def page(self, name, empty=False):
        empty_setup = (
            "if 'emptied' not in st.session_state:\n"
            "    for row in st.session_state['store'].notices(): st.session_state['store'].delete_notice(row['id'])\n"
            "    for name in st.session_state['store'].categories(): st.session_state['store'].delete_category(name)\n"
            "    st.session_state['emptied'] = True\n"
        ) if empty else ""
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.store import DemoStore\n"
            "from demo import data_pages\n"
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            + empty_setup + f"getattr(data_pages, st.session_state.get('data_test_page', '{name}'))(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.addCleanup(lambda: app.session_state['store'].close() if 'store' in app.session_state else None)
        self.assertFalse(app.exception)
        return app

    def new_store(self):
        store = DemoStore()
        self.addCleanup(store.close)
        return store

    def test_category_description_survives_create_and_rename(self):
        app = self.page('categories')
        app.text_input(key='category_name').set_value('가상 새 분야')
        app.text_input(key='category_description').set_value('직접 작성한 가상 설명')
        app.button(key='category_create').click().run()
        self.assertIn('가상 새 분야', app.session_state['store'].categories())
        app.text_input(key='category_edit_가상 새 분야').set_value('가상 변경 분야')
        app.button(key='category_update_가상 새 분야').click().run()
        self.assertEqual(app.session_state['category_descriptions']['가상 변경 분야'], '직접 작성한 가상 설명')
        self.assertFalse(app.exception)

    def test_integrated_is_read_only_search_list_and_details(self):
        app = self.page('integrated')
        store = app.session_state['store']
        row = store.notices()[0]
        app.text_input(key='notice_search').set_value(row['code']).run()
        self.assertEqual(list(app.dataframe[0].value['공고번호']), [row['code']])
        self.assertEqual([widget.key for widget in app.text_input], ['notice_search'])
        self.assertEqual(len(app.button), 0)
        self.assertEqual(len(app.json), 0)
        self.assertFalse(any('출처' in item.value or '충돌' in item.value for item in app.markdown))
        self.assertFalse(any('삭제' in item.label or '등록' in item.label or '수정' in item.label for item in app.expander))
        self.assertFalse(app.exception)

    def test_original_upload_tabs_and_simple_sample_registration(self):
        app = self.page('uploads')
        self.assertEqual([tab.label for tab in app.tabs], ['과거데이터', '관심공고', '입찰서류함 엑셀', '상세 PDF', '개찰결과', '낙찰정보 엑셀', '결과 상세 PDF'])
        count = len(app.session_state['store'].notices())
        app.button(key='current_excel_load_sample').click().run()
        self.assertTrue(any('선택 등록' in button.label for button in app.button))
        self.assertTrue(any('실제 파일' in item.value and '읽지 않습니다' in item.value for item in app.caption))
        self.assertFalse(any('매핑' in item.label for item in app.expander))
        self.assertFalse(any('자동' in item.label for item in app.checkbox))
        for frame in app.dataframe:
            self.assertFalse({'표준 컬럼', '분류 근거', '매핑된 원본 컬럼'} & set(frame.value.columns))
        app.button(key='current_excel_register').click().run()
        self.assertEqual(len(app.session_state['store'].notices()), count + 2)
        self.assertEqual(app.session_state['upload_history'][0]['신규 등록'], 2)
        self.assertFalse(app.exception)

    def test_query_keeps_search_and_public_detail_tabs(self):
        app = self.page('query')
        row = app.session_state['store'].notices()[0]
        app.text_input(key='query_bid_no').set_value(row['code'])
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 1건')
        self.assertEqual([tab.label for tab in app.tabs], ['공고 정보', '연결 PDF', '추천 결과'])
        self.assertEqual({widget.key for widget in app.text_input}, {'query_title', 'query_bid_no'})
        self.assertIn('1순위투찰금액', app.dataframe[0].value.columns)
        self.assertNotIn('분류 근거', app.dataframe[0].value.columns)
        self.assertEqual(len(app.json), 0)
        self.assertFalse(app.exception)

    def test_empty_workspace_keeps_each_data_page_available(self):
        for name in ('categories', 'uploads', 'integrated', 'query', 'daily_notices'):
            with self.subTest(page=name):
                self.assertFalse(self.page(name, empty=True).exception)

    def test_query_csv_neutralizes_user_spreadsheet_formulas(self):
        app = self.page('query')
        store = app.session_state['store']
        row = store.notices()[0]
        store.save_notice({**row, 'title': '=1+1'}, row['id'])
        with patch('demo.data_pages.st.download_button', return_value=False) as download:
            app.run()
        exported = list(csv.DictReader(io.StringIO(download.call_args.args[1].decode('utf-8-sig'))))
        self.assertEqual(exported[0]['공고명'], "'=1+1")
        self.assertFalse(app.exception)

    def test_historical_upload_has_completed_status_and_is_searchable(self):
        app = self.page('uploads')
        app.button(key='historical_load_sample').click().run()
        app.button(key='historical_register').click().run()
        self.assertEqual({row['status'] for row in app.session_state['store'].notices(query='DEMO-HISTORICAL-')}, {'완료'})
        app.session_state['data_test_page'] = 'integrated'
        app.run()
        app.text_input(key='notice_search').set_value('DEMO-HISTORICAL-').run()
        self.assertEqual(len(app.dataframe[0].value), 2)
        self.assertFalse(app.exception)

    def test_pdf_upload_counts_selected_files_once(self):
        app = self.page('uploads')
        app.button(key='current_pdf_load_sample').click().run()
        app.checkbox(key='current_pdf_link_confirm').set_value(True).run()
        app.button(key='current_pdf_register').click().run()
        result = app.session_state['upload_history'][0]
        self.assertEqual((result['전체 행 수'], result['신규 등록'], result['중복 스킵']), (1, 1, 0))
        app.button(key='current_pdf_register').click().run()
        result = app.session_state['upload_history'][0]
        self.assertEqual((result['전체 행 수'], result['신규 등록'], result['중복 스킵']), (1, 0, 1))
        self.assertFalse(app.exception)

    def test_daily_date_query_select_delete_and_cancel(self):
        app = self.page('daily_notices')
        store = app.session_state['store']
        row = store.notices()[0]
        self.assertEqual(len(app.dataframe), 0)
        self.assertEqual([item.key for item in app.date_input], ['daily_notices_date'])
        app.button(key='daily_notices_search').click().run()
        self.assertEqual(list(app.dataframe[0].value['공고번호']), [row['code']])
        self.assertTrue(app.button(key='daily_notices_delete').disabled)
        app.checkbox(key='daily_notices_select_all').set_value(True).run()
        app.button(key='daily_notices_delete').click().run()
        self.assertTrue(app.button(key='daily_notices_confirm').disabled)
        app.selectbox(key='daily_notices_reason').set_value('기타').run()
        self.assertTrue(app.button(key='daily_notices_confirm').disabled)
        app.text_input(key='daily_notices_other_reason').set_value('체험 완료').run()
        self.assertFalse(app.button(key='daily_notices_confirm').disabled)
        app.button(key='daily_notices_cancel').click().run()
        self.assertFalse(any(button.key == 'daily_notices_confirm' for button in app.button))
        self.assertIsNotNone(store.get_notice(row['id']))
        app.button(key='daily_notices_delete').click().run()
        self.assertTrue(app.button(key='daily_notices_confirm').disabled)
        app.selectbox(key='daily_notices_reason').set_value('참여하지 않음').run()
        app.button(key='daily_notices_confirm').click().run()
        self.assertFalse(any(item['id'] == row['id'] for item in store.notices()))
        self.assertEqual(app.session_state['notice_archive'][0]['notice']['code'], row['code'])
        self.assertFalse(app.exception)

    def test_daily_calculation_history_requires_acknowledgement(self):
        app = self.page('daily_notices')
        row = app.session_state['store'].notices()[0]
        app.session_state['demo_recommendations'] = {row['id']: {'notice_id': row['id'], 'amount': 22000000}}
        app.button(key='daily_notices_search').click().run()
        app.checkbox(key='daily_notices_select_all').set_value(True).run()
        app.button(key='daily_notices_delete').click().run()
        app.selectbox(key='daily_notices_reason').set_value('중복 등록').run()
        self.assertTrue(app.button(key='daily_notices_confirm').disabled)
        app.checkbox(key='daily_notices_ack').set_value(True).run()
        self.assertFalse(app.button(key='daily_notices_confirm').disabled)
        app.date_input(key='daily_notices_date').set_value(date.fromisoformat(row['deadline']) + timedelta(days=1)).run()
        self.assertFalse(any(button.key == 'daily_notices_confirm' for button in app.button))
        self.assertEqual(len(app.dataframe), 0)
        self.assertFalse(app.exception)

    def test_daily_selection_change_invalidates_confirmation(self):
        app = self.page('daily_notices')
        app.button(key='daily_notices_search').click().run()
        app.checkbox(key='daily_notices_select_all').set_value(True).run()
        app.button(key='daily_notices_delete').click().run()
        app.checkbox(key='daily_notices_select_all').set_value(False).run()
        self.assertFalse(any(button.key == 'daily_notices_confirm' for button in app.button))
        self.assertFalse(app.exception)

    def test_daily_moves_to_recommendations_for_the_selected_date(self):
        app = self.page('daily_notices')
        opening = app.date_input(key='daily_notices_date').value
        app.button(key='daily_notices_search').click().run()
        app.button(key='daily_notices_recommend').click().run()
        self.assertEqual(app.session_state['daily_requested_date'], opening)
        self.assertEqual(app.session_state['active_tab'], 'daily_recommend')
        self.assertFalse(app.exception)

    def test_archived_sample_registration_restores_linked_records(self):
        app = self.page('uploads')
        app.button(key='current_excel_load_sample').click().run()
        app.button(key='current_excel_register').click().run()
        store = app.session_state['store']
        row = store.notices(query='DEMO-CURRENT_EXCEL-001')[0]
        store.save_result({'notice_id': row['id'], 'outcome': '검토중', 'amount': 21000000, 'note': '가상 복원 결과'})
        state = {}
        with patch.object(data_pages.st, 'session_state', state):
            data_pages._archive_notice(store, row)
        app.session_state['notice_archive'] = state['notice_archive']
        app.button(key='current_excel_register').click().run()
        restored = store.notices(query=row['code'])[0]
        self.assertNotEqual(restored['id'], row['id'])
        self.assertEqual(next(item for item in store.results() if item['notice_id'] == restored['id'])['note'], '가상 복원 결과')
        self.assertEqual(app.session_state['notice_archive'], [])
        self.assertFalse(app.exception)

    def test_category_rename_preserves_archived_notice_restore(self):
        app = self.page('categories')
        store = app.session_state['store']
        row = store.notices()[0]
        state = {}
        with patch.object(data_pages.st, 'session_state', state):
            data_pages._archive_notice(store, row)
        app.session_state['notice_archive'] = state['notice_archive']
        app.text_input(key=f"category_edit_{row['category']}").set_value('가상 보관 분류 개명')
        app.button(key=f"category_update_{row['category']}").click().run()
        state['notice_archive'] = app.session_state['notice_archive']
        self.assertEqual(state['notice_archive'][0]['notice']['category'], '가상 보관 분류 개명')
        with patch.object(data_pages.st, 'session_state', state):
            data_pages._restore_notice(store, 0, '가상 보관 분류 개명')
        self.assertEqual(store.notices(query=row['code'])[0]['category'], '가상 보관 분류 개명')
        self.assertFalse(app.exception)

    def test_deleted_category_can_be_replaced_when_restoring(self):
        store = self.new_store()
        row = store.notices()[0]
        store.add_category('가상 삭제 예정 분류')
        store.save_notice({**row, 'category': '가상 삭제 예정 분류'}, row['id'])
        state = {}
        with patch.object(data_pages.st, 'session_state', state):
            data_pages._archive_notice(store, store.get_notice(row['id']))
            store.delete_category('가상 삭제 예정 분류')
            replacement = store.categories()[0]
            data_pages._restore_notice(store, 0, replacement)
        self.assertEqual(store.notices(query=row['code'])[0]['category'], replacement)

    def test_archive_detaches_and_restores_linked_records_and_metadata(self):
        store = self.new_store()
        row, other = store.notices()[-1], store.notices()[0]
        target = row['id']
        store.save_submission({'notice_id': target, 'company': '가상 복원 참가자', 'amount': 21000000, 'status': '작성중', 'memo': ''})
        store.save_result({'notice_id': target, 'outcome': '검토중', 'amount': 21000000, 'note': '가상 복원 결과'})
        count = sum(item['notice_id'] == target for item in store.submissions())
        recommended = {'notice_id': target, 'code': row['code'], 'title': row['title'], 'scenario': '표준', 'amount': 12340000, 'note': '가상 저장 추천'}
        other_recommended = {**recommended, 'notice_id': other['id'], 'code': other['code']}
        state = {
            'demo_recommendations': {target: recommended.copy(), other['id']: other_recommended},
            'demo_primary': {target: '표준'}, 'demo_result_context': {target: {'planned': 777000, 'award': 555000}},
            'pdf_links': {target: ['가상복원.pdf']}, 'recommendation_display': recommended.copy(),
            'daily_results': [recommended.copy(), other_recommended], 'daily_confirmed': (target, other['id']),
            'daily_result_selection': (target, other['id']), f'result_{target}_planned': 777000,
            f'recommendation_{target}_planned': 777000, 'daily_editor_0_True': {'edited_rows': {1: {'선택': False}}},
        }
        with patch.object(data_pages.st, 'session_state', state):
            data_pages._archive_notice(store, row)
            for key in ('demo_recommendations', 'demo_primary', 'demo_result_context'):
                self.assertNotIn(target, state[key])
            self.assertEqual(state['demo_recommendations'][other['id']], other_recommended)
            for key in ('recommendation_display', 'daily_confirmed', f'result_{target}_planned', f'recommendation_{target}_planned', 'daily_editor_0_True'):
                self.assertNotIn(key, state)
            self.assertEqual(state['daily_results'], [other_recommended])
            self.assertEqual(state['daily_result_selection'], (other['id'],))
            fresh_id = store.save_notice({**row, 'code': 'DEMO-AFTER-ARCHIVE', 'title': '가상 새 공고'})
            for key in ('demo_recommendations', 'demo_primary', 'demo_result_context'):
                self.assertNotIn(fresh_id, state[key])
            data_pages._restore_notice(store, 0, row['category'])
        restored = store.notices(query=row['code'])[0]['id']
        self.assertEqual(state['demo_recommendations'][restored], {**recommended, 'notice_id': restored})
        self.assertEqual(state['demo_primary'][restored], '표준')
        self.assertEqual(state['demo_result_context'][restored], {'planned': 777000, 'award': 555000})
        self.assertNotIn(fresh_id, state['demo_result_context'])
        self.assertEqual(sum(item['notice_id'] == restored for item in store.submissions()), count)
        self.assertEqual(next(item for item in store.results() if item['notice_id'] == restored)['note'], '가상 복원 결과')
        self.assertEqual(state['pdf_links'][restored], ['가상복원.pdf'])


if __name__ == '__main__':
    unittest.main()
