"""README 스크린샷 주소를 각 이미지의 마지막 변경 커밋으로 갱신한다."""
import argparse
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RAW_PREFIX = "https://raw.githubusercontent.com/inhaaa/PriceSystem-demo"
IMAGE_LINK = re.compile(
    r"(?P<start>!\[[^\]]*\]\()"
    r"(?:https://raw\.githubusercontent\.com/inhaaa/PriceSystem-demo/[^/]+/)?"
    r"(?P<path>docs/images/[^)\s?#]+\.(?:png|jpe?g|webp))"
    r"(?P<end>\))",
    re.IGNORECASE,
)


def update_readme(root, *, check=False):
    """주소 갱신이 필요하면 True를 반환한다. check=True는 파일을 쓰지 않는다."""
    root = Path(root).resolve()
    readme = root / "README.md"
    original = readme.read_bytes()

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=root, text=True, encoding="utf-8", stderr=subprocess.PIPE,
        ).strip()

    def replace(match):
        relative = match["path"]
        image = (root / relative).resolve()
        if not image.is_relative_to(root / "docs/images"):
            raise ValueError(f"{relative}: 스크린샷 디렉터리 밖의 경로입니다.")
        if not image.is_file():
            raise FileNotFoundError(f"{relative}: 이미지 파일이 없습니다.")
        commit = git("log", "-1", "--format=%H", "--", relative)
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"{relative}: 추적된 이미지 커밋이 없습니다 (untracked).")
        if git("status", "--porcelain", "--", relative):
            raise ValueError(f"{relative}: 이미지 변경을 먼저 커밋하세요 (uncommitted).")
        return f'{match["start"]}{RAW_PREFIX}/{commit}/{relative}{match["end"]}'

    updated = IMAGE_LINK.sub(replace, original.decode("utf-8")).encode("utf-8")
    changed = updated != original
    if changed and not check:
        # 모든 이미지 검증을 마친 후 저장해 일부 링크만 바뀌는 일을 막는다.
        readme.write_bytes(updated)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="파일을 쓰지 않고 갱신 필요 여부만 확인")
    args = parser.parse_args()
    try:
        changed = update_readme(ROOT, check=args.check)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"오류: {error}\n")
    print("README 스크린샷 주소 갱신 필요" if changed and args.check else
          "README 스크린샷 주소 갱신 완료" if changed else "README 스크린샷 주소 변경 없음")
    return int(args.check and changed)


if __name__ == "__main__":
    raise SystemExit(main())
