"""자동배포 설치는 검증본만 복사하고 기존 서비스와 파일을 보존한다."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SERVICE = "pricesys-demo-auto.service"
TIMER = "pricesys-demo-auto.timer"
SERVICE_BYTES = b"""[Unit]
Description=PriceSystem demo auto deployment
After=network-online.target docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/pricesys-demo/auto_deploy.py
"""
TIMER_BYTES = b"""[Unit]
Description=Check demo main for updates

[Timer]
OnBootSec=2min
OnUnitInactiveSec=60s
AccuracySec=5s

[Install]
WantedBy=timers.target
"""


class AutoDeployInstallTests(unittest.TestCase):
    def helper(self):
        path = ROOT / "deploy/auto_deploy.py"
        self.assertTrue(path.is_file(), "고정 자동배포본을 안전하게 설치하는 도구가 필요합니다")
        spec = importlib.util.spec_from_file_location("auto_deploy_install_test", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module

    def fixture(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        base = Path(directory.name)
        root = base / "source"
        deploy = root / "deploy"
        deploy.mkdir(parents=True)
        state = root / ".local/deploy"
        state.mkdir(parents=True)
        (deploy / "auto_deploy.py").write_bytes(b"# fixed updater fixture\n")
        (deploy / SERVICE).write_bytes(SERVICE_BYTES)
        (deploy / TIMER).write_bytes(TIMER_BYTES)
        (state / "verified-compose.yaml").write_bytes((ROOT / "compose.yaml").read_bytes())
        (state / "current-image").write_text("pricesys-demo:previous\n", encoding="utf-8")
        (state / "current-commit").write_text("a" * 40 + "\n", encoding="utf-8")
        return root, base / "installed", base / "systemd"

    def targets(self, destination, unit_dir):
        return (
            destination / "auto_deploy.py",
            destination / "compose.yaml",
            unit_dir / SERVICE,
            unit_dir / TIMER,
        )

    def source_bytes(self, root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}

    def test_copies_only_fixed_script_verified_compose_and_units_without_running_commands(self):
        helper = self.helper()
        root, destination, unit_dir = self.fixture()
        before = self.source_bytes(root)
        with patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
            helper.install(root, destination, unit_dir)
        run.assert_not_called()
        popen.assert_not_called()
        self.assertEqual((destination / "auto_deploy.py").read_bytes(),
                         (root / "deploy/auto_deploy.py").read_bytes())
        self.assertEqual((destination / "compose.yaml").read_bytes(),
                         (root / ".local/deploy/verified-compose.yaml").read_bytes())
        self.assertEqual((unit_dir / SERVICE).read_bytes(), SERVICE_BYTES)
        self.assertEqual((unit_dir / TIMER).read_bytes(), TIMER_BYTES)
        self.assertEqual({path.name for path in destination.iterdir()},
                         {"auto_deploy.py", "compose.yaml"})
        self.assertEqual({path.name for path in unit_dir.iterdir()}, {SERVICE, TIMER})
        self.assertEqual(self.source_bytes(root), before)

    def test_existing_target_is_detected_before_any_other_target_is_created(self):
        helper = self.helper()
        for index in range(4):
            with self.subTest(target=index):
                root, destination, unit_dir = self.fixture()
                targets = self.targets(destination, unit_dir)
                occupied = targets[index]
                occupied.parent.mkdir(parents=True)
                occupied.write_bytes(b"existing administrator configuration\n")
                before = self.source_bytes(root)
                with self.assertRaises(FileExistsError):
                    helper.install(root, destination, unit_dir)
                self.assertEqual(occupied.read_bytes(), b"existing administrator configuration\n")
                self.assertTrue(all(not path.exists() for path in targets if path != occupied))
                self.assertEqual(self.source_bytes(root), before)

    @unittest.skipUnless(os.name == "posix", "서버의 심볼릭 링크 동작은 POSIX에서 확인")
    def test_even_dangling_target_symlinks_are_never_replaced(self):
        helper = self.helper()
        for index in range(4):
            with self.subTest(target=index):
                root, destination, unit_dir = self.fixture()
                targets = self.targets(destination, unit_dir)
                occupied = targets[index]
                occupied.parent.mkdir(parents=True)
                missing = root / "missing-link-target"
                occupied.symlink_to(missing)
                with self.assertRaises(FileExistsError):
                    helper.install(root, destination, unit_dir)
                self.assertTrue(occupied.is_symlink())
                self.assertEqual(occupied.readlink(), missing)
                self.assertFalse(missing.exists())
                self.assertTrue(all(not path.exists() for path in targets if path != occupied))

    def test_unsafe_verified_compose_is_rejected_without_creating_installation_paths(self):
        helper = self.helper()
        for field, value in (("privileged", True), ("volumes", ["/:/host"]),
                             ("ports", ["0.0.0.0:8501:8501"]),
                             ("container_name", "pricesys-app-1")):
            with self.subTest(field=field):
                root, destination, unit_dir = self.fixture()
                path = root / ".local/deploy/verified-compose.yaml"
                config = json.loads(path.read_text(encoding="utf-8"))
                config["services"]["app"][field] = value
                path.write_text(json.dumps(config), encoding="utf-8")
                before = self.source_bytes(root)
                with self.assertRaises(ValueError):
                    helper.install(root, destination, unit_dir)
                self.assertFalse(destination.exists())
                self.assertFalse(unit_dir.exists())
                self.assertEqual(self.source_bytes(root), before)

    @unittest.skipUnless(os.name == "posix", "서버 파일 권한은 POSIX에서 확인")
    def test_installed_folder_and_files_have_explicit_permissions(self):
        helper = self.helper()
        root, destination, unit_dir = self.fixture()
        helper.install(root, destination, unit_dir)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o700)
        for path, mode in ((destination / "auto_deploy.py", 0o644),
                           (destination / "compose.yaml", 0o600),
                           (unit_dir / SERVICE, 0o644), (unit_dir / TIMER, 0o644)):
            with self.subTest(path=path.name):
                self.assertEqual(path.stat().st_mode & 0o777, mode)

    @unittest.skipUnless(os.name == "posix", "서비스 umask와 컨테이너 읽기 권한은 POSIX에서 확인")
    def test_snapshot_remains_readable_to_container_user_under_private_service_umask(self):
        helper = self.helper()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        base = Path(directory.name)
        archive = base / "source.tar"
        destination = base / "snapshot"
        with tarfile.open(archive, "w") as output:
            for name in ("tests", "tests/demo", "assets"):
                member = tarfile.TarInfo(name)
                member.type = tarfile.DIRTYPE
                member.mode = 0o755
                output.addfile(member)
            for name in ("tests/demo/test_smoke.py", "assets/style.css"):
                content = b"public source\n"
                member = tarfile.TarInfo(name)
                member.size = len(content)
                member.mode = 0o644
                output.addfile(member, io.BytesIO(content))
        previous_umask = os.umask(0o077)
        try:
            helper.extract_snapshot(archive, destination)
        finally:
            os.umask(previous_umask)
        for path in (destination, *destination.rglob("*")):
            with self.subTest(path=str(path.relative_to(destination))):
                permissions = path.stat().st_mode & 0o777
                if path.is_dir():
                    self.assertEqual(permissions, 0o755)
                else:
                    self.assertTrue(permissions & 0o004, "컨테이너 UID10001에 파일 읽기 권한이 필요합니다")


if __name__ == "__main__":
    unittest.main()
