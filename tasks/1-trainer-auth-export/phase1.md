# Phase 1: DB 마이그레이션 + 시드/백필 스크립트

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/mission.md` — 프로젝트 mission (수정 금지)
- `/docs/spec.md` — **iteration 2 개정된 단일 명세** (이번 phase의 truth of source)
- `/docs/testing.md` — 테스트 정책
- `/docs/user-intervention.md` — 운영 개입 지점 (백필/계정 교체 SQL 절차 포함)
- `/iterations/2-20260424_034244/requirement.md` — 전체 요구사항
- `/tasks/1-trainer-auth-export/docs-diff.md` — 이번 task의 문서 변경 기록 (자동 생성)

이전 phase(`phase0`)에서 문서만 수정되었다. 코드는 아직 iteration 1 상태. 먼저 다음 기존 코드를 꼼꼼히 읽어 설계 의도를 파악하라:

- `/app/db.py` — 4개 테이블 CREATE + foreign_keys ON
- `/app/auth.py` — 기존 env 기반 compare_digest
- `/app/main.py` — REQUIRED_ENV 검증 + init_db + SessionMiddleware + register_routes
- `/scripts/seed.py` — 기존 "김관장" + 회원 A/B/C + 세션 12주치 시드
- `/tests/conftest.py` — temp_db, client, authed_client, live_server fixture

이번 phase는 **DB/시드 계층만** 건드린다. 라우트/인증/로그인 흐름은 Phase 2에서.

## 작업 내용

### 1. `/app/db.py` 마이그레이션 확장

기존 `init_db()`의 `CREATE TABLE IF NOT EXISTS` 블록은 그대로 유지하고, 그 뒤에 **idempotent ALTER TABLE** 블록을 추가하라.

시그니처:
```python
def init_db(db_path: Path | None = None) -> None:
    ...  # 기존 CREATE TABLE 블록 유지
    _migrate_iteration2(conn)  # 신규 호출
```

`_migrate_iteration2(conn)` 구현 요건:

1. `trainers` 테이블에 다음 컬럼을 누락 시에만 ADD (PRAGMA table_info로 체크):
   - `username TEXT` (UNIQUE는 ALTER TABLE ADD로 직접 못 붙이므로, 컬럼 ADD 후 `CREATE UNIQUE INDEX IF NOT EXISTS idx_trainers_username ON trainers(username) WHERE username IS NOT NULL`)
   - `password_hash TEXT`
   - `is_owner INTEGER NOT NULL DEFAULT 0`

2. `pt_sessions` 테이블에 다음 컬럼을 누락 시에만 ADD:
   - `input_trainer_id INTEGER REFERENCES trainers(id)` (NULL 허용)

3. 멱등성: `init_db()`를 2회 호출해도 오류 없이 동일 스키마가 유지되어야 한다.

구현 가이드:
- PRAGMA 체크는 `conn.execute("PRAGMA table_info(trainers)").fetchall()`로 컬럼 이름 set을 얻고 `if "username" not in cols: conn.execute("ALTER TABLE ... ADD COLUMN ...")` 패턴.
- ALTER TABLE은 UNIQUE 제약을 거는 방식에 한계가 있으므로, `username` UNIQUE는 **partial index**로 해결 (`WHERE username IS NOT NULL` — 초기 NULL 여러 개 공존 허용, 비-NULL은 유일).

### 2. `/app/auth.py`에 해싱 함수 신규 추가

이번 phase에서는 해싱 유틸만 추가하고, `verify_credentials` / `is_authenticated` 등 기존 함수는 **Phase 2에서 교체**하므로 건드리지 마라 (단 import 충돌만 피하면 됨).

추가할 함수 시그니처:
```python
def hash_password(password: str) -> str:
    """scrypt 기반 해싱. 포맷: 'scrypt$<salt_hex>$<hash_hex>'.
    파라미터: n=16384, r=8, p=1, dklen=64, salt 16바이트 os.urandom."""

def verify_password(password: str, stored: str) -> bool:
    """stored가 'scrypt$<salt_hex>$<hash_hex>' 포맷이면 scrypt 재계산 후 secrets.compare_digest.
    포맷이 다르거나 None이면 False."""
