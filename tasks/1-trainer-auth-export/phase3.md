# Phase 3: 테스트 확장 (auth / log_routes / export)

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` — iteration 2 개정판 (특히 `## 인증`, `## CSV Export`)
- `/docs/testing.md` — 테스트 정책 (mock 금지, tmp_path SQLite, monkeypatch OK)
- `/docs/user-intervention.md`
- `/iterations/2-20260424_034244/requirement.md`
- `/tasks/1-trainer-auth-export/docs-diff.md`

이전 phase들의 작업물을 꼼꼼히 읽어 설계 의도를 이해하라:

- `/app/db.py` — iteration 2 마이그레이션 적용
- `/app/auth.py` — `hash_password` / `verify_password` / `verify_credentials` (DB 조회) / `is_authenticated` / `is_owner` / `current_user` / `ensure_owner_seed`
- `/app/main.py` — `create_app()`에서 `ensure_owner_seed` 호출
- `/app/routes.py` — 로그인이 `session["user"]` dict로 저장, POST /log에서 input_trainer_id 기록, GET /admin/export/sessions.csv
- `/scripts/seed_trainer.py`, `/scripts/backfill_input_trainer.py`
- `/tests/conftest.py` — temp_db / client / authed_client / live_server

이번 phase는 **테스트만** 확장한다. 앱 코드는 건드리지 않는다 (단 conftest.py는 필요 시 확장 가능).

## 작업 내용

### 0. `/tests/conftest.py` 호환성 확인·필요 시 조정

현 상태 점검:
- `client` fixture가 env 3종 주입(`APP_SESSION_SECRET`, `ADMIN_USERNAME=admin`, `ADMIN_PASSWORD=pw1234`) 후 `create_app()` 호출. iteration 2 `ensure_owner_seed`가 돌아 trainer(username=admin, is_owner=1) 시드.
- `authed_client`가 `POST /login {username: admin, password: pw1234}`로 로그인 → session["user"] 저장.

**문제점**: Phase 2의 `ensure_owner_seed`가 "is_owner=1 row 0건 & username=ADMIN_USERNAME row 0건" 케이스에서 신규 INSERT를 하지만, 기존 `test_log_routes`의 일부 테스트(`_seed_trainer_member`)는 직접 `INSERT INTO trainers (name, created_at) VALUES ('트레이너1', ...)`으로 행을 넣는다. 이 행은 `username=NULL, is_owner=0` 상태이므로 `ensure_owner_seed`가 그 후 별도 "admin" trainer를 INSERT해 trainer_id=2가 됨. 테스트 `_seed_trainer_member`가 반환하는 tid는 "트레이너1"의 id=1이고, `authed_client`는 id=2(admin) 세션으로 로그인 — POST /log는 members WHERE id=mid AND trainer_id=tid(=1) 필터로 동작하므로 관계 상 OK. 단 새 테스트 `test_post_log_stamps_input_trainer_id`에서 "입력자 trainer_id"는 admin의 2로 기록되어야 한다.

**조치**: conftest는 건드리지 않아도 되지만, 테스트가 정확한 기대값을 갖도록 아래 테스트에서 `current_user.trainer_id` 를 그때그때 DB에서 조회해 비교.

필요한 신규 fixture (테스트 파일 안 local로 만들어도 되고, conftest에 추가해도 됨):
- `owner_trainer_id(client) -> int`: `client` 세션 없이 DB 직접 조회로 `SELECT id FROM trainers WHERE is_owner=1 LIMIT 1`를 반환.
- `non_owner_client(temp_db) -> TestClient`: 직접 DB에 non-owner trainer를 `seed_trainer` 유틸로 넣고 로그인 후 반환 (또는 테스트 내부에서 만들도록).

conftest.py 변경은 **필요한 최소한**으로 — 기존 테스트가 깨지지 않도록 주의.

### 1. `/tests/test_auth.py` 확장

기존 6개 테스트 (login 페이지, 오답, 정답, 보호, 로그아웃, env 누락) 유지. 단 `test_missing_env_raises_runtime_error`는 `ensure_owner_seed` 추가로 동작이 바뀌었는지 확인 — env 누락 시 여전히 `_validate_env`가 먼저 RuntimeError를 내므로 통과해야 함.

