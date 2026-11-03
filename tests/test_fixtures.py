"""2025~2027년 가상 기록의 기간·연결 관계·세션 독립성을 검증한다."""
from collections import Counter
from datetime import date, timedelta
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
        self.assertEqual(Counter(row['deadline'] for row in store.notices()[:95] if row['deadline'].startswith('2026-10')),
                         DAILY_NOTICE_COUNTS)

    def test_history_records_are_linked_unique_fictional_and_six_months_total_is_exact(self):
        store = self.store()
        notices = store.notices()[:95]
        self.assertEqual([row['code'] for row in notices], [f'DEMO-{i:03d}' for i in range(1, 96)])
        self.assertEqual(len({row['title'] for row in notices[12:]}), 83)
        for row in notices[12:]:
            self.assertTrue(all(row[field].startswith('가상 ') for field in ('title', 'agency', 'region')))
            self.assertGreater(row['base_amount'], 0)
        history_ids = {row['id'] for row in notices[77:]}
        self.assertEqual(len(history_ids), 18)
        self.assertEqual({row['notice_id'] for row in store.submissions()[4:22]}, history_ids)
        self.assertEqual({row['notice_id'] for row in store.results()[4:22]}, history_ids)
        monthly = monthly_performance(notices, store.submissions()[:22], store.results()[:22], year=2026)
        self.assertEqual(tuple(sum(row[key] for row in monthly) for key in ('bid_count', 'win_count', 'award_amount')),
                         (21, 9, 123_500_000))
        self.assertEqual(Counter(row['deadline'][:7] for row in notices[77:]),
                         {'2026-05': 2, '2026-06': 4, '2026-07': 3, '2026-08': 5, '2026-09': 4})

    def test_every_day_and_monthly_category_have_linked_samples_for_three_years(self):
        store = self.store()
        notices, submissions, results = store.notices(), store.submissions(), store.results()
        start, end = date(2025, 1, 1), date(2027, 12, 31)
        days = {(start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)}
        self.assertEqual({row['deadline'] for row in notices}, days)
        added_ids = {row['id'] for row in notices[95:]}
        self.assertEqual({row['notice_id'] for row in submissions[22:]}, added_ids)
        self.assertEqual({row['notice_id'] for row in results[22:]}, added_ids)
        self.assertEqual(len(submissions[22:]), len(added_ids))
        self.assertEqual(len(results[22:]), len(added_ids))
        for year in range(2025, 2028):
            for category in store.categories():
                monthly = monthly_performance(notices, submissions, results, year=year, category=category)
                for row in monthly:
                    with self.subTest(year=year, category=category, month=row['month']):
                        self.assertGreater(row['bid_count'], 0)
                        self.assertGreater(row['win_count'], 0)
                        self.assertGreater(row['award_amount'], 0)

    def test_generated_records_are_unique_fictional_varied_and_consistent(self):
        store = self.store()
        notices = store.notices()
        self.assertGreater(len(notices), 1095)
        self.assertEqual(len({row['code'] for row in notices}), len(notices))
        self.assertEqual(len({row['title'] for row in notices}), len(notices))
        added = notices[95:]
        self.assertEqual({row['status'] for row in added}, {'접수중', '마감', '완료'})
        self.assertGreater(len(set(Counter(row['deadline'] for row in added).values())), 1)
        submissions = {row['notice_id']: row for row in store.submissions()}
        results = {row['notice_id']: row for row in store.results()}
        for row in added:
            self.assertTrue(all(row[field].startswith('가상 ') for field in ('title', 'agency', 'region')))
            self.assertIn(row['category'], store.categories())
            submission, result = submissions[row['id']], results[row['id']]
            self.assertTrue(submission['company'].startswith('가상 '))
            self.assertGreater(submission['amount'], 0)
            self.assertLessEqual(submission['amount'], row['base_amount'])
            if row['status'] == '완료':
                self.assertEqual(submission['status'], '제출완료')
                self.assertIn(result['outcome'], ('샘플 낙찰', '샘플 미선정'))
                self.assertGreater(result['amount'], 0)
                self.assertLessEqual(result['amount'], submission['amount'])
            else:
                self.assertEqual(submission['status'], '작성중' if row['status'] == '접수중' else '제출완료')
                self.assertEqual((result['outcome'], result['amount']), ('검토중', 0))

    def test_factory_calls_are_deterministic_and_session_independent(self):
        first, second = self.store(), self.store()
        self.assertEqual(first.notices(), second.notices())
        self.assertEqual(first.submissions(), second.submissions())
        self.assertEqual(first.results(), second.results())
        first.save_notice({**first.get_notice(1), 'memo': '별도 세션'}, notice_id=1)
        first.save_submission({**first.submissions()[-1], 'memo': '별도 세션'},
                              submission_id=first.submissions()[-1]['id'])
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
