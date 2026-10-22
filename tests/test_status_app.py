"""실제 메뉴에서 가상 투찰 비교·카드 필터·초기화를 확인한다."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / 'app.py'


class StatusAppJourney(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=20).run()
        self.assertFalse(self.app.exception)

    def tearDown(self):
        if 'store' in self.app.session_state:
            self.app.session_state['store'].close()

    def new_app(self):
        return self.app

    def login(self, app):
        app.text_input(key='login_username').set_value('admin')
        app.text_input(key='login_password').set_value('admin')
        app.button(key='login_submit').click().run()
        self.assertFalse(app.exception)
        return app

    def test_status_menu_compares_amounts_filters_cards_and_reset_clears_selection(self):
        app = self.login(self.new_app())
        app.button(key='menu_open_my_bid_status').click().run()
        self.assertFalse(app.exception)
        self.assertIn('status_card_win', {button.key for button in app.button})
        before = app.session_state['store'].notices()
        rows = app.session_state['status_display'].set_index('공고번호')
        self.assertEqual(rows.loc['DEMO-010', ['1순위 대비 차이', '1순위 대비 차이율 (%)']].tolist(),
                         ['+116,000', '+0.40%'])
        app.button(key='status_card_loss').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['status_display']), 12)
        self.assertEqual(set(app.session_state['status_display']['내 낙찰상태']), {'미낙찰'})
        self.assertEqual(app.button(key='status_card_loss').proto.type, 'primary')
        self.assertEqual(app.selectbox(key='status_outcome').value, '미낙찰')
        app.button(key='status_card_win').click().run()
        self.assertEqual(len(app.session_state['status_display']), 8)
        self.assertEqual(set(app.session_state['status_display']['내 낙찰상태']), {'낙찰'})
        self.assertEqual(app.session_state['store'].notices(), before)
        app.button(key='reset_samples').click().run()
        app.button(key='menu_open_my_bid_status').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['status_display']), 95)
        self.assertEqual(app.selectbox(key='status_outcome').value, '전체')
        self.assertEqual(app.button(key='status_card_win').proto.type, 'secondary')


if __name__ == '__main__':
    unittest.main()
