# BET Spec (iteration 2)

## 개요

PT 세션 종료 직후 트레이너가 세트별 운동·중량·횟수를 입력하는 폼과, 회원별 운동 종목별 최대 중량 추이 및 세션당 총 볼륨 추이를 꺾은선 그래프 2개로 시각화하는 단일 뷰 MVP다. 스택은 FastAPI + SQLite + HTMX + Chart.js이며, 트레이너 전용 하드코딩 어드민 인증으로 동작한다. 파일럿 12주 동안 "수치화된 회원 발전 증거"를 트레이너가 확인하고 잠재회원 상담에 활용하는 것이 핵심 목적이다. iteration 2부터는 단일 헬스장 내 다중 트레이너 로그인 계정과 세션 기록의 "입력자 트레이너" 귀속, 관장(is_owner) 전용 CSV 내보내기를 지원한다. 다중 헬스장과 복잡 RBAC는 여전히 범위 외.

## 스택
- Python 3.12 / FastAPI / uvicorn
- SQLite (표준 라이브러리 sqlite3 only, ORM 없음)
- Jinja2 templates
- HTMX (세트 행 추가·폼 POST)
- Chart.js 4.x CDN (대시보드 차트)
- 테스트: pytest + httpx + playwright
- 배포: Fly.io 단일 VM + volume mount

## 데이터 모델
4개 테이블. 모든 PRIMARY KEY는 INTEGER AUTOINCREMENT.

- `trainers(id, name, created_at, username TEXT UNIQUE, password_hash TEXT, is_owner INTEGER NOT NULL DEFAULT 0)`
- `members(id, trainer_id FK, name, created_at)`
- `pt_sessions(id, member_id FK, session_date TEXT YYYY-MM-DD, created_at, input_trainer_id INTEGER REFERENCES trainers(id) NULL 허용)`
- `session_sets(id, session_id FK, exercise TEXT CHECK in 10종, weight_kg REAL CHECK>0, reps INTEGER CHECK>0, set_index INTEGER)`

스키마는 `init_db()`가 idempotent ALTER TABLE (PRAGMA table_info 체크 후 ADD)로 적용한다.

## 운동 종목 (10종 고정, 확장 금지)
스쿼트, 벤치프레스, 데드리프트, 오버헤드프레스, 바벨로우, 풀업, 레그프레스, 랫풀다운, 레그컬, 덤벨컬

## 라우트 목록
- GET /login — 로그인 폼
- POST /login — credential 검증 → 303 / (성공) / 200 재렌더 (실패)
- POST /logout — 세션 clear → 303 /login
- GET / — 로그인 후 기본 (첫 멤버 로그 화면으로 redirect)
- GET /trainers/{tid}/members/{mid}/log — 입력 폼
- POST /trainers/{tid}/members/{mid}/log — 세션 + 세트 생성 (HTMX 응답)
- GET /trainers/{tid}/members/{mid}/dashboard — 차트 뷰 (Chart.js canvas 2개)
- GET /trainers/{tid}/members/{mid}/chart-data.json — 차트 데이터 JSON
- `GET /admin/export/sessions.csv?trainer_id=<int>` — 관장 전용 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)
- `GET /my/export/sessions.csv` — 로그인한 트레이너 본인의 입력분 CSV 내보내기 (자세한 계약은 아래 `## CSV Export` 참조)

## 인증

