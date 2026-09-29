"""Restored bid workflows use only the independent demo store and fixed samples."""
from pathlib import Path
from datetime import date
import unittest

from streamlit.testing.v1 import AppTest


PAGE_FILE = Path(__file__).resolve().parents[1] / "demo" / "bid_pages.py"
PAGES = ("daily_page", "management_page", "status_page", "api_page", "results_page")


class BidPageJourneys(unittest.TestCase):
    def setUp(self):
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            if "store" in app.session_state:
                app.session_state["store"].close()

    def page(self, name):
        self.assertTrue(PAGE_FILE.is_file(), "The bid screens must have a dedicated demo implementation")
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

    def test_recommendation_tabs_show_fixed_backtest_and_highlighted_metrics(self):
        app = self.page("daily_page")
        self.assertEqual(["사용자용 추천계산", "백테스트"], [tab.label for tab in app.tabs])
        app.button(key="backtest_show").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("실제 검증 성과가 아닙니다" in str(item.value) for item in app.info))
        self.assertEqual(4, len(next(frame.value for frame in app.dataframe if "결과" in frame.value.columns)))
        self.assertNotIn("demo_recommendations", app.session_state)
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("recommendation-amount" in str(item.value) for item in app.markdown))
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual("88.45%", metrics["실투찰율 · 샘플"])
        self.assertEqual("76.0%", metrics["신뢰도 · 샘플"])
        result = next(frame.value for frame in app.dataframe if "저장 상태" in frame.value.columns)
        self.assertIn("실투찰율 (%)", result.columns)
        self.assertIn("신뢰도 (%)", result.columns)

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

    def test_daily_search_uses_date_category_and_one_title_or_number_field(self):
        app = self.page("daily_page")
        self.assertEqual(["공고명 또는 번호"], [item.label for item in app.text_input])
        self.assertEqual(["개찰일"], [item.label for item in app.date_input])
        self.assertEqual(["카테고리"], [item.label for item in app.selectbox])
        for query in ("DEMO-001", "산책로"):
            app.text_input(key="daily_keyword").set_value(query)
            app.button(key="daily_search").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(["DEMO-001"], app.dataframe[0].value["공고번호"].tolist())
        app.selectbox(key="daily_category").set_value("가상 물품")
        app.button(key="daily_search").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.dataframe)

    def test_daily_uses_same_sample_after_input_changes(self):
        app = self.page("daily_page")
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        first = app.session_state["daily_results"][0]["amount"]
        store = app.session_state["store"]
        row = store.get_notice(1)
        store.save_notice({**row, "base_amount": 500000000}, notice_id=row["id"])
        app.button(key="daily_calculate").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(first, app.session_state["daily_results"][0]["amount"])
        self.assertTrue(any("고정 샘플" in item.value for item in app.info))

    def test_daily_handoff_applies_requested_date_and_clears_previous_results(self):
        app = self.page("daily_page")
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        app.session_state["daily_requested_date"] = date(2026, 10, 5)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(date(2026, 10, 5), app.date_input(key="daily_date").value)
        self.assertEqual("2026-10-05", app.session_state["daily_query"]["deadline"])
        self.assertNotIn("daily_requested_date", app.session_state)
        self.assertNotIn("daily_results", app.session_state)
        self.assertNotIn("daily_confirmed", app.session_state)
        self.assertEqual(["DEMO-002"], app.dataframe[0].value["공고번호"].tolist())

    def test_daily_saved_status_describes_the_displayed_sample(self):
        app = self.page("daily_page")
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        app.checkbox(key="daily_auto_save").set_value(False)
        app.selectbox(key="daily_scenario").set_value("샘플 B")
        app.button(key="daily_calculate").click().run()
        self.assertEqual("샘플 A", app.session_state["demo_recommendations"][1]["scenario"])
        self.assertEqual("샘플 B", app.session_state["daily_results"][0]["scenario"])
        result = next(frame.value for frame in app.dataframe if "저장 상태" in frame.value.columns)
        self.assertEqual(["저장 가능"], result["저장 상태"].tolist())
        app.button(key="daily_save_all").click().run()
        self.assertFalse(app.exception)
        result = next(frame.value for frame in app.dataframe if "저장 상태" in frame.value.columns)
        self.assertEqual(["저장 완료"], result["저장 상태"].tolist())

    def test_management_and_status_search_keep_only_working_core_filters(self):
        management = self.page("management_page")
        self.assertIn("management_keyword", [item.key for item in management.text_input])
        self.assertFalse(management.date_input)
        management.text_input(key="management_keyword").set_value("DEMO-007")
        management.button(key="management_search").click().run()
        self.assertEqual(["DEMO-007"], management.dataframe[0].value["공고번호"].tolist())
        management.selectbox(key="management_status").set_value("미입력")
        management.button(key="management_search").click().run()
        self.assertFalse(management.exception)
        self.assertFalse(management.dataframe)

        status = self.page("status_page")
        self.assertEqual(["공고명 또는 번호"], [item.label for item in status.text_input])
        status.text_input(key="status_keyword").set_value("DEMO-009")
        status.button(key="status_search").click().run()
        self.assertEqual(["DEMO-009"], status.dataframe[0].value["공고번호"].tolist())
        self.assertFalse(status.get("json"))

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
        self.assertEqual(["결과 금액 (원)"], [item.label for item in app.number_input])
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

    def test_api_search_has_no_keys_paging_or_raw_payload(self):
        app = self.page("api_page")
        self.assertFalse(app.number_input)
        self.assertEqual(["공고명 또는 번호"], [item.label for item in app.text_input])
        for query, code in [("교구", "DEMO-API-002"), ("DEMO-API-001", "DEMO-API-001")]:
            app.text_input(key="api_keyword").set_value(query)
            app.button(key="api_preview").click().run()
            self.assertEqual([code], [row["code"] for row in app.session_state["api_response"]["items"]])
        self.assertFalse(app.get("json"))
        app.selectbox(key="api_category").set_value("가상 물품").run()
        app.button(key="api_preview").click().run()
        self.assertEqual([], app.session_state["api_response"]["items"])

    def test_csv_download_does_not_execute_user_text_as_a_formula(self):
        self.assertTrue(PAGE_FILE.is_file())
        from demo.bid_pages import _csv
        content = _csv([{"공고명": "=1+1", "금액": 42}]).decode("utf-8-sig")
        self.assertIn("'=1+1", content)

    def test_status_shows_my_awards_and_excludes_unsubmitted_results(self):
        app = self.page("status_page")
        rows = app.dataframe[0].value.set_index("공고번호")
        self.assertIn("최종 제출금액", rows.columns)
        self.assertNotIn("내 투찰금액", rows.columns)
        self.assertEqual(0, rows.loc["DEMO-001", "최종 제출금액"])
        self.assertEqual(0, rows.loc["DEMO-011", "최종 제출금액"])
        self.assertTrue(any("완료한 투찰 기록을 기준으로 낙찰 결과를 표시합니다." == item.value for item in app.caption))
        self.assertEqual("낙찰", rows.loc["DEMO-009", "결과 상태"])
        self.assertEqual("미낙찰", rows.loc["DEMO-010", "결과 상태"])
        self.assertEqual("결과 대기", rows.loc["DEMO-007", "결과 상태"])
        self.assertEqual("미투찰", rows.loc["DEMO-011", "결과 상태"])
        self.assertEqual("작성중", rows.loc["DEMO-001", "결과 상태"])
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual("3건", metrics["제출완료"])
        self.assertEqual("1건", metrics["낙찰"])
        self.assertEqual("1건", metrics["미낙찰"])
        self.assertEqual("1건", metrics["결과 대기"])

    def test_status_result_filters_and_counts_match_the_visible_records(self):
        app = self.page("status_page")
        self.assertEqual(
            ["전체", "낙찰", "미낙찰", "결과 대기", "작성중", "미투찰"],
            app.selectbox(key="status_outcome").options,
        )
        for outcome, code in [("낙찰", "DEMO-009"), ("미낙찰", "DEMO-010"), ("결과 대기", "DEMO-007")]:
            app.selectbox(key="status_outcome").set_value(outcome)
            app.button(key="status_search").click().run()
            self.assertFalse(app.exception)
            rows = app.dataframe[0].value
            self.assertEqual([code], rows["공고번호"].tolist())
            self.assertEqual([outcome], rows["결과 상태"].tolist())
            metrics = {item.label: item.value for item in app.metric}
            self.assertEqual("1건", metrics["조회 공고"])
            self.assertEqual("1건", metrics[outcome])
            for other in {"낙찰", "미낙찰", "결과 대기"} - {outcome}:
                self.assertEqual("0건", metrics[other])
        app.selectbox(key="status_outcome").set_value("전체")
        app.text_input(key="status_keyword").set_value("DEMO-011")
        app.button(key="status_search").click().run()
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual("1건", metrics["조회 공고"])
        for label in ("제출완료", "낙찰", "미낙찰", "결과 대기"):
            self.assertEqual("0건", metrics[label])

    def test_status_review_pending_and_later_draft_keep_completed_submission(self):
        app = self.page("status_page")
        store = app.session_state["store"]
        submitted_amount = next(row["amount"] for row in store.submissions() if row["notice_id"] == 9)
        store.save_submission(dict(notice_id=12, company="가상 제출 참가자", amount=1, status="제출완료", memo=""))
        store.save_submission(dict(notice_id=9, company="가상 초안 참가자", amount=2, status="작성중", memo=""))
        app.run()
        self.assertFalse(app.exception)
        rows = app.dataframe[0].value.set_index("공고번호")
        self.assertEqual("결과 대기", rows.loc["DEMO-012", "결과 상태"])
        self.assertEqual("낙찰", rows.loc["DEMO-009", "결과 상태"])
        self.assertEqual("제출완료", rows.loc["DEMO-009", "내 투찰상태"])
        self.assertEqual(submitted_amount, rows.loc["DEMO-009", "최종 제출금액"])
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual("4건", metrics["제출완료"])
        self.assertEqual("1건", metrics["낙찰"])
        self.assertEqual("2건", metrics["결과 대기"])


if __name__ == "__main__":
    unittest.main()
