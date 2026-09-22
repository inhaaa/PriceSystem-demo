import unittest

from demo.services import api_response, authenticate, recommendation


class ServiceTests(unittest.TestCase):
    def test_demo_credentials_are_exact(self):
        self.assertTrue(authenticate("admin", "admin"))
        for username, password in (("ADMIN", "admin"), ("admin ", "admin"), ("admin", "wrong"), ("", "")):
            self.assertFalse(authenticate(username, password))

    def test_recommendation_is_canned_independent_and_labeled(self):
        for scenario in ("샘플 A", "샘플 B", "샘플 C"):
            data = recommendation(scenario)
            self.assertEqual(scenario, data["scenario"])
            self.assertEqual({"scenario", "label", "amount", "points", "note"}, set(data))
            self.assertIn("샘플", data["note"])
            self.assertIsInstance(data["amount"], int)
            self.assertTrue(all(set(p) == {"label", "value"} for p in data["points"]))
            data["points"].clear()
            self.assertTrue(recommendation(scenario)["points"])
        with self.assertRaises(ValueError):
            recommendation("실제 분석")

    def test_api_scenarios_and_payload_copies(self):
        normal = api_response()
        self.assertEqual({"source", "items", "total", "status", "message"}, set(normal))
        self.assertEqual("demo", normal["source"])
        self.assertEqual("ok", normal["status"])
        self.assertEqual(len(normal["items"]), normal["total"])
        self.assertGreater(normal["total"], 0)
        for item in normal["items"]:
            self.assertNotIn("id", item)
            self.assertTrue(item["code"].startswith("DEMO-API-"))
            self.assertIn("가상", item["title"])
        normal["items"][0]["title"] = "changed"
        self.assertNotEqual("changed", api_response()["items"][0]["title"])
        for scenario, status in (("빈 결과", "empty"), ("오류", "error")):
            result = api_response(scenario)
            self.assertEqual(status, result["status"])
            self.assertEqual([], result["items"])
            self.assertEqual(0, result["total"])
        with self.assertRaises(ValueError):
            api_response("실제 호출")


if __name__ == "__main__":
    unittest.main()
