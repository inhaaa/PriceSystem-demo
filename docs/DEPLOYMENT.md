# Hostinger VPS 독립 배포

목표 주소는 `https://demo.inhaaa.com`이다. 아래 명령은 Hostinger **Webconsole의 Ubuntu Bash**에서 실행한다. 관리자 권한이 필요하면 콘솔에서 직접 `sudo -i`로 전환한다. 비밀번호·개인키·Caddy 인증 해시는 채팅이나 Git에 올리지 않는다.

현재 배포 대상 브랜치는 사용자 요청에 따라 `main`으로 통일한다. main push 후의 자동 갱신은 [자동배포 안내](AUTO_DEPLOYMENT.md)를 따른다. 아래 문서의 최초 배포 검증 기록은 자동배포 설정 이전의 이력이다.

Webconsole에서 여러 줄을 한꺼번에 붙이면 명령이 합쳐질 수 있으므로 **한 줄씩 실행하고 결과를 확인**한다. `if` 블록은 각 줄을 차례로 입력하고 마지막 `fi`까지 입력한다.

## 배포 계약

| 항목 | 값 |
| --- | --- |
| 소스 | `https://github.com/inhaaa/PriceSystem-demo.git` |
| 독립 경로 | `/srv/pricesys-demo` |
| Compose 프로젝트 / 컨테이너 | `pricesys-demo` / `pricesys-demo` |
| 서비스 이름 | `app` |
| 호스트 → 컨테이너 | `127.0.0.1:8502` → `8501` |
| 앱 | Python 3.13, Streamlit 1.59.2, pandas 3.0.3, `app.py` |
| 프록시 | 호스트 Caddy → `127.0.0.1:8502` |
| 데이터 | 방문자별 SQLite `:memory:`, 운영 연결·DB 볼륨 없음 |

신규 Compose는 데모 하나만 관리한다. `/srv/pricesys/shared/config/compose.yaml`, 운영 DB·키, `/srv/inhaa-portfolio/current`는 변경하지 않는다. Caddy는 전체 원본을 보관하고 **신규 도메인 블록만 추가**한다. 기존 Streamlit Cloud 앱은 검증 후 별도 승인 전까지 유지한다.

`compose.yaml`은 JSON 문법의 YAML이다. Docker Compose에서 읽을 수 있고, 별도 YAML 패키지 없이 배포 경계를 테스트할 수 있다. 현재 앱은 추가 환경변수·API 키·`.env`가 필요 없다. `DEMO_IMAGE`만 Compose의 이미지 선택에 쓰며 컨테이너에 전달하지 않는다.

## 1. 먼저 확인할 서버 상태

아래는 읽기 전용 점검이다. 기존 사이트의 사전 상태를 기록한다.

```bash
uname -a
docker version
docker compose version
caddy version
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
docker compose ls
docker inspect --format '{{.Id}} {{.State.Status}} {{.State.StartedAt}}' pricesys-app-1
ss -ltnp '( sport = :80 or sport = :443 or sport = :8501 or sport = :8502 )'
free -h
df -h /srv /var/lib/docker
systemctl is-active caddy docker nginx
systemctl is-enabled docker
ip -br address
getent ahostsv4 demo.inhaaa.com
getent ahostsv4 inhaaa.com
awk '/^[^#[:space:]].*\{[[:space:]]*$/ || /^[[:space:]]*bind[[:space:]]/ {print NR ": " $0}' /etc/caddy/Caddyfile
curl -sS -I --max-time 15 https://pricesys.cloud
curl -sS -I --max-time 15 https://inhaaa.com
curl -sS -I --max-time 15 https://www.inhaaa.com
```

8502가 이미 사용 중이면 멈추고 충돌 대상을 확인한다. 기존 프로세스를 종료하지 않는다. Docker Compose v2의 `up --help`에서 `--wait`, `--wait-timeout`, `--pull` 지원도 확인한다. 버전이 오래되면 기존 서비스 영향이 있는 업그레이드를 임의로 진행하지 않는다.

Caddyfile은 **서버 안에서** 전체를 읽고 글로벌 옵션, import, `bind`, HTTP/HTTPS 블록, Tailscale 주소를 확인한다. 위 `awk` 출력은 호스트와 bind를 추리는 보조 자료일 뿐이다. 실제 공개 인터페이스와 기존 `inhaaa.com` 리스너를 대조한다. DNS의 공인 IP를 bind 값으로 추측하지 않는다. Caddy가 컨테이너로 실행된다면 이 문서의 호스트 프록시 전제가 다르므로 먼저 구성을 다시 확인한다.

