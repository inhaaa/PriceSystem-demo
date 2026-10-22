# PriceSystem 디자인 적용 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. 각 작업은 테스트 실패 확인 → 구현 → 검증 순서로 진행한다.

**Goal:** 승인된 신뢰 중심 업무형과 표 중심 실무형을 현재 Streamlit 앱에 결합하고 로그인·홈·분석 화면에 일관된 브랜드를 적용한다.

**Architecture:** 기존 Streamlit 메뉴, 다중 업무 탭, 세션 저장소, 샘플 서비스와 위젯 키를 유지한다. 표현 계층(테마·브랜드 HTML·홈·추천 화면 배치)만 수정한다. 가격 밴드 모티프, 포레스트 그린/아이보리, 제한적인 라임 포인트로 업무 정체성을 만든다.

**Tech Stack:** Python, Streamlit 1.59.2, pandas, 로컬 CSS/SVG, unittest AppTest, Playwright 화면 검증. 추가 패키지·환경설정·운영 DB 변경 없음.

## 화면 및 인터페이스 계약

- `page_header_html(title, description, eyebrow)`, `sidebar_brand_html()`, `login_panel_html(wordmark, tagline, phrase)`, `home_action_card_html(...)` 시그니처 유지. 모든 동적 HTML 텍스트는 escape한다.
- 로그인은 `login_username`, `login_password`, `login_submit` 및 반환값 `(username, password, submitted)`를 유지한다. 기존 WebGL/파티클 스크립트는 로그인에서 마운트하지 않는다.
- 테마는 native Streamlit 테마와 기존 테마 브리지를 유지하며, 업무 영역의 크리스털 배경·반짝임을 렌더링하지 않는다. 입력/표는 불투명하고 두 테마에서 대비를 확보한다.
- 홈은 실제 세션 샘플 데이터의 공고·투찰·결과를 요약하고, 추천계산 및 공고 조회로 이동한다. 가상 성과/성능 수치를 만들지 않는다.
- 추천 화면은 기존 필터·공고 선택 확인·추천계산·자동저장·결과 저장/다운로드 동작과 위젯 키를 유지한다. 넓은 공고표와 별도 검토 패널을 결합한다.
- DEMO 및 독립적인 가상 추천금액/실투찰율/신뢰도 안내를 유지한다. 가격 밴드는 브랜드 그래픽이며 실제 추천 범위를 새로 계산하거나 암시하지 않는다.
- 모바일은 열을 쌓고 표만 필요한 범위에서 가로 스크롤한다. 키보드 초점과 reduced-motion을 지원한다.

## 작업

- [x] 1. 기존 전체 테스트를 실행해 기준 상태를 확인한다.
- [x] 2. 테마 담당: `tests/test_workspace_design.py`에 대비·테마·장식 비마운트 검증을 먼저 추가하고 실패 확인 후 `demo/workspace_theme.py`, `assets/demo.css`, `assets/tokens.css`에 새 토큰·레이아웃을 적용한다.
- [x] 3. 브랜드 담당: `tests/test_brand_design.py`에 escape·새 identity·로그인 정적 그래픽 계약을 먼저 추가하고 실패 확인 후 `demo/visual_components.py`, `assets/login.css`, `assets/logo.svg`, 새 로컬 SVG 자산을 구현한다.
- [x] 4. 통합 담당: `tests/test_workspace.py`, `tests/test_bid_pages.py`, `tests/test_visuals.py`의 새 홈/추천 배치 계약을 먼저 작성하고 실패 확인 후 `demo/workspace.py`, `demo/ui.py`, `demo/bid_pages.py`, `app.py`를 수정한다.
- [x] 5. 각 담당 변경을 독립 검토하고 전체 `python -m unittest discover -s tests -t . -q`를 실행한다. 기존 CRUD·세션 격리·CSV 안전성·추천 확인 순서 회귀를 검증한다.
- [x] 6. 로컬 서버에서 로그인·홈·공고 조회·추천·저장·투찰관리 화면을 데스크톱/모바일 및 라이트/다크로 확인한다. 오류/넘침/콘트라스트 문제를 수정한다.
- [x] 7. 실제 구현 화면 스크린샷을 제공하고 변경 범위·검증·남은 한계를 보고한다. 커밋·푸시·배포는 별도 요청 전 수행하지 않는다.

## 검증 명령

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_workspace_design tests.test_brand_design tests.test_workspace tests.test_bid_pages tests.test_visuals -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -q
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8516 --server.headless true
```

각 담당은 자신의 파일만 수정한다. 파일 삭제·설정 변경·전역 설치·DB 변경·git reset/rebase/force push는 하지 않는다.
