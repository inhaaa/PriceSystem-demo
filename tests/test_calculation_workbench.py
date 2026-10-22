"""계산 작업대의 목록·실행 패널과 기존 선택/저장 계약."""
import json
import unittest
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from demo.store import DemoStore


class CalculationWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_string(
            "import streamlit as st\n"
            "from demo.store import DemoStore\n"
            "from demo.bid_pages import daily_page\n"
            "if 'store' not in st.session_state: st.session_state['store'] = DemoStore()\n"
            "daily_page(st.session_state['store'])\n",
            default_timeout=20,
        ).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.app.session_state["store"].close()

    def container(self, key):
        blocks = [block for block in self.app.get("flex_container")
                  if block.proto.id.endswith("-" + key)]
        self.assertTrue(blocks, f"계산 작업대에 {key} 영역이 있어야 합니다.")
        return blocks[0]

    def test_notice_list_and_controls_share_two_separate_workspace_columns(self):
        app = self.app
        app.button(key="daily_search").click().run()
        workspace = self.container("daily_workspace")
        columns = workspace.get("column")
        self.assertEqual(2, len(columns))
        self.assertIn(self.container("daily_notice_panel"), list(columns[0]))
        self.assertIn(self.container("daily_controls"), list(columns[1]))
        self.assertIn(self.container("daily_result_panel"), list(columns[1]))
        self.assertFalse(columns[0].button)
        self.assertEqual(["daily_check", "daily_calculate"], [button.key for button in columns[1].button])
        self.assertIn("daily_scenario", [item.key for item in columns[1].selectbox])
        self.assertIn("daily_auto_save", [item.key for item in columns[1].checkbox])
        self.assertTrue(any("선택 공고 1건" in item.value for item in columns[1].caption))
        grid = columns[0].dataframe[0]
        self.assertEqual(["선택", "공고명", "기초금액", "공고번호", "개찰일"], list(grid.proto.column_order))
        self.assertNotIn("발주기관", grid.value.columns)
        self.assertNotIn("지역", grid.value.columns)
        self.assertEqual("right", json.loads(grid.proto.columns)["기초금액"]["alignment"])

    def test_controls_remain_visible_and_disabled_before_search(self):
        controls = self.container("daily_controls")
        self.assertTrue(controls.button(key="daily_check").disabled)
        self.assertTrue(controls.button(key="daily_calculate").disabled)
        self.assertTrue(controls.checkbox(key="daily_auto_save").value)
        self.assertTrue(any("선택 공고 0건" in item.value for item in controls.caption))

    def test_calculated_result_precedes_controls_without_nested_panel_borders(self):
        app = self.app
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        self.assertFalse(app.exception)
        execution_column = self.container("daily_workspace").get("column")[1]
        panels = [block for block in execution_column.children.values() if block.type == "flex_container"]
        self.assertEqual(["daily_result_panel", "daily_controls"],
                         [block.proto.id.rsplit("-", 1)[-1] for block in panels])
        for panel in panels:
            self.assertFalse(panel.proto.flex_container.border)
        result = self.container("daily_result_panel")
        self.assertTrue(any("24,000,000원" in item.value for item in result.markdown))
        self.assertIn("daily_save_all", [button.key for button in result.button])

    def test_sample_notice_is_a_compact_caption(self):
        note = "고정 샘플을 표시하며 실제 추천 계산은 하지 않습니다."
        self.assertIn(note, [item.value for item in self.app.caption])
        self.assertNotIn(note, [item.value for item in self.app.info])

    def test_changed_selection_requires_confirmation_and_hides_previous_result(self):
        app = self.app
        store = app.session_state["store"]
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        self.assertEqual((1,), app.session_state["daily_confirmed"])
        self.assertEqual({1}, set(app.session_state["demo_recommendations"]))
        second = store.get_notice(2)
        store.save_notice({**second, "deadline": "2026-10-03"}, notice_id=2)
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button(key="daily_calculate").disabled)
        self.assertNotIn("daily_save_all", [button.key for button in self.container("daily_result_panel").button])
        app.button(key="daily_check").click().run()
        self.assertEqual((1, 2), app.session_state["daily_confirmed"])
        self.assertFalse(app.button(key="daily_calculate").disabled)

    def test_result_amount_and_manual_save_stay_in_execution_column(self):
        app = self.app
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.checkbox(key="daily_auto_save").set_value(False).run()
        app.button(key="daily_calculate").click().run()
        panel = self.container("daily_result_panel")
        self.assertIn("daily_save_all", [button.key for button in panel.button])
        self.assertTrue(any("24,000,000원" in item.value for item in panel.markdown))
        self.assertTrue(any("낙찰 확률이 아닙니다" in item.value for item in panel.caption))
        self.assertNotIn("demo_recommendations", app.session_state)
        panel.button(key="daily_save_all").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["daily_results"][0], app.session_state["demo_recommendations"][1])

    def test_backtest_is_collapsed_and_calculation_has_no_large_metrics(self):
        app = self.app
        self.assertFalse(app.tabs)
        backtest = next(item for item in app.expander if item.label == "백테스트 샘플")
        self.assertFalse(backtest.proto.expanded)
        backtest.button(key="backtest_show").click().run()
        self.assertEqual(4, len(next(grid.value for grid in app.dataframe if "결과" in grid.value.columns)))
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.metric)
        self.assertFalse(any("RECOMMENDATION" in item.value for item in app.markdown))


class CalculationNavigationTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=20)
        self.app.session_state["authenticated"] = True
        self.app.session_state["store"] = DemoStore()
        self.app.run()
        self.assertFalse(self.app.exception)
        self.app.date_input(key="home_calculation_date").set_value(date(2026, 10, 23)).run()
        self.app.button(key="home_open_daily_recommend").click().run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.app.session_state["store"].close()

    def leave_and_return(self):
        self.app.button(key="menu_open_integrated_bids").click().run()
        self.assertFalse(self.app.exception)
        for key in ("daily_date", "daily_category", "daily_keyword"):
            self.assertNotIn(key, self.app.session_state)
        self.app.button(key="tab_activate_daily_recommend").click().run()
        self.assertFalse(self.app.exception)

    def test_home_requested_date_matches_query_after_returning_from_other_tab(self):
        self.leave_and_return()
        app = self.app
        self.assertEqual("2026-10-23", app.session_state["daily_query"]["deadline"])
        self.assertEqual(date(2026, 10, 23), app.date_input(key="daily_date").value)
        self.assertEqual(["DEMO-011"], app.dataframe[0].value["공고번호"].tolist())

    def test_submitted_filters_and_calculation_survive_widget_cleanup(self):
        app = self.app
        app.selectbox(key="daily_category").set_value("가상 물품")
        app.text_input(key="daily_keyword").set_value("DEMO-011")
        app.button(key="daily_search").click().run()
        app.button(key="daily_check").click().run()
        app.button(key="daily_calculate").click().run()
        result = app.session_state["daily_results"]
        self.leave_and_return()
        self.assertEqual("가상 물품", app.selectbox(key="daily_category").value)
        self.assertEqual("DEMO-011", app.text_input(key="daily_keyword").value)
        self.assertEqual(date(2026, 10, 23), app.date_input(key="daily_date").value)
        self.assertEqual(dict(deadline="2026-10-23", category="가상 물품", keyword="DEMO-011"),
                         app.session_state["daily_query"])
        self.assertEqual((11,), app.session_state["daily_confirmed"])
        self.assertEqual(result, app.session_state["daily_results"])
        self.assertFalse(app.button(key="daily_calculate").disabled)
        self.assertEqual(result[0], app.session_state["demo_recommendations"][11])


if __name__ == "__main__":
    unittest.main()
