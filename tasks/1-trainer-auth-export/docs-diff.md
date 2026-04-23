# docs-diff: trainer-auth-export

Baseline: `542631e`

## `docs/spec.md`

```diff
diff --git a/docs/spec.md b/docs/spec.md
index 9f5a44f..218c1a3 100644
--- a/docs/spec.md
+++ b/docs/spec.md
@@ -1,8 +1,8 @@
-# BET MVP Spec (iteration 1)
+# BET Spec (iteration 2)
 
 ## 개요
 
-PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입력하는 폼과, 회원별 운동 종목별 최대 중량 추이 및 세션당 총 볼륨 추이를 꺾은선 그래프 2개로 시각화하는 단일 뷰 MVP다. 스택은 FastAPI + SQLite + HTMX + Chart.js이며, 트레이너 전용 하드코딩 어드민 인증으로 동작한다. 파일럿 12주 동안 "수치화된 회원 발전 증거"를 트레이너가 확인하고 잠재회원 상담에 활용하는 것이 핵심 목적이다.
+PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입력하는 폼과, 회원별 운동 종목별 최대 중량 추이 및 세션당 총 볼륨 추이를 꺾은선 그래프 2개로 시각화하는 단일 뷰 MVP다. 스택은 FastAPI + SQLite + HTMX + Chart.js이며, 트레이너 전용 하드코딩 어드민 인증으로 동작한다. 파일럿 12주 동안 "수치화된 회원 발전 증거"를 트레이너가 확인하고 잠재회원 상담에 활용하는 것이 핵심 목적이다. iteration 2부터는 단일 헬스장 내 다중 트레이너 로그인 계정과 세션 기록의 "입력자 트레이너" 귀속, 관장(is_owner) 전용 CSV 내보내기를 지원한다. 다중 헬스장과 복잡 RBAC는 여전히 범위 외.
 
 ## 스택
 - Python 3.12 / FastAPI / uvicorn
@@ -16,10 +16,12 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 ## 데이터 모델
 4개 테이블. 모든 PRIMARY KEY는 INTEGER AUTOINCREMENT.
 
-- trainers(id, name, created_at)
-- members(id, trainer_id FK, name, created_at)
-- pt_sessions(id, member_id FK, session_date TEXT YYYY-MM-DD, created_at)
-- session_sets(id, session_id FK, exercise TEXT CHECK in 10종, weight_kg REAL CHECK>0, reps INTEGER CHECK>0, set_index INTEGER)
+- `trainers(id, name, created_at, username TEXT UNIQUE, password_hash TEXT, is_owner INTEGER NOT NULL DEFAULT 0)`
+- `members(id, trainer_id FK, name, created_at)`
+- `pt_sessions(id, member_id FK, session_date TEXT YYYY-MM-DD, created_at, input_trainer_id INTEGER REFERENCES trainers(id) NULL 허용)`
+- `session_sets(id, session_id FK, exercise TEXT CHECK in 10종, weight_kg REAL CHECK>0, reps INTEGER CHECK>0, set_index INTEGER)`
+
+스키마는 `init_db()`가 idempotent ALTER TABLE (PRAGMA table_info 체크 후 ADD)로 적용한다.
 
 ## 운동 종목 (10종 고정, 확장 금지)
 스쿼트, 벤치프레스, 데드리프트, 오버헤드프레스, 바벨로우, 풀업, 레그프레스, 랫풀다운, 레그컬, 덤벨컬
@@ -33,13 +35,21 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - POST /trainers/{tid}/members/{mid}/log — 세션 + 세트 생성 (HTMX 응답)
 - GET /trainers/{tid}/members/{mid}/dashboard — 차트 뷰 (Chart.js canvas 2개)
 - GET /trainers/{tid}/members/{mid}/chart-data.json — 차트 데이터 JSON
+- `GET /admin/export/sessions.csv?trainer_id=<int>` — 관장 전용 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
 
 ## 인증
-- 하드코딩 어드민 1개, 환경변수 주입: `ADMIN_USERNAME`, `ADMIN_PASSWORD`
-- `starlette.middleware.sessions.SessionMiddleware`, secret은 `APP_SESSION_SECRET`
-- 비밀번호는 평문 환경변수, 비교는 `secrets.compare_digest`
-- 쿠키 속성: httponly, samesite=lax. `secure`는 env toggle로 on/off.
-- **부팅 시 위 3개 env 미설정 → RuntimeError로 즉시 실패 (fail-fast)**
+
+- 인증 주체는 `trainers` 테이블. 로그인 식별자는 `username`, 비밀번호는 `password_hash` (`hashlib.scrypt`, n=16384, r=8, p=1, salt 16B, dklen=64, 포맷 `scrypt$<salt_hex>$<hash_hex>`).
+- `passlib` / `bcrypt` / 기타 외부 해싱 의존 추가 금지 — 표준 라이브러리 `hashlib`만 사용.
+- 세션 쿠키: `request.session["user"] = {"trainer_id": int, "is_owner": bool}`. 기존 `["admin"] = True` 구조는 제거.
+- `starlette.middleware.sessions.SessionMiddleware`, secret은 `APP_SESSION_SECRET`. 쿠키 속성 httponly, samesite=lax, `SESSION_COOKIE_SECURE` env toggle 유지.
+- **관장 부트 시드 (ensure_owner_seed)**: `create_app()` 부트 시 실행.
+  - is_owner=1 row가 0건 & username==ADMIN_USERNAME row 없음 → 신규 INSERT (name=ADMIN_USERNAME, username=ADMIN_USERNAME, password_hash=hash(ADMIN_PASSWORD), is_owner=1)
+  - is_owner=1 row가 0건 & username==ADMIN_USERNAME row 있음 → UPDATE is_owner=1 (password_hash는 NULL일 때만 채움)
+  - is_owner=1 row ≥1건 & 그 row의 username == ADMIN_USERNAME → no-op (password_hash 불변)
+  - is_owner=1 row ≥1건 & username != ADMIN_USERNAME → stdout에 `[warn] ADMIN_USERNAME mismatch: env=X db_owner=Y (관장 교체 절차 필요)` 1줄 출력 + skip. **부팅은 계속 진행 (exit 0 유지)**.
+- `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `APP_SESSION_SECRET` 3개 env는 여전히 필수 (부트 시드용). 미설정 시 RuntimeError fail-fast.
+- 계정 CRUD는 웹 UI 없음. `scripts/seed_trainer.py`만 사용.
 
 ## 차트 데이터 계약
 `GET /trainers/{tid}/members/{mid}/chart-data.json` 응답:
