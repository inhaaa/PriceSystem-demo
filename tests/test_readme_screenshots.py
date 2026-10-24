"""README 스크린샷은 이미지별 마지막 커밋 URL로 고정한다."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RAW_PREFIX = "https://raw.githubusercontent.com/inhaaa/PriceSystem-demo"


class ScreenshotHelper:
    def helper(self):
        path = ROOT / "scripts/update_readme_screenshots.py"
        self.assertTrue(path.is_file(), "README 스크린샷 URL 자동 갱신 도구가 필요합니다")
        spec = importlib.util.spec_from_file_location("update_readme_screenshots_test", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module


class ReadmeScreenshotContractTests(ScreenshotHelper, unittest.TestCase):
    def test_exposes_update_readme_function_without_requiring_git(self):
        self.assertTrue(callable(getattr(self.helper(), "update_readme", None)),
                        "update_readme(root, *, check=False) 함수가 필요합니다")


@unittest.skipUnless(shutil.which("git"), "이미지 커밋 통합 테스트에는 Git이 필요합니다")
class ReadmeScreenshotGitTests(ScreenshotHelper, unittest.TestCase):
    def git(self, root, *arguments):
        result = subprocess.run(
            ["git", "-c", "user.name=Screenshot Test", "-c", "user.email=screenshot@example.invalid",
             "-c", "core.autocrlf=false", "-C", str(root), *arguments],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        return result.stdout.strip()

    def commit(self, root, *paths):
        self.git(root, "add", "--", *paths)
        self.git(root, "commit", "-q", "-m", "Screenshot test fixture")
        return self.git(root, "rev-parse", "HEAD")

    def url(self, commit, image):
        return f"{RAW_PREFIX}/{commit}/docs/images/{image}"

    def fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        images = root / "docs/images"
        images.mkdir(parents=True)
        (images / "login.png").write_bytes(b"login screenshot version one\n")
        (images / "home.png").write_bytes(b"home screenshot version one\n")
        readme = root / "README.md"
        readme.write_bytes(b"# Screenshot fixture\n")
        self.git(root, "init", "-q")
        original_commit = self.commit(root, "docs/images", "README.md")
        readme.write_text(
            f"# 화면 미리보기\n\n![로그인]({self.url(original_commit, 'login.png')})\n"
            f"![홈]({self.url(original_commit, 'home.png')})\n",
            encoding="utf-8", newline="",
        )
        return root, original_commit

    def old_mtime(self, path):
        timestamp = 1_600_000_000_000_000_000
        os.utime(path, ns=(timestamp, timestamp))
        return path.stat().st_mtime_ns

    def test_replacing_one_image_updates_only_its_immutable_url(self):
        helper = self.helper()
        root, original_commit = self.fixture()
        readme = root / "README.md"
        before = readme.read_bytes()
        (root / "docs/images/login.png").write_bytes(b"replacement login screenshot\n")
        image_commit = self.commit(root, "docs/images/login.png")

        self.assertTrue(helper.update_readme(root))

        self.assertEqual(readme.read_bytes(), before.replace(
            self.url(original_commit, "login.png").encode(),
            self.url(image_commit, "login.png").encode(),
        ))
        self.assertIn(self.url(original_commit, "home.png").encode(), readme.read_bytes())

    def test_readme_and_other_code_commits_do_not_change_image_urls_or_write_readme(self):
        helper = self.helper()
        root, original_commit = self.fixture()
        readme = root / "README.md"
        (root / "example.py").write_bytes(b"print('unrelated code')\n")
        unrelated_commit = self.commit(root, "README.md", "example.py")
        self.assertNotEqual(original_commit, unrelated_commit)
        before = readme.read_bytes()
        previous_mtime = self.old_mtime(readme)

        self.assertFalse(helper.update_readme(root))

        self.assertEqual(readme.read_bytes(), before)
        self.assertEqual(readme.stat().st_mtime_ns, previous_mtime)

    def test_check_mode_never_writes_and_updated_readme_is_idempotent(self):
        helper = self.helper()
        root, original_commit = self.fixture()
        readme = root / "README.md"
        before = readme.read_bytes()
        (root / "docs/images/login.png").write_bytes(b"new screenshot\n")
        image_commit = self.commit(root, "docs/images/login.png")
        previous_mtime = self.old_mtime(readme)

        self.assertTrue(helper.update_readme(root, check=True))
        self.assertEqual(readme.read_bytes(), before)
        self.assertEqual(readme.stat().st_mtime_ns, previous_mtime)
        self.assertTrue(helper.update_readme(root))
        expected = before.replace(self.url(original_commit, "login.png").encode(),
                                  self.url(image_commit, "login.png").encode())
        self.assertEqual(readme.read_bytes(), expected)
        updated_mtime = self.old_mtime(readme)

        self.assertFalse(helper.update_readme(root, check=True))
        self.assertFalse(helper.update_readme(root))
        self.assertEqual(readme.read_bytes(), expected)
        self.assertEqual(readme.stat().st_mtime_ns, updated_mtime)

    def test_relative_raster_links_use_each_files_last_commit(self):
        helper = self.helper()
        root, original_commit = self.fixture()
        for name in ("backtest.jpg", "review.jpeg", "analysis.webp"):
            (root / "docs/images" / name).write_bytes(name.encode())
        later_commit = self.commit(root, "docs/images/backtest.jpg",
                                   "docs/images/review.jpeg", "docs/images/analysis.webp")
        names = ("login.png", "backtest.jpg", "review.jpeg", "analysis.webp")
        readme = root / "README.md"
        readme.write_text("".join(f"![{name}](docs/images/{name})\n" for name in names),
                          encoding="utf-8", newline="")

        self.assertTrue(helper.update_readme(root))

        expected = "".join(
            f"![{name}]({self.url(original_commit if name == 'login.png' else later_commit, name)})\n"
            for name in names
        )
        self.assertEqual(readme.read_bytes(), expected.encode("utf-8"))

    def test_invalid_references_are_all_validated_before_any_readme_write(self):
        helper = self.helper()
        cases = (
            ("missing", "missing.png", r"missing|not found|exist|없|누락"),
            ("untracked", "untracked.png", r"untracked|tracked|commit|추적|커밋"),
            ("modified", "home.png", r"uncommitted|modified|dirty|commit|미커밋|변경|커밋"),
            ("staged", "home.png", r"uncommitted|modified|dirty|commit|미커밋|변경|커밋"),
        )
        for state, image, reason in cases:
            with self.subTest(state=state):
                root, original_commit = self.fixture()
                (root / "docs/images/login.png").write_bytes(b"committed replacement\n")
                self.commit(root, "docs/images/login.png")
                image_path = root / "docs/images" / image
                if state != "missing":
                    image_path.write_bytes(b"not committed screenshot\n")
                if state == "staged":
                    self.git(root, "add", "--", "docs/images/home.png")
                readme = root / "README.md"
                before = (
                    f"![valid first]({self.url(original_commit, 'login.png')})\n"
                    f"![invalid later](docs/images/{image})\n"
                ).encode("utf-8")
                readme.write_bytes(before)
                previous_mtime = self.old_mtime(readme)

                for check in (False, True):
                    with self.subTest(check=check):
                        with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)) as error:
                            helper.update_readme(root, check=check)
                        self.assertIn(image, str(error.exception))
                        self.assertRegex(str(error.exception).lower(), reason)
                        self.assertEqual(readme.read_bytes(), before)
                        self.assertEqual(readme.stat().st_mtime_ns, previous_mtime)

    def test_preserves_crlf_alt_svg_and_content_outside_target_markdown_images(self):
        helper = self.helper()
        root, original_commit = self.fixture()
        readme = root / "README.md"
        old_url = self.url("main", "login.png")
        source = (
            "# 화면 미리보기\r\n\r\n"
            f"![로그인 화면 — 가상 샘플]({old_url})\r\n"
            "![로고](docs/images/logo.svg)\r\n"
            f"![원격 로고]({RAW_PREFIX}/main/docs/images/logo.svg)\r\n"
            "![외부 화면](https://raw.githubusercontent.com/other/repository/main/docs/images/missing.png)\r\n"
            "[이미지 다운로드](docs/images/missing.jpg)\r\n"
            '<img src="docs/images/missing.png" alt="HTML 이미지">\r\n'
            f"문구 속 URL: {RAW_PREFIX}/main/docs/images/missing.png\r\n"
        ).encode("utf-8")
        readme.write_bytes(source)

        self.assertTrue(helper.update_readme(root))

        self.assertEqual(readme.read_bytes(), source.replace(
            old_url.encode(), self.url(original_commit, "login.png").encode(),
        ))


if __name__ == "__main__":
    unittest.main()
