# Phase 1: schema-insert

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` (iter 6 반영본 — Phase 0에서 업데이트됨. "데이터 모델" 섹션의 `export_audit` 정의 + "CSV Export" 섹션의 INSERT 부수효과 2건 + 신규 "## 감사 로그 뷰어 (iter 6 live)" 섹션)
- `/docs/testing.md` (테스트 원칙 — mock 금지, tmp_path SQLite only)
- `/docs/user-intervention.md` (변경 없음 확인용)
- `/tasks/4-my-audit-log/docs-diff.md` (이번 task의 Phase 0 docs 변경 diff — Phase 0 완료 후 `scripts/gen-docs-diff.py`가 자동 생성)
- `/iterations/6-20260424_123444/requirement.md` (요구사항 원문. 특히 "구현 스케치" 1~2 섹션 + "CTO 승인 조건부 조건" 6개)

그리고 이전 phase의 작업물을 반드시 확인하라:

- Phase 0에서 수정된 `docs/spec.md`의 "데이터 모델" / "CSV Export" / "## 감사 로그 뷰어 (iter 6 live)" / "다음 스프린트 예약 티켓"(N0 블록 삭제됨) 섹션

현 코드 베이스를 꼼꼼히 읽고 이해하라:

- `/app/db.py` — `init_db()`가 `executescript(...)`로 4개 테이블 `CREATE TABLE IF NOT EXISTS` 후 `_migrate_iteration2(conn)` 호출. `with get_connection() as conn:` 블록 종료 시 `__exit__`에서 COMMIT.
- `/app/routes.py` — `_write_sessions_csv(conn, trainer_id_filter, buffer) -> int` 공통 헬퍼(data row 수 반환, header 제외). `/admin/export/sessions.csv` (285~325행 부근) + `/my/export/sessions.csv` (327~362행 부근) 양쪽에서 `_write_sessions_csv` 호출 후 stdout `[export]` / `[my-export]` print + `app.state.export_last_ts` / `app.state.my_export_last_ts` dict 업데이트.
- `/app/main.py` — `create_app()`에서 `init_db()` 호출. 즉 init_db 실행 시점에 `export_audit` 테이블이 자동 생성됨.
- `/tests/conftest.py` — `temp_db` fixture가 `init_db(db_path)` 실행. Phase 1 변경 후에도 이 fixture를 통해 테스트용 DB에 `export_audit` 테이블이 자동 생성되어야 한다.

## 작업 내용

이번 phase는 **DB 스키마 추가 + 관장/본인 export 라우트에 INSERT 로직 추가**다. 파일 2개만 수정한다: `app/db.py`, `app/routes.py`.

### 1. `app/db.py` — `export_audit` 테이블 추가

`init_db()` 안의 `conn.executescript("""...""")` 블록에서 기존 4개 `CREATE TABLE IF NOT EXISTS` 정의 뒤에 **5번째 블록**을 추가하라. 이터레이션 경계를 명확히 하기 위해 블록 직전에 **`-- iter 6: export_audit` 주석 1줄**을 반드시 넣어라.

추가할 SQL (정확히 이 스키마):

```sql
-- iter 6: export_audit
CREATE TABLE IF NOT EXISTS export_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('owner_export', 'my_export')),
    actor_trainer_id INTEGER NOT NULL REFERENCES trainers(id),
    target_trainer_id INTEGER REFERENCES trainers(id),
    rows INTEGER NOT NULL
);
```

- 별도 `_migrate_iteration6()` 함수를 추가하지 마라 — `CREATE TABLE IF NOT EXISTS`만으로 idempotent.
- `_migrate_iteration2(conn)` 호출 줄은 그대로 유지.
- `sqlite3.Row` / `row_factory` / `foreign_keys` PRAGMA 등 다른 db.py 로직은 건드리지 마라.

### 2. `app/routes.py` — 2개 export 라우트에 INSERT 추가

#### 2-a. `/admin/export/sessions.csv` 라우트 수정

현재 구조 (대략):
```python
buf = io.StringIO()
with get_connection() as conn:
    rows_count = _write_sessions_csv(conn, trainer_id, buf)

