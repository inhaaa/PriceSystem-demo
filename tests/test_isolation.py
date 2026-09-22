"""The public demo must run without external systems or persistent business data."""
import ast
from pathlib import Path
import socket
import sqlite3
import unittest
from unittest.mock import patch

from demo.services import api_response, recommendation
from demo.store import DemoStore


ROOT = Path(__file__).resolve().parents[1]


class IsolationTests(unittest.TestCase):
    def test_csv_export_keeps_user_text_from_becoming_spreadsheet_formulas(self):
        from demo.ui import csv_bytes
        import csv
        import io

        rows = [{"공고명": value, "금액": 42} for value in ["=1+1", " +1", "-1", "@SUM(1)", "\t=1", "가상 공고"]]
        exported = list(csv.DictReader(io.StringIO(csv_bytes(rows).decode("utf-8-sig"))))
        self.assertTrue(all(row["공고명"].startswith("'") for row in exported[:5]))
        self.assertEqual(exported[-1], {"공고명": "가상 공고", "금액": "42"})

    def test_allowlist_excludes_runtime_data_and_contains_all_local_assets(self):
        files = (ROOT / "PUBLIC_FILES.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(files), len(set(files)))
        for relative in files:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertFalse(Path(relative).is_absolute(), relative)
            self.assertFalse(set(Path(relative).parts) & {"..", ".git", ".local", ".venv", "data", "uploads", "logs"}, relative)
            self.assertNotIn(path.suffix.lower(), {".db", ".sqlite", ".sqlite3", ".log", ".pem", ".key"}, relative)
            self.assertNotIn(path.name.lower(), {".env", "secrets.toml", "users.json"}, relative)

    def test_application_has_only_declared_imports(self):
        allowed = {"base64", "csv", "datetime", "html", "io", "json", "re", "pathlib", "sqlite3", "pandas", "streamlit", "demo"}
        for path in [ROOT / "app.py", *sorted((ROOT / "demo").glob("*.py"))]:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""]
                else:
                    continue
                for module in imports:
                    self.assertIn(module.split(".")[0], allowed, f"Unexpected dependency in {path.name}")

    def test_crud_samples_and_reset_need_no_network_or_disk_database(self):
        connect = sqlite3.connect

        def memory_only(database, *args, **kwargs):
            self.assertEqual(database, ":memory:")
            return connect(database, *args, **kwargs)

        with patch.object(sqlite3, "connect", side_effect=memory_only), \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")), \
                patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")):
            store = DemoStore()
            try:
                for row in api_response()["items"]:
                    store.save_notice(row)
                store.import_csv(store.csv_template())
                for scenario in ["샘플 A", "샘플 B", "샘플 C"]:
                    self.assertTrue(recommendation(scenario)["points"])
                store.reset()
                self.assertEqual(len(store.notices()), 12)
                self.assertTrue(all(row[2] == "" for row in store._db.execute("PRAGMA database_list")))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
