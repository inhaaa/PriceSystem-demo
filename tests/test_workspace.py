"""원본의 메뉴와 여러 업무 탭을 유지하는 회귀 검사."""
import unittest
from unittest.mock import patch

from demo import workspace


class WorkspaceTests(unittest.TestCase):
    def test_original_ten_modules_are_not_merged(self):
        self.assertEqual([p["label"] for p in workspace.PAGES], [
            "카테고리 관리", "데이터 등록", "통합 공고 관리", "입찰/낙찰 데이터 조회",
            "추천투찰금액 계산", "개찰일별 추천계산", "나의 투찰관리", "내 투찰현황",
            "나라장터 API 연동", "결과 관리",
        ])

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