```

구현 가이드:
- `hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=64)`.
- `salt = os.urandom(16)`, 저장 포맷은 `f"scrypt${salt.hex()}${hash.hex()}"`.
- `verify_password`에서 splitting 시 `stored.split("$")` 길이 3 아니면 False. `algo != "scrypt"` 여도 False.
- `passlib` / `bcrypt` 등 외부 의존 import 금지.

### 3. `/scripts/seed_trainer.py` 신규 작성

CLI (argparse):
- `--name` (필수, str, 트레이너 표시 이름)
- `--username` (필수, str, 로그인 ID)
- `--password` (필수, str, 평문, 내부에서 해싱)
- `--owner` (optional flag, 지정 시 해당 계정을 유일 관장으로 설정)

동작:
1. `app.db.init_db()` 호출로 DB 및 iteration 2 스키마 보장.
2. 기존 username 조회:
   - 존재: `UPDATE trainers SET name=?, password_hash=hash_password(password) WHERE username=?`. 이를 "upsert (password reset 포함)"로 처리.
   - 없음: `INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 0, ?)`.
3. `--owner` 플래그가 주어지면:
   - 먼저 `SELECT id, name, username FROM trainers WHERE is_owner=1 AND username != ?`로 기존 관장 목록 조회.
   - `UPDATE trainers SET is_owner=0` (전체 관장 해제)
   - `UPDATE trainers SET is_owner=1 WHERE username=?`
   - stdout에 `[seed_trainer] is_owner transferred: demoted={<기존 관장 username 목록>} promoted={해당 username}` 형태로 1줄 출력 (투명성).
4. 성공 시 stdout: `[seed_trainer] username={u} is_owner={0|1} created={True|False}`.

에러 처리:
- 비어있는 `--password` → argparse에서 `type=lambda s: s or (_ for _ in ()).throw(argparse.ArgumentTypeError(...))` 등으로 거부 or 간단히 `if not args.password: raise SystemExit("--password required")`.
- DB 연결 에러는 그대로 raise (예외는 stderr로 전파).

파일 상단:
```python
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db, get_connection
from app.auth import hash_password
```

### 4. `/scripts/backfill_input_trainer.py` 신규 작성

CLI: 인자 없음.

동작:
1. `init_db()` 호출.
2. 관장(trainer_id) 결정 로직:
   - env `ADMIN_USERNAME`을 읽는다. 설정되어 있고 trainers 테이블에 해당 username의 `is_owner=1` row가 있으면 그 trainer_id 사용.
   - 없으면 `SELECT id FROM trainers WHERE is_owner=1 ORDER BY id LIMIT 1`로 첫 번째 is_owner=1을 사용.
   - 관장 0명이면 **exit 1**, stderr에 다음 메시지 출력:
     ```
     [backfill] ERROR: no is_owner=1 trainer exists.
       Run `uv run python -m scripts.seed_trainer --name "관장이름" --username <u> --password <pw> --owner` first.
     ```
3. `UPDATE pt_sessions SET input_trainer_id=? WHERE input_trainer_id IS NULL` 실행.
4. stdout: `[backfill] updated={N} rows (owner_trainer_id={id})`.
5. 멱등성: 2회 실행 시 두 번째 호출은 `updated=0`.

### 5. `/scripts/seed.py` 확장 (엣지 케이스 해결)

**목적**: 기존 e2e 테스트의 `live_server` fixture가 `seed.py` 실행 후 uvicorn을 기동하는데, seed.py가 "김관장"을 username 없이 넣으면 `ensure_owner_seed`가 별도 트레이너를 만들어 trainer_id 충돌이 난다. 이를 막으려면 seed.py가 env를 읽어 username/password_hash/is_owner=1까지 채워야 한다.

수정:
- `main()` 상단에 env 읽기:
  ```python
  admin_username = os.environ.get("ADMIN_USERNAME")
  admin_password = os.environ.get("ADMIN_PASSWORD")
  ```
- 기존 `INSERT INTO trainers (name, created_at) VALUES (?, ?)` 부분을 다음 로직으로 대체:
  - `name = admin_username or "admin"` (이름 대신 username을 표시 이름으로 재사용. 요구사항이 "관장 1명 + 이름" 구분을 요구하지 않으므로 단순화).
  - username 파라미터가 있으면 `INSERT ... (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 1, ?)` (password_hash는 admin_password가 있을 때만 hash_password(admin_password), 없으면 NULL).
  - **CTO 조건부 조건 5번**: `ADMIN_PASSWORD` 미설정 시 password_hash에 fallback을 박지 마라. NULL로 두고 나중에 ensure_owner_seed가 env 기반으로 채우도록 설계.
  - 기존 "김관장" row가 이미 존재하는 경우 (iteration 1 DB에서 올라온 케이스): UPDATE로 `username=?, is_owner=1`를 채우고, password_hash는 현재 값이 NULL일 때만 admin_password 기반으로 채움.
- admin_username 미설정 시 stdout 경고:
  ```
  [seed.py] WARN: ADMIN_USERNAME not set, using fallback 'admin' for trainer.username.
  [seed.py] WARN: ADMIN_PASSWORD not set — password_hash left NULL. ensure_owner_seed will fill it on app boot based on env.
  ```
- 기존 "김관장" 하드코딩 이름 대신 env를 우선하고, 없으면 "admin"으로 fallback. 기존 테스트(`test_log_routes`에서 "트레이너1"을 직접 INSERT하는 케이스는) 영향 없음.
- 기존 MEMBER_A_SESSIONS 등의 회원 시드 로직은 **그대로 유지**. 단 `trainer_id`를 찾는 SELECT 쿼리는 name 기반에서 username 기반 또는 `is_owner=1` 기반으로 바꿔야 한다:
  - 기존: `SELECT id FROM trainers WHERE name=?` (김관장)
  - 변경: `SELECT id FROM trainers WHERE is_owner=1 ORDER BY id LIMIT 1`로 조회해서 trainer_id 얻기.
  - 회원 이름은 "회원A/B/C" 그대로 유지.

### 6. `app/db.py`의 상수 변경 없음

`DATABASE_PATH` 기본 경로(`./data/bet.db`)는 그대로 유지.

## Acceptance Criteria

```bash
# 1) 코드 컴파일 확인
uv run python -c "from app.db import init_db; from app.auth import hash_password, verify_password; print('imports ok')"

