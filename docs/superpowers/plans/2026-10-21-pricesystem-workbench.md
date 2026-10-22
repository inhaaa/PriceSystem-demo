# PriceSystem Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. 각 작업은 담당 파일을 나누며 기존 변경을 보존한다.

**Goal:** 승인된 공고 작업대 디자인을 등록→날짜 조회→계산 흐름과 날짜별 업무 홈에 적용한다.

**Architecture:** Streamlit native 위젯과 기존 메모리 DemoStore를 재사용한다. 홈과 이동 상태는 workspace, 등록/조회는 data_pages, 계산은 bid_pages, 공통 표현은 기존 CSS와 테마에서 담당한다.

**Tech Stack:** Python, Streamlit, pandas, unittest/AppTest, Playwright(기존 설치본).

---

### Task 1: 날짜별 홈과 이동 계약 (root)
Files: demo/workspace.py, tests/test_workbench.py, tests/test_app.py

- [x] 다음 계약의 테스트를 먼저 작성하고 실패 확인: `schedule_groups(rows, saved)` → 날짜 오름차순 `[{'date': ISO, 'notices': [rows...], 'calculated': int}]`. 중복 공고는 원본 그대로 유지하며 저장 dict에 해당 id가 있는 경우만 계산 완료로 센다. 빈 입력은 빈 목록이다.
- [x] `open_daily_notices(date_or_iso)` → 날짜 입력·조회 상태를 설정하고 기존 `daily_notices` 탭을 연다. `open_daily_calculation(date_or_iso)` → `daily_requested_date`를 설정하고 `daily_recommend`를 연다. 날짜 전달·기존 선택 초기화 테스트를 추가한다.
- [x] 큰 홈 소개/그림을 날짜별 일정+작은 업무 패널로 교체한다. 월 선택·일정 그룹·날짜별 조회/계산·관심공고 등록 동작을 native 버튼으로 연결한다.
- [x] AppTest 홈 이동과 빈 상태를 확인한다.

### Task 2: 관심공고 등록과 날짜별 공고 작업대 (data agent)
Files: demo/data_pages.py, tests/test_data_workbench.py

- [x] 관심공고 탭이 첫 화면이고 기존 샘플 등록이 동작하는 AppTest를 작성하고 실패 확인한다.
- [x] 관심공고 등록 결과에서 등록일의 날짜별 공고 화면을 여는 버튼 테스트를 먼저 작성한다.
- [x] 기존 업로드 도구를 재사용하고 파일 선택/샘플/등록 단계를 정돈한다. 과거자료와 결과자료는 보조 탭으로 유지한다.
- [x] 날짜별 공고를 목록+작은 실행 패널로 재배치한다. 기존 key와 삭제 확인 가드를 유지한다. 열은 필요한 공고/가격/날짜/계산 이력을 우선한다. 통합 조회의 상세는 기본 접힘으로 변경한다.
- [x] `python -m unittest tests.test_data_workbench tests.test_data_pages -v`와 관련 회귀 검증을 실행한다.

### Task 3: 계산 작업대 (calculation agent)
Files: demo/bid_pages.py, tests/test_calculation_workbench.py, tests/test_bid_pages.py

- [x] 공고 목록과 계산 패널/확인 가드/결과 저장에 대한 AppTest를 먼저 작성하고 실패 확인한다.
- [x] 조회 폼 아래 왼쪽에는 최소 공고 열과 선택, 오른쪽에는 확인·샘플 선택·계산·추천금액·저장을 모은다. 백테스트는 접힌 보조 영역에 둔다.
- [x] 기본 실행 key, 선택 tuple 검증, 조회 변경 시 결과 초기화, auto-save 계약을 보존한다. 표와 결과에는 샘플 표시를 유지한다.
- [x] 기존 계산·관리·결과 관련 테스트를 실행한다.

### Task 4: 공통 스타일과 품질 확인 (root)
Files: assets/demo.css, demo/workspace_theme.py, demo/ui.py, tests/test_workspace_design.py, README.md, docs/images/*

- [x] 테마 대비/사이드바 불변 테스트를 유지하고 변경된 본문 계약에 맞춰 스타일 테스트를 갱신한다.
- [x] 기존 사이드바 CSS는 그대로 유지한다. 흰 작업면+회색 캔버스, 작은 헤더/탭, 5~6px 모서리, 얇은 구분선, compact 폼과 표, 동일한 focus·disabled 상태를 구현한다.
- [x] 전체 unittest 실행: `.venv/Scripts/python.exe -m unittest discover -s tests -v`.
- [x] 실제 로컬 브라우저에서 핵심 3단계 흐름·모든 메뉴·작은 화면·다크·가로 넘침 확인 후 필요한 수정만 한다.
- [x] 최종 화면을 캡처하고 README 화면 설명을 갱신한다. 커밋/배포/설정 변경은 하지 않는다.

## 검토 기록

요구 누락 없음: 왼쪽 메뉴 유지, 작업대 적용, 모든 화면 공통 톤, 상세 최소화, 핵심 세 동작, 홈 일정이 각 작업에 연결되어 있다. 업무 데이터나 기능 확장은 포함하지 않는다. 브랜치는 기존 `codex/pricesystem-design`과 작업 중 변경을 그대로 사용한다.
