# Hostinger VPS 독립 배포

목표 주소는 `https://demo.inhaaa.com`이다. 아래 명령은 Hostinger **Webconsole의 Ubuntu Bash**에서 실행한다. 관리자 권한이 필요하면 콘솔에서 직접 `sudo -i`로 전환한다. 비밀번호·개인키·Caddy 인증 해시는 채팅이나 Git에 올리지 않는다.

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

아래 최초 배포 명령은 **이 작업에서 만든 배포 파일까지 GitHub에 반영한 뒤** 실행한다. 로컬 파일 작성만으로 GitHub에 자동 반영되지는 않는다. 기존 main에 Dockerfile이 없으면 clone만으로 이번 구성이 내려오지 않는다. 아래 예시는 기존 Streamlit Cloud가 사용하는 main을 보존하기 위해 `codex/vps-demo-deployment` 브랜치를 지정한다. 검토 후 main에 병합하면 향후 배포 대상도 main으로 전환할 수 있다.

로컬 변경 검토·테스트 후 필요한 파일만 커밋하고 push한다. `.local`, `.env`, 비밀 파일은 포함하지 않는다. 배포용 새 파일은 `PUBLIC_FILES.txt`에 등록되어 있다. 배포 준비 ZIP도 이 공개 목록으로만 만들 수 있다.

VPS에서 아래 블록은 `/srv/pricesys-demo`가 **아직 없을 때만** 실행한다. 이미 있다면 파일과 소유자를 먼저 확인하고 재배포 절차를 따른다.

```bash
test ! -e /srv/pricesys-demo && git clone --branch codex/vps-demo-deployment https://github.com/inhaaa/PriceSystem-demo.git /srv/pricesys-demo
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

## 4. Caddy 후보 작성·검증

`deploy/Caddyfile.demo.example`은 실제 bind 확인 전에는 적용할 수 없는 예시다. 기존에 같은 도메인이 이미 정의되어 있으면 중복 추가하지 말고 해당 블록을 먼저 검토한다. 기존 글로벌 옵션이 자동 HTTPS를 끄거나 인증서를 별도로 관리한다면 현행 방식에 맞춰 신규 호스트만 추가한다.

Caddy는 동일 포트에서 bind 유무나 주소를 혼용하면 다른 리스너가 요청을 받을 수 있다. 공개 포트폴리오의 검증된 bind 주소 목록을 확인한 뒤 신규 블록에도 일관되게 적용한다. [bind 공식 설명](https://caddyserver.com/docs/caddyfile/directives/bind)을 참고한다.

### Webconsole에서 후보 자동 생성

기존 모든 명시적 `bind`가 동일하고 외부 `import`가 없는 현재 구성에서는 다음 도구를 사용할 수 있다. 먼저 이 도구가 포함된 배포 브랜치를 받는다. 실행 중인 컨테이너는 소스 업데이트만으로 바뀌지 않는다.

```bash
git -C /srv/pricesys-demo pull --ff-only origin codex/vps-demo-deployment
python3 /srv/pricesys-demo/deploy/prepare_caddy.py
caddy validate --config /etc/caddy/Caddyfile.demo-candidate --adapter caddyfile
diff -u /etc/caddy/Caddyfile /etc/caddy/Caddyfile.demo-candidate
```

도구는 현재 파일의 내용을 그대로 백업하고 신규 블록만 붙인 후보를 만든다. 백업과 후보는 권한 600으로 생성한다. 실제 bind·인증 해시는 화면에 출력하지 않는다. 기존 도메인 설정, 다른 bind, import, 기존 후보·백업 기록이 있으면 덮어쓰지 않고 중단한다. 실패해도 실제 Caddyfile을 수정하거나 서비스를 reload하지 않는다. 일부 준비 파일이 남으면 삭제하지 말고 오류를 확인한다.

이 방법을 사용했다면 아래 **수동 후보 생성** 부분은 건너뛰고 후보 검증과 비교를 확인한 후 **후보 반영**으로 진행한다. diff에는 신규 데모 블록 추가만 있어야 한다. `diff`는 차이가 있으면 종료 코드 1을 반환하므로 출력 내용으로 판단한다.

### 수동 후보 생성

먼저 전체 파일을 백업하고 후보를 만든다. 이 파일들에는 기존 인증 해시가 있으므로 서버에만 보관한다.

```bash
cd /srv/pricesys-demo
umask 077
CADDY_BACKUP="/etc/caddy/Caddyfile.before-demo.$(date -u +%Y%m%dT%H%M%SZ)"
cp -pL /etc/caddy/Caddyfile "$CADDY_BACKUP"
printf '%s\n' "$CADDY_BACKUP" > .local/deploy/caddy-backup-path
cp -pL /etc/caddy/Caddyfile /etc/caddy/Caddyfile.demo-candidate
chmod 600 "$CADDY_BACKUP" /etc/caddy/Caddyfile.demo-candidate
cp deploy/Caddyfile.demo.example .local/deploy/Caddyfile.demo
nano .local/deploy/Caddyfile.demo
```

편집기에서 `__CONFIRMED_BIND_ADDRESSES__` 두 곳을 **확인한 실제 bind 주소 목록**으로 바꾼다. 현재 서버처럼 HTTP/HTTPS를 명시하는 구성을 예시에 반영했다. 다른 사이트의 설정은 수정하지 않는다. 자리표시자가 남으면 아래 명령은 추가를 거부한다.

```bash
if grep -q '__CONFIRMED_BIND_ADDRESSES__' .local/deploy/Caddyfile.demo; then
  printf '%s\n' '실제 bind 주소를 먼저 입력하세요.'
