# Phase 2: 인증 재구축 + 라우트 마이그레이션 + input_trainer_id 기록 + CSV export

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` — **iteration 2 개정된 단일 명세** (특히 `## 인증`, `## 라우트 목록`, `## CSV Export`, `## 트레이너간 회원 접근 격리` 섹션)
- `/docs/testing.md`
- `/docs/user-intervention.md` — 재로그인 필요, 백필 실행 절차
- `/iterations/2-20260424_034244/requirement.md`
- `/tasks/1-trainer-auth-export/docs-diff.md`

이전 phase(`phase1`)에서 아래가 이미 완료되어 있다. 꼼꼼히 읽고 설계 의도를 파악하라:

- `/app/db.py` — `_migrate_iteration2` 추가. trainers에 username/password_hash/is_owner, pt_sessions에 input_trainer_id 컬럼 존재.
- `/app/auth.py` — `hash_password` / `verify_password` 함수 신규 추가. **단, `verify_credentials` / `is_authenticated` / `login_required_redirect`는 iteration 1 원형 그대로** (이번 phase에서 교체).
- `/scripts/seed_trainer.py` — 트레이너 upsert + `--owner` 승격.
- `/scripts/backfill_input_trainer.py` — NULL input_trainer_id 백필.
- `/scripts/seed.py` — env 기반 admin username/is_owner 생성 로직으로 확장.

이번 phase는 라우트/인증 계층을 교체한다.

## 작업 내용

### 1. `/app/auth.py` 인증 로직 교체

다음 함수들을 **완전히 교체**하라:

```python
def is_authenticated(request: Request) -> bool:
    """session["user"]["trainer_id"]가 있으면 True."""

def is_owner(request: Request) -> bool:
    """session["user"]["is_owner"]가 True면 True."""

def current_user(request: Request) -> dict | None:
    """session["user"] dict 반환, 없으면 None."""

def verify_credentials(username: str, password: str) -> dict | None:
    """trainers 테이블에서 username 조회 → verify_password 성공 시
    {"trainer_id": int, "is_owner": bool} 반환, 실패 시 None."""

def login_required_redirect() -> RedirectResponse:
    """기존 그대로 유지 (/login으로 303)."""

def owner_required_redirect() -> RedirectResponse:
    """RedirectResponse('/', 303) — non-owner 접근 차단용."""
```

구현 요건:
- `verify_credentials`는 `app.db.get_connection()`으로 trainers에서 `username, password_hash, is_owner` 조회. `verify_password(password, row["password_hash"])` 실패 또는 row 없음 → None.
- `verify_password(_, None)` 반환값이 False여야 함 (Phase 1의 해시 함수가 이미 처리).
- `is_authenticated`는 예전 `session["admin"]` 경로 완전 삭제. 오직 `session.get("user", {}).get("trainer_id")`만.
- `secrets.compare_digest` 기반의 기존 env 비교 로직은 완전 제거.
- `import secrets` 필요성 재검토 후 미사용이면 삭제.

### 2. `/app/main.py`에 `ensure_owner_seed` 통합

`create_app()` 순서를 이렇게 만든다:

```python
def create_app() -> FastAPI:
    _validate_env()
    init_db()
    ensure_owner_seed()   # 신규
    app = FastAPI()
    ...
```

`ensure_owner_seed()` 구현 위치: `app/auth.py`에 추가.

시그니처:
```python
def ensure_owner_seed() -> None:
    """부팅 시 관장 시드. 로직은 spec의 `## 인증` 섹션을 따른다."""
```

동작 명세 (spec 기반, 4케이스):

1. `is_owner=1` row가 0건 AND `trainers WHERE username=ADMIN_USERNAME` 0건 → 신규 INSERT (`name=ADMIN_USERNAME`, `username=ADMIN_USERNAME`, `password_hash=hash_password(ADMIN_PASSWORD)`, `is_owner=1`, `created_at=now`). stdout: `[auth] owner seeded: username={X}`.

2. `is_owner=1` row가 0건 AND `trainers WHERE username=ADMIN_USERNAME` 1건 (is_owner=0) → `UPDATE trainers SET is_owner=1` (password_hash NULL인 경우 동시에 `password_hash=hash_password(ADMIN_PASSWORD)`로 채움). stdout: `[auth] owner promoted: username={X}`.

3. `is_owner=1` row가 ≥1건 AND 그 row의 username == ADMIN_USERNAME → no-op. **password_hash는 건드리지 않는다**.

4. `is_owner=1` row가 ≥1건 AND 모든 row의 username != ADMIN_USERNAME → **stdout에 1줄 warn 출력 후 skip, exit 0 유지 (부팅 계속)**:
   ```
   [warn] ADMIN_USERNAME mismatch: env={ADMIN_USERNAME} db_owner={db_username} — 관장 교체 절차 필요 (docs/user-intervention.md 참조)
   ```

구현 가이드:
- `os.environ["ADMIN_USERNAME"]`, `os.environ["ADMIN_PASSWORD"]` 직접 읽음 (main.py의 `_validate_env`가 이미 존재 보장).
- DB 작업은 `get_connection()` 컨텍스트 하나에서 묶어 단일 트랜잭션.
- `datetime.utcnow().isoformat()` 같은 기존 패턴 재사용.

### 3. `/app/routes.py` 로그인/로그아웃 흐름 교체

아래 변경:

#### 3-a. `POST /login`

```python
@app.post("/login")
async def post_login(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    user = verify_credentials(username, password)
    if user is not None:
        request.session["user"] = user
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request, "login.html",
        {"error": "아이디 또는 비밀번호가 올바르지 않습니다."},
        status_code=200,
    )