csv_content = "﻿" + buf.getvalue()
...
print(f"[export] owner_id={owner_id} target_trainer_id={...} rows={rows_count}", flush=True)
export_last_ts[owner_id] = time.monotonic()
return Response(...)
```

변경 후 구조:
```python
buf = io.StringIO()
with get_connection() as conn:
    rows_count = _write_sessions_csv(conn, trainer_id, buf)
    conn.execute(
        "INSERT INTO export_audit (created_at, action, actor_trainer_id, target_trainer_id, rows)"
        " VALUES (?, 'owner_export', ?, ?, ?)",
        (datetime.utcnow().isoformat(), owner_id, trainer_id, rows_count),
    )
```

원칙:
- **INSERT는 `with get_connection() as conn:` 블록 안에서** `_write_sessions_csv` 호출 **직후**에 수행. 블록 종료 시 `__exit__`의 자동 COMMIT이 SELECT와 INSERT를 하나의 트랜잭션으로 마감한다 (원자성).
- `trainer_id` 파라미터가 `None`이면 그대로 `None`을 바인딩하여 `target_trainer_id` 컬럼이 NULL로 저장된다.
- `datetime.utcnow().isoformat()` 은 ISO8601 UTC 문자열. 파일 상단 `from datetime import date, datetime` import는 이미 존재.
- stdout `print(f"[export] ...")` 줄은 **유지** (CTO 조건 2 — 이중 기록).
- `export_last_ts[owner_id]` 업데이트도 그대로 유지.
- 429 rate-limit 분기는 **`with get_connection()` 블록 진입 전**이므로 INSERT 스킵이 자동 보장됨 (성공 경로만 INSERT).

#### 2-b. `/my/export/sessions.csv` 라우트 수정

동일 패턴:
```python
buf = io.StringIO()
with get_connection() as conn:
    rows_count = _write_sessions_csv(conn, trainer_id, buf)
    conn.execute(
        "INSERT INTO export_audit (created_at, action, actor_trainer_id, target_trainer_id, rows)"
        " VALUES (?, 'my_export', ?, ?, ?)",
        (datetime.utcnow().isoformat(), trainer_id, trainer_id, rows_count),
    )
```

원칙:
- `my_export`의 actor와 target은 **동일한 session user의 trainer_id**.
- stdout `print(f"[my-export] ...")` 유지.
- `my_export_last_ts[trainer_id]` 업데이트 유지.
- 429 경로는 `with` 블록 진입 전이므로 스킵 자동.

### 3. 추가 상수/헬퍼 금지

- `MY_AUDIT_LOG_LIMIT` 상수는 Phase 2에서 라우트와 함께 추가한다. Phase 1에서는 **선언하지 마라**.
- `my_audit_log.html` 템플릿은 Phase 2에서 추가한다. Phase 1에서는 **생성하지 마라**.
- INSERT 실패 시 FastAPI 기본 500 응답 허용. 별도 try/except나 감쇠 경로 추가 금지.

## Acceptance Criteria

```bash
# 1. import + 앱 구성 OK
uv run python -c "from app.db import init_db; from app.routes import register_routes; print('OK')"

# 2. export_audit 테이블이 init_db 실행 후 실제로 생성되는지 (tmp DB)
uv run python -c "
import sqlite3, pathlib, tempfile, os
d = tempfile.mkdtemp()
p = pathlib.Path(d) / 'x.db'
from app.db import init_db
init_db(p)
c = sqlite3.connect(str(p))
cols = [r[1] for r in c.execute('PRAGMA table_info(export_audit)').fetchall()]
assert cols == ['id','created_at','action','actor_trainer_id','target_trainer_id','rows'], cols
c.close()
print('schema OK')
"