런타임은 CPU 0.75개·메모리 768MiB·PID 128개·로그 약 30MB로 제한한다. **이미지 빌드는 이 제한을 받지 않는다.** 운영 서버의 여유 메모리·디스크를 확인하고 사용량이 낮을 때 빌드한다. 자원이 부족하면 다른 환경에서 이미지를 빌드해 가져오는 절차를 별도로 정한다.

## 2. GitHub 소스 준비

아래 최초 배포 명령은 **배포 파일까지 GitHub main에 반영한 뒤** 실행한다. 최초 VPS 배포에서는 `codex/vps-demo-deployment` 브랜치를 사용했으며, 이후 자동배포 요청에 따라 main으로 통일한다.

로컬 변경 검토·테스트 후 필요한 파일만 커밋하고 push한다. `.local`, `.env`, 비밀 파일은 포함하지 않는다. 배포용 새 파일은 `PUBLIC_FILES.txt`에 등록되어 있다. 배포 준비 ZIP도 이 공개 목록으로만 만들 수 있다.

VPS에서 아래 블록은 `/srv/pricesys-demo`가 **아직 없을 때만** 실행한다. 이미 있다면 파일과 소유자를 먼저 확인하고 재배포 절차를 따른다.

```bash
test ! -e /srv/pricesys-demo && git clone --branch main https://github.com/inhaaa/PriceSystem-demo.git /srv/pricesys-demo
cd /srv/pricesys-demo
git status --short
git log -1 --oneline
test -f Dockerfile && test -f compose.yaml && test -f .dockerignore
install -d -m 700 .local/deploy
```

명령이 실패하거나 예상하지 않은 로컬 변경이 보이면 다음 단계로 넘어가지 않는다. 기존 경로를 삭제하거나 reset해서 맞추지 않는다.

## 3. 신규 데모만 빌드하고 시작

8502 미사용, 충분한 자원, 새 배포 파일 존재를 확인한 뒤 실행한다. 첫 배포 전에 기존 운영 컨테이너 ID와 응답도 보관한다.

```bash
cd /srv/pricesys-demo
docker inspect --format '{{.Id}} {{.State.Status}} {{.State.StartedAt}}' pricesys-app-1 > .local/deploy/production-before.txt
docker compose -p pricesys-demo -f compose.yaml config --quiet
DEMO_IMAGE="pricesys-demo:$(git rev-parse --short=12 HEAD)-$(date -u +%Y%m%dT%H%M%SZ)"
DEMO_IMAGE="$DEMO_IMAGE" docker compose -p pricesys-demo -f compose.yaml build app
DEMO_IMAGE="$DEMO_IMAGE" docker compose -p pricesys-demo -f compose.yaml up -d --no-build --pull never --wait --wait-timeout 120 app
docker compose -p pricesys-demo -f compose.yaml ps
docker compose -p pricesys-demo -f compose.yaml logs --tail 100 app
curl -fsS http://127.0.0.1:8502/_stcore/health
docker port pricesys-demo
```

각 명령에서 오류가 나면 멈춘다. 건강 확인은 `ok`, 공개 포트는 `127.0.0.1:8502` 하나만 표시되어야 한다.

`unless-stopped` 설정으로 수동 정지하지 않은 컨테이너는 Docker 시작 시 복구된다. Docker 자동 시작이 `enabled`가 아니면 기존 운영 영향을 확인한 후 별도로 설정한다. 이 작업에서 실제 VPS 재부팅은 실행하지 않는다. `unhealthy` 상태만으로 자동 재시작되지는 않으며, 프로세스 종료에 따른 재시작 정책과 구분한다.

## 4. Caddy 후보 임시 적용·검증·영구 저장