```

기존 `request.session["admin"] = True` 삭제.

#### 3-b. `POST /logout`

기존 그대로 (`request.session.clear()`).

#### 3-c. `POST /trainers/{tid}/members/{mid}/log`

**input_trainer_id 기록**: `pt_sessions` INSERT 시 `input_trainer_id=current_user(request)["trainer_id"]` 추가.

```python
cur = conn.execute(
    "INSERT INTO pt_sessions (member_id, session_date, created_at, input_trainer_id) VALUES (?, ?, ?, ?)",
    (mid, session_date, now, current_user(request)["trainer_id"]),
)
```

`current_user`가 None인 경우 — is_authenticated가 False이므로 이미 login_required_redirect로 막혀있음. 방어적 코드 불필요.

#### 3-d. 기존 보호 라우트 (`GET /`, `GET /log`, `POST /log`, `GET /dashboard`, `GET /chart-data.json`) — 본 문의 변경 없이 그대로 작동. 단 `is_authenticated` 내부가 session["user"]로 바뀌었으므로 자동으로 적용됨.

#### 3-e. 신규 라우트 `GET /admin/export/sessions.csv`

```python
@app.get("/admin/export/sessions.csv")
async def get_export_sessions(request: Request, trainer_id: int | None = None):
    ...
```

동작:
1. `is_authenticated(request) is False` → `login_required_redirect()`
2. `is_owner(request) is False` → `owner_required_redirect()`  (303 → `/`)
3. Rate limit 체크:
   - `owner_id = current_user(request)["trainer_id"]`
   - 모듈 전역 (`app.state`에 바인딩) dict `export_last_ts: dict[int, float]`를 통해 `time.monotonic()` 비교.
   - 60초 이내 → `Response("Too Many Requests: retry in 60s", status_code=429, media_type="text/plain; charset=utf-8")`
4. DB에서 세션 데이터 조회 — `trainer_id` 쿼리 파라미터 반영:
   ```sql
   SELECT ps.session_date, m.name AS member_name,
          ss.exercise, ss.weight_kg, ss.reps, ss.set_index,
          COALESCE(t.name, '') AS input_trainer_name
   FROM session_sets ss
   JOIN pt_sessions ps ON ss.session_id = ps.id
   JOIN members m ON ps.member_id = m.id
   LEFT JOIN trainers t ON ps.input_trainer_id = t.id
   WHERE (:trainer_id IS NULL OR ps.input_trainer_id = :trainer_id)
   ORDER BY ps.session_date, ps.id, ss.set_index
   ```
   (`?` placeholder로 trainer_id NULL 여부 분기)
5. CSV 본문 생성:
   - `io.StringIO` + `csv.writer`.
   - 첫 줄 헤더: `session_date,member_name,exercise,weight_kg,reps,set_index,input_trainer_name`
   - 본문 문자열 앞에 UTF-8 BOM (`"﻿"`) 접두.
6. 파일명:
   - 날짜는 `date.today().strftime("%Y%m%d")`
   - trainer_id 있으면 `sessions_{YYYYMMDD}_trainer_{id}.csv`, 없으면 `sessions_{YYYYMMDD}.csv`
7. stdout 감사 로그 (성공 응답 반환 직전):
   ```python
   print(f"[export] owner_id={owner_id} target_trainer_id={trainer_id if trainer_id is not None else 'all'} rows={N}", flush=True)
   ```
8. 마지막에 `export_last_ts[owner_id] = time.monotonic()` 업데이트.

**rate limit dict 은닉**:
- 모듈 전역 변수로 만들지 말 것. `app.state.export_last_ts = {}` 형태로 `create_app()`에서 초기화하고, 라우트 핸들러에서 `request.app.state.export_last_ts`로 접근. 이렇게 하면 TestClient가 앱 인스턴스를 새로 만들 때마다 dict가 초기화되어 테스트 간 state 누수가 없다.

#### 3-f. 기존 `/` 라우트 "seed를 실행하세요" 메시지

기존 그대로 유지. 단 `SELECT id FROM trainers ORDER BY id LIMIT 1`은 그대로 두되, seed.py/ensure_owner_seed 이후 관장이 trainer_id=1이 됨이 보장되므로 동작에 문제 없음.

### 4. 404 / 권한 가드 재확인

- `/trainers/{tid}/members/{mid}/...` 라우트는 `members WHERE id=mid AND trainer_id=tid` 필터 유지 → 잘못된 조합은 404.
- "트레이너간 회원 접근 격리"는 이번 스프린트 범위 외 (spec의 해당 섹션 참조). URL을 직접 치면 같은 헬스장 내 다른 트레이너의 회원 페이지 접근 가능한 permissive 동작 유지.

## Acceptance Criteria

```bash
# 1) 코드 컴파일 확인
uv run python -c "
from app.auth import hash_password, verify_password, verify_credentials, is_authenticated, is_owner, current_user, ensure_owner_seed, login_required_redirect, owner_required_redirect
from app.main import create_app
print('imports ok')
"