#### 추가 테스트 (5개)

**1. `test_boot_seeds_owner_when_absent`**
```python
def test_boot_seeds_owner_when_absent(client):
    """create_app 부팅 후 trainers에 is_owner=1, username=admin, password_hash 존재."""
```
- `client` fixture는 이미 create_app을 돌린 상태. `with get_connection(temp_db) as c: ...`로 조회.
- 검증: `is_owner=1`인 row 1건, `username='admin'`, `password_hash is not None` (빈 문자열 아님).

**2. `test_boot_preserves_existing_owner_password`**
```python
def test_boot_preserves_existing_owner_password(temp_db, monkeypatch):
    """기존 관장의 password_hash는 두 번째 부팅 시 유지된다."""
```
- env 설정 후 첫 번째 `create_app()` → password_hash_1 저장.
- env 그대로 두 번째 `create_app()` → password_hash_2 조회.
- `assert password_hash_1 == password_hash_2` (재해싱 없음).

**3. `test_boot_warns_on_username_mismatch`**
```python
def test_boot_warns_on_username_mismatch(temp_db, monkeypatch, capsys):
    """is_owner=1 row의 username과 env ADMIN_USERNAME이 다르면 warn + skip."""
```
- DB에 `username=alice, is_owner=1, password_hash=...` 직접 INSERT.
- env `ADMIN_USERNAME=bob ADMIN_PASSWORD=bobpw`로 `create_app()` 호출.
- stdout 캡처에서 `ADMIN_USERNAME mismatch` 포함 확인.
- DB 상태: `alice`의 is_owner=1 유지, `bob`은 DB에 없음.
- 부팅이 에러 없이 끝났는지(create_app 리턴)도 검증.

**4. `test_non_owner_trainer_login`**
```python
def test_non_owner_trainer_login(client, temp_db):
    """seed_trainer로 직접 INSERT한 non-owner 계정으로 로그인하면 session.user.is_owner == False."""
```
- DB에 직접 `INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES ('직원', 'stafft', hash_password('spw'), 0, ...)` 삽입.
- `client.post('/login', data={'username': 'stafft', 'password': 'spw'})` → 303.
- `client.cookies`에 세션 쿠키가 있음을 확인 (혹은 후속 보호 라우트 GET이 303 아님 확인으로 간접 검증).
- 검증을 명확히 하려면 보호 라우트(예: `/`)에 접근 후 303이 `/login`이 **아닌** 지 확인.

**5. `test_session_structure_user_dict`**
```python
def test_session_structure_user_dict(client):
    """로그인 후 session["user"]가 {trainer_id, is_owner} 구조, 기존 'admin' 키는 없음."""
```
- 로그인 후 `client.cookies.get("bet_session")` 값을 `itsdangerous` 같은 의존으로 풀기 어렵다면 **간접 검증**: 로그아웃 → 재시도 패턴.
- 혹은 `starlette.middleware.sessions.SessionMiddleware`의 서명 검증을 생략하고 쿠키를 base64 decode하는 헬퍼를 작성 (mock 금지 원칙과 무관한 읽기).
- 가장 실용적: POST /login 성공 → 보호 라우트 200 접근 확인 + 로그아웃 후 재차 303 확인으로 **간접** 보장. 세션 내부 키 검증은 과도한 결합이라 생략 OK.
- 대신 **`test_owner_can_access_export_non_owner_cannot`** 테스트로 세션의 is_owner 플래그를 기능 행동으로 간접 검증한다. test_export.py에서 커버하므로 이 항목은 생략 가능.

→ **결정**: #5는 생략. 4개 신규 테스트로 충분.

### 2. `/tests/test_log_routes.py` 확장

기존 테스트 전부 유지. 추가:

**1. `test_post_log_stamps_input_trainer_id`**
```python
def test_post_log_stamps_input_trainer_id(temp_db, authed_client):
    """POST /log 시 session["user"]["trainer_id"]가 input_trainer_id로 기록된다."""
```
- `_seed_trainer_member(temp_db)` → tid, mid (iteration 1 그대로 회원 생성)
- authed_client는 "admin" 세션 (ensure_owner_seed가 만든 trainer — 그의 trainer_id를 조회)
- `authed_client.post(f"/trainers/{tid}/members/{mid}/log", data={...})` 한 번
- DB 조회: `SELECT input_trainer_id FROM pt_sessions WHERE member_id=?` → `admin`의 trainer_id와 같아야 함.

