"""공개 일정의 범위·일괄 접기와 브라우저 표시 설정 저장 계약."""
from copy import deepcopy
from datetime import date
import importlib
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
GROUPS = [{'date': day, 'notices': []} for day in ('2026-10-03', '2026-10-23', '2026-10-28', '2026-11-03')]
SAVED = {'version': 1, 'showAll': True, 'expandedDates': ['2026-10-03', '2026-10-28'], 'month': '2026-10'}
DEFAULT = {'version': 1, 'showAll': False, 'expandedDates': [], 'month': None}


def schedule_module(test):
    test.assertTrue((ROOT / 'demo/schedule.py').is_file(), '공개 일정 모듈이 필요합니다.')
    return importlib.import_module('demo.schedule')


class ScheduleStateTests(unittest.TestCase):
    def test_saved_preferences_validate_dates_months_version_and_preserve_input(self):
        module = schedule_module(self)
        value = {**SAVED, 'expandedDates': ['2026-10-28', '2026-10-03', '2026-10-28', 'invalid', {}, None]}
        before = deepcopy((value, GROUPS))
        self.assertEqual(module.normalize_preferences(value, GROUPS), SAVED)
        self.assertEqual((value, GROUPS), before)
        for value in (None, [], 'bad', {}, {'version': 2}, {'version': True}):
            with self.subTest(value=value):
                self.assertEqual(module.normalize_preferences(value, GROUPS), DEFAULT)
        self.assertEqual(module.normalize_preferences({**SAVED, 'showAll': 'true', 'expandedDates': {}, 'month': '2030-10'}, GROUPS), DEFAULT)

    def test_restore_runs_once_and_preserves_non_schedule_session_data(self):
        module = schedule_module(self)
        marker = object()
        state = {'store': marker, 'demo_recommendations': {1: {'amount': 24000000}}}
        with patch.object(module.st, 'session_state', state):
            module.restore_preferences(SAVED, GROUPS)
            self.assertTrue(state['schedule_preferences_loaded'])
            self.assertTrue(state['schedule_show_all'])
            self.assertEqual(state['schedule_expanded_dates'], {'2026-10-03', '2026-10-28'})
            self.assertEqual(state['schedule_month'], '2026-10')
            state['schedule_show_all'] = False
            module.restore_preferences({**SAVED, 'month': '2026-11'}, GROUPS)
            self.assertFalse(state['schedule_show_all'])
            self.assertEqual(state['schedule_month'], '2026-10')
        self.assertIs(state['store'], marker)
        self.assertEqual(state['demo_recommendations'], {1: {'amount': 24000000}})

    def test_direct_choice_wins_over_late_restore_and_bulk_preserves_hidden_days(self):
        module = schedule_module(self)
        state = {'schedule_expanded_dates': {'2026-10-03', '2026-11-03'}}
        with patch.object(module.st, 'session_state', state):
            module.set_expanded(('2026-10-23', '2026-10-28'), True)
            module.restore_preferences(SAVED, GROUPS)
            self.assertEqual(state['schedule_expanded_dates'], {'2026-10-03', '2026-10-23', '2026-10-28', '2026-11-03'})
            module.set_expanded(('2026-10-23', '2026-10-28'), False)
            self.assertEqual(state['schedule_expanded_dates'], {'2026-10-03', '2026-11-03'})
            self.assertNotIn('schedule_month', state)

    def test_week_is_inclusive_and_month_selection_intersects_scope(self):
        module = schedule_module(self)
        self.assertEqual([row['date'] for row in module.visible_groups(GROUPS, '2026-10', date(2026, 10, 22), False)],
                         ['2026-10-23', '2026-10-28'])
        self.assertEqual([row['date'] for row in module.visible_groups(GROUPS, '2026-11', date(2026, 10, 29), False)], ['2026-11-03'])
        self.assertEqual([row['date'] for row in module.visible_groups(GROUPS, '2026-10', date(2026, 10, 22), True)],
                         ['2026-10-03', '2026-10-23', '2026-10-28'])

    def test_bridge_restores_before_saving_and_saves_false_empty_preferences(self):
        module = schedule_module(self)
        state = {}
        with patch.object(module.st, 'session_state', state), patch.object(module.st.components.v2, 'component') as factory:
            module.render_preferences(GROUPS)
            first = factory.return_value.call_args.kwargs
            self.assertFalse(first['data']['ready'])
            self.assertEqual(first['height'], 0)
            state[first['key']] = {'restored': {'preferences': SAVED}}
            first['on_restored_change']()
            state['schedule_show_all'] = False
            state['schedule_expanded_dates'] = set()
            module.render_preferences(GROUPS)
            data = factory.return_value.call_args.kwargs['data']
            self.assertTrue(data['ready'])
            self.assertEqual(data['preferences'], {**DEFAULT, 'month': '2026-10'})

    def test_browser_storage_handles_reload_corruption_and_denied_storage(self):
        path = ROOT / 'static/schedule-preferences.js'
        self.assertTrue(path.is_file(), '일정 표시 설정 브라우저 저장 연결이 필요합니다.')
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node가 설치된 환경에서 브라우저 저장 브리지를 실행합니다.')
        script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8').replace('export default', '');
