"""원본의 메뉴와 여러 업무 탭을 유지하는 회귀 검사."""
import unittest
from unittest.mock import patch

from demo import workspace
from demo.store import DemoStore


class WorkspaceTests(unittest.TestCase):
    def test_home_summary_counts_session_records_and_pending_notices(self):
        store = DemoStore()
        try:
            self.assertEqual(workspace.home_summary(store), {
                "notices": 12, "submissions": 4, "awaiting_results": 1,
            })
            store.save_result(dict(notice_id=7, outcome="검토중", amount=0, note="가상 검토"))
            self.assertEqual(workspace.home_summary(store)["awaiting_results"], 1)
            store.save_result(dict(notice_id=7, outcome="샘플 미선정", amount=1, note="가상 결과"))
            self.assertEqual(workspace.home_summary(store)["awaiting_results"], 0)
        finally:
            store.close()

    def test_home_summary_handles_an_empty_session(self):
        store = DemoStore()
        try:
            for row in store.notices():
                store.delete_notice(row["id"])
            self.assertEqual(workspace.home_summary(store), {
                "notices": 0, "submissions": 0, "awaiting_results": 0,
            })
        finally:
            store.close()

    def test_visitor_menu_has_daily_notices_and_no_standalone_calculator(self):
        self.assertEqual([p["label"] for p in workspace.PAGES], [
            "카테고리 관리", "데이터 등록", "통합 공고 조회", "입찰/낙찰 데이터 조회",
            "개찰일별 공고관리", "개찰일별 추천계산", "나의 투찰관리", "내 투찰현황",
            "나라장터 API 연동", "결과 관리", "투찰 검토함", "성과 리포트",
        ])
        with patch.object(workspace.st, "session_state", {}):
            workspace.open_tab("daily_notices")
            with self.assertRaises(ValueError):
                workspace.open_tab("recommend_price")

    def test_tabs_open_once_close_to_neighbor_and_home_clears_them(self):
        state = {}
        with patch.object(workspace.st, "session_state", state):
            workspace.open_tab("data_upload")
            workspace.open_tab("daily_recommend")
            workspace.open_tab("data_upload")
            self.assertEqual(state["open_tabs"], ["data_upload", "daily_recommend"])
            self.assertEqual(state["active_tab"], "data_upload")
            workspace.close_tab("data_upload")
            self.assertEqual(state["active_tab"], "daily_recommend")
            workspace.home()
            self.assertEqual(state["open_tabs"], [])
            self.assertEqual(state["active_tab"], "")

    def test_unknown_page_cannot_be_opened(self):
        with patch.object(workspace.st, "session_state", {}):
            with self.assertRaises(ValueError):
                workspace.open_tab("production")

    def test_review_menu_has_its_own_group_and_opens_a_workspace_tab(self):
        self.assertIn(('업무 관리', ('bid_review',)), workspace.SIDEBAR_GROUPS)
        with patch.object(workspace.st, 'session_state', {}):
            workspace.open_tab('bid_review')
            self.assertEqual(workspace.st.session_state['active_tab'], 'bid_review')

    def test_closing_upload_discards_preview_but_keeps_registered_history(self):
        state = {"current_excel_preview": True, "current_excel_selection": ["DEMO-1"],
                 "historical_preview": True, "upload_history": [{"신규 등록": 2}],
                 "pdf_links": {1: ["가상.pdf"]}, "daily_results": [{"amount": 10}]}
        with patch.object(workspace.st, "session_state", state):
            workspace.open_tab("data_upload")
            workspace.close_tab("data_upload")
        self.assertNotIn("current_excel_preview", state)
        self.assertNotIn("historical_preview", state)
        self.assertEqual(state["upload_history"], [{"신규 등록": 2}])
        self.assertEqual(state["pdf_links"], {1: ["가상.pdf"]})
        self.assertEqual(state["daily_results"], [{"amount": 10}])


if __name__ == "__main__":
    unittest.main()
