"""날짜별 업무 홈과 등록·조회·계산 사이의 이동 계약."""
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo import workspace
from demo.store import DemoStore


APP = Path(__file__).resolve().parents[1] / "app.py"


class WorkbenchTests(unittest.TestCase):
    def test_schedule_groups_order_dates_and_count_only_saved_notices(self):
        build = getattr(workspace, "schedule_groups", None)
        self.assertTrue(callable(build), "날짜별 일정 집계가 필요합니다.")
        rows = [dict(id=3, deadline="2026-10-23"), dict(id=2, deadline="2026-10-21"),
                dict(id=1, deadline="2026-10-21")]
        groups = build(rows, {1: {"amount": 24000000}, 99: {"amount": 1}})
        self.assertEqual([group["date"] for group in groups], ["2026-10-21", "2026-10-23"])
        self.assertEqual([row["id"] for row in groups[0]["notices"]], [2, 1])
        self.assertEqual([group["calculated"] for group in groups], [1, 0])
        self.assertEqual(rows[0]["id"], 3, "집계가 입력 순서를 변경하면 안 됩니다.")
        self.assertEqual(build([], {1: {}}), [])

    def test_schedule_link_sets_requested_date_and_clears_stale_selection(self):
        go = getattr(workspace, "open_daily_notices", None)
        self.assertTrue(callable(go), "일정에서 날짜별 조회로 이동할 수 있어야 합니다.")
        state = {"daily_notices_query": "2026-10-03", "daily_notices_select_all": True,
                 "daily_notices_pending": (1,), "daily_notices_ack": True}
        with patch.object(workspace.st, "session_state", state):
            go("2026-10-23")
        self.assertEqual(state["active_tab"], "daily_notices")
        self.assertEqual(state["daily_notices_date"], date(2026, 10, 23))
        self.assertEqual(state["daily_notices_query"], "2026-10-23")
        self.assertNotIn("daily_notices_pending", state)
        self.assertNotIn("daily_notices_select_all", state)
        self.assertNotIn("daily_notices_ack", state)

    def test_schedule_calculation_link_uses_existing_date_contract(self):
        go = getattr(workspace, "open_daily_calculation", None)
        self.assertTrue(callable(go))
        state = {}
        with patch.object(workspace.st, "session_state", state):
            go(date(2026, 10, 21))
        self.assertEqual(state["active_tab"], "daily_recommend")
        self.assertEqual(state["daily_requested_date"], date(2026, 10, 21))

    def test_invalid_schedule_date_does_not_open_a_page(self):
        for name in ("open_daily_notices", "open_daily_calculation"):
            go = getattr(workspace, name, None)
            self.assertTrue(callable(go))
            state = {}
            with patch.object(workspace.st, "session_state", state), self.assertRaises(ValueError):
                go("2026-02-30")
            self.assertNotIn("active_tab", state)

    def _app(self):
        app = AppTest.from_file(str(APP), default_timeout=20)
        app.session_state["authenticated"] = True
        app.session_state["store"] = DemoStore()
        self.addCleanup(app.session_state["store"].close)
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_home_shows_schedule_and_opens_that_days_notices(self):
        app = self._app()
        markup = "\n".join(item.value for item in app.markdown)
        self.assertNotIn('class="home-editorial"', markup)
        self.assertIn("개찰 일정", markup)
        self.assertIn('schedule_scope_toggle', {button.key for button in app.button})
        app.button(key='schedule_scope_toggle').click().run()
        app.button(key='home_day_toggle_2026-10-03').click().run()
        markup = "\n".join(item.value for item in app.markdown)
        self.assertIn("가상 산책로 안내판 설치", markup)
        app.button(key="home_day_notices_2026-10-03").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["active_tab"], "daily_notices")
        self.assertEqual(app.session_state["daily_notices_query"], "2026-10-03")

    def test_home_calculation_link_opens_date_with_matching_notices(self):
        app = self._app()
        app.date_input(key="home_calculation_date").set_value(date(2026, 10, 23)).run()
        app.button(key="home_open_daily_recommend").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["active_tab"], "daily_recommend")
        self.assertEqual(app.session_state["daily_query"]["deadline"], "2026-10-23")

    def test_home_empty_session_keeps_registration_action(self):
        app = self._app()
        for row in app.session_state["store"].notices():
            app.session_state["store"].delete_notice(row["id"])
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("등록된 공고가 없습니다" in item.value for item in app.info))
        app.button(key="home_open_data_upload").click().run()
        self.assertEqual(app.session_state["active_tab"], "data_upload")


if __name__ == "__main__":
    unittest.main()
