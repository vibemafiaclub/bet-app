# BET Testing Policy

## 원칙
- **mock 금지.** DB는 실 SQLite temp file(`tmp_path` fixture)을 쓴다.
- **ORM 도입 금지.** 표준 라이브러리 `sqlite3`만 사용. 테스트도 동일.
- **coverage % 목표 없음.** 필수 시나리오가 green이면 DoD 충족.
- 테스트 DB는 각 테스트마다 별도 temp file → teardown에서 제거.

## 테스트 구성 (5 파일)
1. `tests/test_aggregates.py` — 집계 함수 단위 테스트 (`max_weight_per_session`, `total_volume_per_session`). **CHECK 제약 스모크 테스트 포함**: 음수 weight / 미등록 exercise INSERT가 `sqlite3.IntegrityError`를 내는지 런타임 증명.
2. `tests/test_auth.py` — 로그인 / 세션 / 로그아웃 라우트.
3. `tests/test_log_routes.py` — 로그 폼 GET / POST, 빈 세트 스킵, 검증 실패 처리.
4. `tests/test_dashboard.py` — `chart-data.json` 계약. **빈 member 케이스(세션 0건)에서 labels=[], datasets=[] 반환 확인 필수**.
5. `tests/test_e2e_dashboard.py` — Playwright headless. uvicorn 서브프로세스 fixture는 teardown에서 `process.terminate() + process.wait(timeout=5)` 필수. 임시 DB 파일 cleanup 필수.

## 프레임워크
- `pytest`, `pytest-asyncio` (async 라우트 테스트용)
- `httpx.AsyncClient` 또는 FastAPI `TestClient`
- `playwright` (chromium headless)

## 산출물
- 집계/라우트 테스트는 green/red 판정만.
- E2E 테스트는 `iterations/1-20260424_020912/artifacts/dashboard.png` 스크린샷 생성을 AC로 요구.
