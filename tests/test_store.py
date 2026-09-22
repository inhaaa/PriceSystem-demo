import csv
import gc
import io
import sqlite3
import unittest

from demo.store import DemoStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = DemoStore()
        self.addCleanup(self.store.close)
        self.notice = {
            **self.store.notices()[0],
            "code": "DEMO-TEST-001",
            "title": "가상 테스트 공고",
        }
        self.notice.pop("id")

    def csv_bytes(self, rows):
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(self.notice))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode("utf-8-sig")

    def test_seed_is_in_memory_and_isolated_then_reset(self):
        other = DemoStore()
        self.addCleanup(other.close)
        self.assertEqual(12, len(self.store.notices()))
        self.assertEqual(3, len(self.store.categories()))
        self.assertEqual(4, len(self.store.submissions()))
        self.assertEqual(4, len(self.store.results()))
        self.assertTrue(all(n["code"].startswith("DEMO-") for n in self.store.notices()))
        self.store.save_notice(self.notice)
        self.assertEqual(12, len(other.notices()))
        self.store.reset()
        self.assertEqual(other.notices(), self.store.notices())
        self.assertEqual(other.submissions(), self.store.submissions())

    def test_collection_closes_the_connection(self):
        store = DemoStore()
        connection = store._db
        store = None
        gc.collect()
        try:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")
        finally:
            connection.close()

    def test_deadline_matches_the_ui_date_range(self):
        for deadline in ("0001-01-01", "1999-12-31", "2101-01-01"):
            with self.subTest(deadline=deadline), self.assertRaisesRegex(ValueError, "2000-01-01.*2100-12-31"):
                self.store.save_notice({**self.notice, "deadline": deadline})
        self.assertEqual(12, len(self.store.notices()))
        notice_id = self.store.save_notice({**self.notice, "deadline": "2000-01-01"})
        self.store.save_notice({**self.notice, "deadline": "2100-12-31"}, notice_id)
        self.assertEqual("2100-12-31", self.store.get_notice(notice_id)["deadline"])

    def test_notice_create_edit_search_delete_and_cascade(self):
        notice_id = self.store.save_notice(self.notice)
        self.assertEqual(1, len(self.store.notices(query="가상 테스트")))
        updated = {**self.notice, "title": "가상 변경 공고", "status": "완료"}
        self.store.save_notice(updated, notice_id)
        self.assertEqual("가상 변경 공고", self.store.get_notice(notice_id)["title"])
        self.assertEqual([notice_id], [n["id"] for n in self.store.notices("가상 변경", self.notice["category"], "완료")])
        self.store.save_submission(dict(notice_id=notice_id, company="가상 데모 참가자", amount=100, status="작성중", memo=""))
        self.store.save_result(dict(notice_id=notice_id, outcome="검토중", amount=0, note="데모"))
        self.store.delete_notice(notice_id)
        self.assertFalse(any(n["notice_id"] == notice_id for n in self.store.submissions()))
        self.assertFalse(any(n["notice_id"] == notice_id for n in self.store.results()))
        with self.assertRaisesRegex(ValueError, "찾을 수"):
            self.store.get_notice(notice_id)

    def test_notice_validation_and_uniqueness(self):
        invalid = [(key, " ") for key in ("code", "title", "agency", "category", "region")]
        invalid += [("code", "REAL-1"), ("category", "없는 분류"), ("status", "잘못된 상태"), ("deadline", "2026-02-30"), ("deadline", "20261001")]
        invalid += [("base_amount", n) for n in (-1, 10**12 + 1, 1.5, "1.5", True)]
        for key, value in invalid:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.store.save_notice({**self.notice, key: value})
        self.assertEqual(12, len(self.store.notices()))
        self.store.save_notice(self.notice)
        with self.assertRaisesRegex(ValueError, "코드"):
            self.store.save_notice(self.notice)

    def test_oversized_numeric_input_has_a_korean_validation_message(self):
        with self.assertRaisesRegex(ValueError, "금액"):
            self.store.save_notice({**self.notice, "base_amount": "9" * 5000})

    def test_template_without_categories_has_a_validation_message(self):
        for notice in self.store.notices():
            self.store.delete_notice(notice["id"])
        for category in self.store.categories():
            self.store.delete_category(category)
        with self.assertRaisesRegex(ValueError, "분류"):
            self.store.csv_template()

    def test_category_rename_propagates_and_in_use_delete_fails(self):
        old = self.notice["category"]
        self.store.rename_category(old, "가상 변경분류")
        self.assertTrue(self.store.notices(category="가상 변경분류"))
        self.assertFalse(self.store.notices(category=old))
        with self.assertRaises(ValueError):
            self.store.delete_category("가상 변경분류")
        self.store.add_category("가상 임시분류")
        self.store.delete_category("가상 임시분류")
        self.assertNotIn("가상 임시분류", self.store.categories())
        with self.assertRaises(ValueError):
            self.store.add_category(" ")
        with self.assertRaises(ValueError):
            self.store.add_category(self.store.categories()[0])

    def test_submission_and_result_crud_join_titles(self):
        notice_id = self.store.notices()[0]["id"]
        submission = dict(notice_id=notice_id, company="가상 참가자 테스트", amount=123, status="작성중", memo="데모")
        submission_id = self.store.save_submission(submission)
        self.store.save_submission({**submission, "status": "제출완료"}, submission_id)
        saved = next(s for s in self.store.submissions() if s["id"] == submission_id)
        self.assertEqual("제출완료", saved["status"])
        self.assertEqual(self.store.get_notice(notice_id)["code"], saved["notice_code"])
        self.assertIn("notice_title", saved)
        self.store.delete_submission(submission_id)
        result = dict(notice_id=notice_id, outcome="샘플 낙찰", amount=456, note="가상 표시값")
        self.assertEqual(notice_id, self.store.save_result(result))
        self.store.save_result({**result, "outcome": "샘플 미선정"})
        results = [r for r in self.store.results() if r["notice_id"] == notice_id]
        self.assertEqual(1, len(results))
        self.assertEqual("샘플 미선정", results[0]["outcome"])
        self.assertIn("notice_title", results[0])
        self.assertIn("notice_code", results[0])
        self.store.delete_result(notice_id)

    def test_unknown_ids_and_invalid_submission_result_are_rejected(self):
        for operation in (
            lambda: self.store.save_notice(self.notice, 99999),
            lambda: self.store.delete_notice(99999),
            lambda: self.store.delete_submission(99999),
            lambda: self.store.delete_result(99999),
            lambda: self.store.rename_category("없는 분류", "가상 새분류"),
            lambda: self.store.delete_category("없는 분류"),
            lambda: self.store.save_submission(dict(notice_id=99999, company="가상", amount=1, status="작성중")),
            lambda: self.store.save_result(dict(notice_id=99999, outcome="검토중", amount=0)),
            lambda: self.store.save_submission(dict(notice_id=1, company="", amount=-1, status="오류")),
            lambda: self.store.save_result(dict(notice_id=1, outcome="오류", amount=-1)),
        ):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                operation()

    def test_csv_valid_and_template_headers(self):
        data = self.csv_bytes([self.notice, {**self.notice, "code": "DEMO-TEST-002"}])
        self.assertEqual(2, self.store.import_csv(data))
        template = self.store.csv_template()
        self.assertTrue(template.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(list(self.notice), next(csv.reader(io.StringIO(template.decode("utf-8-sig")))))

    def test_csv_validation_is_atomic_and_bounded(self):
        invalid_batches = [
            self.csv_bytes([self.notice, {**self.notice, "code": "DEMO-TEST-002", "base_amount": -1}]),
            self.csv_bytes([self.notice, self.notice]),
            b"wrong,header\n1,2\n",
            b"\xff\xfe\xff",
            b"x" * (2 * 1024 * 1024 + 1),
            self.csv_bytes([{**self.notice, "code": f"DEMO-BULK-{n}"} for n in range(101)]),
            self.csv_bytes([self.notice]).replace(b",memo", b",unknown"),
            self.csv_bytes([]),
        ]
        for data in invalid_batches:
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                self.store.import_csv(data)
            self.assertEqual(12, len(self.store.notices()))


if __name__ == "__main__":
    unittest.main()
