# main push 자동배포

GitHub의 `main`을 VPS가 약 60초마다 확인한다. 변경이 있으면 전용 builder로 이미지를 만들고 격리 컨테이너에서 전체 테스트를 실행한 뒤 `pricesys-demo`만 교체한다. 주기는 이전 작업 종료 후 60초이며 빌드·테스트 시간이 추가된다. GitHub Actions, SSH 키, 웹훅, 신규 공개 포트는 사용하지 않는다.

## 설치 확인 (2026-10-21)

현재 VPS에는 고정 updater·Compose·서비스·timer를 설치하고 timer를 활성화했다. 아래 최초 설치 절차는 반복하지 않는다.

- 실제 builder 제한: 메모리 `1610612736`, CPU period `100000`, quota `75000` 확인.
- 첫 서비스 실행: `413574f1b734a87caec054dccbb9c0ec6d72b93a` 이미지 빌드 후 Linux 격리 컨테이너에서 테스트 **118개 모두 통과**(14.640초). 데모 Healthy, `Result=success`, `ExecMainStatus=0` 확인.
- HTTPS health `ok`, 운영 컨테이너 ID·running 상태·시작 시각이 최초 배포 전 기준과 동일함을 확인.
- timer의 부팅 자동 시작 symlink와 `list-timers`의 LAST/NEXT 예약 확인.

VPS 명령은 사용자가 Hostinger Webconsole에서 실행하고 결과를 전달했다. 실행 중인 정확한 커밋과 이후 자동배포 결과는 아래 로그·`current-commit` 명령으로 확인한다. OS 전체 재부팅 시험은 수행하지 않았다.

## 배포 경계

- 대상: `https://github.com/inhaaa/PriceSystem-demo.git`의 `main`.
- 호스트: `/srv/pricesys-demo`, 프로젝트·컨테이너 `pricesys-demo`, 서비스 `app`, `127.0.0.1:8502`.
- 빌드: 전용 `pricesys-demo-builder`, CPU 0.75개·메모리 1.5GiB. 기본 builder를 바꾸지 않는다.
- 테스트: UID 10001, CPU 0.75개·메모리 768MiB·PID 128개, network none, 읽기 전용 snapshot, 권한 상승 금지.
- 적용: 서버에 설치한 **고정 Compose**만 사용한다. Git의 Compose가 검증본과 다르면 중단한다. `.env`는 읽지 않는다.
- updater와 systemd unit도 서버 고정본이다. 해당 파일 수정은 Git push만으로 실행 로직에 반영되지 않으며 별도 검토·설치가 필요하다.
- Caddy, 운영 Compose·DB·컨테이너, 포트폴리오 파일을 수정·재시작하는 명령은 없다. 운영 컨테이너 ID·상태·시작 시각이 바뀌면 중단한다.

새 커밋은 `git archive`의 별도 snapshot으로 빌드한다. VPS의 작업 트리는 자동 checkout/pull하지 않으며, **실제 실행 버전은 `.local/deploy/current-commit`**으로 확인한다. `main`에 쓸 수 있는 사용자는 데모 코드를 배포할 수 있으므로 해당 브랜치는 신뢰할 수 있는 변경만 반영한다.

## 최초 설치: Webconsole에서 한 줄씩

현재 설치 여부와 로컬 변경을 먼저 확인한다. 아래는 설치 전 절차이며 **한 줄씩 실행하고 오류가 있으면 멈춘다**. 기존 자동배포 파일이 있으면 설치 도구가 덮어쓰지 않고 중단한다.

```bash
git -C /srv/pricesys-demo status --short
git -C /srv/pricesys-demo fetch origin main
git -C /srv/pricesys-demo switch main
git -C /srv/pricesys-demo pull --ff-only origin main
python3 -m unittest discover -s /srv/pricesys-demo/tests -t /srv/pricesys-demo -p 'test_auto_deploy*.py' -q
```

`status`는 빈 출력이어야 하며 실제 Linux에서 자동배포 테스트가 통과해야 한다. 위 테스트는 외부 Git/Docker 호출을 대체하고 임시 디렉터리 안에서만 파일을 검증한다.

```bash
docker buildx create --name pricesys-demo-builder --driver docker-container --driver-opt memory=1536m,cpu-period=100000,cpu-quota=75000
docker buildx inspect --bootstrap pricesys-demo-builder
docker inspect --format '{{.HostConfig.Memory}} {{.HostConfig.CpuPeriod}} {{.HostConfig.CpuQuota}}' buildx_buildkit_pricesys-demo-builder0
```

builder가 이미 있으면 새로 생성하거나 기본 builder를 변경하지 말고 기존 설정부터 확인한다. 마지막 출력은 `1610612736 100000 75000`이어야 한다.

