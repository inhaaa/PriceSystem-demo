"""GitHub main을 확인하고 검증된 설정으로 데모 컨테이너만 갱신한다."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import uuid


ROOT = Path("/srv/pricesys-demo")
INSTALLED = Path("/usr/local/lib/pricesys-demo")
UNITS = Path("/etc/systemd/system")
REPOSITORY = "https://github.com/inhaaa/PriceSystem-demo.git"
BUILDER = "pricesys-demo-builder"
COMPOSE_HASH = "6af798d10eaa74ee920b7186e95c4de8e877f1333ba84de05fb28d1535119456"


class DeployError(RuntimeError):
    pass


def validate_compose(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != COMPOSE_HASH:
        raise DeployError("Compose 변경은 자동 적용하지 않습니다. 별도 검토가 필요합니다.")
    return config


def extract_snapshot(archive, destination):
    destination = Path(destination).resolve()
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            target = (destination / member.name).resolve()
            if (not (member.isfile() or member.isdir()) or name.is_absolute()
                    or ".." in name.parts or "\\" in member.name or ":" in member.name
                    or not target.is_relative_to(destination)):
                raise DeployError(f"안전하지 않은 소스 항목: {member.name}")
        destination.mkdir(mode=0o755, parents=True, exist_ok=True)
        destination.chmod(0o755)
        source.extractall(destination, members=members, filter="data")
        # systemd의 UMask=0077에서도 테스트 UID10001이 snapshot을 읽어야 한다.
        for path in destination.rglob("*"):
            path.chmod(0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644)


def run_command(args, *, env=None, timeout=60):
    result = subprocess.run([str(arg) for arg in args], env=env, timeout=timeout,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    visible = (list(args[:3]) == ["docker", "buildx", "build"]
               or list(args[:2]) in (["docker", "run"], ["docker", "compose"]))
    if result.stdout and (visible or result.returncode):
        print(result.stdout.rstrip(), flush=True)
    result.check_returncode()
    return result.stdout


def write_atomic(path, content):
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(root, destination, unit_dir):
    root, destination, unit_dir = Path(root), Path(destination), Path(unit_dir)
    verified = root / ".local/deploy/verified-compose.yaml"
    try:
        validate_compose(verified)
    except DeployError as error:
        raise ValueError(str(error)) from error
    for name in ("current-image", "current-commit"):
        if not (root / ".local/deploy" / name).read_text().strip():
            raise ValueError(f"검증 기록 누락: {name}")
    copies = [
        (root / "deploy/auto_deploy.py", destination / "auto_deploy.py", 0o644),
        (verified, destination / "compose.yaml", 0o600),
        *[(root / "deploy" / name, unit_dir / name, 0o644)
          for name in ("pricesys-demo-auto.service", "pricesys-demo-auto.timer")],
    ]
    for _, target, _ in copies:
        if os.path.lexists(target):
            raise FileExistsError(f"기존 파일을 보존합니다: {target}")
    if destination.is_symlink() or unit_dir.is_symlink():
        raise FileExistsError("설치 디렉터리가 심볼릭 링크입니다")
    contents = [(source.read_bytes(), target, mode) for source, target, mode in copies]
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.chmod(0o700)
    unit_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    for content, target, mode in contents:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        target.chmod(mode)
    print("고정 updater·Compose·unit 설치 완료. 서비스는 아직 시작하지 않았습니다.")


def deploy(root, compose_path, *, run=run_command, check=False, retry=False):
    root, compose_path = Path(root).resolve(), Path(compose_path).resolve()
    validate_compose(compose_path)
    state = root / ".local/deploy"
    old_image = (state / "current-image").read_text().strip()
    old_commit = (state / "current-commit").read_text().strip()
    if not old_image.startswith("pricesys-demo:") or len(old_commit) != 40:
        raise DeployError("검증한 데모 이미지·커밋 기록을 먼저 확인하세요")
    env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
           "HOME": "/root", "LANG": "C.UTF-8", "GIT_TERMINAL_PROMPT": "0",
           "DOCKER_HOST": "unix:///var/run/docker.sock"}

    def command(args, *, image=None, timeout=60):
        return run([str(arg) for arg in args], env={**env, **({"DEMO_IMAGE": image} if image else {})},
                   timeout=timeout)

    def inspect(name):
        template = ('{"Id":{{json .Id}},"State":{"Status":{{json .State.Status}},'
                    '"StartedAt":{{json .State.StartedAt}},"Health":{"Status":'
                    '{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}},'
                    '"Config":{"Image":{{json .Config.Image}},"Labels":'
                    '{"com.docker.compose.project":{{json (index .Config.Labels "com.docker.compose.project")}}}},'
                    '"HostConfig":{"PortBindings":{{json .HostConfig.PortBindings}},'
                    '"Memory":{{json .HostConfig.Memory}},"CpuPeriod":{{json .HostConfig.CpuPeriod}},'
                    '"CpuQuota":{{json .HostConfig.CpuQuota}}}}')
        result = json.loads(command(["docker", "inspect", "--format", template,
                                     "--type", "container", name]))
        return result[0] if isinstance(result, list) else result

    def identity(container):
        return (container["Id"], container["State"]["Status"], container["State"]["StartedAt"])

    def validate_demo(container, image):
        ports = {"8501/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8502"}]}
        if (container["Config"].get("Labels", {}).get("com.docker.compose.project") != "pricesys-demo"
                or container["Config"]["Image"] != image
                or container["HostConfig"]["PortBindings"] != ports
                or container["State"]["Status"] != "running"
                or container["State"].get("Health", {}).get("Status") != "healthy"):
            raise DeployError("데모 이미지·프로젝트·포트·health가 검증 기록과 다릅니다")

    def update(image):
        command(["docker", "compose", "--project-directory", root, "--env-file", "/dev/null",
                 "-p", "pricesys-demo", "-f", compose_path, "up", "-d", "--no-deps",
                 "--no-build", "--pull", "never", "--wait", "--wait-timeout", "120", "app"],
                image=image, timeout=150)
        validate_demo(inspect("pricesys-demo"), image)

    demo_before = inspect("pricesys-demo")
    validate_demo(demo_before, old_image)
    production_before = identity(inspect("pricesys-app-1"))
    if production_before[1] != "running":
        raise DeployError("운영 컨테이너가 running이 아니므로 데모 배포를 중단합니다")
    command(["git", "-C", root, "fetch", "--no-tags", REPOSITORY, "main"])
    commit = command(["git", "-C", root, "rev-parse", "FETCH_HEAD"]).strip()
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise DeployError("GitHub 커밋 형식을 확인할 수 없습니다")
    if commit == old_commit:
        print(f"변경 없음: {commit}", flush=True)
        return "unchanged"
    marker = state / "autodeploy.json"
    status = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else {}
    if status.get("failed_commit") == commit and not retry and not check:
        print(f"실패 커밋 대기: {commit} (수정 push 또는 --retry 필요)", flush=True)
        return "failed-skip"
    replaced = False
    try:
        command(["git", "-C", root, "merge-base", "--is-ancestor", old_commit, commit])
        builder = inspect(f"buildx_buildkit_{BUILDER}0")
        limits = builder["HostConfig"]
        if (builder["State"]["Status"] != "running" or limits.get("Memory") != 1610612736
                or limits.get("CpuPeriod") != 100000 or limits.get("CpuQuota") != 75000):
            raise DeployError("전용 builder의 CPU·메모리 제한을 먼저 확인하세요")
        if check:
            print(f"점검 완료: main={commit}, 현재={old_commit}", flush=True)
            return "checked"
        if shutil.disk_usage(root).free < 5 * 1024 ** 3:
            raise DeployError("여유 디스크가 5GiB 미만이므로 빌드를 중단합니다")
        command(["docker", "image", "inspect", "--format", "{{.Id}}", old_image])
        with tempfile.TemporaryDirectory(prefix="release-", dir=state) as temporary:
            archive = Path(temporary) / "source.tar"
            source = Path(temporary) / "source"
            command(["git", "-C", root, "archive", "--format=tar", f"--output={archive}", commit])
            extract_snapshot(archive, source)
            validate_compose(source / "compose.yaml")
            image = f"pricesys-demo:{commit}"
            print(f"빌드 시작: {commit}", flush=True)
            command(["docker", "buildx", "build", "--builder", BUILDER, "--load", "--tag", image,
                     source], timeout=900)
            print("격리 컨테이너에서 전체 테스트 실행", flush=True)
            test_name = f"pricesys-demo-test-{uuid.uuid4().hex}"
            try:
                command(["docker", "run", "--rm", "--name", test_name,
                         "--network", "none", "--user", "10001:10001",
                         "--memory", "768m", "--cpus", "0.75", "--pids-limit", "128", "--read-only",
                         "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                         "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m", "-v", f"{source}:/source:ro",
                         "--workdir", "/source", "--entrypoint", "python", image,
                         "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"], timeout=180)
            except BaseException:
                # CLI 종료만으로 Docker daemon의 테스트 컨테이너가 멈추지는 않는다.
                try:
                    command(["docker", "rm", "--force", test_name])
                except Exception as cleanup_error:
                    print(f"테스트 컨테이너 정리 확인 필요: {test_name}: {cleanup_error}", flush=True)
                raise
            if identity(inspect("pricesys-app-1")) != production_before:
                raise DeployError("빌드 중 운영 컨테이너 변경 감지: 교체하지 않고 중단합니다")
            current_demo = inspect("pricesys-demo")
            validate_demo(current_demo, old_image)
            if identity(current_demo) != identity(demo_before):
                raise DeployError("다른 데모 관리 작업 감지: 교체하지 않고 중단합니다")
            for name in ("image", "commit"):
                write_atomic(state / f"rollback-{name}", (state / f"current-{name}").read_text())
            write_atomic(state / "rollback-compose.yaml", compose_path.read_text())
            replaced = True
            update(image)
            if identity(inspect("pricesys-app-1")) != production_before:
                raise DeployError("교체 후 운영 컨테이너 변경 감지: 데모만 이전 이미지로 복구합니다")
            write_atomic(state / "current-image", image + "\n")
            write_atomic(state / "current-commit", commit + "\n")
            write_atomic(state / "verified-compose.yaml", compose_path.read_text())
            write_atomic(marker, json.dumps({"failed_commit": None, "deployed_commit": commit}) + "\n")
            print(f"배포 완료: {image}; 운영 컨테이너 변경 없음", flush=True)
            return "deployed"
    except Exception as error:
        message = str(error)
        if replaced:
            try:
                update(old_image)
                write_atomic(state / "current-image", old_image + "\n")
                write_atomic(state / "current-commit", old_commit + "\n")
                message += "; 이전 데모 이미지로 복구 완료"
            except Exception as rollback_error:
                message += f"; 데모 복구 실패, 수동 확인 필요: {rollback_error}"
        if not check:
            write_atomic(marker, json.dumps({"failed_commit": commit, "error": message}, ensure_ascii=False) + "\n")
        raise DeployError(message) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--install", action="store_true", help="고정본 설치만 수행")
    mode.add_argument("--check", action="store_true", help="빌드·교체 없이 사전 점검")
    mode.add_argument("--retry", action="store_true", help="실패한 main 커밋 재시도")
    args = parser.parse_args()
    if os.name != "posix" or os.geteuid() != 0:
        parser.error("VPS의 root Webconsole에서 실행하세요")
    import fcntl
    import signal

    def interrupted(signum, frame):
        raise DeployError(f"종료 신호 수신: {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    with (ROOT / ".local/deploy/autodeploy.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("다른 데모 배포 작업이 실행 중입니다")
            return
        if args.install:
            install(ROOT, INSTALLED, UNITS)
        else:
            deploy(ROOT, INSTALLED / "compose.yaml", check=args.check, retry=args.retry)


if __name__ == "__main__":
    main()
