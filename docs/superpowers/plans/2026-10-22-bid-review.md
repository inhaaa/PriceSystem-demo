# 투찰 검토함 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. 사용자 요청에 따라 현재 세션에서 병렬 수행한다.

**Goal:** 기존 디자인의 투찰 검토함에서 공고별 체크·상태·메모를 실제 저장하고 다시 조회한다.

**Architecture:** 순수 Python 검토 데이터 계약을 기존 `demo/services.py`, Streamlit 화면을 기존 `demo/bid_pages.py`에 둔다. 세션별 사전을 사용하고 기존 SQLite·추천 엔진·설정에는 변경을 가하지 않는다. 기존 배포 허용 목록에 포함된 모듈을 사용한다.

**Tech Stack:** Python, unittest, Streamlit AppTest, 기존 CSS 토큰.

---

### Task 1: 검토 데이터 계약 — 하위 에이전트

- [x] `tests/test_reviews.py`에 기본값·복사 격리·왕복 저장·완료 조건·검증 실패 시 원본 보존 테스트를 먼저 작성한다.
- [x] `.venv/Scripts/python.exe -m unittest tests.test_reviews -v`로 기능 누락 실패를 확인한다.
- [x] 설계 문서의 `get_review`/`save_review` 계약을 `demo/services.py`에 구현한다.
- [x] 같은 테스트를 실행해 통과를 확인한다.

### Task 2: 화면과 연결 — 주 에이전트

- [x] `tests/test_review_pages.py`에 AppTest로 저장/재조회, 완료 조건, 검색·필터, 공고 전환·빈 상태를 먼저 작성한다.
- [x] `tests/test_app.py`, `tests/test_workspace.py`에 새 메뉴와 탭 유지·세션 초기화 검증을 추가한다.
- [x] `.venv/Scripts/python.exe -m unittest tests.test_review_pages tests.test_workspace -v`로 화면·메뉴 누락 실패를 확인한다.
- [x] `demo/bid_pages.py`에 `review_page`를 구현하고 `demo/workspace.py`, `app.py`에 `bid_review`를 연결한다.
- [x] `assets/demo.css`에 기존 색상 변수를 사용하는 검토 작업대·모바일 배치 스타일을 추가한다.
- [x] `demo/data_pages.py`의 기존 보관/복원 메타데이터에 검토 내용을 포함하고 관련 테스트를 통과시킨다.

### Task 3: 문서·검증·검토

- [x] README·ARCHITECTURE에 새 화면과 데이터 계약을 반영한다. 기존 실행 모듈을 사용하므로 PUBLIC_FILES와 배포 설정 수정은 필요 없다.
- [x] `.venv/Scripts/python.exe -m unittest discover -s tests -t . -v`로 전체 테스트를 실행한다.
- [x] 로컬 Streamlit을 실행해 브라우저에서 체크·상태 저장과 데스크톱·모바일 배치를 확인한다.
- [x] 독립 에이전트가 요구사항과 코드 품질을 검토하고 발견된 문제를 수정한 뒤 관련 검증을 반복한다.
- [x] 변경 요약·검증 결과·세션 저장 범위를 사용자에게 전달한다. 기존 미커밋 변경을 포함한 자동 커밋·push는 하지 않는다.

## 검증 결과

- 2026-10-22: 전체 unittest 185개 실행, 실패 0개, POSIX 전용 3개 건너뜀.
- 독립 코드 리뷰: 요구사항 및 품질 검토에서 구체 결함 없음.
- 실제 브라우저: 네 항목과 메모 입력 후 검토완료 저장, 성공 메시지·완료 1건·진행률 4/4 확인.
- 1440px 좌우 작업대, 390px 세로 배치와 문서 가로 넘침 없음 확인. 임시 뷰포트 설정 복원.
- git diff --check 통과. 커밋·push·운영 배포 없음.