- 인증 주체는 `trainers` 테이블. 로그인 식별자는 `username`, 비밀번호는 `password_hash` (`hashlib.scrypt`, n=16384, r=8, p=1, salt 16B, dklen=64, 포맷 `scrypt$<salt_hex>$<hash_hex>`).
- `passlib` / `bcrypt` / 기타 외부 해싱 의존 추가 금지 — 표준 라이브러리 `hashlib`만 사용.
- 세션 쿠키: `request.session["user"] = {"trainer_id": int, "is_owner": bool}`. 기존 `["admin"] = True` 구조는 제거.
- `starlette.middleware.sessions.SessionMiddleware`, secret은 `APP_SESSION_SECRET`. 쿠키 속성 httponly, samesite=lax, `SESSION_COOKIE_SECURE` env toggle 유지.
- **관장 부트 시드 (ensure_owner_seed)**: `create_app()` 부트 시 실행.
  - is_owner=1 row가 0건 & username==ADMIN_USERNAME row 없음 → 신규 INSERT (name=ADMIN_USERNAME, username=ADMIN_USERNAME, password_hash=hash(ADMIN_PASSWORD), is_owner=1)
  - is_owner=1 row가 0건 & username==ADMIN_USERNAME row 있음 → UPDATE is_owner=1 (password_hash는 NULL일 때만 채움)
  - is_owner=1 row ≥1건 & 그 row의 username == ADMIN_USERNAME → no-op (password_hash 불변)
  - is_owner=1 row ≥1건 & username != ADMIN_USERNAME → stdout에 `[warn] ADMIN_USERNAME mismatch: env=X db_owner=Y (관장 교체 절차 필요)` 1줄 출력 + skip. **부팅은 계속 진행 (exit 0 유지)**.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `APP_SESSION_SECRET` 3개 env는 여전히 필수 (부트 시드용). 미설정 시 RuntimeError fail-fast.
- 계정 CRUD는 웹 UI 없음. `scripts/seed_trainer.py`만 사용.

## 차트 데이터 계약
`GET /trainers/{tid}/members/{mid}/chart-data.json` 응답:
```json
{
  "member": {"id": int, "name": str},
  "max_weight": {
    "labels": ["YYYY-MM-DD", ...],
    "datasets": [{"label": "<운동명>", "data": [<kg>, ...]}, ...]
  },
  "total_volume": {
    "labels": ["YYYY-MM-DD", ...],
    "data": [<volume>, ...]
  }
}
```
- 세션이 0건인 회원 → `labels: []`, `datasets: []`, `data: []`. 이 계약은 테스트에서 강제.
- `datasets`는 회원이 실제로 수행한 운동 종목만 포함.
- `labels`는 세션 날짜 오름차순. `max_weight.labels`와 `total_volume.labels`는 동일.

## CSV Export

> iteration 3에서 `/my/export/sessions.csv`가 추가됐다. 관장 전용 `/admin/export/sessions.csv`와 공통 헬퍼 `_write_sessions_csv`를 공유하여 컬럼 drift를 코드 레벨에서 방지한다.

### 관장 export (`GET /admin/export/sessions.csv`)

- 권한: `session["user"]["is_owner"] == True`만. 아니면 303 → `/`.
- 쿼리: `trainer_id` (optional). 있으면 `pt_sessions.input_trainer_id = trainer_id` 필터. 없으면 전체.
- 응답: `text/csv; charset=utf-8`. 본문 **UTF-8 BOM (`﻿`) 접두** 1회 (Excel 기본 열기 한글 깨짐 방지).
- 컬럼 순서 고정: `session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`
- `input_trainer_name`은 `LEFT JOIN trainers ON pt_sessions.input_trainer_id = trainers.id` 후 `COALESCE(trainers.name, '')`.
- 파일명 헤더: `Content-Disposition: attachment; filename=sessions_YYYYMMDD.csv` (trainer_id 쿼리 시 `sessions_YYYYMMDD_trainer_<tid>.csv`).
- Rate limit: `app.state.export_last_ts` dict (owner_trainer_id → 마지막 요청 `time.monotonic()`). 60초 이내 재요청 시 429.
- 감사 로그: 매 성공 응답마다 stdout 1줄 `[export] owner_id={X} target_trainer_id={Y|all} rows={N}`.

### 트레이너 본인 export (`GET /my/export/sessions.csv`)

