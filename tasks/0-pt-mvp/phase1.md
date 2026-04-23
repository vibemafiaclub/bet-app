# Phase 1: 프로젝트 스캐폴드 + 데이터 모델 + DB 초기화 + seed 스크립트

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/mission.md` — 프로젝트 mission
- `/docs/spec.md` — 이번 iteration의 명세 (데이터 모델, 운동 10종, 차트 데이터 계약 등)
- `/docs/testing.md` — 테스트 정책 (mock 금지, 실 SQLite)
- `/iterations/1-20260424_020912/requirement.md` — 요구사항 원문
- `/tasks/0-pt-mvp/docs-diff.md` — 이번 task의 문서 변경 기록 (Phase 0 산출물)

이전 phase 산출물:
- `/docs/spec.md`, `/docs/testing.md`, `/docs/user-intervention.md` (Phase 0 신규)

이전 phase에서 결정된 스펙을 꼼꼼히 읽고, 설계 의도를 이해한 뒤 작업하라.

## 작업 내용

### 1. 프로젝트 스캐폴드

루트에 `pyproject.toml`을 신규 작성하라:

```toml
[project]
name = "bet"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "itsdangerous>=2.2",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "playwright>=1.45",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**의존성 8개 외 추가 금지.** sqlalchemy, alembic, bcrypt, pytest-cov, factory_boy 등 도입 금지.

`.gitignore`에 다음 항목이 포함되어 있는지 확인하고, 없으면 **기존 내용을 유지한 채로 추가**:
```
data/
*.db
.venv/
.pytest_cache/
uv.lock
```
※ `uv.lock` 커밋 여부는 선택이지만, `uv sync` 실패 시 재시도 비용을 줄이기 위해 이 스프린트에서는 **gitignore 하지 않는다** → 위 줄에서 `uv.lock`만 빼고 나머지 4개만 추가. (이미 `iterations/**/*.log`, `__pycache__`, `node_modules`, `.omc` 은 있다.)

### 2. 패키지 초기화

- `app/__init__.py` — 빈 파일
- `app/exercises.py`:
  ```python
  EXERCISES: tuple[str, ...] = (
      "스쿼트", "벤치프레스", "데드리프트", "오버헤드프레스", "바벨로우",
      "풀업", "레그프레스", "랫풀다운", "레그컬", "덤벨컬",
  )
  ```
  ※ 정확히 이 10개. 순서 변경 허용, 철자 변경 불가.

- `app/db.py`:
  ```python
  import os
  import sqlite3
  from contextlib import contextmanager
  from pathlib import Path

  DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "./data/bet.db"))

  @contextmanager
  def get_connection(db_path: Path | None = None):
      """sqlite3 connection context manager. row_factory=Row, foreign_keys=ON."""
      ...

  def init_db(db_path: Path | None = None) -> None:
      """CREATE TABLE IF NOT EXISTS for 4 tables. Idempotent."""
      ...
  ```

  `init_db`가 생성할 스키마 — 정확히 이 컬럼/제약으로 박아라:
  ```sql
  CREATE TABLE IF NOT EXISTS trainers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS members (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      trainer_id INTEGER NOT NULL REFERENCES trainers(id),
      name TEXT NOT NULL,
      created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS pt_sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      member_id INTEGER NOT NULL REFERENCES members(id),
      session_date TEXT NOT NULL,
      created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS session_sets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id INTEGER NOT NULL REFERENCES pt_sessions(id),
      exercise TEXT NOT NULL CHECK(exercise IN (
          '스쿼트','벤치프레스','데드리프트','오버헤드프레스','바벨로우',
          '풀업','레그프레스','랫풀다운','레그컬','덤벨컬'
      )),
      weight_kg REAL NOT NULL CHECK(weight_kg > 0),
      reps INTEGER NOT NULL CHECK(reps > 0),
      set_index INTEGER NOT NULL
  );
  ```
  
  `get_connection` 내부에서 `PRAGMA foreign_keys=ON`을 실행하라. DB 경로의 부모 디렉토리(`data/`)가 없으면 `mkdir(parents=True, exist_ok=True)`.

- `app/aggregates.py`:
  ```python
  import sqlite3

  def max_weight_per_session(conn: sqlite3.Connection, member_id: int) -> list[dict]:
      """
      Returns:
        [
          {"session_date": "YYYY-MM-DD", "exercise": "스쿼트", "max_weight": 70.0},
          ...
        ]
      세션 날짜 오름차순, 같은 날짜 내에서는 exercise 이름 오름차순.
      """
      ...

  def total_volume_per_session(conn: sqlite3.Connection, member_id: int) -> list[dict]:
      """
      Returns:
        [
          {"session_date": "YYYY-MM-DD", "total_volume": 810.0},
          ...
        ]
      session 단위로 Σ(weight_kg × reps). 날짜 오름차순.
      동일 날짜에 세션이 2개면 각각 별도 row.
      """
      ...
  ```
  ※ 두 함수 모두 **순수 집계 함수**. I/O는 `conn` 인자로만 수행. 로깅 금지.

### 3. seed 스크립트

`scripts/seed.py` — 멱등 실행 가능. 실행 로직:

