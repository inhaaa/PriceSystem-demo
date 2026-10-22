"""투찰 검토함의 공고별 저장·필터·완료 조건을 실제 화면에서 검증한다."""
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo import data_pages


ROOT = Path(__file__).resolve().parents[1]
CHECKS = ('eligibility', 'documents', 'amount', 'schedule')


class ReviewPageJourneys(unittest.TestCase):
    def setUp(self):
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            if 'store' in app.session_state:
                app.session_state['store'].close()

    def page(self):
        app = AppTest.from_string(
            'import streamlit as st\n'
            'from demo.store import DemoStore\n'
            'from demo.bid_pages import review_page\n'
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            "review_page(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.apps.append(app)
        self.assertFalse(app.exception)
        return app

    def test_initial_checklist_and_status_counts(self):
        app = self.page()
        self.assertEqual({item.label: item.value for item in app.metric}, {
            '검토대기': '12건', '준비중': '0건', '검토완료': '0건', '보류': '0건',
        })
        self.assertEqual(len(app.checkbox), 4)
        self.assertTrue(all(not item.value for item in app.checkbox))
        self.assertEqual(len(app.dataframe[0].value), 12)

    def test_saves_checks_status_and_note_independently_for_each_notice(self):
        app = self.page()
        before_submissions = app.session_state['store'].submissions()
        app.checkbox(key='review_1_eligibility').set_value(True)
        app.checkbox(key='review_1_documents').set_value(True)
        app.selectbox(key='review_1_status').set_value('준비중')
        app.text_area(key='review_1_note').set_value('필수 서류 확인 후 금액 검토 예정')
        app.button(key='review_save_1').click().run()
        self.assertFalse(app.exception)
        saved = app.session_state['demo_reviews'][1]
        self.assertEqual(saved['status'], '준비중')
        self.assertTrue(saved['checks']['documents'])
        self.assertFalse(saved['checks']['amount'])
        self.assertEqual(saved['note'], '필수 서류 확인 후 금액 검토 예정')
        self.assertEqual({item.label: item.value for item in app.metric}['준비중'], '1건')
        app.selectbox(key='review_notice').select_index(1).run()
        self.assertTrue(all(not item.value for item in app.checkbox))
        self.assertEqual(app.text_area[0].value, '')
        app.selectbox(key='review_notice').select_index(0).run()
        self.assertTrue(app.checkbox(key='review_1_documents').value)
        self.assertEqual(app.text_area[0].value, saved['note'])
        self.assertEqual(app.session_state['store'].submissions(), before_submissions)

    def test_completion_requires_all_checks_and_preserves_previous_save(self):
        app = self.page()
        app.selectbox(key='review_1_status').set_value('보류')
        app.text_area(key='review_1_note').set_value('금액 검토 대기')
        app.button(key='review_save_1').click().run()
        app.selectbox(key='review_1_status').set_value('검토완료')
        app.button(key='review_save_1').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertEqual(app.session_state['demo_reviews'][1]['status'], '보류')
        for key in CHECKS:
            app.checkbox(key=f'review_1_{key}').set_value(True)
        app.button(key='review_save_1').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['demo_reviews'][1]['status'], '검토완료')
        self.assertEqual({item.label: item.value for item in app.metric}['검토완료'], '1건')
        app.checkbox(key='review_1_amount').set_value(False)
        app.button(key='review_save_1').click().run()
        self.assertTrue(app.error)
        self.assertTrue(app.session_state['demo_reviews'][1]['checks']['amount'])

    def test_keyword_category_and_status_filters_include_empty_results(self):
        app = self.page()
        app.selectbox(key='review_1_status').set_value('준비중')
        app.button(key='review_save_1').click().run()
        app.selectbox(key='review_filter_status').set_value('준비중').run()
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), ['DEMO-001'])
        app.selectbox(key='review_category').set_value('가상 물품').run()
        self.assertFalse(app.dataframe)
        self.assertFalse(app.checkbox)
        self.assertTrue(app.info)
        app.selectbox(key='review_filter_status').set_value('전체')
        app.selectbox(key='review_category').set_value('전체')
        app.text_input(key='review_keyword').set_value('DEMO-002').run()
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), ['DEMO-002'])
        self.assertEqual(len(app.checkbox), 4)
        app.text_input(key='review_keyword').set_value('산책로').run()
        self.assertEqual(app.dataframe[0].value['공고번호'].tolist(), ['DEMO-001'])
        self.assertFalse(app.exception)

    def test_saving_status_under_a_filter_removes_only_that_notice(self):
        app = self.page()
        app.selectbox(key='review_filter_status').set_value('검토대기').run()
        app.selectbox(key='review_1_status').set_value('준비중')
        app.button(key='review_save_1').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 11)
        self.assertNotIn('DEMO-001', app.dataframe[0].value['공고번호'].tolist())
        self.assertEqual(app.selectbox(key='review_notice').value, 2)

    def test_empty_store_and_session_isolation(self):
        first = self.page()
        first.selectbox(key='review_1_status').set_value('보류')
        first.button(key='review_save_1').click().run()
        second = self.page()
        self.assertEqual(second.selectbox(key='review_1_status').value, '검토대기')
        self.assertFalse(second.session_state['demo_reviews'])
        store = first.session_state['store']
        for row in store.notices():
            store.delete_notice(row['id'])
        first.run()
        self.assertFalse(first.exception)
        self.assertFalse(first.checkbox)
        self.assertTrue(first.info)
        self.assertTrue(all(item.value == '0건' for item in first.metric))

    def test_notice_text_is_escaped_in_detail_panel(self):
        app = self.page()
        store = app.session_state['store']
        row = store.get_notice(1)
        store.save_notice({**row, 'title': '<img src=x onerror=alert(1)>가상 공고'}, 1)
        app.run()
        self.assertFalse(app.exception)
        markup = '\n'.join(item.value for item in app.markdown)
        self.assertIn('&lt;img', markup)
        self.assertNotIn('<img src=x', markup)

    def test_archive_and_restore_keep_review_attached_to_restored_notice(self):
        app = self.page()
        app.checkbox(key='review_1_documents').set_value(True)
        app.selectbox(key='review_1_status').set_value('보류')
        app.text_area(key='review_1_note').set_value('가상 검토 보관')
        app.button(key='review_save_1').click().run()
        store = app.session_state['store']
        row = store.get_notice(1)
        review = app.session_state['demo_reviews'][1]
        state = {'demo_reviews': {1: review}, 'review_1_note': '가상 검토 보관'}
        with patch.object(data_pages.st, 'session_state', state):
            data_pages._archive_notice(store, row)
            self.assertNotIn(1, state['demo_reviews'])
            self.assertNotIn('review_1_note', state)
            data_pages._restore_notice(store, 0, row['category'])
        restored = store.notices(query=row['code'])[0]
        self.assertNotEqual(restored['id'], 1)
        self.assertEqual(state['demo_reviews'][restored['id']], review)


if __name__ == '__main__':
    unittest.main()
