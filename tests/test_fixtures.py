"""최근 6개월 가상 기록이 원본 샘플과 방문자별 독립성을 보존한다."""
from collections import Counter
import unittest
from unittest.mock import patch

from demo.fixtures import DAILY_NOTICE_COUNTS, create_demo_store
from demo.performance import monthly_performance
from demo.store import DemoStore


class DemoFixtureTests(unittest.TestCase):
    def store(self):
        store = create_demo_store()
        self.addCleanup(store.close)
        return store

    def test_factory_preserves_all_original_records_and_october_distribution(self):
        original = DemoStore()
        self.addCleanup(original.close)
        store = self.store()
        self.assertEqual(store.notices()[:12], original.notices())
        self.assertEqual(store.submissions()[:4], original.submissions())
        self.assertEqual(store.results()[:4], original.results())
        self.assertEqual(store.categories(), original.categories())
        self.assertEqual(len(store.notices()), 95)
        self.assertEqual((len(store.submissions()), len(store.results())), (22, 22))
        self.assertEqual(Counter(row['deadline'] for row in store.notices() if row['deadline'].startswith('2026-10')),
                         DAILY_NOTICE_COUNTS)

    def test_history_records_are_linked_unique_fictional_and_six_months_total_is_exact(self):
        store = self.store()
        notices = store.notices()
        self.assertEqual([row['code'] for row in notices], [f'DEMO-{i:03d}' for i in range(1, 96)])
        self.assertEqual(len({row['title'] for row in notices[12:]}), 83)
        for row in notices[12:]:
            self.assertTrue(all(row[field].startswith('가상 ') for field in ('title', 'agency', 'region')))
            self.assertGreater(row['base_amount'], 0)
        history_ids = {row['id'] for row in notices[77:]}
        self.assertEqual(len(history_ids), 18)
        self.assertEqual({row['notice_id'] for row in store.submissions()[4:]}, history_ids)
        self.assertEqual({row['notice_id'] for row in store.results()[4:]}, history_ids)
        monthly = monthly_performance(notices, store.submissions(), store.results(), year=2026)
        self.assertEqual(tuple(sum(row[key] for row in monthly) for key in ('bid_count', 'win_count', 'award_amount')),
                         (21, 8, 116_500_000))
        self.assertEqual(Counter(row['deadline'][:7] for row in notices[77:]),
                         {'2026-05': 2, '2026-06': 4, '2026-07': 3, '2026-08': 5, '2026-09': 4})

    def test_factory_calls_are_deterministic_and_session_independent(self):
        first, second = self.store(), self.store()
        self.assertEqual(first.notices(), second.notices())
        self.assertEqual(first.submissions(), second.submissions())
        self.assertEqual(first.results(), second.results())
        first.save_notice({**first.get_notice(1), 'memo': '별도 세션'}, notice_id=1)
        first.save_submission({**first.submissions()[-1], 'memo': '별도 세션'}, submission_id=22)
        first.save_result({**first.results()[-1], 'note': '별도 세션'})
        self.assertNotEqual(first.notices(), second.notices())
        self.assertNotEqual(first.submissions(), second.submissions())
        self.assertNotEqual(first.results(), second.results())

    def test_failure_closes_partial_store_and_preserves_error(self):
        store = DemoStore()
        self.addCleanup(store.close)
        with patch('demo.fixtures.DemoStore', return_value=store), \
             patch.object(store, 'save_result', side_effect=ValueError('가상 결과 저장 실패')), \
             patch.object(store, 'close', wraps=store.close) as close:
            with self.assertRaisesRegex(ValueError, '가상 결과 저장 실패'):
                create_demo_store()
            close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