@@ -60,18 +70,36 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 - `datasets`는 회원이 실제로 수행한 운동 종목만 포함.
 - `labels`는 세션 날짜 오름차순. `max_weight.labels`와 `total_volume.labels`는 동일.
 
+## CSV Export
+
+- 권한: `session["user"]["is_owner"] == True`만. 아니면 303 → `/`.
+- 쿼리: `trainer_id` (optional). 있으면 `pt_sessions.input_trainer_id = trainer_id` 필터. 없으면 전체.
+- 응답: `text/csv; charset=utf-8`. 본문 **UTF-8 BOM (`﻿`) 접두** 1회 (Excel 기본 열기 한글 깨짐 방지).
+- 컬럼 순서 고정: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`
+- `input_trainer_name`은 `LEFT JOIN trainers ON pt_sessions.input_trainer_id = trainers.id` 후 `COALESCE(trainers.name, '')`.
+- 파일명 헤더: `Content-Disposition: attachment; filename=sessions_YYYYMMDD.csv` (trainer_id 쿼리 시 `sessions_YYYYMMDD_trainer_<tid>.csv`).
+- Rate limit: 모듈 전역 `dict[int, float]` (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429. **테스트 간 state 누수 방지를 위해 전역 dict는 `app.state`에 붙이거나 앱 팩토리 closure로 은닉**.
+- 감사 로그: 매 성공 응답마다 stdout 1줄 `[export] owner_id={X} target_trainer_id={Y|all} rows={N}`.
+
+## 트레이너간 회원 접근 격리
+
+- 이번 스프린트는 **permissive**. 트레이너A가 트레이너B 담당 회원의 `/trainers/{tid}/members/{mid}/...` URL을 직접 입력하면 접근 가능.
+- 단 URL의 `tid`와 `mid`는 `members WHERE id=mid AND trainer_id=tid` 필터로 검증 유지 → 잘못된 조합은 404.
+- 트레이너간 완전 격리는 **R5 (회원용 자가 대시보드 + 트레이너 IP 가드레일)**에서 다룸. 이번 스프린트 범위 외.
+
 ## 명시적 제외 항목 (이번 스프린트 금지)
 - 자세 교정 기록 / 자가보고 / 인바디 연동
 - AI 트레이너 대화
 - PDF 리포트 내보내기
 - Rappo 연동 / CSV import
 - 회원용 UI (트레이너 전용)
-- 다중 트레이너 / 다중 헬스장
+- 다중 헬스장 (여전히 금지)
 - 회원 CRUD 웹 UI (seed 스크립트 only)
-- 권한 분리 / 다중 유저
-- **로그인 brute-force 보호 / rate limit** (명시적으로 스프린트 외)
+- 복잡 RBAC / 트레이너 간 회원 접근 격리 (R5에서 다룸)
+- **로그인 brute-force 보호 / 로그인 rate limit** (스프린트 외). 단 `/admin/export/sessions.csv`는 IP 자산 유출 경로이므로 owner_trainer_id별 60초 in-memory rate limit만 최소 감사 흔적으로 허용.
 - 11번째 이후 운동 종목
 - 코드 내 "TODO: 다중 트레이너" 같은 힌트 주석도 금지
+- 계정 CRUD 웹 UI (`scripts/seed_trainer.py` only)
 
 ## 배포
 - Fly.io 단일 VM (region `nrt`)
@@ -82,3 +110,7 @@ PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입
 
 ## DoD
 `iterations/1-20260424_020912/artifacts/dashboard.png` — 꺾은선 그래프가 실제로 그려진 대시보드 스크린샷 (Playwright headless 자동 캡처).
+
+## 다음 스프린트 예약 티켓
+
+**트레이너 본인의 "내 입력분 CSV export" 라우트** — `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 `input_trainer_id`만 필터링하여 다운로드. 관장 허가 불요. 이 기능이 붙어야 개선점 4("트레이너·헬스장 공동 소유, 퇴사 시 트레이너 본인이 export 가능")의 해소가 완성된다. iteration 2 백필 스크립트 실행이 이 기능의 전제.
```

## `docs/testing.md`

```diff
diff --git a/docs/testing.md b/docs/testing.md
index 0f5fbce..cb2ccb2 100644
--- a/docs/testing.md
+++ b/docs/testing.md
@@ -5,13 +5,15 @@
 - **ORM 도입 금지.** 표준 라이브러리 `sqlite3`만 사용. 테스트도 동일.
 - **coverage % 목표 없음.** 필수 시나리오가 green이면 DoD 충족.
 - 테스트 DB는 각 테스트마다 별도 temp file → teardown에서 제거.