else
  printf '\n' >> /etc/caddy/Caddyfile.demo-candidate
  cat .local/deploy/Caddyfile.demo >> /etc/caddy/Caddyfile.demo-candidate
  caddy validate --config /etc/caddy/Caddyfile.demo-candidate --adapter caddyfile
fi
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
diff -u "$CADDY_BACKUP" /etc/caddy/Caddyfile.demo-candidate
```

후보 생성은 한 번만 한다. 재시도할 때는 백업에서 후보를 다시 만들고 신규 블록이 중복되지 않았는지 확인한다. `diff`에 **신규 데모 블록 추가만** 있어야 한다. 상대 경로 import가 있으면 후보도 `/etc/caddy`에서 검증되도록 기존 파일과 같은 실행 디렉터리를 사용한다. 환경변수 치환이 있다면 실제 Caddy 서비스와 같은 환경에서도 유효해야 한다.

### 후보 반영

`Valid configuration`과 diff를 직접 확인한 뒤 아래를 실행한다. 후보·백업의 크기와 읽기 권한을 검사하고, 원본이 백업 후 바뀌지 않았는지도 확인한다. 검증한 후보를 새 임시 파일에 완전히 복사한 뒤 원본의 소유자·권한을 적용하고 같은 디렉터리 안에서 교체한다. Caddyfile이 심볼릭 링크라면 대상 파일에 반영하여 링크를 유지한다.

```bash
CADDY_BACKUP="$(cat .local/deploy/caddy-backup-path)"
CADDY_TARGET="$(readlink -f /etc/caddy/Caddyfile)"
test -r "$CADDY_BACKUP" && test -s "$CADDY_BACKUP" && test -r /etc/caddy/Caddyfile.demo-candidate && test -s /etc/caddy/Caddyfile.demo-candidate
cmp -s "$CADDY_BACKUP" "$CADDY_TARGET"
caddy validate --config /etc/caddy/Caddyfile.demo-candidate --adapter caddyfile
```

상기 명령이 모두 성공해야 아래 교체를 수행한다. `cmp`가 실패하면 다른 변경이 있는 것이므로 멈추고 비교한다.

```bash
if test -s "$CADDY_BACKUP" && test -s /etc/caddy/Caddyfile.demo-candidate && cmp -s "$CADDY_BACKUP" "$CADDY_TARGET" && cp /etc/caddy/Caddyfile.demo-candidate "${CADDY_TARGET}.demo-new" && chown --reference="$CADDY_TARGET" "${CADDY_TARGET}.demo-new" && chmod --reference="$CADDY_TARGET" "${CADDY_TARGET}.demo-new" && mv -T "${CADDY_TARGET}.demo-new" "$CADDY_TARGET" && caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && systemctl reload caddy; then
  systemctl is-active caddy
else
  printf '%s\n' '적용 실패: 새 reload를 반복하지 말고 백업과 현재 파일을 비교한 뒤 아래 Caddy 복구 절차를 실행하세요.'