# 2) ensure_owner_seed 4케이스 동작
rm -rf /tmp/bet_phase2_test && mkdir -p /tmp/bet_phase2_test
DATABASE_PATH=/tmp/bet_phase2_test/bet.db \
APP_SESSION_SECRET=test-secret-xxxxxxxxxxxxxxxx \
ADMIN_USERNAME=owner1 ADMIN_PASSWORD=pw1 \
uv run python -c "
import os
from app.main import create_app
create_app()  # 첫 부팅: 신규 INSERT
from app.db import get_connection
with get_connection() as c:
    r = c.execute('SELECT username, is_owner FROM trainers WHERE is_owner=1').fetchone()
    assert r['username'] == 'owner1', r
create_app()  # 두번째 부팅: no-op (password_hash 불변)
r1 = list(get_connection().__enter__().execute('SELECT password_hash FROM trainers WHERE username=\"owner1\"').fetchall())
print('ensure ok')
"

# 3) ensure_owner_seed mismatch warn
DATABASE_PATH=/tmp/bet_phase2_test/bet.db \
APP_SESSION_SECRET=test-secret-xxxxxxxxxxxxxxxx \
ADMIN_USERNAME=different ADMIN_PASSWORD=pw1 \
uv run python -c "from app.main import create_app; create_app()" 2>&1 | tee /tmp/bet_phase2_test/warn.out
grep -q 'ADMIN_USERNAME mismatch' /tmp/bet_phase2_test/warn.out

# 4) 전체 pytest 수트 (iteration 1 기존 테스트는 여전히 green이어야 — 단 Phase 3에서 테스트 확장하므로, 이 phase에서는 기존 5파일 + 신규 테스트 미도입 상태로 1회 실행)
# Phase 2 완료 시점에는 기존 test_auth/test_log_routes가 새 인증으로 깨질 가능성이 큼 (iteration 1 테스트가 session["admin"]=True 전제로 작성됨).
# 이미 기존 conftest.py authed_client는 "POST /login" 경로로 로그인하므로 새 인증도 동작해야 함 — 단 ensure_owner_seed가 temp_db 환경에서 admin/pw1234를 시드해야 함.
# → ensure_owner_seed 미도입 시 실패할 수 있으니, 이 AC는 2개로 분리:
uv run pytest tests/test_aggregates.py tests/test_auth.py tests/test_log_routes.py tests/test_dashboard.py -q

# 5) CSV export 스모크 (authed_client 직접 사용 — 짧게 확인)
DATABASE_PATH=/tmp/bet_phase2_test/bet.db \
APP_SESSION_SECRET=test-secret-xxxxxxxxxxxxxxxx \
ADMIN_USERNAME=owner1 ADMIN_PASSWORD=pw1 \
uv run python -c "
from app.main import create_app
from fastapi.testclient import TestClient
app = create_app()
with TestClient(app) as c:
    r = c.post('/login', data={'username': 'owner1', 'password': 'pw1'}, follow_redirects=False)
    assert r.status_code == 303, r.status_code
    r = c.get('/admin/export/sessions.csv')
    assert r.status_code == 200, r.status_code
    assert r.headers['content-type'].startswith('text/csv'), r.headers
    body = r.content
    assert body.startswith(b'\xef\xbb\xbf'), 'UTF-8 BOM missing'
    assert b'session_date,member_name,exercise' in body
    # rate limit
    r = c.get('/admin/export/sessions.csv')
    assert r.status_code == 429, r.status_code