const saved = {version: 1, showAll: true, expandedDates: ['2026-10-23'], month: '2026-10'};
const defaults = {version: 1, showAll: false, expandedDates: [], month: null};
const values = new Map([['other-setting', 'kept']]), events = [], writes = [];
let blocked = '';
const localStorage = {
  getItem(key) { if (blocked === 'read') throw Error('blocked'); return values.get(key) ?? null; },
  setItem(key, value) { if (blocked === 'write') throw Error('blocked'); writes.push(key); values.set(key, value); },
};
const mount = vm.runInNewContext(`(${source})`, {localStorage});
const run = (parentElement, ready = false, preferences = defaults) => mount({parentElement,
  data: {storageKey: 'schedule-test', ready, preferences},
  setStateValue(name, value) { events.push(JSON.parse(JSON.stringify([name, value]))); }});
values.set('schedule-test', JSON.stringify(saved));
const host = {}; run(host); run(host);
assert.deepEqual(events, [['restored', {preferences: saved}]]);
assert.equal(writes.length, 0);
run(host, true, defaults);
assert.deepEqual(JSON.parse(values.get('schedule-test')), defaults);
run({}); assert.deepEqual(events.at(-1), ['restored', {preferences: defaults}]);
values.set('schedule-test', '{bad'); run({});
assert.deepEqual(events.at(-1), ['restored', {preferences: null}]);
assert.equal(values.get('schedule-test'), '{bad');
blocked = 'read'; assert.doesNotThrow(() => run({}));
assert.deepEqual(events.at(-1), ['restored', {preferences: null}]);
blocked = 'write'; assert.doesNotThrow(() => run({}, true, saved));
assert.equal(values.get('other-setting'), 'kept');
console.log('browser preferences verified');
'''
        result = subprocess.run([node, '-e', script, str(path)], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('verified', result.stdout)


class SchedulePageJourneys(unittest.TestCase):
    def page(self, *, show_all=False, expanded=()):
        module = schedule_module(self)
        clock = patch.object(module, '_today', return_value=date(2026, 10, 22))
        clock.start()
        self.addCleanup(clock.stop)
        app = AppTest.from_string('''
import streamlit as st
from demo.store import DemoStore
from demo.workspace import schedule_groups
from demo.schedule import render_schedule
if 'store' not in st.session_state:
    st.session_state['store'] = DemoStore()
    sample = st.session_state['store'].notices()[0]
    st.session_state['store'].save_notice({**sample, 'code': 'DEMO-NOV', 'deadline': '2026-11-03'})