1. `app.db.init_db()` 호출
2. 트레이너 "김관장" 1명 확보 (있으면 재사용, 없으면 INSERT)
3. 회원 "회원A", "회원B", "회원C" 3명 확보 (트레이너에 속함)
4. 각 회원별 과거 4주 12세션 (주 3회) 더미 세트 데이터 생성. **이미 해당 member_id로 세션이 1개 이상 있으면 skip** (멱등).
5. 더미 데이터 패턴:
   - 회원A: 스쿼트/벤치프레스/데드리프트 주력, 매주 +2.5kg 점진
   - 회원B: 벤치프레스/오버헤드프레스/풀업 주력, 중량은 유지·횟수 증가 패턴
   - 회원C: 레그프레스/랫풀다운/레그컬 주력, 점진 증가
   - 각 세션당 3~4세트, 운동은 2~3종.
   - 날짜는 오늘(`2026-04-24`) 기준 역산해서 4주 전부터 오늘까지 분포.
6. 종료 시 stdout에 정확히 이 포맷으로 출력:
   ```
   TRAINER_ID=<int> MEMBER_IDS=<id1>,<id2>,<id3>
   ```
   (E2E 테스트가 이 줄을 parse한다.)

스크립트는 프로젝트 루트에서 `python scripts/seed.py` 로 실행되어야 한다. 환경변수 `DATABASE_PATH` 존중.

### 4. 단위 테스트

`tests/__init__.py` (빈 파일)과 `tests/conftest.py` 신규:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from app import db as db_module

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """각 테스트마다 별도 temp sqlite file + init_db 실행."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    db_module.init_db(db_path)
    yield db_path
```

`tests/test_aggregates.py` 신규 — 아래 케이스 포함 (CTO 조건부 조건 #1):

1. `test_empty_member_returns_empty_lists` — 세션 0건 회원 → 둘 다 빈 리스트
2. `test_max_weight_picks_heaviest_set` — 한 세션에 스쿼트 60x5, 60x5, 70x3 → max_weight[스쿼트]=70
3. `test_total_volume_sums_weight_times_reps` — 위 예시 → total_volume = 60·5 + 60·5 + 70·3 = 810
4. `test_labels_ascending_by_date` — 서로 다른 날짜 세션 2개 → 반환 순서가 날짜 오름차순
5. `test_check_constraint_rejects_negative_weight` — `INSERT INTO session_sets (..., weight_kg=-5, ...)` → `sqlite3.IntegrityError` raise (pytest.raises로 검증)
6. `test_check_constraint_rejects_unknown_exercise` — `exercise='풀라인업'` INSERT → `sqlite3.IntegrityError`

각 테스트는 `temp_db` fixture를 쓰고, 필요한 trainer/member/session/sets를 in-test로 INSERT해서 검증한다. (픽스처에 seed를 섞지 마라 — 집계 테스트는 명시적 입력으로만.)

## Acceptance Criteria

```bash
# 의존성 설치 (uv가 설치되어 있다면 uv sync, 아니면 pip)
if command -v uv >/dev/null 2>&1; then
  uv sync --extra dev
  RUN="uv run"
else
  python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
  RUN=""
fi

# init_db 동작
$RUN python -c "from app.db import init_db; init_db()"

# seed 멱등 (2회 실행 후에도 트레이너/회원 수가 1/3 유지)
$RUN python scripts/seed.py
$RUN python scripts/seed.py
$RUN python -c "
from app.db import get_connection
with get_connection() as c:
    assert c.execute('SELECT COUNT(*) FROM trainers').fetchone()[0] == 1
    assert c.execute('SELECT COUNT(*) FROM members').fetchone()[0] == 3
    # 세션 수는 1차 실행 때 생성된 양 그대로 유지되어야 함 (재실행 시 skip)
    sessions_1st = c.execute('SELECT COUNT(*) FROM pt_sessions').fetchone()[0]
    assert sessions_1st > 0
"

# 단위 테스트
$RUN pytest tests/test_aggregates.py -v
```

전부 exit 0이어야 통과.

## AC 검증 방법

위 커맨드를 순서대로 실행하라. 모두 통과하면 `/tasks/0-pt-mvp/index.json`의 phase 1 status를 `"completed"`로 변경하라.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- **ORM 금지.** `sqlalchemy`, `sqlmodel` 등 도입 금지. `sqlite3` 표준 라이브러리만.
- **import 위치 고정.** 테스트는 `from app.db import ...`, `from app.aggregates import ...` 형태로만 import. flat layout 금지.
- **운동 10종 확장 금지.** `EXERCISES` 튜플에 11번째 종목 추가하지 마라. CHECK 제약도 정확히 10개.
- **seed 재실행 시 중복 데이터 INSERT 금지.** 트레이너/회원/세션 모두 existence 체크 후 skip.
- **더미 데이터 날짜는 4주치만** — 너무 많으면 테스트가 느려진다. 회원당 12세션 범위 엄수.
- **파일럿용 단일 트레이너 가정.** 여러 트레이너 생성 로직 추가 금지.
- 기존 테스트를 깨뜨리지 마라 (현재 tests/ 디렉토리 비어있으므로 신규 생성).
- seed 스크립트의 stdout 포맷 정확히: `TRAINER_ID=1 MEMBER_IDS=1,2,3` — Phase 4 E2E가 정규식으로 파싱한다.
