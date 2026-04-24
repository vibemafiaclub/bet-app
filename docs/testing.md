# BET Testing Policy

## 원칙
- **mock 금지.** DB는 실 SQLite temp file(`tmp_path` fixture)을 쓴다.
- **ORM 도입 금지.** 표준 라이브러리 `sqlite3`만 사용. 테스트도 동일.
- **coverage % 목표 없음.** 필수 시나리오가 green이면 DoD 충족.
- 테스트 DB는 각 테스트마다 별도 temp file → teardown에서 제거.
- `pytest.monkeypatch`를 통한 env / 모듈 attribute / 모듈 전역 dict 조작은 mock 금지 원칙에 저촉되지 않음 (conftest가 이미 이 방식으로 DB 경로와 env를 주입한다). 단 DB 자체를 mock하거나 `time.monotonic` 자체를 패치하는 것은 금지.

## 테스트 구성 (6 파일)
1. `tests/test_aggregates.py` — 집계 함수 단위 테스트 (`max_weight_per_session`, `total_volume_per_session`). **CHECK 제약 스모크 테스트 포함**: 음수 weight / 미등록 exercise INSERT가 `sqlite3.IntegrityError`를 내는지 런타임 증명.
2. `tests/test_auth.py` — 로그인 / 세션 / 로그아웃 라우트. **iteration 2 확장**: 관장 부트 시드(신규 INSERT / 기존 password_hash 불변 / username mismatch 시 warn+skip), non-owner 트레이너 로그인, `session["user"]` 스키마 검증.
3. `tests/test_log_routes.py` — 로그 폼 GET / POST, 빈 세트 스킵, 검증 실패 처리. **iteration 2 확장**: POST /log가 세션의 `trainer_id`를 `pt_sessions.input_trainer_id`에 기록.
4. `tests/test_dashboard.py` — `chart-data.json` 계약. **빈 member 케이스(세션 0건)에서 labels=[], datasets=[] 반환 확인 필수**.
5. `tests/test_e2e_dashboard.py` — Playwright headless. uvicorn 서브프로세스 fixture는 teardown에서 `process.terminate() + process.wait(timeout=5)` 필수. 임시 DB 파일 cleanup 필수.
6. `tests/test_export.py` (iteration 2 신규) — `/admin/export/sessions.csv` 권한 분기(owner only), `trainer_id` 쿼리 필터, 60초 rate limit, stdout 감사 로그 포맷, NULL `input_trainer_id` row의 빈 이름 렌더, UTF-8 BOM 본문 접두.
7. `tests/test_my_export.py` (iteration 3 신규) — `/my/export/sessions.csv` 권한 분기(is_authenticated만 필요, is_owner bypass 없음), 본인 `input_trainer_id` 필터, 관장 로그인 시에도 본인 row만 반환, 60초 rate limit (관장 export와 dict 물리 분리), stdout 감사 로그 포맷 `[my-export] trainer_id=X rows=N`, UTF-8 BOM 본문 접두, `filename="my_sessions_YYYYMMDD.csv"` 헤더, **컬럼 동등성 회귀 테스트**(관장 `/admin/export?trainer_id=X` body와 X 로그인 `/my/export` body가 bit-exact 일치).
8. `tests/test_member_access.py` (iteration 5 신규) — R5 partial isolation 가드. 12 시나리오: 타 트레이너 회원 GET/POST/chart-data/dashboard 4 라우트 → 403 "forbidden"; POST 403 시 pt_sessions·session_sets INSERT 0건 회귀; 본인 회원 4 라우트 → 200 regression; 관장 bypass 4 라우트 → 200 (tid 일치); 관장 + URL tid 불일치 → 404 (URL 위조 방지); 비로그인 → 303 /login; 존재하지 않는 mid → 404 (403과 구분); GET / 비관장 로그인 → 본인 첫 회원으로 303; GET / 관장 로그인 → 기존 동작 유지 303; GET / 회원 0건 트레이너 → 200 안내 페이지.

## 프레임워크
- `pytest`, `pytest-asyncio` (async 라우트 테스트용)
- `httpx.AsyncClient` 또는 FastAPI `TestClient`
- `playwright` (chromium headless)

## 산출물
- 집계/라우트 테스트는 green/red 판정만.
- E2E 테스트는 `iterations/1-20260424_020912/artifacts/dashboard.png` 스크린샷 생성을 AC로 요구.