fi
journalctl -u caddy --since '-5 minutes' --no-pager -n 80
```

일반적인 Caddy 설정에서 호스트 이름 사이트는 자동 HTTPS와 HTTP 리디렉션을 사용한다. 현재 서버의 글로벌 옵션과 방화벽 80/443·인증서 발급 로그를 함께 확인한다. 데모 블록에는 Caddy Basic Auth를 추가하지 않으며, 앱의 공개 `admin/admin` 로그인은 유지한다. 기존 Basic Auth·리디렉션·SSL·프록시는 그대로 둔다.

`reverse_proxy`는 WebSocket 업그레이드를 기본 지원하므로 CORS/XSRF 보호를 끄거나 수동 Upgrade 헤더를 추가하지 않는다. 다만 **Caddy reload 때 기존 WebSocket이 재연결될 수 있다.** 운영 사용량이 낮을 때 반영하고 사용 중 세션 영향이 전혀 없다고 단정하지 않는다. [Caddy WebSocket 동작](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming)

## 5. 신규·기존 서비스 검증

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

기대 결과는 demo HTTP에서 같은 호스트의 HTTPS로 리디렉션, demo HTTPS/health에서 200/`ok`, pricesys에서 미인증 401과 Basic realm, inhaaa에서 200, www에서 inhaaa로 301이다. 운영 컨테이너 ID·시작 시각이 사전 기록과 같은지도 확인한다. `curl -k`로 인증서 오류를 무시하고 통과로 처리하지 않는다.

PC와 스마트폰 브라우저에서 다음을 확인한다. HTTP 200이나 health 응답만으로 기능 검증을 완료하지 않는다.

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

모두 통과한 뒤 검증된 이미지와 Compose를 기록한다.

```bash
docker inspect --format '{{.Config.Image}}' pricesys-demo > .local/deploy/current-image
cp compose.yaml .local/deploy/verified-compose.yaml
git rev-parse HEAD > .local/deploy/current-commit
```

## 6. 소스 수정 후 재배포

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

데모 재생성·재시작 때 현재 체험 세션은 초기화된다. 앱은 한 컨테이너에서 실행하며 무중단 배포나 다중 인스턴스 세션 공유를 구현하지 않는다. 자동 배포는 이 수동 절차가 검증된 후 도입한다.

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

신규 도메인의 접속·기능·기존 서비스 검증이 끝난 후 README의 대표 데모 링크를 전환한다. 기존 Streamlit Cloud 앱 중지/삭제는 별도로 사용자 승인을 받은 후 수행한다.

## 실제 확인과 남은 작업 (2026-10-20)

| 항목 | 확인 상태 |
| --- | --- |
| 데모 엔트리포인트·고정 의존성·가상 데이터 격리 | 로컬 소스/테스트로 확인 |
| 로컬 검증 | 앱/격리/배포 경계 및 Caddy 후보 테스트 88개 통과, 공식 Compose JSON 스키마 검사 통과. 실제 Docker 엔진 실행은 별도 확인 필요 |
| DNS | demo CNAME → inhaaa.com, 둘 다 `76.13.215.52`, 공개 조회에서 AAAA 관측 안 됨 |
| 기존 공개 서비스 | 포트폴리오 HTTPS 200, www HTTPS 301, 운영 HTTPS 401 Basic Auth 관측 |
| 데모 HTTPS | 로컬 TLS handshake 실패. 회사 TLS 검사 환경이 개입해 원 서버 원인·인증서 체인은 미확인 |
| Webconsole 사전 확인 | 운영 컨테이너만 8501 사용, 8502 TCP 리스너 없음, Compose v5.3.1, 메모리 7.8GiB 중 available 7.1GiB |
| Caddy bind 구조 | 사용자 제공 출력에서 기존 HTTP/HTTPS 블록 모두 명시적 bind 사용. 실제 주소는 서버 안에서 확인 필요 |
| VPS 파일·여유 디스크·서비스 실행 경로 | 서버에서 추가 확인 필요 |
| Docker 빌드/실행·재시작·부팅 복구 | Docker/VPS에서 확인 필요 |
| 신규 HTTPS·WebSocket·PC/모바일·CRUD | 실제 배포 후 확인 필요 |
| 기존 컨테이너 ID·운영 설정 불변 | 서버 사전/사후 비교 필요 |

이번 로컬 작업은 VPS·DNS·기존 서비스·Streamlit Cloud를 수정하지 않았다. 공개 HTTP 사전 확인은 인증 후 내부 기능이나 원 서버 인증서의 정상 동작을 보증하지 않는다.

공식 참고: [Streamlit Docker](https://docs.streamlit.io/deploy/tutorials/docker), [Docker Compose 서비스 설정](https://docs.docker.com/reference/compose-file/services/).
