"""Caddy 후보 생성은 기존 설정과 비밀 값을 보존해야 한다."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = b"""http://pricesys.cloud {
    bind 192.0.2.10
    redir https://pricesys.cloud{uri} permanent
}
https://pricesys.cloud {
    bind 192.0.2.10
    basic_auth {
        sample placeholder-hash
    }
    reverse_proxy 127.0.0.1:8501
}
https://inhaaa.com {
    bind 192.0.2.10
    root * /srv/inhaa-portfolio/current
    file_server
}
"""


class CaddyCandidateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.source = self.folder / "Caddyfile"
        self.source.write_bytes(ORIGINAL)
        self.state = self.folder / "state"
        self.template = ROOT / "deploy/Caddyfile.demo.example"

    def helper(self):
        path = ROOT / "deploy/prepare_caddy.py"
        self.assertTrue(path.is_file(), "안전한 Caddy 후보 생성 도구가 필요합니다")
        spec = importlib.util.spec_from_file_location("prepare_caddy", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_prepares_private_backup_and_candidate_without_changing_live_file(self):
        backup, candidate = self.helper().prepare(self.source, self.template, self.state)
        self.assertEqual(self.source.read_bytes(), ORIGINAL)
        self.assertEqual(backup.read_bytes(), ORIGINAL)
        rendered = candidate.read_bytes()
        self.assertTrue(rendered.startswith(ORIGINAL))
        addition = rendered[len(ORIGINAL):]
        self.assertEqual(addition.count(b"bind 192.0.2.10"), 2)
        self.assertIn(b"reverse_proxy 127.0.0.1:8502", addition)
        self.assertNotIn(b"__CONFIRMED_BIND_ADDRESSES__", addition)
        self.assertEqual((self.state / "caddy-backup-path").read_text().strip(), str(backup))
        if os.name == "posix":
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(candidate.stat().st_mode & 0o777, 0o600)

    def test_rejects_different_bind_values_before_writing(self):
        self.source.write_bytes(ORIGINAL.replace(b"bind 192.0.2.10", b"bind 192.0.2.11", 1))
        with self.assertRaises(ValueError):
            self.helper().prepare(self.source, self.template, self.state)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.folder / "Caddyfile.demo-candidate").exists())

    def test_rejects_missing_bind_and_external_imports(self):
        helper = self.helper()
        for source in (b"example.com {\n respond ok\n}\n", ORIGINAL + b"import other-sites\n"):
            with self.subTest(source=source):
                self.source.write_bytes(source)
                with self.assertRaises(ValueError):
                    helper.prepare(self.source, self.template, self.state)
                self.assertEqual(self.source.read_bytes(), source)

    def test_rejects_existing_demo_configuration(self):
        source = ORIGINAL + b"demo.inhaaa.com {\n respond ok\n}\n"
        self.source.write_bytes(source)
        with self.assertRaises(ValueError):
            self.helper().prepare(self.source, self.template, self.state)
        self.assertEqual(self.source.read_bytes(), source)

    def test_does_not_overwrite_an_existing_candidate(self):
        candidate = self.folder / "Caddyfile.demo-candidate"
        candidate.write_bytes(b"previous candidate")
        with self.assertRaises(FileExistsError):
            self.helper().prepare(self.source, self.template, self.state)
        self.assertEqual(candidate.read_bytes(), b"previous candidate")
        self.assertEqual(self.source.read_bytes(), ORIGINAL)

    def test_does_not_replace_an_existing_backup_record(self):
        self.state.mkdir()
        record = self.state / "caddy-backup-path"
        record.write_text("previous backup")
        with self.assertRaises(FileExistsError):
            self.helper().prepare(self.source, self.template, self.state)
        self.assertEqual(record.read_text(), "previous backup")
        self.assertEqual(self.source.read_bytes(), ORIGINAL)


if __name__ == "__main__":
    unittest.main()
