# Phase 1: 공통 CSV 헬퍼 추출 + `/my/export/sessions.csv` 라우트 추가

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/mission.md` — 프로젝트 mission (수정 금지)
- `/docs/spec.md` — 최신 spec (Phase 0에서 `/my/export` 계약이 이미 추가됨). 특히 `## CSV Export` 섹션의 "관장 export" / "트레이너 본인 export" 2개 하위 섹션을 정확히 읽어라.
- `/docs/testing.md` — 테스트 정책
- `/tasks/2-my-export/docs-diff.md` — 이번 task의 문서 변경 기록 (Phase 0 완료 후 자동 생성됨)

그리고 이전 phase의 작업물을 반드시 확인하라:

- `/tasks/2-my-export/phase0.md` — Phase 0 작업 내용
- `/docs/spec.md` — 특히 `## 라우트 목록`, `## CSV Export`, `## 다음 스프린트 예약 티켓` 섹션이 Phase 0에서 개정됐다.

또한 **기존 코드의 구조**를 반드시 읽어라:

- `/app/routes.py` L218-289 — 기존 `/admin/export/sessions.csv` 라우트 (리팩터링 대상)
- `/app/main.py` L32 — `app.state.export_last_ts = {}` 초기화 위치
- `/app/auth.py` L37-49 — `is_authenticated`, `is_owner`, `current_user`, `login_required_redirect` 헬퍼 (재사용)

이전 phase에서 만들어진 코드를 꼼꼼히 읽고, 설계 의도를 이해한 뒤 작업하라.

## 작업 내용

이 phase의 목표:
1. 기존 `/admin/export/sessions.csv` 라우트의 SELECT + `csv.writer` 로직을 module-level private 헬퍼로 추출.
2. 신규 `/my/export/sessions.csv` 라우트 추가.
3. `app.state.my_export_last_ts` dict 초기화 추가.

### 1. `app/routes.py` 상단에 module-level 헬퍼 추가

파일 상단 import 블록 아래, `register_routes` 함수 앞에 아래 구조의 private 상수 + 함수를 추가하라:

```python
_SESSIONS_CSV_COLUMNS = (
    "session_date",
    "member_name",
    "exercise",
    "weight_kg",
    "reps",
    "set_index",
    "input_trainer_name",
)


def _write_sessions_csv(conn, trainer_id_filter, buffer) -> int:
    """세션 row들을 CSV 포맷으로 buffer에 쓴다 (BOM 없음).

    `trainer_id_filter`가 None이면 전체 세션, 정수면 해당 trainer_id의 input 세션만.
    반환값은 header row를 **제외한** data row 수 (감사 로그 `rows=N` 용).

    관장 export(`/admin/export/sessions.csv`)와 본인 export(`/my/export/sessions.csv`)
    양쪽이 이 함수를 공유하여 컬럼 drift를 코드 레벨에서 차단한다.
    헤더 row와 data row 모두 `_SESSIONS_CSV_COLUMNS` 단일 상수를 참조한다.
    """
    # 1. writer = csv.writer(buffer)
    # 2. writer.writerow(_SESSIONS_CSV_COLUMNS)  # 헤더
    # 3. SELECT 쿼리:
    #    SELECT ps.session_date, m.name AS member_name,
    #           ss.exercise, ss.weight_kg, ss.reps, ss.set_index,
    #           COALESCE(t.name, '') AS input_trainer_name
    #    FROM session_sets ss
    #    JOIN pt_sessions ps ON ss.session_id = ps.id
    #    JOIN members m ON ps.member_id = m.id
    #    LEFT JOIN trainers t ON ps.input_trainer_id = t.id
    #    [WHERE ps.input_trainer_id = ?]   -- trainer_id_filter가 not None일 때만
    #    ORDER BY ps.session_date, ps.id, ss.set_index
    # 4. 각 row마다 writer.writerow(tuple(row[c] for c in _SESSIONS_CSV_COLUMNS))
    # 5. return data_row_count
```

