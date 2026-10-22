"""세션별 투찰 검토 데이터 계약을 검증한다."""

from copy import deepcopy
import unittest

from demo import services


CHECKS = {
    "eligibility": False,
    "documents": False,
    "amount": False,
    "schedule": False,
}


class ReviewTests(unittest.TestCase):
    def test_contract_constants_are_fixed(self):
        self.assertEqual(
            ("검토대기", "준비중", "검토완료", "보류"),
            getattr(services, "REVIEW_STATUSES", None),
        )
        self.assertEqual(
            (
                ("eligibility", "참가 자격·조건 확인"),
                ("documents", "필수 서류 준비"),
                ("amount", "투찰금액 확인"),
                ("schedule", "제출 일정 확인"),
            ),
            getattr(services, "REVIEW_CHECKS", None),
        )

    def test_get_default_does_not_change_session(self):
        reviews = {}
        actual = services.get_review(reviews, 1)
        self.assertEqual({"status": "검토대기", "checks": CHECKS, "note": ""}, actual)
        self.assertEqual({}, reviews)

    def test_default_reviews_have_independent_nested_checks(self):
        reviews = {}
        first = services.get_review(reviews, 1)
        first["checks"]["amount"] = True
        first["note"] = "별도 메모"
        self.assertEqual(CHECKS, services.get_review(reviews, 1)["checks"])
        self.assertEqual(CHECKS, services.get_review(reviews, 2)["checks"])

    def test_get_saved_review_returns_deep_copy(self):
        reviews = {1: {"status": "준비중", "checks": dict(CHECKS), "note": "기존 메모"}}
        actual = services.get_review(reviews, 1)
        actual["checks"]["amount"] = True
        actual["status"] = "보류"
        actual["note"] = "외부 변경"
        self.assertEqual(CHECKS, reviews[1]["checks"])
        self.assertEqual("준비중", reviews[1]["status"])
        self.assertEqual("기존 메모", reviews[1]["note"])

    def test_save_copies_input_and_return_value(self):
        reviews = {}
        checks = dict(CHECKS, eligibility=True)
        actual = services.save_review(reviews, 1, status="준비중", checks=checks, note="확인 예정")
        self.assertEqual(
            {"status": "준비중", "checks": dict(CHECKS, eligibility=True), "note": "확인 예정"},
            actual,
        )
        checks["amount"] = True
        actual["checks"]["schedule"] = True
        actual["note"] = "반환값 변경"
        self.assertFalse(reviews[1]["checks"]["amount"])
        self.assertFalse(reviews[1]["checks"]["schedule"])
        self.assertEqual("확인 예정", reviews[1]["note"])

    def test_non_complete_statuses_accept_any_check_count(self):
        reviews = {}
        for status in ("검토대기", "준비중", "보류"):
            for complete in (False, True):
                with self.subTest(status=status, complete=complete):
                    checks = {key: complete for key in CHECKS}
                    actual = services.save_review(reviews, 1, status=status, checks=checks)
                    self.assertEqual(status, actual["status"])
                    self.assertEqual(checks, actual["checks"])
                    self.assertEqual("", actual["note"])

    def test_complete_status_requires_every_check(self):
        reviews = {}
        checks = {key: True for key in CHECKS}
        actual = services.save_review(reviews, 1, status="검토완료", checks=checks)
        self.assertEqual("검토완료", actual["status"])
        self.assertEqual(actual, reviews[1])

    def test_incomplete_save_preserves_original_review(self):
        for missing_key in CHECKS:
            with self.subTest(missing_key=missing_key):
                reviews = {1: {"status": "준비중", "checks": dict(CHECKS), "note": "원래 메모"}}
                original = reviews[1]
                before = deepcopy(reviews)
                checks = {key: key != missing_key for key in CHECKS}
                with self.assertRaises(ValueError):
                    services.save_review(reviews, 1, status="검토완료", checks=checks, note="새 메모")
                self.assertEqual(before, reviews)
                self.assertIs(original, reviews[1])

    def test_invalid_first_save_does_not_create_review(self):
        reviews = {}
        with self.assertRaises(ValueError):
            services.save_review(reviews, 1, status="검토완료", checks=CHECKS)
        self.assertEqual({}, reviews)

    def test_invalid_ids_are_rejected_for_get_and_save(self):
        for notice_id in (0, -1, True, False, 1.0, "1", None, [], {}):
            with self.subTest(notice_id=notice_id):
                reviews = {}
                with self.assertRaises(ValueError):
                    services.get_review(reviews, notice_id)
                with self.assertRaises(ValueError):
                    services.save_review(reviews, notice_id, status="준비중", checks=CHECKS)
                self.assertEqual({}, reviews)

    def test_invalid_statuses_preserve_original(self):
        for status in ("", "완료", " 검토대기", None, True, 1, [], {}):
            with self.subTest(status=status):
                self.assert_invalid_save_preserves_original(status=status)

    def test_checks_require_dictionary_with_exact_keys(self):
        invalid_checks = (
            None, False, "", [], tuple(CHECKS.items()),
            {}, {key: False for key in CHECKS if key != "amount"},
            dict(CHECKS, extra=False), {**CHECKS, 1: False},
        )
        for checks in invalid_checks:
            with self.subTest(checks=checks):
                self.assert_invalid_save_preserves_original(checks=checks)

    def test_each_check_requires_boolean_value(self):
        for key in CHECKS:
            for value in (0, 1, None, "true", [], {}):
                with self.subTest(key=key, value=value):
                    self.assert_invalid_save_preserves_original(checks={**CHECKS, key: value})

    def test_note_requires_string_with_at_most_1000_trimmed_characters(self):
        for note in (None, True, 1, [], {}, "가" * 1001):
            with self.subTest(note_type=type(note).__name__):
                self.assert_invalid_save_preserves_original(note=note)
        reviews = {}
        actual = services.save_review(
            reviews, 1, status="준비중", checks=CHECKS, note=" \n" + "가" * 1000 + "\t "
        )
        self.assertEqual("가" * 1000, actual["note"])

    def test_note_is_trimmed_and_kept_as_plain_text(self):
        reviews = {}
        actual = services.save_review(
            reviews, 1, status="보류", checks=CHECKS, note=" \n<script>확인</script>\n후속 검토\t "
        )
        self.assertEqual("<script>확인</script>\n후속 검토", actual["note"])

    def test_different_notices_remain_independent(self):
        reviews = {}
        first = services.save_review(reviews, 1, status="준비중", checks=CHECKS, note="첫 공고")
        services.save_review(reviews, 2, status="보류", checks=dict(CHECKS, amount=True), note="다른 공고")
        self.assertEqual(first, services.get_review(reviews, 1))
        self.assertEqual("다른 공고", services.get_review(reviews, 2)["note"])

    def test_different_sessions_remain_independent(self):
        first_session, second_session = {}, {}
        services.save_review(first_session, 1, status="준비중", checks=dict(CHECKS, amount=True), note="첫 세션")
        self.assertEqual({"status": "검토대기", "checks": CHECKS, "note": ""}, services.get_review(second_session, 1))
        services.save_review(second_session, 1, status="보류", checks=CHECKS, note="다른 세션")
        self.assertEqual("첫 세션", services.get_review(first_session, 1)["note"])
        self.assertEqual("다른 세션", services.get_review(second_session, 1)["note"])

    def assert_invalid_save_preserves_original(self, **overrides):
        reviews = {1: {"status": "준비중", "checks": dict(CHECKS), "note": "원래 메모"}}
        before = deepcopy(reviews)
        values = {"status": "보류", "checks": dict(CHECKS), "note": "새 메모", **overrides}
        with self.assertRaises(ValueError):
            services.save_review(reviews, 1, **values)
        self.assertEqual(before, reviews)


if __name__ == "__main__":
    unittest.main()
