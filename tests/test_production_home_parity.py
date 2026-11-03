"""운영 홈의 기간 조회·월 경계 주간과 데모 데이터 보존 계약."""
from datetime import date
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo import schedule, workspace


class ProductionHomeParityTests(unittest.TestCase):
    def test_sidebar_starts_with_data_management(self):
        self.assertEqual([name for name, _ in workspace.SIDEBAR_GROUPS],
                         ['자료 관리', '입찰 업무', '업무 관리', '성과 분석', '시스템'])

    def test_week_crosses_selected_month_without_duplicating_remaining_dates(self):
        groups = [{'date': day, 'notices': []} for day in
                  ['2026-11-05', '2026-10-02', '2026-11-02', '2026-10-31', '2026-11-03']]
        weekly, remaining = schedule.split_schedule_groups(groups, '2026-10', date(2026, 10, 29))
        self.assertEqual([group['date'] for group in weekly],
                         ['2026-10-31', '2026-11-02', '2026-11-03'])
        self.assertEqual([group['date'] for group in remaining], ['2026-10-02'])

    def page(self, notice_years=()):
        clock = patch.object(schedule, '_today', return_value=date(2026, 10, 29))
        clock.start()
        self.addCleanup(clock.stop)
        app = AppTest.from_string('''
import streamlit as st
from demo.store import DemoStore
from demo.workspace import render_home
if 'store' not in st.session_state:
    st.session_state['store'] = DemoStore()
    sample = st.session_state['store'].notices()[0]
    for code, day in [('DEMO-OCT-END', '2026-10-31'), ('DEMO-NOV-START', '2026-11-02')]:
        st.session_state['store'].save_notice({**sample, 'code': code, 'deadline': day})
    for year in st.session_state['notice_years']:
        st.session_state['store'].save_notice({**sample, 'code': f'DEMO-YEAR-{year}', 'deadline': f'{year}-06-15'})
render_home(st.session_state['store'])
''', default_timeout=20)
        app.session_state['notice_years'] = notice_years
        app.run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def markup(self, app):
        return '\n'.join(item.value for item in app.markdown)

    def test_home_has_period_refresh_and_date_tables_with_cross_month_week(self):
        app = self.page()
        periods = app.selectbox(key='home_opening_period')
        self.assertEqual(periods.value, '2026-10')
        self.assertEqual(len(periods.options), 13)
        self.assertIn('home_refresh_schedule', {item.key for item in app.button})
        self.assertIn('home_day_notices_2026-11-02', {item.key for item in app.button})
        self.assertNotIn('home_day_notices_2026-10-03', {item.key for item in app.button})
        markup = self.markup(app)
        self.assertIn('<table class="schedule-notices"', markup)
        self.assertIn('DEMO-OCT-END', markup)
        self.assertIn('DEMO-NOV-START', markup)
        self.assertFalse(any(str(item.key).startswith('home_day_toggle_') for item in app.button))

    def test_period_changes_reset_scope_keep_week_and_never_change_store(self):
        app = self.page()
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        app.button(key='schedule_scope_toggle').click().run()
        self.assertIn('DEMO-001', self.markup(app))
        app.selectbox(key='home_opening_period').set_value('2026-11').run()
        self.assertFalse(app.exception)
        self.assertNotIn('DEMO-001', self.markup(app))
        self.assertIn('DEMO-OCT-END', self.markup(app))
        self.assertIn('DEMO-NOV-START', self.markup(app))
        self.assertFalse(app.session_state['home_schedule_all_visible'])
        app.button(key='home_refresh_schedule').click().run()
        app.button(key='home_day_notices_2026-11-02').click().run()
        self.assertEqual(app.session_state['daily_notices_query'], '2026-11-02')
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)

    def test_home_periods_include_notice_years_and_default_to_current_month(self):
        app = self.page((2025, 2027))
        store = app.session_state['store']
        periods = app.selectbox(key='home_opening_period')
        self.assertEqual(periods.value, '2026-10')
        self.assertEqual(len(periods.options), 39)
        for year in (2025, 2026, 2027):
            self.assertIn(f'{year}년 전체', periods.options)
            for month in range(1, 13):
                self.assertIn(f'{year}년 {month}월', periods.options)
        before = (store.notices(), store.submissions(), store.results())
        for year in (2025, 2027):
            for period in (f'{year}-06', str(year)):
                app.selectbox(key='home_opening_period').set_value(period).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox(key='home_opening_period').value, period)
                app.button(key='schedule_scope_toggle').click().run()
                self.assertIn(f'DEMO-YEAR-{year}', self.markup(app))
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)


if __name__ == '__main__':
    unittest.main()
