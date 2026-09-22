"""User journeys, with a separate Streamlit session for each visitor."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"
PAGES = ["category", "data_upload", "integrated_bids", "bid_award_search", "recommend_price", "daily_recommend", "my_bid_manage", "my_bid_status", "g2b_api", "result_manage"]


class AppJourneys(unittest.TestCase):
    def setUp(self):
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            if "store" in app.session_state:
                app.session_state["store"].close()

    def new_app(self):
        self.assertTrue(APP.exists(), "The demo entry point must exist")
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        self.apps.append(app)
        self.assertFalse(app.exception)
        return app

    def login(self, app):
        app.text_input(key="login_username").set_value("admin")
        app.text_input(key="login_password").set_value("admin")
        app.button(key="login_submit").click().run()
        self.assertFalse(app.exception)
        return app

    def test_login_rejects_wrong_password(self):
        app = self.new_app()
        app.text_input(key="login_username").set_value("admin")
        app.text_input(key="login_password").set_value("wrong")
        app.button(key="login_submit").click().run()
        self.assertTrue(app.error)
        self.assertEqual(len(app.radio), 0)

    def test_every_page_renders_without_errors(self):
        app = self.login(self.new_app())
        for page in PAGES:
            with self.subTest(page=page):
                app.button(key=f"menu_open_{page}").click().run()
                self.assertFalse(app.exception)

    def test_original_menu_opens_separate_workspace_tabs(self):
        app = self.login(self.new_app())
        self.assertEqual(len(app.radio), 0)
        self.assertEqual(len([b for b in app.button if str(b.key).startswith("menu_open_")]), 10)
        app.button(key="menu_open_data_upload").click().run()
        self.assertEqual([tab.label for tab in app.tabs], ["과거데이터", "관심공고", "입찰서류함 엑셀", "상세 PDF", "개찰결과", "낙찰정보 엑셀", "결과 상세 PDF"])
        app.button(key="menu_open_daily_recommend").click().run()
        self.assertEqual(app.session_state["open_tabs"], ["data_upload", "daily_recommend"])
        app.button(key="tab_close_daily_recommend").click().run()
        self.assertEqual(app.session_state["active_tab"], "data_upload")
        app.button(key="sidebar_home").click().run()
        self.assertEqual(app.session_state["open_tabs"], [])

    def test_create_notice_and_reset_restores_seed(self):
        app = self.login(self.new_app())
        initial = len(app.session_state["store"].notices())
        app.button(key="menu_open_integrated_bids").click().run()
        app.text_input(key="new_code").set_value("DEMO-TEST-01")
        app.text_input(key="new_title").set_value("가상 체험 공고")
        app.text_input(key="new_agency").set_value("가상 기관")
        app.text_input(key="new_region").set_value("가상 북부")
        app.button(key="create_notice").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["store"].notices()), initial + 1)
        app.button(key="reset_samples").click().run()
        self.assertEqual(len(app.session_state["store"].notices()), initial)
        self.assertFalse(app.session_state["store"].notices(query="DEMO-TEST-01"))

    def test_visitors_and_logout_are_isolated(self):
        first = self.login(self.new_app())
        store = first.session_state["store"]
        count = len(store.notices())
        store.delete_notice(store.notices()[0]["id"])
        second = self.login(self.new_app())
        self.assertEqual(len(second.session_state["store"].notices()), count)
        self.assertEqual(len(first.session_state["store"].notices()), count - 1)
        first.button(key="logout").click().run()
        self.assertEqual(len(first.radio), 0)
        self.login(first)
        self.assertEqual(len(first.session_state["store"].notices()), count)

    def test_notice_edit_search_and_delete(self):
        app = self.login(self.new_app())
        row = app.session_state["store"].notices()[0]
        app.button(key="menu_open_integrated_bids").click().run()
        app.text_input(key=f"edit_{row['id']}_title").set_value("가상 화면 수정 검증")
        app.button(key="update_notice").click().run()
        self.assertEqual(app.session_state["store"].get_notice(row["id"])["title"], "가상 화면 수정 검증")
        app.text_input(key="notice_search").set_value("가상 화면 수정 검증").run()
        app.checkbox(key=f"delete_confirm_{row['id']}").set_value(True).run()
        app.button(key="delete_notice").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["store"].notices(query="가상 화면 수정 검증"))

    def test_analysis_and_api_are_explicit_samples(self):
        app = self.login(self.new_app())
        app.button(key="menu_open_recommend_price").click().run()
        self.assertTrue(any("샘플" in str(item.value) for item in app.info))
        app.button(key="menu_open_g2b_api").click().run()
        app.selectbox(key="api_scenario").set_value("오류").run()
        app.button(key="api_preview").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)

    def test_empty_workspace_still_renders_all_pages(self):
        app = self.login(self.new_app())
        store = app.session_state["store"]
        for row in store.notices():
            store.delete_notice(row["id"])
        for category in store.categories():
            store.delete_category(category)
        for page in PAGES:
            with self.subTest(page=page):
                app.button(key=f"menu_open_{page}").click().run()
                self.assertFalse(app.exception)

    def test_deleting_result_clears_its_edit_form(self):
        app = self.login(self.new_app())
        saved = app.session_state["store"].results()[0]
        notice_id = saved["notice_id"]
        app.button(key="menu_open_result_manage").click().run()
        app.selectbox(key="result_notice").set_value(notice_id).run()
        app.checkbox(key=f"result_confirm_{notice_id}").set_value(True).run()
        next(button for button in app.button if button.label == "결과 삭제").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any(row["notice_id"] == notice_id for row in app.session_state["store"].results()))
        self.assertEqual(app.number_input(key=f"result_{notice_id}_amount").value, 0)
        self.assertEqual(app.text_input(key=f"result_{notice_id}_note").value, "")


if __name__ == "__main__":
    unittest.main()