# 2) 빈 DB에서 마이그레이션 실행
rm -rf /tmp/bet_phase1_test
mkdir -p /tmp/bet_phase1_test
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -c "
from app.db import init_db, get_connection
init_db()
init_db()  # 멱등성 검증
with get_connection() as c:
    cols_t = {r[1] for r in c.execute('PRAGMA table_info(trainers)').fetchall()}
    cols_s = {r[1] for r in c.execute('PRAGMA table_info(pt_sessions)').fetchall()}
    assert 'username' in cols_t, cols_t
    assert 'password_hash' in cols_t, cols_t
    assert 'is_owner' in cols_t, cols_t
    assert 'input_trainer_id' in cols_s, cols_s
    idx = [r[1] for r in c.execute('PRAGMA index_list(trainers)').fetchall()]
    assert any('username' in i for i in idx), idx
print('migration ok')
"

# 3) 해싱 왕복 검증
uv run python -c "
from app.auth import hash_password, verify_password
h = hash_password('hello')
assert h.startswith('scrypt\$')
assert verify_password('hello', h) is True
assert verify_password('wrong', h) is False
assert verify_password('hello', 'garbage') is False
assert verify_password('hello', None) is False
print('hash ok')
"

# 4) seed_trainer 스크립트 동작
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -m scripts.seed_trainer --name "관장" --username owner1 --password pw1 --owner
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -m scripts.seed_trainer --name "트레이너A" --username trA --password pwA
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -c "
from app.db import get_connection
with get_connection() as c:
    rows = c.execute('SELECT username, is_owner, password_hash IS NOT NULL AS has_pw FROM trainers ORDER BY username').fetchall()
    d = {r['username']: (r['is_owner'], r['has_pw']) for r in rows}
    assert d['owner1'] == (1, 1), d
    assert d['trA'] == (0, 1), d
print('seed_trainer ok')
"
# 관장 교체 로그
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -m scripts.seed_trainer --name "트레이너A 승격" --username trA --password pwA2 --owner 2>&1 | grep -q 'is_owner transferred'

