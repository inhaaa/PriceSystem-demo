"""원본 자료 화면 구성과 가상 세션 CRUD 회귀 확인."""
import unittest
import csv
import io
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


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

    def test_notice_create_edit_archive_restore(self):
        app = self.page('integrated')
        store = app.session_state['store']
        initial = len(store.notices())
        app.text_input(key='new_code').set_value('DEMO-FORM-01')
        app.text_input(key='new_title').set_value('가상 복원 확인 공고')
        app.text_input(key='new_agency').set_value('가상 자료센터')
        app.text_input(key='new_region').set_value('가상 북부')
        app.button(key='create_notice').click().run()
        self.assertEqual(len(store.notices()), initial + 1)
        app.text_input(key='notice_search').set_value('DEMO-FORM-01').run()
        row = store.notices(query='DEMO-FORM-01')[0]
        app.text_input(key=f"edit_{row['id']}_title").set_value('가상 수정 공고')
        app.button(key='update_notice').click().run()
        self.assertEqual(store.get_notice(row['id'])['title'], '가상 수정 공고')
        app.checkbox(key=f"delete_confirm_{row['id']}").set_value(True).run()
        app.button(key='delete_notice').click().run()
        self.assertEqual(len(store.notices()), initial)
        app.checkbox(key='restore_acknowledged').set_value(True).run()
        app.button(key='restore_notice').click().run()
        self.assertEqual(store.notices(query='DEMO-FORM-01')[0]['title'], '가상 수정 공고')
        self.assertFalse(app.exception)

    def test_original_upload_tabs_and_sample_registration(self):
        app = self.page('uploads')
        self.assertEqual([tab.label for tab in app.tabs], ['과거데이터', '관심공고', '입찰서류함 엑셀', '상세 PDF', '개찰결과', '낙찰정보 엑셀', '결과 상세 PDF'])
        count = len(app.session_state['store'].notices())
        app.button(key='current_excel_load_sample').click().run()
        self.assertTrue(any('선택 등록' in button.label for button in app.button))
        app.button(key='current_excel_register').click().run()
        self.assertEqual(len(app.session_state['store'].notices()), count + 2)
        self.assertEqual(app.session_state['upload_history'][0]['신규 등록'], 2)
        self.assertFalse(app.exception)

    def test_query_filters_and_original_detail_tabs(self):
        app = self.page('query')
        row = app.session_state['store'].notices()[0]
        app.text_input(key='query_bid_no').set_value(row['code'])
        app.button(key='query_submit').click().run()
        self.assertEqual(app.metric[0].value, '총 1건')
        self.assertEqual([tab.label for tab in app.tabs], ['카테고리', '업로드 출처', '연결 PDF', '추천 결과'])
        self.assertIn('번호(No)', app.dataframe[0].value.columns)
        self.assertIn('1순위투찰금액', app.dataframe[0].value.columns)
        self.assertFalse(app.exception)

    def test_archive_restores_all_linked_records(self):
        app = self.page('integrated')
        store = app.session_state['store']
        row = store.notices()[0]
        store.save_submission({'notice_id': row['id'], 'company': '가상 복원 참가자', 'amount': 21000000, 'status': '작성중', 'memo': ''})
        store.save_result({'notice_id': row['id'], 'outcome': '검토중', 'amount': 21000000, 'note': '가상 복원 결과'})
        app.session_state['pdf_links'] = {row['id']: ['가상복원.pdf']}
        count = sum(item['notice_id'] == row['id'] for item in store.submissions())
        app.checkbox(key=f"delete_confirm_{row['id']}").set_value(True).run()
        app.button(key='delete_notice').click().run()
        app.checkbox(key='restore_acknowledged').set_value(True).run()
        app.button(key='restore_notice').click().run()
        restored = next(item for item in store.notices() if item['code'] == row['code'])
        self.assertEqual(sum(item['notice_id'] == restored['id'] for item in store.submissions()), count)
        self.assertEqual(next(item for item in store.results() if item['notice_id'] == restored['id'])['note'], '가상 복원 결과')
        self.assertEqual(app.session_state['pdf_links'][restored['id']], ['가상복원.pdf'])
        self.assertFalse(app.exception)

    def test_empty_workspace_keeps_each_data_page_available(self):
        for name in ('categories', 'uploads', 'integrated', 'query'):
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

    def test_category_rename_preserves_archived_notice_restore(self):
        app = self.page('integrated')
        store = app.session_state['store']
        row = store.notices()[0]
        app.checkbox(key=f"delete_confirm_{row['id']}").set_value(True).run()
        app.button(key='delete_notice').click().run()
        app.session_state['data_test_page'] = 'categories'
        app.run()
        app.text_input(key=f"category_edit_{row['category']}").set_value('가상 보관 분류 개명')
        app.button(key=f"category_update_{row['category']}").click().run()
        self.assertEqual(app.session_state['notice_archive'][0]['notice']['category'], '가상 보관 분류 개명')
        app.session_state['data_test_page'] = 'integrated'
        app.run()
        app.checkbox(key='restore_acknowledged').set_value(True).run()
        app.button(key='restore_notice').click().run()
        self.assertEqual(store.notices(query=row['code'])[0]['category'], '가상 보관 분류 개명')
        self.assertFalse(app.exception)

    def test_deleted_category_can_be_replaced_when_restoring(self):
        app = self.page('integrated')
        store = app.session_state['store']
        row = store.notices()[0]
        store.add_category('가상 삭제 예정 분류')
        store.save_notice({**row, 'category': '가상 삭제 예정 분류'}, row['id'])
        app.run()
        app.checkbox(key=f"delete_confirm_{row['id']}").set_value(True).run()
        app.button(key='delete_notice').click().run()
        store.delete_category('가상 삭제 예정 분류')
        app.run()
        self.assertTrue(any(item.key == 'restore_category' for item in app.selectbox))
        replacement = store.categories()[0]
        app.selectbox(key='restore_category').set_value(replacement).run()
        app.checkbox(key='restore_acknowledged').set_value(True).run()
        app.button(key='restore_notice').click().run()
        self.assertEqual(store.notices(query=row['code'])[0]['category'], replacement)
        self.assertFalse(app.exception)

    def test_historical_upload_appears_in_historical_filter(self):
        app = self.page('uploads')
        app.button(key='historical_load_sample').click().run()
        app.button(key='historical_register').click().run()
        app.session_state['data_test_page'] = 'integrated'
        app.run()
        app.text_input(key='notice_search').set_value('DEMO-HISTORICAL-').run()
        app.selectbox(key='notice_status').set_value('HISTORICAL').run()
        self.assertTrue(any(len(frame.value) == 2 and '공고번호' in frame.value.columns for frame in app.dataframe))
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

    def test_archive_detaches_metadata_and_restores_it_under_new_notice_id(self):
        app = self.page('integrated')
        store = app.session_state['store']
        row, other = store.notices()[-1], store.notices()[0]
        target = row['id']
        app.selectbox(key='notice_detail').set_value(target).run()
        recommended = {'notice_id': target, 'code': row['code'], 'title': row['title'], 'scenario': '표준', 'amount': 12340000, 'note': '가상 저장 추천'}
        other_recommended = {**recommended, 'notice_id': other['id'], 'code': other['code']}
        app.session_state['demo_recommendations'] = {target: recommended.copy(), other['id']: other_recommended}
        app.session_state['demo_primary'] = {target: '표준'}
        app.session_state['demo_result_context'] = {target: {'planned': 777000, 'award': 555000}}
        app.session_state['recommendation_display'] = recommended.copy()
        app.session_state['daily_results'] = [recommended.copy(), other_recommended]
        app.session_state['daily_confirmed'] = (target, other['id'])
        app.session_state['daily_result_selection'] = (target, other['id'])
        app.session_state[f'result_{target}_planned'] = 777000
        app.session_state[f'recommendation_{target}_planned'] = 777000
        app.session_state['daily_editor_0_True'] = {'edited_rows': {1: {'선택': False}}}
        app.checkbox(key=f'delete_confirm_{target}').set_value(True).run()
        app.button(key='delete_notice').click().run()
        for key in ('demo_recommendations', 'demo_primary', 'demo_result_context'):
            self.assertNotIn(target, app.session_state[key])
        self.assertEqual(app.session_state['demo_recommendations'][other['id']], other_recommended)
        self.assertNotIn('recommendation_display', app.session_state)
        self.assertEqual(app.session_state['daily_results'], [other_recommended])
        self.assertEqual(app.session_state['daily_result_selection'], (other['id'],))
        self.assertNotIn('daily_confirmed', app.session_state)
        self.assertNotIn(f'result_{target}_planned', app.session_state)
        self.assertNotIn(f'recommendation_{target}_planned', app.session_state)
        self.assertNotIn('daily_editor_0_True', app.session_state)
        fresh_id = store.save_notice({**row, 'code': 'DEMO-AFTER-ARCHIVE', 'title': '가상 새 공고'})
        for key in ('demo_recommendations', 'demo_primary', 'demo_result_context'):
            self.assertNotIn(fresh_id, app.session_state[key])
        app.checkbox(key='restore_acknowledged').set_value(True).run()
        app.button(key='restore_notice').click().run()
        restored = store.notices(query=row['code'])[0]['id']
        self.assertEqual(app.session_state['demo_recommendations'][restored], {**recommended, 'notice_id': restored})
        self.assertEqual(app.session_state['demo_primary'][restored], '표준')
        self.assertEqual(app.session_state['demo_result_context'][restored], {'planned': 777000, 'award': 555000})
        self.assertNotIn(fresh_id, app.session_state['demo_result_context'])
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