아래는 신규 도메인을 처음 추가할 때의 절차다. **현재 배포는 영구 저장까지 완료됐으므로 다시 실행하지 않는다.** 앱 재배포는 6절을 따른다. 기존 5개 HTTP/HTTPS `bind`가 모두 같고 외부 `import`가 없는 구성을 Webconsole에서 확인했다. 신규 두 블록도 같은 bind를 사용한다. [bind 공식 설명](https://caddyserver.com/docs/caddyfile/directives/bind)

### 후보 생성과 검증

```bash
git -C /srv/pricesys-demo pull --ff-only origin main
python3 /srv/pricesys-demo/deploy/prepare_caddy.py
cd /srv/pricesys-demo
CADDY_LIVE=/etc/caddy/Caddyfile
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
CADDY_CANDIDATE=/etc/caddy/Caddyfile.demo-candidate
test -r "$CADDY_BACKUP" && test -s "$CADDY_BACKUP" && test -r "$CADDY_CANDIDATE" && test -s "$CADDY_CANDIDATE"
stat -c '%a %n' "$CADDY_BACKUP" "$CADDY_CANDIDATE"
caddy validate --config "$CADDY_CANDIDATE" --adapter caddyfile
diff -u "$CADDY_LIVE" "$CADDY_CANDIDATE"
```

도구는 원본 전체의 백업과 신규 HTTP/HTTPS 블록만 추가한 후보를 권한 `600`으로 만든다. 기존 데모 설정·후보·백업 기록, 다른 bind, import가 있으면 중단하며 원본이나 실행 중 설정을 바꾸지 않는다. 준비 파일이 남아도 삭제·덮어쓰기하지 말고 원인을 확인한다. 실제 bind와 인증 해시가 있는 파일은 서버에만 보관한다.

`Valid configuration`, 두 파일의 `600`, diff의 **신규 데모 블록 추가만** 확인한 후 계속한다. `diff`의 종료 코드 1은 차이가 있다는 뜻이므로 출력으로 판단한다. 실제 생성된 백업은 `/etc/caddy/Caddyfile.before-demo.20261020T041656190872Z`다. 글로벌 옵션·환경변수·인증서 관리 방식이 바뀌면 현재 서비스와 같은 환경에서 후보를 다시 검토한다.

### 원본을 유지한 채 후보 임시 적용

원본이 백업과 같은지 확인하고 후보를 런타임에 먼저 적용한다. 이때 원본 파일은 아직 변경되지 않는다.

```bash
cd /srv/pricesys-demo
CADDY_LIVE=/etc/caddy/Caddyfile
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
CADDY_CANDIDATE=/etc/caddy/Caddyfile.demo-candidate
if test -r "$CADDY_BACKUP" && test -s "$CADDY_BACKUP" && test -r "$CADDY_CANDIDATE" && test -s "$CADDY_CANDIDATE" && cmp -s "$CADDY_BACKUP" "$CADDY_LIVE" && caddy validate --config "$CADDY_CANDIDATE" --adapter caddyfile && caddy reload --config "$CADDY_CANDIDATE" --adapter caddyfile; then
  systemctl is-active caddy
else
  printf '%s\n' '임시 적용 실패: 원본·백업·로그를 확인하고 reload를 반복하지 마세요.'
fi
journalctl -u caddy --since '-5 minutes' --no-pager -n 80
```

실패하면 멈춘다. 임시 적용 후에는 아래 응답과 운영 컨테이너를 비교하고, 브라우저에서 로그인 및 가상 카테고리 생성 → 메뉴 이동 후 재조회 → 수정 → 삭제를 확인한다. 기존 사이트에 문제가 있으면 7절의 Caddy 복구 절차를 따른다. **영구 저장 전에는 Caddy 재시작·원본 기준 reload·VPS 재부팅을 하지 않는다.**

```bash
curl -sS -I --max-time 15 http://demo.inhaaa.com
curl -sS -I --max-time 15 https://demo.inhaaa.com
curl -fsS --max-time 15 https://demo.inhaaa.com/_stcore/health
curl -sS -I --max-time 15 https://pricesys.cloud
curl -sS -I --max-time 15 https://inhaaa.com
curl -sS -I --max-time 15 https://www.inhaaa.com
docker inspect --format '{{.Id}} {{.State.Status}} {{.State.StartedAt}}' pricesys-app-1
cat .local/deploy/production-before.txt
docker inspect --format '{{.State.Health.Status}} {{.HostConfig.RestartPolicy.Name}} {{json .HostConfig.PortBindings}}' pricesys-demo
```

기대 결과는 demo HTTP에서 같은 호스트의 HTTPS로 리디렉션, demo HTTPS/health에서 200/`ok`, pricesys에서 미인증 401과 Basic realm, inhaaa에서 200, www에서 inhaaa로 301이다. 운영 컨테이너 ID·상태·시작 시각도 사전 기록과 같아야 한다. `curl -k`로 인증서 오류를 무시하고 통과로 처리하지 않는다.

### 검증한 후보를 원본에 영구 저장

위 응답·운영 컨테이너 비교와 브라우저 기본 CRUD가 통과한 후 실행한다. `--attributes-only`는 후보 내용을 유지하면서 원본의 소유자·권한만 적용한다. 같은 파일시스템·UID·GID·권한인지 확인하고, 원본이 여전히 백업과 같을 때만 `mv -T`로 교체한다. `readlink -f`로 실제 대상에 반영하므로 원본의 심볼릭 링크도 유지한다. **원본 파일에 `cat ... > /etc/caddy/Caddyfile`로 직접 쓰지 않는다.**

```bash
cd /srv/pricesys-demo
CADDY_LIVE=/etc/caddy/Caddyfile
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
CADDY_CANDIDATE=/etc/caddy/Caddyfile.demo-candidate
CADDY_TARGET="$(readlink -f "$CADDY_LIVE")"
if test -n "$CADDY_TARGET" && test -r "$CADDY_BACKUP" && test -s "$CADDY_BACKUP" && test -r "$CADDY_CANDIDATE" && test -s "$CADDY_CANDIDATE" && cmp -s "$CADDY_BACKUP" "$CADDY_LIVE" && cp -Lv --attributes-only --preserve=mode,ownership "$CADDY_LIVE" "$CADDY_CANDIDATE" && stat -Lc '%d:%u:%g:%a %n' "$CADDY_LIVE" "$CADDY_CANDIDATE" && test "$(stat -Lc '%d:%u:%g:%a' "$CADDY_LIVE")" = "$(stat -Lc '%d:%u:%g:%a' "$CADDY_CANDIDATE")" && cmp -s "$CADDY_BACKUP" "$CADDY_LIVE" && mv -vT "$CADDY_CANDIDATE" "$CADDY_TARGET"; then
  caddy validate --config "$CADDY_LIVE" --adapter caddyfile
else
  printf '%s\n' '저장 조건 미충족: 후보 유무와 원본 차이를 확인하고 복구를 자동 실행하지 마세요.'
fi
diff -u "$CADDY_BACKUP" "$CADDY_LIVE"
```

최종 `Valid configuration`과 백업 대비 차이가 신규 데모 블록뿐인지 확인한다. 검증한 후보가 이미 런타임에 적용됐으므로 **추가 reload는 필요 없다.** 성공한 `mv` 뒤에는 후보 파일이 없어진다. 재실행 시 후보의 `stat`가 missing이어도 그것만으로 실패는 아니다. 원본 검증·차이·HTTPS 응답으로 저장 완료 여부를 판단하며, 무조건 백업을 복원하지 않는다.

데모에는 Caddy Basic Auth를 추가하지 않고 공개 `admin/admin` 로그인을 유지한다. 기존 인증·리디렉션·SSL·프록시는 그대로 둔다. `reverse_proxy`는 WebSocket을 기본 지원하므로 CORS/XSRF 보호나 Upgrade 헤더를 변경하지 않는다. reload 때 기존 WebSocket이 재연결될 수 있으므로 운영 사용량이 낮을 때 적용한다. [Caddy WebSocket 동작](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming)

## 5. 추가 기능·재시작 검증

영구 저장 후 PC와 스마트폰에서 다음을 확인한다. HTTP 200과 기본 CRUD만으로 전체 기능 검증을 완료하지 않는다.

- 주소창이 `demo.inhaaa.com`으로 유지되고 유효한 인증서가 표시되며 Streamlit Cloud로 이동하지 않는다.
- `admin/admin` 로그인, 홈, 10개 메뉴, 자료 등록→재조회, 투찰·결과 등록/수정/삭제, 추천/백테스트/API의 고정 샘플을 확인한다.
- 메뉴 이동 후 현재 세션의 값을 조회할 수 있고 다른 브라우저에서는 별도 데이터를 사용한다. 로그아웃/샘플 초기화 후 기본값으로 돌아온다.
- 개발자 도구 Network의 `/_stcore/stream`이 WebSocket으로 연결되어 화면 조작이 계속된다. 로그인 다이아몬드와 로컬 이미지/JS도 표시된다.
- 모바일 사이드바, 입력, 표, 다운로드를 확인한다.

기능 확인 후 데모만 재시작하고 health와 재로그인을 확인한다. 세션 데이터는 초기화된다.

```bash
docker compose -p pricesys-demo -f compose.yaml restart app
DEMO_IMAGE="$(docker inspect --format '{{.Config.Image}}' pricesys-demo)" docker compose -p pricesys-demo -f compose.yaml up -d --no-build --pull never --wait --wait-timeout 120 app
curl -fsS https://demo.inhaaa.com/_stcore/health
```

검증한 이미지와 Compose를 기록한다. `current-commit`에는 현재 소스 HEAD가 아니라 **이미지 태그의 빌드 원본 커밋**을 저장한다. 현재 이미지의 원본은 `c0d96b5`이고, 후보 생성 도구를 받은 소스 HEAD는 `9f0cba8`이다. 두 커밋 사이에 앱 코드 변경은 없다.

```bash
CURRENT_IMAGE="$(docker inspect --format '{{.Config.Image}}' pricesys-demo)"
IMAGE_REVISION="${CURRENT_IMAGE##*:}"
IMAGE_COMMIT="$(git rev-parse "${IMAGE_REVISION%%-*}^{commit}")"
test -n "$CURRENT_IMAGE" && test -n "$IMAGE_COMMIT"
printf '%s\n' "$CURRENT_IMAGE" > .local/deploy/current-image
cp compose.yaml .local/deploy/verified-compose.yaml
printf '%s\n' "$IMAGE_COMMIT" > .local/deploy/current-commit
docker inspect --format '{{.Name}} {{.Id}} {{.State.Status}} {{.State.StartedAt}}' pricesys-demo pricesys-app-1 > .local/deploy/containers-verified.txt
```

## 6. 소스 수정 후 재배포

자동배포 설치·활성화 후에는 main push로 갱신된다. 아래 수동 절차나 7절의 롤백을 실행하려면 먼저 [자동배포 중지 절차](AUTO_DEPLOYMENT.md)를 따르고 실행 중 작업이 없는지 확인한다.

로컬에서 테스트 후 GitHub에 변경을 반영한다. VPS에서는 작업 트리가 깨끗한지와 현재 데모가 정상인지 먼저 확인한다. 이전 검증 기록을 덮어쓰기 전에 롤백 자료를 보관한다.

```bash
cd /srv/pricesys-demo
git status --short
docker inspect --format '{{.State.Health.Status}}' pricesys-demo
cp .local/deploy/current-image .local/deploy/rollback-image
cp .local/deploy/verified-compose.yaml .local/deploy/rollback-compose.yaml
cp .local/deploy/current-commit .local/deploy/rollback-commit
git pull --ff-only origin "$(git branch --show-current)"
docker compose -p pricesys-demo -f compose.yaml config --quiet
DEMO_IMAGE="pricesys-demo:$(git rev-parse --short=12 HEAD)-$(date -u +%Y%m%dT%H%M%SZ)"
DEMO_IMAGE="$DEMO_IMAGE" docker compose -p pricesys-demo -f compose.yaml build app
DEMO_IMAGE="$DEMO_IMAGE" docker compose -p pricesys-demo -f compose.yaml up -d --no-build --pull never --wait --wait-timeout 120 app
curl -fsS https://demo.inhaaa.com/_stcore/health
```

각 명령이 성공한 경우에만 계속한다. `git status`에 변경이 있거나 fast-forward가 실패하면 멈추고 확인한다. 새 버전의 주요 기능과 기존 서비스까지 재검증한 뒤 5절의 검증 기록을 갱신한다. 이전 이미지와 기록은 롤백을 위해 보관한다. 이미지/컨테이너 전체 정리, 다른 프로젝트의 down 또는 Docker 데몬 재시작은 사용하지 않는다.

데모 재생성·재시작 때 현재 체험 세션은 초기화된다. 앱은 한 컨테이너에서 실행하며 무중단 배포나 다중 인스턴스 세션 공유를 구현하지 않는다.

## 7. 장애 시 데모만 롤백

이전 이미지가 로컬에 남아 있어야 한다. 이미지와 **이전 검증 Compose**를 함께 사용하므로 소스에 새 배포 설정이 생겨도 해당 컨테이너는 이전 구성으로 복원한다.

```bash
cd /srv/pricesys-demo
DEMO_IMAGE="$(cat .local/deploy/rollback-image)" docker compose --project-directory /srv/pricesys-demo -p pricesys-demo -f .local/deploy/rollback-compose.yaml up -d --no-build --pull never --wait --wait-timeout 120 app
curl -fsS https://demo.inhaaa.com/_stcore/health
```

롤백 성공 후 이전 검증 상태도 기록에 반영한다. Git reset/rebase는 필요 없다.

```bash
cp .local/deploy/rollback-image .local/deploy/current-image
cp .local/deploy/rollback-compose.yaml .local/deploy/verified-compose.yaml
cp .local/deploy/rollback-commit .local/deploy/current-commit
```

첫 배포의 Caddy 변경 후 기존 사이트에 문제가 생기면 저장한 백업을 복원한다. 백업 이후 다른 관리자의 Caddy 변경이 있었으면 먼저 diff로 확인하며 해당 변경을 덮어쓰지 않는다.

```bash
cd /srv/pricesys-demo
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
caddy validate --config "$CADDY_BACKUP" --adapter caddyfile
diff -u "$CADDY_BACKUP" /etc/caddy/Caddyfile
```

백업 검증과 차이를 확인한 후 복원한다.

```bash
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
CADDY_TARGET="$(readlink -f /etc/caddy/Caddyfile)"
test -r "$CADDY_BACKUP" && test -s "$CADDY_BACKUP" && caddy validate --config "$CADDY_BACKUP" --adapter caddyfile && cp "$CADDY_BACKUP" "${CADDY_TARGET}.demo-restore" && chown --reference="$CADDY_TARGET" "${CADDY_TARGET}.demo-restore" && chmod --reference="$CADDY_TARGET" "${CADDY_TARGET}.demo-restore" && mv -T "${CADDY_TARGET}.demo-restore" "$CADDY_TARGET" && caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && systemctl reload caddy
```

## 8. 로그·환경변수·백업

```bash
cd /srv/pricesys-demo
docker compose -p pricesys-demo -f compose.yaml ps
docker compose -p pricesys-demo -f compose.yaml logs --tail 200 app
docker stats --no-stream pricesys-demo
journalctl -u caddy --since '-15 minutes' --no-pager -n 100
```

실행 파일과 설정은 Git 커밋 및 검증 이미지 태그로 보관한다. `.local/deploy`의 이미지/Compose 기록과 서버 내 Caddy 백업도 보관하되 인증 해시가 있는 백업을 공개 저장소에 넣지 않는다. 데모의 업무 데이터는 세션 메모리에만 있으므로 백업·영속화하지 않는다. 필요한 가상 결과는 UI의 CSV 다운로드로 내보낼 수 있다.

운영 `.env`, `secrets.toml`, DB 파일, Docker 소켓, 운영 경로를 이 컨테이너에 전달하거나 마운트하지 않는다. 향후 API 키/외부 DB/영속화 요구가 생기면 지금의 공개 세션 격리 계약과 달라지므로 별도 설계한다. 신규 실행 파일이나 자산을 추가하면 `.dockerignore`와 `PUBLIC_FILES.txt`도 함께 검토한다.

신규 도메인의 접속·주요 기능·기존 서비스 검증 후 README의 대표 데모 링크를 신규 주소로 전환했다. 기존 Streamlit Cloud 앱 중지/삭제는 별도로 사용자 승인을 받은 후 수행한다.

## 생성·수정한 파일

| 구분 | 파일 |
| --- | --- |
| 신규 배포 구성 | `Dockerfile`, `.dockerignore`, `compose.yaml` |
| 신규 Caddy 도구·예시 | `deploy/prepare_caddy.py`, `deploy/Caddyfile.demo.example` |
| 신규 문서·테스트 | `docs/DEPLOYMENT.md`, `tests/test_deployment.py`, `tests/test_caddy_candidate.py` |
| 기존 파일 수정 | `README.md`의 데모 링크·배포 안내, `PUBLIC_FILES.txt`의 공개 배포 파일 목록 |

앱 화면·업무 코드와 `requirements.txt`는 변경하지 않았다. 최초 배포 파일 목록이며 이후 추가한 자동배포 파일은 [별도 안내](AUTO_DEPLOYMENT.md)에 설명한다.

## 최초 배포 확인 결과와 검증 범위 (2026-10-20, 자동배포 설정 전)

| 항목 | 확인 상태 |
| --- | --- |
| 데모 엔트리포인트·고정 의존성·가상 데이터 격리 | 로컬 소스/테스트로 확인 |
| 로컬 검증 | 앱/격리/배포 경계 및 Caddy 후보 테스트 88개, 공식 Compose JSON 스키마·Bash 구문 검사 통과 |
| DNS | demo CNAME → inhaaa.com, 둘 다 `76.13.215.52`, 공개 조회에서 AAAA 관측 안 됨 |
| 소스와 빌드 원본 | VPS 소스 HEAD `9f0cba8`, 이미지 빌드 원본 `c0d96b53e896ba27fd03de6fa3770ac4da7569f5`. 후보 생성 도구·문서만 추가돼 앱 코드는 동일 |
| VPS 사전 확인 | Compose v5.3.1, 메모리 available 7.1GiB, 여유 디스크 38GB. 배포 전 8502 리스너 없음, Caddy 실행 설정 `/etc/caddy/Caddyfile` 확인 |
| Docker 빌드·실행 | VPS에서 `pricesys-demo:c0d96b5-20261020` 빌드 후 Healthy. 데모는 `127.0.0.1:8502`만 공개하며 호스트 health `ok` |
| Caddy 후보·백업 | 기존 5개 bind 동일 확인. `/etc/caddy/Caddyfile.before-demo.20261020T041656190872Z` 백업·후보 권한 600, 후보 validate 성공·diff는 신규 블록만 확인 |
| Caddy 적용·영구 저장 | 후보 reload → 응답·브라우저 검증 → 원본 동일성·파일시스템·소유자·권한 검사 → 심볼릭 링크를 보존한 원본 교체 완료. 최종 원본 validate 성공, 백업 대비 신규 데모 블록만 확인. 추가 reload 불필요 |
| 신규 HTTPS·TLS | demo HTTPS 200, VPS에서 `curl -fsS https://demo.inhaaa.com/_stcore/health`가 `-k` 없이 `ok`. 로컬 회사 TLS 검사 환경의 제약은 유지되며, 원 서버 인증서 발급자·만료·전체 체인은 별도 조사하지 않음 |
| PC 브라우저 | 로그인·홈·10개 메뉴 표시와 진입, 가상 카테고리 생성 → 다른 화면 이동 후 재조회 → 수정 → 삭제 성공. 데모 재시작 후 재로그인 성공 |
| 추천·백테스트 샘플 | 추천 조회 1건 → 샘플 계산 → 저장 완료 1건 표시. 백테스트 샘플 4건·1건·25% 표 표시 확인 |
| WebSocket 상호작용 | 실제 로그인·메뉴 이동·CRUD가 동작함을 확인. Network의 101 업그레이드 헤더를 직접 캡처하지는 않음 |
| 모바일 실기기 | 로그인·홈·사이드바 정상 확인. 그 외 전체 입력·표·다운로드 동작은 미검증 |
| 데모 재시작 | 데모 restart 후 같은 `c0d96b5-20261020` 이미지의 `up --wait`로 Healthy 복구, 최종 running·`unless-stopped` 확인 |
| 부팅 설정 | Docker·Caddy 서비스 enabled 확인. OS 전체 재부팅과 실제 부팅 복구 시험은 수행하지 않음 |
| 기존 서비스 보존 | 운영 HTTPS 401 Basic Auth, 포트폴리오 HTTPS 200, www → inhaaa.com 301. 운영 컨테이너 ID·running 상태·시작 시각이 배포 전 기준과 동일 |
| 검증 기록 | `current-image`는 `pricesys-demo:c0d96b5-20261020`, `current-commit`은 전체 `c0d96b5` 커밋으로 저장. `verified-compose.yaml`·`containers-verified.txt` 저장과 두 컨테이너의 running·`unless-stopped` 확인 |
| 추가 검증 | 다운로드 파일의 내용·정상 생성, 모든 화면의 전체 업무 동작은 미검증. OS 전체 재부팅·별도 부하 테스트·원 서버 인증서 상세 조사는 수행하지 않음 |

VPS 명령은 사용자가 Hostinger Webconsole에서 실행하고 결과를 전달했다. 신규 데모 컨테이너와 Caddy 도메인 블록을 추가했으며 기존 운영 Compose·DB, 포트폴리오 파일, main 브랜치와 Streamlit Cloud 앱은 유지했다. 공개 401 응답만으로 인증 후 운영 기능 전체를 보증하지 않으며, 확인하지 않은 항목은 위 표에 구분했다.

공식 참고: [Streamlit Docker](https://docs.streamlit.io/deploy/tutorials/docker), [Docker Compose 서비스 설정](https://docs.docker.com/reference/compose-file/services/).