### 3. `/tests/test_export.py` 신규

새 파일. 6개 테스트.

```python
import csv
import io
from datetime import datetime

from app.db import get_connection
from app.auth import hash_password


def _insert_non_owner(db_path, username="stafft", password="spw", name="직원"):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 0, ?)",
            (name, username, hash_password(password), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def _insert_session_with_set(db_path, member_id, exercise, weight, reps, input_trainer_id=None, session_date="2026-04-10"):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO pt_sessions (member_id, session_date, created_at, input_trainer_id) VALUES (?, ?, ?, ?)",
            (member_id, session_date, "2026-04-10T00:00:00", input_trainer_id),
        )
        session_id = cur.lastrowid
        c.execute(
            "INSERT INTO session_sets (session_id, exercise, weight_kg, reps, set_index) VALUES (?, ?, ?, ?, 0)",
            (session_id, exercise, weight, reps),
        )


def _insert_member(db_path, trainer_id, name="회원1"):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
            (trainer_id, name, "2026-04-01T00:00:00"),
        )
        return cur.lastrowid


def _owner_trainer_id(db_path):
    with get_connection(db_path) as c:
        return c.execute("SELECT id FROM trainers WHERE is_owner=1 LIMIT 1").fetchone()["id"]
```

#### 테스트 6개

**1. `test_export_requires_owner(temp_db, client)`**
- 직접 DB INSERT non-owner + POST /login으로 로그인
- `GET /admin/export/sessions.csv` → 303, location == `/`

**2. `test_export_returns_csv_with_bom(temp_db, authed_client)`**
- owner_id = 관장 trainer_id
- member 1명, 세션 1개 (스쿼트 60/5), input_trainer_id=owner_id
- `GET /admin/export/sessions.csv` → 200
- `content-type` startswith `text/csv`
- body bytes `\xef\xbb\xbf`로 시작
- `Content-Disposition` header에 `filename=sessions_` 포함, `.csv` 끝
- BOM 제거 후 csv.reader로 파싱 → header row == `['session_date','member_name','exercise','weight_kg','reps','set_index','input_trainer_name']`
- 데이터 행 1건, member_name '회원1', exercise '스쿼트', input_trainer_name '관장' 유사 (관장 name이 admin이면 'admin').

**3. `test_export_filter_by_trainer_id(temp_db, authed_client)`**
- non_owner_id 생성
- member에 세션 2건: input_trainer_id=owner_id 하나, =non_owner_id 하나
- `GET /admin/export/sessions.csv?trainer_id={non_owner_id}` → 1 data row, input_trainer_name은 non-owner 이름.
- filename에 `_trainer_{non_owner_id}` 포함.

**4. `test_export_rate_limit_429(temp_db, authed_client)`**
- 세션 1건 준비.
- 1차 `GET /admin/export/sessions.csv` → 200
- 2차 `GET /admin/export/sessions.csv` → 429
- body text에 "Too Many Requests" 또는 retry 안내.

**5. `test_export_rate_limit_resets_per_owner(temp_db, authed_client, monkeypatch)`**
- 1차 → 200 후 `authed_client.app.state.export_last_ts.clear()` (또는 해당 dict 직접 수정)
- 2차 → 200
- 이 테스트는 **monkeypatch 대신 dict 직접 조작** (전역 state가 app.state에 은닉되어 있으므로).

**6. `test_export_stdout_log(temp_db, authed_client, capsys)`**
- 세션 1건 준비 후 `GET /admin/export/sessions.csv`
- `captured = capsys.readouterr().out` (또는 `readouterr` 후 out/err 모두 검사)
- `[export] owner_id=` 포함, `target_trainer_id=all` 포함, `rows=1` 포함.

**7. `test_export_null_input_trainer_id_row_has_empty_name(temp_db, authed_client)`**
- 세션 1건 `input_trainer_id=NULL`
- `GET /admin/export/sessions.csv` → 200
- CSV 파싱해서 해당 row의 `input_trainer_name`이 빈 문자열 `""`인지 확인.