# 3. 기존 export 테스트가 깨지지 않는지 (stdout 포맷·rate limit·컬럼 drift 회귀 없음)
uv run pytest tests/test_export.py tests/test_my_export.py -x

# 4. 전체 regression (e2e 제외)
uv run pytest -x --ignore=tests/test_e2e_dashboard.py

# 5. 기존 export 성공 호출 1건 후 export_audit row 1건 증가 (adhoc 검증)
uv run python -c "
import os, tempfile, pathlib, sqlite3
from datetime import datetime
d = tempfile.mkdtemp()
p = pathlib.Path(d) / 'y.db'
os.environ.update(DATABASE_PATH=str(p), APP_SESSION_SECRET='x'*32, ADMIN_USERNAME='a', ADMIN_PASSWORD='p')
from app.db import init_db, get_connection
from app.auth import hash_password
init_db(p)
with get_connection(p) as conn:
    conn.execute(\"INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES ('admin','a',?,1,?)\",(hash_password('p'), datetime.utcnow().isoformat()))
from fastapi.testclient import TestClient
from app.main import create_app
app = create_app()
c = TestClient(app)
c.post('/login', data={'username':'a','password':'p'}, follow_redirects=False)
app.state.export_last_ts.clear()
r = c.get('/admin/export/sessions.csv')
assert r.status_code == 200
with get_connection(p) as conn:
    n = conn.execute('SELECT COUNT(*) FROM export_audit').fetchone()[0]
assert n == 1, n
print('insert OK')
"
```

## AC 검증 방법

위 AC 커맨드를 직접 실행하라. 1~4번이 모두 통과하면 `/tasks/4-my-audit-log/index.json`의 phase 1 status를 `"completed"`로 변경하라.
5번은 adhoc이지만 INSERT 경로의 스모크 증명이 되므로 실행하라. 실패 시 5번 에러 내용을 phase 1 "notes"에 1줄 기록.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 index.json의 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- **별도 마이그레이션 함수 추가 금지.** `_migrate_iteration6` 등을 만들지 마라. `CREATE TABLE IF NOT EXISTS` 한 줄로 idempotent.
- **`init_db()` 호출 위치/순서 변경 금지**. `app/main.py`의 `create_app()` 흐름은 건드리지 마라.
- **stdout `[export]` / `[my-export]` print 줄 제거·포맷 변경 금지** (CTO 조건 2 — 이중 기록). 기존 테스트 `test_export.py::stdout_log`, `test_my_export.py::stdout_log`가 해당 포맷에 의존.
- **INSERT를 `with` 블록 밖으로 빼지 마라.** 원자성 상실 + rate-limit dict 업데이트 시점과 섞이면 감사 의미가 흐려진다.
- **`rows` 컬럼 값은 반드시 `_write_sessions_csv` 반환값**(header 제외 data row 수). `len(csv_content.splitlines())` 같은 대안 금지 (CTO 조건 5).
- **429 rate-limit 분기에 INSERT 추가 금지.** 429는 실패 경로, 감사 로그는 성공 기록.
- **DB 쪽 `PRAGMA foreign_keys=ON`이 이미 켜져 있다.** `actor_trainer_id`가 유효하지 않은 값이면 IntegrityError. 테스트는 항상 seed된 trainer_id로만 INSERT 경로가 호출되므로 문제 없음.
- **`app/templates/my_audit_log.html` 만들지 마라**. Phase 2 scope.
- **`MY_AUDIT_LOG_LIMIT` 상수 선언 금지**. Phase 2에서.
- **`GET /my/audit-log` 라우트 추가 금지**. Phase 2에서.
- 기존 테스트 파일 수정 금지 — `test_export.py`·`test_my_export.py`는 기존 stdout 포맷·rate limit·컬럼 drift만 검증하며, export_audit INSERT 존재 자체는 깨뜨리지 않아야 한다.
