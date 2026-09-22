"""Restored bid workflows use only the independent demo store and fixed samples."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


PAGE_FILE = Path(__file__).resolve().parents[1] / "demo" / "bid_pages.py"
PAGES = ("recommendation_page", "daily_page", "management_page", "status_page", "api_page", "results_page")


class BidPageJourneys(unittest.TestCase):
    def setUp(self):
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            if "store" in app.session_state:
                app.session_state["store"].close()

    def page(self, name):
        self.assertTrue(PAGE_FILE.is_file(), "The six original bid screens must have a dedicated demo implementation")
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.store import DemoStore\n"
            f"from demo.bid_pages import {name}\n"
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            f"{name}(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.apps.append(app)
        self.assertFalse(app.exception)
        return app

    def test_all_screens_render_with_seed_and_empty_store(self):
        for name in PAGES:
            with self.subTest(name=name):
                app = self.page(name)
                store = app.session_state["store"]
                for row in store.notices():
                    store.delete_notice(row["id"])
                for category in store.categories():
                    store.delete_category(category)
                app.run()
                self.assertFalse(app.exception)

    def test_daily_requires_sample_confirmation_and_saves_selected_result(self):
        app = self.page("daily_page")
        app.button(key="daily_search").click().run()
        self.assertTrue(app.button(key="daily_calculate").disabled)
        app.button(key="daily_check").click().run()
        self.assertFalse(app.button(key="daily_calculate").disabled)
        app.checkbox(key="daily_auto_save").set_value(False).run()
        app.button(key="daily_calculate").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["daily_results"])
        app.button(key="daily_save_all").click().run()
        self.assertTrue(app.session_state["demo_recommendations"])
        app.checkbox(key="daily_select_all").set_value(False).run()
        self.assertTrue(app.button(key="daily_calculate").disabled)

    def test_recommendation_uses_same_sample_after_input_changes(self):
        app = self.page("recommendation_page")
        app.button(key="recommendation_run").click().run()
        first = app.session_state["recommendation_display"]["amount"]
        app.number_input(key="recommendation_1_base").set_value(500000000)
        app.button(key="recommendation_run").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(first, app.session_state["recommendation_display"]["amount"])
        self.assertTrue(any("고정 샘플" in item.value for item in app.info))

    def test_recommendation_saved_status_describes_the_displayed_sample(self):
        app = self.page("recommendation_page")
        app.button(key="recommendation_run").click().run()
        app.checkbox(key="recommendation_auto_save").set_value(False)
        app.selectbox(key="analysis_scenario").set_value("샘플 B")
        app.button(key="recommendation_run").click().run()
        self.assertEqual("샘플 A", app.session_state["demo_recommendations"][1]["scenario"])
        self.assertEqual("샘플 B", app.session_state["recommendation_display"]["scenario"])
        progress = next(frame.value for frame in app.dataframe if list(frame.value.columns) == ["단계", "상태"])
        self.assertEqual("미저장", progress.loc[progress["단계"] == "결과 저장", "상태"].iloc[0])
        app.button(key="recommendation_save").click().run()
        self.assertFalse(app.exception)
        progress = next(frame.value for frame in app.dataframe if list(frame.value.columns) == ["단계", "상태"])
        self.assertEqual("세션 저장됨", progress.loc[progress["단계"] == "결과 저장", "상태"].iloc[0])

    def test_management_can_save_and_delete_a_submission(self):
        app = self.page("management_page")
        before = len(app.session_state["store"].submissions())
        app.number_input(key="submission_None_amount").set_value(12300000)
        app.button(key="save_submission").click().run()
        self.assertFalse(app.exception)
        records = app.session_state["store"].submissions()
        self.assertEqual(before + 1, len(records))
        saved = records[-1]
        self.assertEqual(12300000, saved["amount"])
        app.selectbox(key="submission_edit").set_value(saved["id"]).run()
        app.checkbox(key=f"submission_confirm_{saved['id']}").set_value(True).run()
        app.button(key="delete_submission").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(before, len(app.session_state["store"].submissions()))

    def test_company_profile_updates_unchanged_new_submission_default(self):
        app = self.page("management_page")
        for company in ["가상 새 기본회사", "가상 다시 변경한 회사"]:
            app.text_input(key="demo_company_name").set_value(company)
            next(button for button in app.button if button.label == "가상 회사 정보 저장").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(company, app.text_input(key="submission_None_company").value)
        app.button(key="save_submission").click().run()
        self.assertEqual(company, app.session_state["store"].submissions()[-1]["company"])

    def test_company_profile_preserves_a_different_submission_draft(self):
        app = self.page("management_page")
        original_records = app.session_state["store"].submissions()
        draft = "가상 직접 입력한 참가회사"
        app.text_input(key="submission_None_company").set_value(draft).run()
        app.text_input(key="demo_company_name").set_value("가상 변경한 기본회사")
        next(button for button in app.button if button.label == "가상 회사 정보 저장").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(draft, app.text_input(key="submission_None_company").value)
        self.assertEqual(original_records, app.session_state["store"].submissions())
        app.button(key="save_submission").click().run()
        self.assertEqual(draft, app.session_state["store"].submissions()[-1]["company"])

    def test_result_tabs_keep_crud_and_explicit_sample_choice(self):
        app = self.page("results_page")
        self.assertEqual(
            ["결과 미회수 공고", "개찰결과 엑셀", "개찰결과 PDF", "수기 입력 및 비교", "추천 결과 비교/대표 지정"],
            [tab.label for tab in app.tabs],
        )
        app.number_input(key="result_1_amount").set_value(21000000)
        app.text_input(key="result_1_note").set_value("가상 결과 수정")
        app.button(key="save_result").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(21000000, app.session_state["store"].results()[0]["amount"])
        app.checkbox(key="result_confirm_1").set_value(True).run()
        app.button(key="delete_result").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(0, app.number_input(key="result_1_amount").value)
        self.assertEqual("", app.text_input(key="result_1_note").value)
        app.selectbox(key="result_sample_choice").set_value("샘플 B").run()
        app.checkbox(key="result_primary_confirm").set_value(True).run()
        app.button(key="result_set_primary").click().run()
        self.assertEqual("샘플 B", app.session_state["demo_primary"][1])

    def test_api_sample_bulk_apply_is_idempotent_and_error_is_visible(self):
        app = self.page("api_page")
        before = len(app.session_state["store"].notices())
        app.button(key="api_preview").click().run()
        app.button(key="api_apply").click().run()
        self.assertEqual(before + 2, len(app.session_state["store"].notices()))
        app.button(key="api_apply").click().run()
        self.assertEqual(before + 2, len(app.session_state["store"].notices()))
        app.selectbox(key="api_scenario").set_value("오류").run()
        app.button(key="api_preview").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)

    def test_csv_download_does_not_execute_user_text_as_a_formula(self):
        self.assertTrue(PAGE_FILE.is_file())
        from demo.bid_pages import _csv
        content = _csv([{"공고명": "=1+1", "금액": 42}]).decode("utf-8-sig")
        self.assertIn("'=1+1", content)


if __name__ == "__main__":
    unittest.main()