**핵심 규칙**:
- 컬럼명 리스트는 `_SESSIONS_CSV_COLUMNS` 하나에서만 정의. 헤더 writerow, data writerow 둘 다 이 상수를 참조할 것. 두 곳에 문자열 리스트를 따로 하드코딩하면 drift 방지 목적이 무너진다.
- data row 작성 시 `row[column_name]` 방식(sqlite3 Row에 key 접근) 사용. 인덱스 접근 금지 (컬럼 순서 바뀌면 깨짐).
- 반환값은 **헤더 제외 data row 수**.
- BOM 접두는 **라우트**에서 처리. 이 함수는 순수 CSV만 쓴다.

### 2. 기존 `/admin/export/sessions.csv` 라우트 리팩터링 (`app/routes.py` L218-289)

기존 라우트의 내부 로직 중 SELECT + writerow 부분을 제거하고 헬퍼 호출로 교체하라. 유지해야 하는 부분:

- 인증 검증 (`is_authenticated` + `is_owner`)
- rate limit (`app.state.export_last_ts`, 60초, 429)
- `buf = io.StringIO()` 버퍼 준비
- `_write_sessions_csv(conn, trainer_id, buf)` 호출 → rows_count 수신
- BOM 접두 (`csv_content = "﻿" + buf.getvalue()`)
- 파일명: `sessions_YYYYMMDD.csv` (trainer_id 있을 시 `sessions_YYYYMMDD_trainer_<id>.csv`)
- 감사 로그: `print(f"[export] owner_id={owner_id} target_trainer_id={trainer_id if trainer_id is not None else 'all'} rows={rows_count}", flush=True)`
- `export_last_ts[owner_id] = time.monotonic()` (감사 로그 **이후**)
- `Content-Disposition: attachment; filename="<name>"` 헤더

리팩터링 결과 기존 SELECT + writerow 2버전 코드(30줄 가량)가 `rows_count = _write_sessions_csv(conn, trainer_id, buf)` 1줄로 축소된다. `csv.writer` import 는 헬퍼에서 사용하므로 파일 상단 import 유지.

### 3. `/my/export/sessions.csv` 신규 라우트 추가

기존 관장 export 라우트 바로 **아래**에 신규 라우트를 추가하라. 시그니처:

```python
@app.get("/my/export/sessions.csv")
async def get_my_export_sessions(request: Request):
    # 1. is_authenticated 체크 → 아니면 login_required_redirect()
    # 2. trainer_id = current_user(request)["trainer_id"]
    # 3. rate limit: app.state.my_export_last_ts[trainer_id], 60초, 429
    # 4. buf = io.StringIO()
    # 5. with get_connection() as conn:
    #        rows_count = _write_sessions_csv(conn, trainer_id, buf)
    # 6. csv_content = "﻿" + buf.getvalue()
    # 7. filename = f"my_sessions_{date.today().strftime('%Y%m%d')}.csv"
    # 8. print(f"[my-export] trainer_id={trainer_id} rows={rows_count}", flush=True)
    # 9. request.app.state.my_export_last_ts[trainer_id] = time.monotonic()   # stdout 이후
    # 10. return Response(content=csv_content.encode("utf-8"),
    #                     media_type="text/csv; charset=utf-8",
    #                     headers={"Content-Disposition": f'attachment; filename="{filename}"'})
```

**중요**:
- `is_owner` 체크 **없음**. 관장도 본인 자격으로 호출 가능. 관장이 호출해도 관장 본인의 `trainer_id` row만 반환된다(헬퍼가 고정 필터링하므로).
- `trainer_id` 쿼리 파라미터 받지 않음. 경로 시그니처에 인자 없음.
- 429 body는 기존 관장 export와 동일한 `"Too Many Requests: retry in 60s"` plain text.
- 감사 로그는 `[my-export]` prefix. 관장 `[export]` prefix와 반드시 구분.

### 4. `app/main.py` 수정

L32 `app.state.export_last_ts = {}` 바로 아래에 1줄 추가:

```python
app.state.my_export_last_ts = {}
```

이 dict는 `create_app()` 호출마다 빈 dict로 초기화된다(기존 `export_last_ts`와 동일 패턴, 테스트 격리성 유지).

### 5. 기타 건드리지 말 것

- `app/auth.py`, `app/db.py`, `app/aggregates.py`, `app/exercises.py`, `app/templates/` — 변경 금지
- `scripts/` — 변경 금지
- `tests/` — **Phase 2에서 처리**. 이 phase에서 테스트 파일 생성하지 마라.
- `pyproject.toml`, `fly.toml`, `Dockerfile` — 변경 금지
- `docs/` — Phase 0에서 이미 완료. 이 phase에서 건드리지 마라.