+- `pytest.monkeypatch`를 통한 env / 모듈 attribute / 모듈 전역 dict 조작은 mock 금지 원칙에 저촉되지 않음 (conftest가 이미 이 방식으로 DB 경로와 env를 주입한다). 단 DB 자체를 mock하거나 `time.monotonic` 자체를 패치하는 것은 금지.
 
-## 테스트 구성 (5 파일)
+## 테스트 구성 (6 파일)
 1. `tests/test_aggregates.py` — 집계 함수 단위 테스트 (`max_weight_per_session`, `total_volume_per_session`). **CHECK 제약 스모크 테스트 포함**: 음수 weight / 미등록 exercise INSERT가 `sqlite3.IntegrityError`를 내는지 런타임 증명.
-2. `tests/test_auth.py` — 로그인 / 세션 / 로그아웃 라우트.
-3. `tests/test_log_routes.py` — 로그 폼 GET / POST, 빈 세트 스킵, 검증 실패 처리.
+2. `tests/test_auth.py` — 로그인 / 세션 / 로그아웃 라우트. **iteration 2 확장**: 관장 부트 시드(신규 INSERT / 기존 password_hash 불변 / username mismatch 시 warn+skip), non-owner 트레이너 로그인, `session["user"]` 스키마 검증.
+3. `tests/test_log_routes.py` — 로그 폼 GET / POST, 빈 세트 스킵, 검증 실패 처리. **iteration 2 확장**: POST /log가 세션의 `trainer_id`를 `pt_sessions.input_trainer_id`에 기록.
 4. `tests/test_dashboard.py` — `chart-data.json` 계약. **빈 member 케이스(세션 0건)에서 labels=[], datasets=[] 반환 확인 필수**.
 5. `tests/test_e2e_dashboard.py` — Playwright headless. uvicorn 서브프로세스 fixture는 teardown에서 `process.terminate() + process.wait(timeout=5)` 필수. 임시 DB 파일 cleanup 필수.
