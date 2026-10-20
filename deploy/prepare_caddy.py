"""동일한 명시적 bind를 사용하는 서버에서 Caddy 백업과 후보만 생성한다."""
from datetime import datetime, timezone
import os
from pathlib import Path
import re


TOKEN = b"__CONFIRMED_BIND_ADDRESSES__"


def prepare(source, template, state):
    original = source.read_bytes()
    active = b"\n".join(line.split(b"#", 1)[0] for line in original.splitlines())
    if b"demo.inhaaa.com" in active:
        raise ValueError("데모 도메인이 이미 있습니다. 기존 블록을 먼저 확인하세요.")
    if re.search(rb"(?m)^[ \t]*import[ \t]", active):
        raise ValueError("import 설정이 있습니다. 포함된 설정을 먼저 검토하세요.")
    bindings = re.findall(rb"(?m)^[ \t]*bind[ \t]+([^\r\n]+)", active)
    bindings = [b" ".join(value.split()) for value in bindings]
    if not bindings or not bindings[0] or len(set(bindings)) != 1:
        raise ValueError("명시적 bind 값이 없거나 서로 다릅니다. 자동 생성을 중단합니다.")
    block = template.read_bytes()
    if block.count(TOKEN) != 2:
        raise ValueError("HTTP/HTTPS bind 자리표시자가 있는 템플릿이 필요합니다.")
    candidate = source.with_name("Caddyfile.demo-candidate")
    record = state / "caddy-backup-path"
    for path in (candidate, record):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"기존 파일은 덮어쓰지 않습니다: {path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = source.with_name(f"Caddyfile.before-demo.{stamp}")
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(state, 0o700)
    for path, content in (
        (backup, original),
        (candidate, original + b"\n" + block.replace(TOKEN, bindings[0])),
        (record, (str(backup.resolve()) + "\n").encode("utf-8")),
    ):
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
            file.write(content)
    return backup, candidate


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    backup, candidate = prepare(
        Path("/etc/caddy/Caddyfile"),
        root / "deploy/Caddyfile.demo.example",
        root / ".local/deploy",
    )
    print(f"백업: {backup}")
    print(f"후보: {candidate}")
    print("기존 Caddyfile은 변경하지 않았습니다. 다음 단계에서 후보를 검증하세요.")
