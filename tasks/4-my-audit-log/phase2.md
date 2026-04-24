# Phase 2: view-template-tests

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` (iter 6 반영본. 특히 "## 감사 로그 뷰어 (iter 6 live)" 섹션과 "데이터 모델"의 `export_audit` 정의)
- `/docs/testing.md` (원칙: mock 금지, tmp_path SQLite only, ORM 금지. `pytest.monkeypatch` 통한 env/모듈 attribute/전역 dict 조작은 허용. `time.monotonic` 패치 금지, DB mock 금지)
- `/tasks/4-my-audit-log/docs-diff.md` (이번 task의 Phase 0 docs diff)
- `/iterations/6-20260424_123444/requirement.md` (구현 스케치 3~4 섹션 + CTO 조건 1/4/5/6)

그리고 이전 phase의 작업물을 반드시 확인하라:

- Phase 0에서 수정된 `docs/spec.md` / `docs/testing.md`
- Phase 1에서 수정된 `app/db.py` (`export_audit` 테이블 추가) + `app/routes.py` (`/admin/export`, `/my/export` 양쪽 INSERT 추가). Phase 1 AC가 모두 green 상태여야 본 phase 진행 가능.

기존 테스트 fixture / 헬퍼 패턴 확인:

- `/tests/conftest.py` — `temp_db` (monkeypatch DB_PATH + init_db), `client`, `authed_client` (admin ADMIN_USERNAME=admin, ADMIN_PASSWORD=pw1234, is_owner=1 자동 시드).
- `/tests/test_my_export.py` — `_insert_trainer`, `_insert_member`, `_insert_session_with_set`, `_owner_trainer_id`, `_login`, `_logout` private 헬퍼 패턴.

## 작업 내용

이번 phase는 **라우트 + 템플릿 + 테스트**를 한 phase에 묶어 수행한다. 파일 3개만 수정/생성한다: `app/routes.py`, `app/templates/my_audit_log.html` (신규), `tests/test_my_audit_log.py` (신규).

### 1. `app/routes.py` — `MY_AUDIT_LOG_LIMIT` 상수 + `GET /my/audit-log` 라우트 추가

#### 1-a. 모듈 상수 추가

파일 상단의 `_SESSIONS_CSV_COLUMNS = (...)` 정의 아래에 다음 상수 1줄을 추가:

```python
MY_AUDIT_LOG_LIMIT = 100
```

- 이 상수는 테스트에서 `from app.routes import MY_AUDIT_LOG_LIMIT`로 import되어 drift 방지 장치로 쓰인다.
- 값 변경 금지. 첫 배포에서 100 유지.

#### 1-b. `GET /my/audit-log` 라우트 추가

`register_routes(app)` 함수 안에 새 async 라우트로 추가하라. `/my/export/sessions.csv` 바로 아래에 배치.

시그니처 및 로직:

```python
@app.get("/my/audit-log")
async def get_my_audit_log(request: Request):
    if not is_authenticated(request):
        return login_required_redirect()

    self_tid = current_user(request)["trainer_id"]
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ea.id, ea.created_at, ea.action, ea.target_trainer_id, ea.rows,
                   actor.name AS actor_name, target.name AS target_name
            FROM export_audit ea
            JOIN trainers actor ON ea.actor_trainer_id = actor.id
            LEFT JOIN trainers target ON ea.target_trainer_id = target.id
            WHERE ea.target_trainer_id = ?
               OR ea.actor_trainer_id = ?
               OR (ea.action = 'owner_export' AND ea.target_trainer_id IS NULL)
            ORDER BY ea.id DESC
            LIMIT ?
            """,
            (self_tid, self_tid, MY_AUDIT_LOG_LIMIT),
        ).fetchall()

    return templates.TemplateResponse(
        request,
        "my_audit_log.html",
        {"rows": rows},
    )
```

원칙:
- **본인 조회는 감사 대상 아님** — 이 라우트는 stdout/DB 로그를 남기지 않는다. 어떤 `print()` / INSERT 도 넣지 마라.
- WHERE 절의 **3 OR 조건**은 spec의 "## 감사 로그 뷰어" 섹션에 정의된 그대로. 조건 순서 바꾸지 마라 (읽기 가독성과 리뷰 효율). SQL 주석으로 3줄 매핑을 명시적으로 달아도 좋으나 의무는 아님.
- `ORDER BY ea.id DESC LIMIT ?` — AUTOINCREMENT id에 의존하므로 INSERT 순서 = id 순 = 최신성. `created_at` 기반 정렬이 아님에 주의.
- `LEFT JOIN trainers target` — `target_trainer_id IS NULL` row는 `target.name`이 NULL이 됨. 템플릿에서 별도 분기.
- `templates.TemplateResponse` 반환.

### 2. `app/templates/my_audit_log.html` (신규 템플릿)

`base.html` extends. 테이블 구조는 최소한으로 작성. **필터/검색/정렬 UI·페이지네이션 UI·CSV 다운로드 버튼 일절 금지** (CTO 조건 1).

파일 내용 (정확히 이 구조 유지):

```html
{% extends "base.html" %}
{% block content %}
  <h1>감사 로그</h1>
  <p>본인 관련 export 이력 최신 {{ rows|length }}건 (상한 100).</p>
  <table>
    <thead>
      <tr>
        <th>일시</th>
        <th>행위</th>
        <th>호출자</th>
        <th>대상</th>
        <th>rows</th>
      </tr>
    </thead>
    <tbody>
      {% for row in rows %}
      <tr data-action="{{ row.action }}">
        <td>{{ row.created_at }}</td>
        <td>{{ row.action }}</td>
        <td>{{ row.actor_name }}</td>
        <td>
          {% if row.action == 'owner_export' and row.target_trainer_id is none %}
            전체 대상(본인 포함)
          {% else %}
            {{ row.target_name }}
          {% endif %}
        </td>
        <td>{{ row.rows }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
{% endblock %}
```

원칙:
- 각 `<tr>`에 **`data-action="..."` 속성을 정확히 1회** 삽입 — 테스트가 `r.text.count('data-action="owner_export"')`, `r.text.count('data-action="my_export"')` 기반 카운트 assertion을 사용한다. 속성 이름/위치 변경 금지.
- `{{ row.action }}`은 `<td>` 안에서 한 번 더 렌더되므로 `r.text.count('owner_export')`는 **행당 2회 카운트**됨 — 테스트는 `data-action="..."` 속성을 기준으로 카운트하므로 이 이중 노출은 무해. 테스트 작성 시 반드시 `data-action="owner_export"` 전체 문자열로 카운트하라.
- `actor_name` / `target_name` 렌더링 시 트레이너 실제 이름이 HTML에 노출됨 — 타 트레이너 이름 노출 = 회귀 (test #4가 감지).
- HTML escape는 Jinja2 autoescape 기본 동작을 신뢰 (추가 설정 불요).
- 추가 CSS/JS 금지. `base.html`이 이미 `htmx.org`를 로드하지만 이번 페이지는 HTMX 미사용.

### 3. `tests/test_my_audit_log.py` (신규)

**파일 상단에 다음 1줄 주석을 포함하라**:

```python
# ORDER BY ea.id DESC는 AUTOINCREMENT id에 의존한다. id 컬럼 정의 변경 시 아래 시나리오 #7 (LIMIT)이 깨질 수 있다.
```

이후 import 및 헬퍼:

```python
import csv
import io
import sqlite3
from datetime import datetime

from app.auth import hash_password
from app.db import get_connection
from app.routes import MY_AUDIT_LOG_LIMIT


def _insert_trainer(db_path, username, password, name, is_owner=0): ...
def _insert_member(db_path, trainer_id, name="회원1"): ...
def _insert_session_with_set(db_path, member_id, exercise, weight, reps, input_trainer_id=None, session_date="2026-04-10"): ...
def _owner_trainer_id(db_path): ...
def _login(client, username, password): ...
def _logout(client): ...
def _fetch_audit_rows(db_path): ...  # returns list[sqlite3.Row] of export_audit ORDER BY id
def _count_audit_rows(db_path): ...  # returns int
```

헬퍼 구현은 `tests/test_my_export.py`와 동일한 패턴을 따른다. `_fetch_audit_rows` / `_count_audit_rows`는 별도 `sqlite3.connect(str(db_path))` 커넥션으로 수행하고 `try/finally close()`로 안전 해제.

#### 8 시나리오

각 시나리오는 별도 `test_*` 함수. `client` fixture + 명시적 `_login` 사용 (관장/비관장 전환이 잦음). 시나리오 내 export 호출 직전에는 반드시 해당 state dict를 clear:

```python
client.app.state.export_last_ts.clear()
client.app.state.my_export_last_ts.clear()
```

---

**1. test_admin_export_with_trainer_id_inserts_audit_row** — (CTO 조건 5 보완)

- Seed: `x_id = _insert_trainer(temp_db, "staff_x", "xpw", "X직원")`, `x_member = _insert_member(temp_db, x_id)`, `_insert_session_with_set(temp_db, x_member, "스쿼트", 60, 5, x_id)`, `_insert_session_with_set(temp_db, x_member, "벤치프레스", 50, 5, x_id, "2026-04-11")`.
- `_login(client, "admin", "pw1234")`; `client.app.state.export_last_ts.clear()`.
- `r = client.get(f"/admin/export/sessions.csv?trainer_id={x_id}")` → `assert r.status_code == 200`.
- `rows = _fetch_audit_rows(temp_db)`; `assert len(rows) == 1`; `assert rows[0]["action"] == "owner_export"`; `assert rows[0]["actor_trainer_id"] == _owner_trainer_id(temp_db)`; `assert rows[0]["target_trainer_id"] == x_id`; `assert rows[0]["rows"] == 2`.

---

**2. test_admin_export_without_trainer_id_inserts_audit_row_target_null**

- Seed: owner 본인 입력분 1개 + X직원 입력분 1개.
- `_login admin`; `client.app.state.export_last_ts.clear()`.
- `r = client.get("/admin/export/sessions.csv")` → 200.
- `rows = _fetch_audit_rows(temp_db)`; `assert len(rows) == 1`; `assert rows[0]["action"] == "owner_export"`; `assert rows[0]["target_trainer_id"] is None`; `assert rows[0]["rows"] == 2`.

---

**3. test_my_export_inserts_audit_row_with_self_actor_target**

- Seed: `a_id = _insert_trainer(temp_db, "a_t", "apw", "A트레이너")`, `a_member = _insert_member(temp_db, a_id)`, `_insert_session_with_set(..., input_trainer_id=a_id)`.
- `_login(client, "a_t", "apw")`; `client.app.state.my_export_last_ts.clear()`.
- `r = client.get("/my/export/sessions.csv")` → 200.
- `rows = _fetch_audit_rows(temp_db)`; `assert len(rows) == 1`; `assert rows[0]["action"] == "my_export"`; `assert rows[0]["actor_trainer_id"] == a_id`; `assert rows[0]["target_trainer_id"] == a_id`; `assert rows[0]["rows"] == 1`.

---

**4. test_my_audit_log_filters_rows_correctly** — **(CTO 조건 4 — WHERE 3 OR 절 회귀 방지)**

시나리오 목적: A의 `/my/audit-log`에는 "타 트레이너만 actor/target인 row"가 절대 노출되지 않아야 한다. 3 OR 조건 중 오직 `target IS NULL`만 match되는 케이스 1개만 노출되는 시나리오를 세운다.

- Seed 3 트레이너: `a_id = _insert_trainer(temp_db, "a_t","apw","A트레이너")`, `b_id = _insert_trainer(temp_db, "b_t","bpw","B트레이너")`, `c_id = _insert_trainer(temp_db, "c_t","cpw","C트레이너")`. 각자 회원 1명 + 세션 1개 입력 (각자 own `input_trainer_id`로).
- `_login admin`; `client.app.state.export_last_ts.clear()`.
- `client.get(f"/admin/export/sessions.csv?trainer_id={b_id}")` → 200. **(row1: owner_export, actor=owner, target=b_id)**
- `client.app.state.export_last_ts.clear()`.
- `client.get("/admin/export/sessions.csv")` → 200. **(row2: owner_export, actor=owner, target=NULL)**
- `_logout(client)`.
- `_login(client, "c_t","cpw")`; `client.app.state.my_export_last_ts.clear()`.
- `client.get("/my/export/sessions.csv")` → 200. **(row3: my_export, actor=target=c_id)**
- `_logout(client)`.
- `_login(client, "a_t","apw")`.
- `r = client.get("/my/audit-log")` → `assert r.status_code == 200`.
- **3 OR 조건별 매핑 (테스트 안에 주석으로 명시)**:
    - `target = a_id`: 0 row (아무도 A를 target으로 뽑지 않음)
    - `actor = a_id`: 0 row
    - `owner_export AND target IS NULL`: 1 row (row2)
- 따라서 A의 `/my/audit-log`는 **정확히 row2 1건만** 표시.
- Assertions:
  - `assert r.text.count('data-action="owner_export"') == 1`
  - `assert r.text.count('data-action="my_export"') == 0`
  - 타 트레이너 이름 미노출 (행 안에만 렌더되므로, `data-action` 속성 외에서 이름 중복 노출이 안 됨을 단정): `assert "B트레이너" not in r.text`, `assert "C트레이너" not in r.text`.
  - row2는 target=NULL이므로 대상 셀에 `"전체 대상(본인 포함)"` 문자열 포함: `assert "전체 대상(본인 포함)" in r.text`.

---

**5. test_my_audit_log_unauthenticated_redirects_to_login**

- 비로그인 상태.
- `r = client.get("/my/audit-log", follow_redirects=False)`.
- `assert r.status_code == 303`; `assert r.headers["location"] == "/login"`.

---

**6. test_owner_self_target_and_null_both_visible_in_audit_log** — **(CTO 조건 6 강화)**

- `_login(client, "admin", "pw1234")`; `owner_id = _owner_trainer_id(temp_db)`.
- Seed: owner 본인 입력 session_set 1개 + X직원 입력 1개 (X직원의 id를 x_id로 따로 seed).
- `client.app.state.export_last_ts.clear()`; `client.get(f"/admin/export/sessions.csv?trainer_id={owner_id}")` → 200. **(row1: owner_export, target=owner_id)**
- `client.app.state.export_last_ts.clear()`; `client.get("/admin/export/sessions.csv")` → 200. **(row2: owner_export, target=NULL)**
- `client.app.state.my_export_last_ts.clear()`; `client.get("/my/export/sessions.csv")` → 200. **(row3: my_export, actor=target=owner_id)**
- `r = client.get("/my/audit-log")` → 200.
- **3 OR 조건 매핑**:
    - row1: target = owner_id → target match ✓
    - row2: target IS NULL + owner_export → third-clause match ✓
    - row3: actor = owner_id AND target = owner_id → actor & target match ✓
- Assertions:
  - `assert r.text.count('data-action="owner_export"') == 2`
  - `assert r.text.count('data-action="my_export"') == 1`

---

**7. test_my_audit_log_respects_limit_100** — **(CTO 조건 1)**

- `_login admin`; `owner_id = _owner_trainer_id(temp_db)`.
- 직접 sqlite에 `MY_AUDIT_LOG_LIMIT + 5`건 INSERT (`my_export`, actor=target=owner_id):
  ```python
  with get_connection(temp_db) as conn:
      for i in range(MY_AUDIT_LOG_LIMIT + 5):
          conn.execute(
              "INSERT INTO export_audit (created_at, action, actor_trainer_id, target_trainer_id, rows)"
              " VALUES (?, 'my_export', ?, ?, 1)",
              (f"2026-04-{(i % 28) + 1:02d}T00:00:00", owner_id, owner_id),
          )
  ```
- `r = client.get("/my/audit-log")` → 200.
- `assert r.text.count('data-action="my_export"') == MY_AUDIT_LOG_LIMIT`.

---

**8. test_rows_column_matches_write_sessions_csv_return** — **(CTO 조건 5)**

- `_login admin`; `owner_id = _owner_trainer_id(temp_db)`.
- Seed: 정확히 3개 session_set INSERT (owner 본인 입력).
- `client.app.state.export_last_ts.clear()`.
- `r = client.get("/admin/export/sessions.csv")` → 200.
- CSV body 파싱: `csv_text = r.content[3:].decode("utf-8")` (BOM skip); `reader_rows = list(csv.reader(io.StringIO(csv_text)))`; `assert len(reader_rows) == 4` (header 1 + data 3).
- `audit_rows = _fetch_audit_rows(temp_db)`; `assert audit_rows[0]["rows"] == 3`; `assert audit_rows[0]["rows"] == len(reader_rows) - 1` (2-축 단정).

---

### 4. Regression 확인

Phase 2 말미에 다음을 실행:

```bash
uv run pytest tests/test_my_audit_log.py -v
uv run pytest -x --ignore=tests/test_e2e_dashboard.py
```

기존 8 파일(test_aggregates, test_auth, test_log_routes, test_dashboard, test_e2e_dashboard, test_export, test_my_export, test_member_access) + 신규 1 파일 전체 green을 확인한다.

**e2e 처리**: Playwright chromium 미설치 환경에서는 e2e skip 허용. Phase 1의 INSERT 추가로 인한 e2e 회귀는 예상되지 않음 (대시보드 차트는 `export_audit`와 무관).

## Acceptance Criteria

```bash
# 1. 신규 테스트 8 시나리오 전체 통과
uv run pytest tests/test_my_audit_log.py -v

# 2. 전체 regression (e2e 제외)
uv run pytest -x --ignore=tests/test_e2e_dashboard.py

# 3. e2e는 환경 가능할 때만 확인 (스킵 허용)
uv run pytest tests/test_e2e_dashboard.py || echo "e2e env-dependent, skipped"

# 4. 템플릿 파일 존재 확인
test -f app/templates/my_audit_log.html

# 5. 상수 노출 확인
uv run python -c "from app.routes import MY_AUDIT_LOG_LIMIT; assert MY_AUDIT_LOG_LIMIT == 100; print('const OK')"

# 6. 라우트 응답 스모크
uv run python -c "
import os, tempfile, pathlib
from datetime import datetime
d = tempfile.mkdtemp()
p = pathlib.Path(d) / 'z.db'
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
r0 = c.get('/my/audit-log', follow_redirects=False)
assert r0.status_code == 303 and r0.headers['location'] == '/login', r0.status_code
c.post('/login', data={'username':'a','password':'p'}, follow_redirects=False)
r1 = c.get('/my/audit-log')
assert r1.status_code == 200, r1.status_code
assert '감사 로그' in r1.text
print('route OK')
"
```

## AC 검증 방법

위 AC 1~2, 4~6이 모두 통과하면 `/tasks/4-my-audit-log/index.json`의 phase 2 status를 `"completed"`로 변경하라.
3번(e2e)은 통과/스킵 둘 다 허용. R5 가드나 이번 phase로 e2e가 명백히 깨진다면 원인을 특정 후 수정. chromium 미설치 등 환경 문제는 `notes`에 "e2e skipped due to env" 1줄 기록.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 index.json의 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- **mock 금지 / ORM 금지 / `time.monotonic` 패치 금지** (`docs/testing.md` 원칙).
- **템플릿에 필터/검색/정렬/페이지네이션 UI 추가 금지** (CTO 조건 1).
- **`/my/audit-log` 라우트에 `print()` / INSERT 금지** — 본인 조회는 감사 대상 아님.
- **`data-action` 속성은 행당 정확히 1회**. 이름/위치 변경 금지 — 테스트가 이 토큰에 카운트 의존.
- **WHERE 절의 3 OR 순서 변경 금지** — 가독성 + 리뷰 안정성. SQL 주석은 허용.
- **`ORDER BY ea.id DESC`**. `created_at` 기준 정렬 금지 (AUTOINCREMENT id = INSERT 순서 = 최신성 보장).
- **`MY_AUDIT_LOG_LIMIT = 100` 변경 금지**. 테스트가 이 상수를 import해 사용.
- **기존 테스트 파일 수정 금지**. 단, 본 phase의 변경으로 인한 regression이 발생한다면 원인 특정 후 최소 범위 수정 (예: 다른 테스트가 `export_audit` 테이블 존재를 모르고 `PRAGMA table_info(...)` 결과 길이에 의존했을 리는 없음 — 대부분은 문제 없음).
- **`app/main.py` 건드리지 마라**. `create_app()`에서 `init_db()`가 자동 호출되므로 별도 조치 불요.
- **`_insert_session_with_set`의 `session_id` + `set_index` 중복 주의**: 같은 session에 2개 세트를 넣을 때 `set_index`를 다르게. 현재 `test_my_export.py::_insert_session_with_set`은 항상 `set_index=0`으로 INSERT하므로 같은 member에 2번 호출하면 각기 다른 session_id가 생성되어 OK.
- **시나리오 #4의 `_login`/`_logout` 사이에 `state.*_last_ts` clear**를 반드시 각 호출 직전에 실행. 60초 rate limit에 걸려 429로 떨어지면 INSERT가 발생하지 않아 시나리오 가정이 무너진다.
- **시나리오 #7의 `ORDER BY ea.id DESC` 의존성**: AUTOINCREMENT id 기준 정렬이므로 INSERT 순서가 곧 최신성. `created_at` 문자열을 다양화하지만 정렬 기준은 id임을 주석으로 명시.
- **`sqlite3` row → dict 접근**: `conn.row_factory = sqlite3.Row` 가 `get_connection()`에서 이미 설정됨. `rows[0]["action"]` 스타일로 접근 가능.
- 테스트에서 직접 `sqlite3.connect(str(temp_db))`를 여는 경우 반드시 `try/finally close()` — SQLite file lock 회피.