print('export ok')
"

# 6) non-owner 접근 차단
DATABASE_PATH=/tmp/bet_phase2_test/bet.db \
APP_SESSION_SECRET=test-secret-xxxxxxxxxxxxxxxx \
ADMIN_USERNAME=owner1 ADMIN_PASSWORD=pw1 \
uv run python -m scripts.seed_trainer --name 직원 --username stafft --password spw
DATABASE_PATH=/tmp/bet_phase2_test/bet.db \
APP_SESSION_SECRET=test-secret-xxxxxxxxxxxxxxxx \
ADMIN_USERNAME=owner1 ADMIN_PASSWORD=pw1 \
uv run python -c "
from app.main import create_app
from fastapi.testclient import TestClient
app = create_app()
with TestClient(app) as c:
    c.post('/login', data={'username': 'stafft', 'password': 'spw'}, follow_redirects=False)
    r = c.get('/admin/export/sessions.csv', follow_redirects=False)
    assert r.status_code == 303, r.status_code
    assert r.headers['location'] == '/', r.headers
print('non-owner blocked ok')
"
```

**AC #4 중 `tests/test_auth.py`와 `tests/test_log_routes.py`가 기존 구조에서 실패할 수 있다.** conftest.py의 `authed_client` fixture를 함께 살펴라 — admin/pw1234로 로그인하는 플로우가 `ensure_owner_seed` 덕에 admin 계정을 DB에 자동 시드하면 통과한다. 만약 기존 `test_missing_env_raises_runtime_error` 같은 테스트가 깨지면 env 검증 로직이 유지되는지 확인 (deletion 없이 넘어가야 함).

기존 테스트 통과를 만들기 위해 **테스트 자체는 수정하지 마라** — Phase 3에서 체계적으로 확장한다. 단 conftest가 잘못 작성되어 있으면 conftest는 수정 가능.

## AC 검증 방법

위 AC 커맨드들을 순서대로 실행하라. 전부 exit 0이어야 한다.
- 성공 시 `/tasks/1-trainer-auth-export/index.json`의 phase 2 status를 `"completed"`로 변경.
- 실패 시 모듈 수정 후 재시도. 3회 이상 실패 시 `"error"` + `"error_message"` 기록.

## 주의사항

- **rate limit dict를 모듈 전역 변수로 두지 말 것**. 반드시 `app.state.export_last_ts = {}` 형태로 `create_app()`에서 초기화. 테스트에서 `TestClient(create_app())`를 만들 때마다 fresh 상태가 되어야 한다 — 전역 dict는 테스트 순서 의존 flaky 유발.
- `ensure_owner_seed`가 **exit하지 말 것** — mismatch 케이스에서 raise SystemExit이나 sys.exit 호출 금지. 반드시 stdout warn 1줄 + return. 부팅이 막히면 관장이 env 교체 없이는 앱을 못 띄우는 상황이 됨.
- `ADMIN_PASSWORD`가 mismatch 케이스에서 "어차피 안 쓰임"이지만, `create_app`은 여전히 env 3종을 요구함 — `_validate_env`가 미설정 시 RuntimeError fail-fast로 먼저 막음.
- CSV export의 rate limit은 **owner_trainer_id별**. 같은 owner가 연속 2회 치면 429, 다른 owner는 별개. 앱 재시작 시 dict는 리셋됨 (허용).
- 감사 로그는 `print(..., flush=True)` — uvicorn stdout 버퍼링으로 로그 유실 막기.
- CSV 첫 줄 헤더 앞에 UTF-8 BOM 1회만 (매 행 앞에 넣지 말 것). Excel이 BOM을 보면 UTF-8로 해석하고 헤더로 렌더한다.
- `input_trainer_name`이 NULL일 때 LEFT JOIN으로 `COALESCE(trainers.name, '')` → 빈 문자열. CSV 셀은 빈 칸.
- **로그인 rate limit은 넣지 마라**. spec의 "명시적 제외 항목"에 명시된 대로.
- 기존 `app/exercises.py` 및 `app/aggregates.py`는 수정 금지.
- `pyproject.toml` 변경 금지 — 외부 의존성 추가 불가.
- 기존 templates(`login.html`, `log.html`, `dashboard.html`)는 변경 금지.
- `main.py`에서 `init_db()` 호출 **후** `ensure_owner_seed()`를 호출해야 한다 (스키마 보장 후 insert).
- `/admin/export/sessions.csv`의 `trainer_id` 쿼리 파라미터 파싱은 FastAPI가 자동 `int | None` 변환. 잘못된 값(`?trainer_id=abc`)은 FastAPI 422 — 의도된 동작.