- 권한: `is_authenticated(request) == True` 만. is_owner 체크 없음. 관장도 본인 자격으로 호출 가능 (단, 관장 본인의 `trainer_id` row만 반환되며 is_owner bypass 없음).
- 쿼리 파라미터: 없음. `pt_sessions.input_trainer_id = session["user"]["trainer_id"]`로 고정 필터링.
- 응답: `text/csv; charset=utf-8`, 본문 **UTF-8 BOM** 접두 1회. 관장 export와 **컬럼 순서 bit-exact 동일** (`session_date, member_name, exercise, weight_kg, reps, set_index, input_trainer_name`).
- 파일명 헤더: `Content-Disposition: attachment; filename="my_sessions_YYYYMMDD.csv"`. trainer_id 접미사 없음 (본인 것이므로 URL로 암시됨).
- Rate limit: 별도 `app.state.my_export_last_ts` dict. 관장 `app.state.export_last_ts`와 **물리 분리**되어 상호 영향 없음. 60초 이내 재요청 시 429.
- 감사 로그: stdout 1줄 `[my-export] trainer_id={X} rows={N}`. 관장 export 로그(`[export] ...`)와 prefix로 구분.
- 공통 헬퍼: 양 라우트는 `app/routes.py` 내부 private 함수 `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int`를 공유한다. 컬럼명은 단일 상수 tuple `_SESSIONS_CSV_COLUMNS`로 정의되며 header/data writerow가 모두 이를 참조해 컬럼 drift를 코드 레벨에서 차단한다.

## 트레이너간 회원 접근 격리

- 이번 스프린트는 **permissive**. 트레이너A가 트레이너B 담당 회원의 `/trainers/{tid}/members/{mid}/...` URL을 직접 입력하면 접근 가능.
- 단 URL의 `tid`와 `mid`는 `members WHERE id=mid AND trainer_id=tid` 필터로 검증 유지 → 잘못된 조합은 404.
- 트레이너간 완전 격리는 **R5 (회원용 자가 대시보드 + 트레이너 IP 가드레일)**에서 다룸. 이번 스프린트 범위 외.

## 명시적 제외 항목 (이번 스프린트 금지)
- 자세 교정 기록 / 자가보고 / 인바디 연동
- AI 트레이너 대화
- PDF 리포트 내보내기
- Rappo 연동 / CSV import
- 회원용 UI (트레이너 전용)
- 다중 헬스장 (여전히 금지)
- 회원 CRUD 웹 UI (seed 스크립트 only)
- 복잡 RBAC / 트레이너 간 회원 접근 격리 (R5에서 다룸)
- **로그인 brute-force 보호 / 로그인 rate limit** (스프린트 외). 단 `/admin/export/sessions.csv`는 IP 자산 유출 경로이므로 owner_trainer_id별 60초 in-memory rate limit만 최소 감사 흔적으로 허용.
- 11번째 이후 운동 종목
- 코드 내 "TODO: 다중 트레이너" 같은 힌트 주석도 금지
- 계정 CRUD 웹 UI (`scripts/seed_trainer.py` only)

## 배포
- Fly.io 단일 VM (region `nrt`)
- Dockerfile: `python:3.12-slim` 베이스, `pip install .`
- volume mount `/data`, DB 경로는 `DATABASE_PATH` env (기본 `./data/bet.db`)
- 관측: stdout + Fly 기본 로그. Sentry/Datadog/커스텀 관측 금지.
- `fly deploy` 실제 실행은 사용자 개입 (see `docs/user-intervention.md`)

## DoD
`iterations/1-20260424_020912/artifacts/dashboard.png` — 꺾은선 그래프가 실제로 그려진 대시보드 스크린샷 (Playwright headless 자동 캡처).

## 다음 스프린트 예약 티켓

**트레이너 본인 감사 로그 뷰어** — `GET /my/audit-log` — 트레이너가 "누가 언제 내 입력분을 export 했는가"를 능동 조회하는 페이지. 현재 `[export]` / `[my-export]` stdout 감사 흔적은 트레이너가 직접 볼 수 없으므로, DB에 `export_audit` 테이블을 추가하고 관장/본인 export 시 1 row INSERT + 본인 조회 전용 뷰를 제공한다. 시뮬 5/6 언급 2순위 우려(트레이너가 "감시 메커니즘이 live, 방어장치는 roadmap"이라고 판단하는 비대칭성 해소)에 대응.