+6. `tests/test_export.py` (iteration 2 신규) — `/admin/export/sessions.csv` 권한 분기(owner only), `trainer_id` 쿼리 필터, 60초 rate limit, stdout 감사 로그 포맷, NULL `input_trainer_id` row의 빈 이름 렌더, UTF-8 BOM 본문 접두.
 
 ## 프레임워크
 - `pytest`, `pytest-asyncio` (async 라우트 테스트용)
```

## `docs/user-intervention.md`

```diff
diff --git a/docs/user-intervention.md b/docs/user-intervention.md
index 49f1376..0a65072 100644
--- a/docs/user-intervention.md
+++ b/docs/user-intervention.md
@@ -48,3 +48,35 @@ APP_SESSION_SECRET=dev-secret-change-me ADMIN_USERNAME=admin ADMIN_PASSWORD=pass
 ```
 
 브라우저에서 `http://localhost:8000` 접속 후 위에서 설정한 `ADMIN_USERNAME` / `ADMIN_PASSWORD`로 로그인.
+
+## iteration 2 트레이너 계정 운영
+
+### 배포 후 관장 1회 재로그인 필요
+iteration 2 배포 직후, 기존에 로그인된 관장 세션 쿠키는 구조(`admin=True`)가 달라져 자동으로 로그아웃된다. 배포 완료 후 관장이 직접 로그인 폼에서 재로그인해야 한다.
+
+### 트레이너 계정 생성 / 비밀번호 리셋
+`fly ssh console` 후:
+```bash
+ uv run python -m scripts.seed_trainer --name "트레이너 이름" --username trainer_u --password "pw"
+```
+- 같은 `--username`으로 재실행하면 비밀번호 리셋 (upsert).
+- `--owner` 플래그를 주면 해당 계정을 is_owner=1로 승격 (다른 계정의 is_owner는 0으로 전환되며 stdout에 목록 출력).
+- **shell history 회피**: 명령 앞에 공백 prefix를 붙이거나 실행 후 `history -c` (HISTCONTROL=ignorespace 가정).
+
+### 관장 교체
+`fly ssh console` 후:
+```bash
+sqlite3 /data/bet.db "UPDATE trainers SET is_owner=0; UPDATE trainers SET is_owner=1 WHERE username='<새관장_username>';"
+```
+그 후 `fly secrets set ADMIN_USERNAME='<새관장_username>' ADMIN_PASSWORD='<새비번 또는 기존비번>'` 로 env도 갱신. env를 갱신하지 않으면 부팅 시 `[warn] ADMIN_USERNAME mismatch` 경고가 stdout에 뜨지만 앱은 계속 기동한다.
+
+### 백필 스크립트 실행 (iteration 2 배포 후 필수 1회)
+`fly ssh console` 후 **반드시** 1회 실행:
+```bash
+uv run python -m scripts.backfill_input_trainer
+```
+- iteration 1 시절 누적된 `pt_sessions.input_trainer_id IS NULL` row를 관장의 trainer_id로 UPDATE.
+- 멱등: 2회 실행해도 0건 UPDATE.
+- 관장 계정이 DB에 없으면 (env 미설정 또는 seed 미완료) exit 1 + stderr 안내. 이 경우 먼저 `seed_trainer --owner`로 관장 생성 후 재실행.
+- 이 백필이 다음 스프린트 "트레이너 본인의 CSV export 라우트"의 전제다. 백필 없이 배포되면 NULL rows가 계속 쌓여 후속 스프린트가 깨진다.
+- 배포 순서: **(1) Phase 1~2 코드 배포 → (2) 이 백필 1회 실행 → (3) 운영 재개**.
```