# 5) 백필 스크립트
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -c "
from app.db import init_db, get_connection
init_db()
with get_connection() as c:
    cur = c.execute('INSERT INTO members (trainer_id, name, created_at) VALUES (1, \"회원\", \"2026-01-01\")')
    mid = cur.lastrowid
    c.execute('INSERT INTO pt_sessions (member_id, session_date, created_at, input_trainer_id) VALUES (?, \"2026-04-01\", \"2026-04-01T00:00\", NULL)', (mid,))
    c.execute('INSERT INTO pt_sessions (member_id, session_date, created_at, input_trainer_id) VALUES (?, \"2026-04-02\", \"2026-04-02T00:00\", NULL)', (mid,))
"
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -m scripts.backfill_input_trainer | tee /tmp/bet_phase1_test/backfill.out
grep -q 'updated=2 rows' /tmp/bet_phase1_test/backfill.out
# 멱등성
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -m scripts.backfill_input_trainer | grep -q 'updated=0 rows'

# 6) 백필 관장 부재 시 exit 1
rm /tmp/bet_phase1_test/bet.db
DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -c "from app.db import init_db; init_db()"
! DATABASE_PATH=/tmp/bet_phase1_test/bet.db uv run python -m scripts.backfill_input_trainer 2>/tmp/bet_phase1_test/err.out
grep -q 'no is_owner=1 trainer' /tmp/bet_phase1_test/err.out

# 7) 기존 테스트 수트는 이 phase에서 아직 돌지 않음 (auth.py의 verify_credentials가 아직 기존 env 방식 그대로라서 회귀 없음)
uv run pytest tests/test_aggregates.py -q  # iteration 1 aggregates 단위 테스트만 일단 통과 확인
```

## AC 검증 방법

위 AC 커맨드들을 순서대로 실행하라. **전부 exit 0**이어야 한다.

- 성공 시 `/tasks/1-trainer-auth-export/index.json`의 phase 1 status를 `"completed"`로 변경하라.
- 실패 시 해당 모듈을 수정하고 재시도. 3회 이상 실패 시 status를 `"error"`로 변경하고 `"error_message"`에 원인을 기록하라.

## 주의사항

- **auth.py의 기존 함수 (`verify_credentials`, `is_authenticated`, `login_required_redirect`) 삭제·수정 금지**. 이번 phase에서 추가만 하고, 교체는 Phase 2가 담당. 교체를 미리 하면 라우트가 부팅 시 깨져서 AC까지 못 간다.
- **main.py 수정 금지** — ensure_owner_seed 호출은 Phase 2에서.
- **기존 테스트를 깨뜨리지 마라**. 특히 `tests/conftest.py`의 `live_server` fixture가 `scripts/seed.py`를 서브프로세스로 돌리는데, seed.py가 env 없이도 크래시하지 않고 fallback으로 동작해야 한다.
- scripts/seed.py의 MEMBER_*_SESSIONS 세션 데이터는 **절대 수정 금지**. trainer_id 조회 방식만 is_owner 기반으로 바꿔라.
- scripts/seed.py에서 `hash_password` import 시 env 읽기 순서에 주의 — module-top-level에서 env를 읽고 `hash_password(None)`을 호출하는 실수가 없도록 `main()` 함수 내에서만 env 접근.
- seed_trainer.py의 `--owner`는 파괴적이므로 (기존 관장 demote), stdout 로그는 **반드시** `is_owner transferred` 문구를 포함해야 한다 — CTO 조건의 "소리 없이 덮지 마라" 이행.
- backfill 스크립트는 멱등해야 한다. `WHERE input_trainer_id IS NULL` 조건 유지로 자동 달성.
- bcrypt/passlib/cryptography 같은 외부 해싱 라이브러리 import 금지 — pyproject.toml 변경도 금지.
- scripts/seed_trainer.py의 `--password` 값은 argparse 기본 처리로 shell 인자에 그대로 노출된다. shell history 회피는 운영자 책임이고 user-intervention.md에 명시되어 있음.
- 마이그레이션이 실패하면 DB가 부분 상태에 빠진다 — `init_db()`는 단일 트랜잭션 내에서 모든 ALTER가 성공해야 commit. 기존 `get_connection` 컨텍스트가 트랜잭션을 커버하므로 `_migrate_iteration2(conn)`를 같은 conn 범위에서 호출하면 자동 처리됨.