```bash
python3 /srv/pricesys-demo/deploy/auto_deploy.py --install
systemd-analyze verify /etc/systemd/system/pricesys-demo-auto.service /etc/systemd/system/pricesys-demo-auto.timer
python3 /usr/local/lib/pricesys-demo/auto_deploy.py --check
systemctl daemon-reload
systemctl start pricesys-demo-auto.service
```

설치는 updater·고정 Compose·새 unit 두 개만 생성하고 서비스는 시작하지 않는다. `--check`는 현재 이미지·운영 상태·main 커밋·builder 제한만 확인하며 빌드·교체하지 않는다. 마지막 `start`는 실제로 새 버전을 빌드·테스트·배포하며 몇 분 걸릴 수 있다. Caddy와 Docker 서비스는 reload/restart하지 않는다.

```bash
systemctl show pricesys-demo-auto.service -p Result -p ExecMainStatus
journalctl -u pricesys-demo-auto.service --no-pager -n 60
curl -fsS --max-time 20 https://demo.inhaaa.com/_stcore/health
docker inspect --format '{{.Id}} {{.State.Status}} {{.State.StartedAt}}' pricesys-app-1
```

`Result=success`, `ExecMainStatus=0`, 배포 완료 로그, health `ok`, 기존 운영 컨테이너 기준과 일치를 확인한 후 timer를 켠다. oneshot 서비스가 완료 후 `inactive (dead)`가 되는 것은 정상이다.

```bash
systemctl enable --now pricesys-demo-auto.timer
systemctl list-timers --all pricesys-demo-auto.timer --no-pager
```

마지막으로 별도 `main` 커밋을 push하고 수동 `start` 없이 새로운 커밋의 자동 배포 로그와 HTTPS health를 확인한다. 설치·활성화 출력이 확인되기 전에는 자동배포가 완료됐다고 판단하지 않는다.

## 이후 소스 수정

로컬에서 테스트 후 `main`으로 commit/push한다. VPS에서 따로 pull·빌드·restart할 필요가 없다. 새 이미지가 테스트를 통과할 때까지 기존 데모가 실행되고, 교체 시점에는 짧은 재연결과 세션 초기화가 발생한다.

```bash
journalctl -u pricesys-demo-auto.service --no-pager -n 60
cat /srv/pricesys-demo/.local/deploy/current-commit
docker inspect --format '{{.Config.Image}} {{.State.Health.Status}}' pricesys-demo
```

문서만 바뀐 커밋도 빌드·테스트한다. 동일한 성공 커밋은 다시 빌드하지 않는다. 파일이 추가되면 기존 `PUBLIC_FILES.txt`·`.dockerignore`·Dockerfile의 명시적 복사 목록도 검토한다. Dockerfile과 의존성 변경은 빌드·테스트를 거쳐 반영하지만 Compose·Caddy·updater·unit 변경은 별도 검토한다.

## 실패·중지·롤백

fetch 오류는 다음 주기에 재확인한다. 빌드·테스트 실패는 실행 중 데모를 그대로 두며, 교체·health 실패는 직전 이미지로 데모만 복구한다. 실패한 커밋은 반복 빌드하지 않고 다음 수정 push를 기다린다. 일시적 오류 해결 후 같은 커밋을 직접 재시도할 때만 실행한다.

```bash
python3 /usr/local/lib/pricesys-demo/auto_deploy.py --retry
```

timer와 직접 실행은 같은 파일 잠금을 사용한다. 테스트가 실패·중단되면 이번 작업에서 만든 고유 테스트 컨테이너만 정리한다. Docker 전체 prune, 전체 프로젝트 down, 기존 컨테이너 삭제는 수행하지 않는다.

자동배포를 일시 중지하려면 아래를 실행한다. 실행 중인 서비스가 있다면 끝날 때까지 기다린다. timer 중지는 현재 데모를 중지하지 않는다.

```bash
systemctl stop pricesys-demo-auto.timer
systemctl is-active pricesys-demo-auto.service
```

서비스가 `inactive`인 것을 확인한 뒤 [수동 재배포·롤백](DEPLOYMENT.md)의 6·7절을 사용할 수 있다. 롤백 후 timer를 다시 켜면 현재 main이 재배포될 수 있으므로 원인을 수정한 뒤 재개한다.

```bash
systemctl start pricesys-demo-auto.timer
```

이전 이미지·Compose·커밋은 `.local/deploy/rollback-*`에 보관한다. 빌드 전 여유 디스크가 5GiB 미만이면 중단한다. 빌드 캐시·이전 이미지는 자동 전체 정리하지 않으므로 장기 운영 시 사용량을 확인한다. 갑작스러운 전원 상실로 이미지·커밋 기록 저장이 중간에 끊기면 실제 컨테이너와 기록을 비교해 수동 복구해야 할 수 있다. 기존 Streamlit Cloud 앱 중지·삭제는 이 설정과 별개다.

공식 참고: [Docker 전용 builder와 자원 제한](https://docs.docker.com/build/builders/drivers/docker-container/), [systemd timer](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).