def open_notices(day): st.session_state['schedule_target'] = ('notices', day.isoformat())
def open_calculation(day): st.session_state['schedule_target'] = ('calculation', day.isoformat())
store = st.session_state['store']
saved = st.session_state.get('demo_recommendations', {})
render_schedule(schedule_groups(store.notices(), saved), saved,
                open_notices=open_notices, open_calculation=open_calculation)
''', default_timeout=20)
        app.session_state['schedule_show_all'] = show_all
        app.session_state['schedule_expanded_dates'] = set(expanded)
        app.run()
        self.addCleanup(lambda: app.session_state['store'].close())
        self.assertFalse(app.exception)
        return app

    def notice_count(self, app):
        return '\n'.join(item.value for item in app.markdown).count('class="schedule-notice"')

    def test_default_week_has_collapsed_dates_and_original_callbacks_work(self):
        app = self.page()
        self.assertEqual(app.selectbox(key='schedule_month').value, '2026-10')
        self.assertEqual(self.notice_count(app), 0)
        self.assertIn('home_day_notices_2026-10-23', {item.key for item in app.button})
        self.assertNotIn('home_day_notices_2026-10-03', {item.key for item in app.button})
        app.button(key='home_day_toggle_2026-10-23').click().run()
        self.assertEqual(self.notice_count(app), 1)
        app.button(key='home_day_notices_2026-10-23').click().run()
        self.assertEqual(app.session_state['schedule_target'], ('notices', '2026-10-23'))
        app.button(key='home_day_calculate_2026-10-23').click().run()
        self.assertEqual(app.session_state['schedule_target'], ('calculation', '2026-10-23'))

    def test_bulk_changes_visible_days_only_and_scope_preserves_hidden_expansion(self):
        app = self.page(expanded=('2026-10-03',))
        store = app.session_state['store']
        before = (store.notices(), store.submissions(), store.results())
        self.assertTrue(app.button(key='schedule_collapse_all').disabled)
        self.assertFalse(app.button(key='schedule_expand_all').disabled)
        app.button(key='schedule_expand_all').click().run()
        self.assertTrue(app.button(key='schedule_expand_all').disabled)
        self.assertEqual(app.session_state['schedule_expanded_dates'], {'2026-10-03', '2026-10-23', '2026-10-25'})
        self.assertEqual(self.notice_count(app), 2)
        app.button(key='schedule_collapse_all').click().run()
        self.assertEqual(app.session_state['schedule_expanded_dates'], {'2026-10-03'})
        app.button(key='schedule_scope_toggle').click().run()
        self.assertEqual(self.notice_count(app), 1)
        self.assertIn('home_day_notices_2026-10-03', {item.key for item in app.button})
        app.button(key='schedule_expand_all').click().run()
        self.assertEqual(self.notice_count(app), 12)
        self.assertEqual((store.notices(), store.submissions(), store.results()), before)

    def test_empty_selected_week_disables_bulk_and_month_switch_keeps_hidden_dates(self):
        app = self.page(expanded=('2026-10-03',))
        app.selectbox(key='schedule_month').set_value('2026-11').run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button(key='schedule_expand_all').disabled)
        self.assertTrue(app.button(key='schedule_collapse_all').disabled)
        self.assertEqual(app.session_state['schedule_expanded_dates'], {'2026-10-03'})
        app.button(key='schedule_scope_toggle').click().run()
        app.button(key='schedule_expand_all').click().run()
        self.assertEqual(app.session_state['schedule_expanded_dates'], {'2026-10-03', '2026-11-03'})
        app.selectbox(key='schedule_month').set_value('2026-10').run()
        self.assertEqual(self.notice_count(app), 1)

    def test_empty_groups_keep_registration_guidance(self):
        app = self.page()
        store = app.session_state['store']
        for row in store.notices():
            store.delete_notice(row['id'])
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('등록된 개찰 일정이 없습니다' in item.value for item in app.info))


if __name__ == '__main__':
    unittest.main()