## Acceptance Criteria

아래 커맨드를 순서대로 실행해서 전부 exit 0이어야 한다.

```bash
# 1. 기존 test_export.py 7케이스 전원 green (리팩터링 안전망 — CTO 조건 2)
uv run pytest tests/test_export.py -x -q

# 2. 전체 기존 테스트 suite green (regression 없음)
uv run pytest tests/ --ignore=tests/test_e2e_dashboard.py -x -q

# 3. 신규 라우트가 실제로 등록됐는지 + rate limit dict가 초기화됐는지
uv run python -c "
import os
os.environ['APP_SESSION_SECRET'] = 'x'*32
os.environ['ADMIN_USERNAME'] = 'admin'
os.environ['ADMIN_PASSWORD'] = 'pw'
os.environ['DATABASE_PATH'] = '/tmp/bet_phase1_smoke.db'
import pathlib
pathlib.Path('/tmp/bet_phase1_smoke.db').unlink(missing_ok=True)
from app.main import create_app
app = create_app()
# 라우트 등록 확인
paths = {r.path for r in app.routes if hasattr(r, 'path')}
assert '/my/export/sessions.csv' in paths, f'라우트 누락: {sorted(paths)}'
# state dict 초기화 확인
assert hasattr(app.state, 'my_export_last_ts'), 'my_export_last_ts 미초기화'
assert app.state.my_export_last_ts == {}, 'my_export_last_ts가 빈 dict가 아님'
# 헬퍼 + 상수 노출 확인
from app.routes import _write_sessions_csv, _SESSIONS_CSV_COLUMNS
assert _SESSIONS_CSV_COLUMNS == (
    'session_date', 'member_name', 'exercise', 'weight_kg', 'reps', 'set_index', 'input_trainer_name'
)
print('OK')
"

# 4. 헬퍼가 실제로 호출자 2곳에서 공유되는지 문자열 검색
grep -c '_write_sessions_csv(' app/routes.py | grep -q '^[3-9]'  # 정의 1회 + 호출 2회 = 최소 3번 등장
```

## AC 검증 방법

위 AC 커맨드를 순서대로 실행하라. 전부 exit 0이면 `/tasks/2-my-export/index.json`의 phase 1 status를 `"completed"`로 변경하라.

수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고 `"error_message"` 필드에 원인을 기록하라.

## 주의사항

- **컬럼명은 `_SESSIONS_CSV_COLUMNS` 단일 상수에서만 정의.** 헤더 writerow / data writerow / (선택적) 다른 참조 모두 이 상수를 사용. 문자열 리스트를 두 곳에 별도로 하드코딩하지 마라 — 이게 CTO 조건 1의 핵심.
- **rate limit dict는 물리 분리.** `export_last_ts`와 `my_export_last_ts`는 서로 다른 dict. 합치거나 튜플 키로 공유하지 마라.
- **is_owner 체크 금지** in `/my/export/sessions.csv`. `is_authenticated`만. 관장도 본인 자격으로 호출 가능해야 한다.
- **`trainer_id` 쿼리 파라미터 받지 않음.** `/my/export/sessions.csv?trainer_id=99` 같은 형태로 다른 사람 데이터 추출 가능하게 만들지 마라.
- BOM은 라우트에서 처리. 헬퍼 함수는 순수 CSV만 쓴다. 헬퍼 안에서 `"﻿"`를 쓰면 관장/본인 양쪽 응답에 BOM이 중복 추가된다.
- 감사 로그 prefix는 `[my-export]`. `[export]`와 다르다. 테스트가 이걸 강제한다.
- `my_export_last_ts[trainer_id] = time.monotonic()`는 stdout 로그 **이후**에 업데이트. 기존 관장 export와 동일 패턴.
- `tests/` 디렉토리 변경 금지. Phase 2에서 테스트 파일을 신규 생성한다.
- 기존 테스트를 깨뜨리지 마라 (tests/test_export.py 7케이스 + 전체 suite).
- `date.today()` import는 기존 `routes.py`에 이미 있음. 추가 import 불필요.
