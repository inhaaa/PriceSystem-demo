"""운영과 같은 주간 우선 일정 표와 날짜별 이동을 검증한다."""
from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from demo import schedule


class ScheduleStateTests(unittest.TestCase):
    def test_week_is_inclusive_and_remaining_period_is_disjoint(self):
        groups = [{'date': day, 'notices': []} for day in
                  ['2026-11-05', '2026-11-04', '2026-10-29', '2026-10-28', '2026-10-31']]
        before = deepcopy(groups)
        week, remaining = schedule.split_schedule_groups(groups, '2026-10', date(2026, 10, 29))
        self.assertEqual([row['date'] for row in week], ['2026-10-29', '2026-10-31', '2026-11-04'])
        self.assertEqual([row['date'] for row in remaining], ['2026-10-28'])
        self.assertEqual(groups, before)

    def test_selected_year_and_month_boundary_queries_are_unique(self):
        self.assertEqual(schedule.query_periods('2026-10', date(2026, 10, 29)), [(2026, 10), (2026, 11)])
        self.assertEqual(schedule.query_periods('2026', date(2026, 12, 29)), [(2026, None), (2027, 1)])
        self.assertEqual(schedule.query_periods('2026-08', date(2026, 10, 29)),
                         [(2026, 8), (2026, 10), (2026, 11)])

    def test_scope_toggle_and_reset_preserve_other_session_records(self):
        state = {'store': object(), 'demo_recommendations': {1: {'amount': 1}}}
        before = dict(state)
        with patch.object(schedule.st, 'session_state', state):
            schedule._toggle_scope()
            self.assertTrue(state['home_schedule_all_visible'])
            schedule.reset_scope()
            self.assertFalse(state['home_schedule_all_visible'])
        self.assertIs(state['store'], before['store'])
        self.assertEqual(state['demo_recommendations'], before['demo_recommendations'])


class SchedulePageJourneys(unittest.TestCase):
    def page(self):
        app = AppTest.from_string("""
import streamlit as st
from demo.store import DemoStore
from demo.workspace import schedule_groups
from demo.schedule import render_schedule
from datetime import date
if 'store' not in st.session_state: st.session_state['store'] = DemoStore()
def open_notices(day): st.session_state['schedule_target'] = ('notices', day.isoformat())
def open_calculation(day): st.session_state['schedule_target'] = ('calculation', day.isoformat())
render_schedule(schedule_groups(st.session_state['store'].notices(), {}), {}, period='2026-10',
                open_notices=open_notices, open_calculation=open_calculation, today=date(2026, 10, 22))
""", default_timeout=20).run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def test_week_shows_tables_without_expanding_and_callbacks_keep_dates(self):
        app = self.page()
        markup = '\n'.join(item.value for item in app.markdown)
        self.assertEqual(markup.count('<table class="schedule-notices"'), 2)
        self.assertIn('DEMO-011', markup)
        self.assertNotIn('home_day_notices_2026-10-03', {item.key for item in app.button})
        app.button(key='home_day_notices_2026-10-23').click().run()
        self.assertEqual(app.session_state['schedule_target'], ('notices', '2026-10-23'))
        app.button(key='home_day_calculate_2026-10-23').click().run()
        self.assertEqual(app.session_state['schedule_target'], ('calculation', '2026-10-23'))

    def test_remaining_scope_preserves_week_and_store_and_escapes_titles(self):
        app = self.page()
        store = app.session_state['store']
        row = store.get_notice(1)
        store.save_notice({**row, 'title': '<script>sample</script>'}, notice_id=1)
        before = (store.notices(), store.submissions(), store.results())
        app.button(key='schedule_scope_toggle').click().run()
        markup = '\n'.join(item.value for item in app.markdown)
        self.assertEqual(markup.count('<table class="schedule-notices"'), 12)
        self.assertIn('&lt;script&gt;sample&lt;/script&gt;', markup)
        self.assertNotIn('<script>sample</script>', markup)
        app.button(key='schedule_scope_toggle').click().run()
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)

    def test_empty_groups_keep_week_guidance(self):
        app = self.page()
        store = app.session_state['store']
        for row in store.notices(): store.delete_notice(row['id'])
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('7일 이내 개찰 일정이 없습니다' in item.value for item in app.info))
        self.assertTrue(app.button(key='schedule_scope_toggle').disabled)


if __name__ == '__main__':
    unittest.main()