→ 총 7개 (6→7 업그레이드 OK. 이전 논의 Q8의 fixture 분리 지침 반영하여 #7은 authed_client를 그대로 써도 문제 없음 — 각 테스트가 temp_db fixture를 받아 독립된 DB 사용).

### 4. 기존 e2e (`/tests/test_e2e_dashboard.py`) 호환성 확인

수정 금지. 단 conftest의 live_server fixture가 iteration 2 이후에도 동작하는지 Phase 2에서 이미 scripts/seed.py를 수정해서 호환성을 확보했음. 이 phase에서는 돌려서 그대로 green인지 확인만 하면 충분.

### 5. 기존 `/tests/test_dashboard.py`, `/tests/test_aggregates.py` — 수정 금지

iteration 2 변경은 이 계층에 영향 없음. 다만 회귀 검증 용도로 돌려서 green 확인.

## Acceptance Criteria

```bash
# 1) 전체 테스트 수트 실행 (playwright 포함)
uv run pytest -q

# 2) 신규·확장 테스트 개별 확인
uv run pytest tests/test_auth.py -q
uv run pytest tests/test_log_routes.py -q
uv run pytest tests/test_export.py -q

# 3) test_export.py가 정확히 존재하고 7개 테스트 항목을 갖는지 확인
test -f tests/test_export.py
uv run pytest tests/test_export.py --collect-only -q | grep -E '^tests/test_export\.py::' | wc -l | awk '$1 >= 7 {exit 0} {exit 1}'
```

- 모든 AC 커맨드가 exit 0 이면 `/tasks/1-trainer-auth-export/index.json`의 phase 3 status를 `"completed"`로 변경.
- Playwright e2e 테스트(`test_e2e_dashboard.py`)가 환경 문제(크로미움 미설치 등)로 실패하면, 해당 파일만 `uv run pytest --ignore tests/test_e2e_dashboard.py -q`로 제외하고 나머지 통과 확인. 단 `error_message`에 "e2e skipped: playwright runtime unavailable"라고 명시.

## AC 검증 방법

위 AC를 순차 실행. 3회 시도해도 실패 시 `"error"` + `"error_message"`.

## 주의사항

- **mock 금지** — `unittest.mock`, `pytest-mock` 사용 금지. DB는 tmp_path sqlite 그대로. monkeypatch는 허용 (env, attribute, 모듈 전역 dict 조작까지는 mock이 아니라 state injection이다).
- **`time.monotonic` 직접 패치 금지** — rate limit 테스트는 `app.state.export_last_ts` dict 조작으로 해결.
- 새 테스트들은 `conftest.py`의 `temp_db`, `client`, `authed_client` fixture를 재사용. 필요한 fixture가 없으면 **테스트 파일 내 helper 함수**로 충분 (추가 fixture 대량 생성 금지).
- `_seed_trainer_member` 패턴(직접 INSERT) 유지. iteration 1 테스트가 이 패턴을 쓰고 있으니 일관성 유지.
- `test_boot_*` 테스트는 `create_app`을 직접 호출해야 하므로 conftest의 `client` fixture 대신 **각 테스트 내부**에서 `monkeypatch.setenv`로 env 설정 후 직접 `create_app()` 호출. fixture `client`는 이미 1회 create_app한 상태라 재검증 안 됨.
- CSV 본문 읽을 때 `r.content` (bytes)로 읽어 BOM 비교, 이후 `r.content[3:].decode('utf-8')`로 parsing.
- `authed_client.app` 속성은 FastAPI 앱 참조. `authed_client.app.state.export_last_ts`로 rate limit dict 접근 가능. `TestClient.app`은 `app` attribute로 사용 가능함.
- 기존 `test_auth.py::test_missing_env_raises_runtime_error`는 이미 `_validate_env`가 env 3종을 체크하므로 그대로 통과. 확인만.
- conftest.py를 수정하는 경우, 기존 fixture 시그니처/동작을 깨뜨리지 마라. 추가만 허용.
- pyproject.toml, Dockerfile, fly.toml 변경 금지.
- 기존 templates, exercises.py, aggregates.py는 변경 금지.
- e2e 테스트가 환경 문제로 실패하면 `--ignore` 옵션으로 제외 허용 (AC에 명시된 완화 조건). 이외 테스트는 반드시 green.
