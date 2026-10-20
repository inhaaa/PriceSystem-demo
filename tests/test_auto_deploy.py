"""자동배포의 외부 명령만 대체하고 실제 파일·복구 경계를 검증한다."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
OLD_COMMIT = "c0d96b53e896ba27fd03de6fa3770ac4da7569f5"
NEW_COMMIT = "a" * 40
OLD_IMAGE = "pricesys-demo:c0d96b5-20261020"
REPOSITORY = "https://github.com/inhaaa/PriceSystem-demo.git"
BUILDER = "buildx_buildkit_pricesys-demo-builder0"


def write_tar(path, entries):
    """entries의 (name, bytes 또는 TarInfo)를 실제 tar로 저장한다."""
    with tarfile.open(path, "w") as archive:
        for name, value in entries:
            if isinstance(value, tarfile.TarInfo):
                archive.addfile(value)
            else:
                info = tarfile.TarInfo(name)
                info.size = len(value)
                archive.addfile(info, io.BytesIO(value))


class FakeRunner:
    """Git/Docker 부작용을 모델링하며 허용하지 않은 명령은 즉시 거부한다."""
    def __init__(self, compose):
        self.compose = copy.deepcopy(compose)
        self.calls = []
        self.remote_commit = NEW_COMMIT
        self.current_image = OLD_IMAGE
        self.fail_test = False
        self.timeout_test = False
        self.interrupt_test = False
        self.fail_up = False
        self.non_fast_forward = False
        self.production_changes_after_test = False
        self.production_restarted_after_test = False
        self.test_ran = False
        self.demo_healthy = True
        self.demo_labels = {"com.docker.compose.project": "pricesys-demo"}
        self.demo_ports = {"8501/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8502"}]}
        self.builder_memory = 1610612736
        self.strict_templates = False

    @staticmethod
    def option(args, option):
        for index, arg in enumerate(args):
            if arg.startswith(option + "="):
                return arg.partition("=")[2]
            if arg == option:
                return args[index + 1]
        raise AssertionError(f"필수 옵션 누락: {option}: {args}")

    def container(self, name):
        if name == "pricesys-app-1":
            changed = self.production_changes_after_test and self.test_ran
            restarted = self.production_restarted_after_test and self.test_ran
            return {"Id": "production-changed" if changed else "production-original",
                    "Name": "/pricesys-app-1",
                    "Config": {"Image": "production:existing"},
                    "State": {"Status": "running", "StartedAt": "2026-10-20T09:00:00Z"
                              if restarted else "2026-10-19T07:12:36Z"}}
        if name == "pricesys-demo":
            return {"Id": "demo-current", "Name": "/pricesys-demo",
                    "Config": {"Image": self.current_image, "Labels": self.demo_labels},
                    "HostConfig": {"PortBindings": self.demo_ports},
                    "State": {"Status": "running", "StartedAt": "2026-10-20T04:30:45Z",
                              "Health": {"Status": "healthy" if self.demo_healthy else "unhealthy"}}}
        if name == BUILDER:
            return {"Id": "isolated-builder", "Name": "/" + BUILDER,
                    "State": {"Status": "running"},
                    "HostConfig": {"Memory": self.builder_memory, "CpuPeriod": 100000,
                                   "CpuQuota": 75000}}
        raise AssertionError(f"허용되지 않은 컨테이너 조회: {name}")

    def __call__(self, args, *, env=None, timeout=60):
        args = [str(arg) for arg in args]
        self.calls.append((args, dict(env or {}), timeout))
        if args[0] == "git":
            if "fetch" in args:
                return ""
            if "rev-parse" in args:
                return (self.remote_commit if "FETCH_HEAD" in args else OLD_COMMIT) + "\n"
            if "merge-base" in args:
                if self.non_fast_forward:
                    raise subprocess.CalledProcessError(1, args)
                return ""
            if "archive" in args:
                output = Path(self.option(args, "--output"))
                write_tar(output, [("compose.yaml", json.dumps(self.compose).encode()),
                                   ("app.py", b"# isolated snapshot\n"),
                                   ("tests/test_smoke.py", b"# test snapshot\n")])
                return ""
            if "status" in args:
                return ""
            raise AssertionError(f"예상하지 않은 Git 명령: {args}")
        if args[:3] == ["docker", "image", "inspect"]:
            return json.dumps([{"Id": "rollback-image", "RepoTags": [OLD_IMAGE]}])
        if args[:2] == ["docker", "inspect"]:
            names = args[args.index("container") + 1:] if "container" in args else args[2:]
            if self.strict_templates:
                template = self.option(args, "--format")
                container = self.container(names[0])
                if ".State.Health" in template and "Health" not in container["State"]:
                    raise subprocess.CalledProcessError(1, args, output='map has no entry for key "Health"')
                if ".Config.Labels" in template and not container.get("Config", {}).get("Labels"):
                    raise subprocess.CalledProcessError(1, args, output='index of untyped nil')
                return json.dumps(container)
            return json.dumps([self.container(name) for name in names])
        if args[:3] == ["docker", "buildx", "inspect"]:
            return "Name: pricesys-demo-builder\nDriver: docker-container\n"
        if args[:3] == ["docker", "buildx", "build"]:
            return "image built\n"
        if args[:2] == ["docker", "run"]:
            self.test_ran = True
            if self.timeout_test:
                raise subprocess.TimeoutExpired(args, timeout)
            if self.interrupt_test:
                raise KeyboardInterrupt("test process interrupted")
            if self.fail_test:
                raise subprocess.CalledProcessError(1, args, output="sample regression")
            return "Ran tests OK\n"
        if args[:2] == ["docker", "rm"]:
            if (len(args) != 4 or args[2] != "--force"
                    or not args[3].startswith("pricesys-demo-test-")):
                raise AssertionError(f"자신의 임시 테스트 컨테이너만 삭제할 수 있습니다: {args}")
            return args[3] + "\n"
        if args[:2] == ["docker", "compose"]:
            if "config" in args:
                return json.dumps(self.compose)
            if "up" in args:
                image = (env or {}).get("DEMO_IMAGE")
                if not image:
                    raise AssertionError("Compose는 명시적 DEMO_IMAGE가 필요합니다")
                self.current_image = image
                if self.fail_up and image != OLD_IMAGE:
                    raise subprocess.CalledProcessError(1, args, output="candidate unhealthy")
                self.demo_healthy = True
                return "Healthy\n"
        raise AssertionError(f"예상하지 않은 외부 명령: {args}")

    def mutations(self):
        return [(args, env) for args, env, _ in self.calls
                if args[:3] == ["docker", "buildx", "build"]
                or args[:2] in (["docker", "run"], ["docker", "rm"])
                or (args[:2] == ["docker", "compose"] and "up" in args)]

    def compose_updates(self):
        return [(args, env) for args, env in self.mutations()
                if args[:2] == ["docker", "compose"]]


class AutoDeployTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state = self.root / ".local/deploy"
        self.state.mkdir(parents=True)
        self.config = json.loads((ROOT / "compose.yaml").read_text(encoding="utf-8"))
        self.compose = self.state / "verified-compose.yaml"
        self.compose.write_text(json.dumps(self.config), encoding="utf-8")
        (self.state / "current-image").write_text(OLD_IMAGE + "\n", encoding="utf-8")
        (self.state / "current-commit").write_text(OLD_COMMIT + "\n", encoding="utf-8")
        self.runner = FakeRunner(self.config)
        # /tmp가 64MiB인 테스트 컨테이너와 VPS의 빌드 디스크 관측을 분리한다.
        space = patch("shutil.disk_usage", return_value=SimpleNamespace(free=20 * 1024 ** 3))
        space.start()
        self.addCleanup(space.stop)

    def helper(self):
        path = ROOT / "deploy/auto_deploy.py"
        self.assertTrue(path.is_file(), "격리된 자동배포 도구가 필요합니다")
        spec = importlib.util.spec_from_file_location("auto_deploy_under_test", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def deploy(self, **kwargs):
        return self.helper().deploy(self.root, self.compose, run=self.runner, **kwargs)

    def assert_current_unchanged(self):
        self.assertEqual((self.state / "current-image").read_text().strip(), OLD_IMAGE)
        self.assertEqual((self.state / "current-commit").read_text().strip(), OLD_COMMIT)

    def assert_stopped(self):
        helper = self.helper()
        with self.assertRaises((helper.DeployError, subprocess.CalledProcessError)):
            helper.deploy(self.root, self.compose, run=self.runner)
        self.assert_current_unchanged()

    def assert_failed_test_cleaned(self):
        run_args = next(args for args, _, _ in self.runner.calls
                        if args[:2] == ["docker", "run"])
        name = FakeRunner.option(run_args, "--name")
        self.assertRegex(name, r"^pricesys-demo-test-[a-zA-Z0-9_-]+$")
        self.assertEqual([args for args, _, _ in self.runner.calls
                          if args[:2] == ["docker", "rm"]],
                         [["docker", "rm", "--force", name]])
        self.assertEqual(self.runner.compose_updates(), [])
        self.assert_current_unchanged()

    def test_approved_compose_accepts_formatting_but_rejects_changed_limits(self):
        helper = self.helper()
        self.assertEqual(helper.validate_compose(self.compose), self.config)
        self.compose.write_text(json.dumps(self.config, indent=4), encoding="utf-8")
        self.assertEqual(helper.validate_compose(self.compose), self.config)
        altered = copy.deepcopy(self.config)
        altered["services"]["app"]["mem_limit"] = "8g"
        self.compose.write_text(json.dumps(altered), encoding="utf-8")
        with self.assertRaises(helper.DeployError):
            helper.validate_compose(self.compose)

    def test_changed_compose_cannot_add_production_mount_or_change_project(self):
        helper = self.helper()
        for field, value in (("name", "pricesys"), ("volumes", ["/srv/pricesys:/production"])):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.config)
                target = altered if field == "name" else altered["services"]["app"]
                target[field] = value
                self.compose.write_text(json.dumps(altered), encoding="utf-8")
                with self.assertRaises(helper.DeployError):
                    helper.validate_compose(self.compose)

    def test_same_commit_performs_no_build_test_or_container_replacement(self):
        self.runner.remote_commit = OLD_COMMIT
        self.assertEqual(self.deploy(), "unchanged")
        self.assertEqual(self.runner.mutations(), [])
        self.assert_current_unchanged()

    def test_failed_commit_is_skipped_until_explicit_retry(self):
        marker = self.state / "autodeploy.json"
        marker.write_text(json.dumps({"failed_commit": NEW_COMMIT}), encoding="utf-8")
        self.assertEqual(self.deploy(), "failed-skip")
        self.assertEqual(self.runner.mutations(), [])
        self.assertEqual(self.deploy(retry=True), "deployed")

    def test_check_mode_does_not_build_or_change_records(self):
        before = {path.name: path.read_bytes() for path in self.state.iterdir()}
        self.assertEqual(self.deploy(check=True), "checked")
        self.assertEqual(self.runner.mutations(), [])
        after = {path.name: path.read_bytes() for path in self.state.iterdir()}
        self.assertEqual(after, before)

    def test_check_supports_real_builder_without_healthcheck_or_compose_labels(self):
        self.runner.strict_templates = True
        self.assertEqual(self.deploy(check=True), "checked")
        self.assertEqual(self.runner.mutations(), [])
        self.assert_current_unchanged()

    def test_tests_fail_before_container_replacement_and_mark_commit(self):
        self.runner.fail_test = True
        self.assert_stopped()
        self.assertTrue(self.runner.test_ran)
        self.assertEqual(self.runner.compose_updates(), [])
        self.assert_failed_test_cleaned()
        marker = json.loads((self.state / "autodeploy.json").read_text())
        self.assertEqual(marker["failed_commit"], NEW_COMMIT)

    def test_timed_out_test_removes_only_its_named_container_before_aborting(self):
        self.runner.timeout_test = True
        self.assert_stopped()
        self.assert_failed_test_cleaned()
        marker = json.loads((self.state / "autodeploy.json").read_text(encoding="utf-8"))
        self.assertEqual(marker["failed_commit"], NEW_COMMIT)

    def test_interrupted_test_removes_its_named_container_and_leaves_live_demo(self):
        self.runner.interrupt_test = True
        helper = self.helper()
        with self.assertRaises((helper.DeployError, KeyboardInterrupt)):
            helper.deploy(self.root, self.compose, run=self.runner)
        self.assert_failed_test_cleaned()

    def test_unhealthy_candidate_rolls_back_using_verified_old_image(self):
        self.runner.fail_up = True
        self.assert_stopped()
        updates = self.runner.compose_updates()
        self.assertEqual([env["DEMO_IMAGE"] for _, env in updates],
                         [f"pricesys-demo:{NEW_COMMIT}", OLD_IMAGE])
        self.assertEqual(self.runner.current_image, OLD_IMAGE)
        self.assertEqual(json.loads((self.state / "autodeploy.json").read_text(encoding="utf-8"))["failed_commit"],
                         NEW_COMMIT)

    def test_production_change_during_build_prevents_demo_replacement(self):
        self.runner.production_changes_after_test = True
        self.assert_stopped()
        self.assertTrue(self.runner.test_ran)
        self.assertEqual(self.runner.compose_updates(), [])

    def test_production_restart_with_same_id_prevents_demo_replacement(self):
        self.runner.production_restarted_after_test = True
        self.assert_stopped()
        self.assertTrue(self.runner.test_ran)
        self.assertEqual(self.runner.compose_updates(), [])

    def test_low_disk_stops_before_build_or_replacement(self):
        helper = self.helper()
        with patch.object(helper.shutil, "disk_usage", return_value=SimpleNamespace(free=4 * 1024 ** 3)):
            with self.assertRaises(helper.DeployError):
                helper.deploy(self.root, self.compose, run=self.runner)
        self.assertEqual(self.runner.mutations(), [])
        self.assert_current_unchanged()

    def test_existing_demo_must_match_recorded_image_and_scope(self):
        for change in ("image", "project", "port", "health"):
            with self.subTest(change=change):
                runner = FakeRunner(self.config)
                if change == "image":
                    runner.current_image = "pricesys-demo:unrecorded"
                elif change == "project":
                    runner.demo_labels = {"com.docker.compose.project": "pricesys"}
                elif change == "port":
                    runner.demo_ports["8501/tcp"][0]["HostIp"] = "0.0.0.0"
                else:
                    runner.demo_healthy = False
                helper = self.helper()
                with self.assertRaises(helper.DeployError):
                    helper.deploy(self.root, self.compose, run=runner)
                self.assertEqual(runner.mutations(), [])
                self.assert_current_unchanged()

    def test_builder_without_confirmed_memory_limit_cannot_build(self):
        self.runner.builder_memory = 0
        self.assert_stopped()
        self.assertEqual(self.runner.mutations(), [])

    def test_non_fast_forward_main_cannot_replace_a_verified_deployment(self):
        self.runner.non_fast_forward = True
        self.assert_stopped()
        self.assertEqual(self.runner.mutations(), [])

    def test_snapshot_compose_change_cannot_bypass_frozen_configuration(self):
        self.runner.compose["services"]["app"]["ports"] = ["8501:8501"]
        self.assert_stopped()
        self.assertEqual(self.runner.mutations(), [])

    def test_success_records_the_exact_commit_and_clears_failure(self):
        (self.state / "autodeploy.json").write_text(
            json.dumps({"failed_commit": "b" * 40}), encoding="utf-8")
        self.assertEqual(self.deploy(), "deployed")
        self.assertEqual((self.state / "current-image").read_text().strip(), f"pricesys-demo:{NEW_COMMIT}")
        self.assertEqual((self.state / "current-commit").read_text().strip(), NEW_COMMIT)
        self.assertFalse(json.loads((self.state / "autodeploy.json").read_text()).get("failed_commit"))
        fetch = next(args for args, _, _ in self.runner.calls if args[0] == "git" and "fetch" in args)
        self.assertIn(REPOSITORY, fetch)
        self.assertIn("main", fetch)

    def test_deployment_commands_keep_demo_project_and_resources_fixed(self):
        self.assertEqual(self.deploy(), "deployed")
        build = next(args for args, _, _ in self.runner.calls
                     if args[:3] == ["docker", "buildx", "build"])
        self.assertEqual(FakeRunner.option(build, "--builder"), "pricesys-demo-builder")
        self.assertIn("--load", build)
        self.assertEqual(FakeRunner.option(build, "--tag"), f"pricesys-demo:{NEW_COMMIT}")
        test = next(args for args, _, _ in self.runner.calls if args[:2] == ["docker", "run"])
        self.assertRegex(FakeRunner.option(test, "--name"), r"^pricesys-demo-test-[a-zA-Z0-9_-]+$")
        self.assertIn("--rm", test)
        self.assertFalse(any(args[:2] == ["docker", "rm"] for args, _, _ in self.runner.calls))
        for option, value in (("--network", "none"), ("--user", "10001:10001"),
                              ("--memory", "768m"), ("--cpus", "0.75"),
                              ("--pids-limit", "128"), ("--cap-drop", "ALL")):
            self.assertEqual(FakeRunner.option(test, option), value)
        self.assertIn("--read-only", test)
        self.assertIn("no-new-privileges:true", " ".join(test))
        self.assertIn("unittest", test)
        self.assertIn("discover", test)
        self.assertIn(":ro", " ".join(test))
        update, env = self.runner.compose_updates()[0]
        self.assertEqual(FakeRunner.option(update, "-p"), "pricesys-demo")
        self.assertEqual(FakeRunner.option(update, "-f"), str(self.compose))
        self.assertEqual(FakeRunner.option(update, "--env-file"), "/dev/null")
        self.assertEqual(env["DEMO_IMAGE"], f"pricesys-demo:{NEW_COMMIT}")
        for option in ("--no-deps", "--no-build", "--wait"):
            self.assertIn(option, update)
        self.assertEqual(FakeRunner.option(update, "--pull"), "never")
        self.assertEqual(FakeRunner.option(update, "--wait-timeout"), "120")
        self.assertEqual(update[-1], "app")
        for args, _ in self.runner.mutations():
            joined = " ".join(args)
            self.assertNotIn("pricesys-app-1", joined)
            self.assertNotIn("/srv/pricesys/", joined)
            self.assertNotIn("caddy", joined.lower())
            self.assertNotIn("systemctl", joined)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.archive = self.root / "snapshot.tar"
        self.destination = self.root / "source"

    def helper(self):
        return AutoDeployTests.helper(self)

    def test_extracts_regular_files_and_directories(self):
        directory = tarfile.TarInfo("demo")
        directory.type = tarfile.DIRTYPE
        write_tar(self.archive, [("demo", directory), ("demo/sample.py", b"safe contents")])
        self.helper().extract_snapshot(self.archive, self.destination)
        self.assertEqual((self.destination / "demo/sample.py").read_bytes(), b"safe contents")

    def test_rejects_absolute_and_parent_paths_without_writing_outside(self):
        helper = self.helper()
        for name in ("../escaped", "demo/../../escaped", "/tmp/autodeploy-escaped"):
            with self.subTest(name=name):
                write_tar(self.archive, [(name, b"unsafe")])
                with self.assertRaises(helper.DeployError):
                    helper.extract_snapshot(self.archive, self.destination)
                self.assertFalse((self.root / "escaped").exists())

    def test_rejects_symlinks_hardlinks_and_device_entries(self):
        helper = self.helper()
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind):
                entry = tarfile.TarInfo("unsafe")
                entry.type = kind
                entry.linkname = "../escaped"
                write_tar(self.archive, [("unsafe", entry)])
                with self.assertRaises(helper.DeployError):
                    helper.extract_snapshot(self.archive, self.destination)
                self.assertFalse((self.root / "escaped").exists())


if __name__ == "__main__":
    unittest.main()
