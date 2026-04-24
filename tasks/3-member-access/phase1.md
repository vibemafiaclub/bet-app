# Phase 1: guard-impl

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` (iter 5 반영본 — Phase 0에서 업데이트됨. 트레이너간 회원 접근 격리 섹션 + 인증 섹션 + CSV Export 섹션 전체)
- `/docs/testing.md` (테스트 원칙 — mock 금지, tmp_path SQLite only)
- `/tasks/3-member-access/docs-diff.md` (이번 task의 Phase 0 docs 변경 diff)
- `/iterations/5-20260424_104337/requirement.md` (요구사항 원문. 특히 "구현 스케치" 섹션 1~7)

그리고 이전 phase의 작업물을 반드시 확인하라:

- Phase 0에서 수정된 `docs/spec.md` 99~103행 + 113행 + "다음 스프린트 예약 티켓" 섹션
- Phase 0에서 수정된 `docs/testing.md` "테스트 구성" 섹션

현 코드 베이스를 꼼꼼히 읽고 이해하라:

- `/app/auth.py` — 기존 `is_authenticated`, `is_owner`, `current_user`, `login_required_redirect`, `verify_credentials` 헬퍼 구조
- `/app/routes.py` — 106~126행 `GET /`, 128~149행 `GET /log`, 151~211행 `POST /log`, 213~250행 `GET /chart-data.json`, 252~267행 `GET /dashboard`. 각 라우트는 현재 `is_authenticated` 체크 후 `members WHERE id=? AND trainer_id=?` 조합으로 존재 검증(잘못된 조합 → 404). **R5 가드는 아직 없음.**
- `/app/db.py` — `get_connection()` context manager, `init_db()`는 iter 2 마이그레이션 포함

## 작업 내용

이번 phase는 **서버사이드 회원 접근 격리 가드 구현**이다. 파일 2개만 수정한다: `app/auth.py`, `app/routes.py`.

### 1. `app/auth.py`에 `require_member_access` 헬퍼 추가

파일 하단 기존 `ensure_owner_seed()` 아래에 새 함수로 추가하라. 타입 힌트 import로 `sqlite3`를 (필요 시) 추가하라 (현재는 import 없음 — 타입 어노테이션에만 사용하므로 `from __future__ import annotations` 대신 `import sqlite3` 한 줄 추가).

시그니처:

```python
def require_member_access(
    request: Request,
    conn: sqlite3.Connection,
    tid: int,
    mid: int,
) -> tuple[bool, int | None, sqlite3.Row | None]:
    """회원 접근 권한 및 URL 정합성 검사.

    반환값 (ok, status, member_row):
    - (False, None, None): 비인증. 호출측은 login_required_redirect() 반환.
    - (False, 404, None): mid 부재 or URL tid 불일치 (URL 위조 방지, 관장 포함).
    - (False, 403, None): mid 존재 + tid 일치 + 비관장 + 타인 소유.
    - (True, None, row): 통과. 관장 bypass 또는 본인 소유.

    row는 members 테이블의 id, trainer_id, name 3컬럼 sqlite3.Row.
    """
```

로직 순서 (정확히 이 순서로 판정):

1. `is_authenticated(request)` False → `(False, None, None)`
2. `row = conn.execute("SELECT id, trainer_id, name FROM members WHERE id=?", (mid,)).fetchone()` — 와일드카드(`SELECT *`) **금지**.
3. `row is None` → `(False, 404, None)`
4. `row["trainer_id"] != tid` → `(False, 404, None)` — 관장 여부와 무관. URL 위조 차단.
5. `is_owner(request)` True → `(True, None, row)` — 관장 bypass (tid 일치 전제)
6. `row["trainer_id"] == current_user(request)["trainer_id"]` → `(True, None, row)`
7. 나머지 → `(False, 403, None)`

### 2. `app/routes.py`의 4개 라우트에 가드 적용

신규 import 추가: `from fastapi.responses import PlainTextResponse` — 기존 `HTMLResponse, JSONResponse, RedirectResponse, Response` 줄에 이어붙여라. 그리고 `from app.auth import ...`에 `require_member_access`를 추가.

공통 가드 블록 (각 라우트의 진입 최전방에 삽입):

```python
with get_connection() as conn:
    ok, status, member = require_member_access(request, conn, tid, mid)
    if not ok:
        if status is None:
            return login_required_redirect()
        if status == 403:
            return PlainTextResponse("forbidden", status_code=403)
        return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
    # 이 아래부터 라우트 고유 로직 (member, conn 재사용)
```

**라우트별 적용 가이드:**

#### a) GET `/trainers/{tid}/members/{mid}/log` (128~149행)

- 기존 `is_authenticated` 체크 + 기존 `SELECT ... WHERE id=mid AND trainer_id=tid` 조회를 **전부 제거**하고 위 공통 가드 블록으로 대체.
- 가드 통과 후 `conn`은 이미 close되므로(`with get_connection()` 블록 종료 시), 템플릿 렌더링은 블록 밖에서 진행하거나 블록 내부로 옮겨라. **추천: 가드 블록 안에서 템플릿 컨텍스트까지 구성 후 return.**
- `member["name"]`을 사용하여 기존과 동일한 렌더링 컨텍스트 생성.

#### b) POST `/trainers/{tid}/members/{mid}/log` (151~211행)

- **가드는 `await request.form()` 전에 배치**. 403/404 시 INSERT 시도 0건이 보장되어야 한다 (CTO 조건 4).
- 가드 블록은 form 파싱 전 최상단에 배치하되, `with get_connection()` 블록을 열고 검사만 수행 후 블록을 닫는 패턴 허용. 실제 INSERT는 기존대로 별도 `with get_connection()` 블록에서 수행 (2-conn 패턴).
- 가드 통과 후 기존 form 파싱, validation, INSERT 로직을 그대로 유지.

#### c) GET `/trainers/{tid}/members/{mid}/chart-data.json` (213~250행)

- 기존 `is_authenticated` 체크 + 기존 `SELECT ... WHERE id=mid AND trainer_id=tid` 조회를 제거하고 공통 가드 블록으로 대체.
- 가드 통과 후 동일 `conn`에서 `max_weight_per_session(conn, mid)`, `total_volume_per_session(conn, mid)` 호출 유지.
- JSONResponse 반환 형식(`"member": {"id": member["id"], "name": member["name"]}`) 동일.

#### d) GET `/trainers/{tid}/members/{mid}/dashboard` (252~267행)

- 동일 패턴. `member["name"]`을 템플릿 컨텍스트로 전달.

### 3. `GET /` redirect 로직 변경 (106~126행)

기존 코드를 다음 로직으로 재작성:

- `is_authenticated(request)` False → `login_required_redirect()`.
- `is_owner(request)` True:
    - 기존 로직 유지. `SELECT id FROM trainers ORDER BY id LIMIT 1` → `SELECT id FROM members WHERE trainer_id=? ORDER BY id LIMIT 1` → redirect. seed 안 된 상태는 기존 `HTMLResponse("<p>seed를 실행하세요</p>")` 유지.
- `is_owner(request)` False (일반 트레이너):
    - `user = current_user(request)`; `self_tid = user["trainer_id"]`.
    - `SELECT id FROM members WHERE trainer_id=? ORDER BY id LIMIT 1` (`self_tid`).
    - 있으면 → `RedirectResponse(url=f"/trainers/{self_tid}/members/{mid}/log", status_code=303)`.
    - 없으면 → `HTMLResponse("<p>담당 회원이 아직 없습니다. 관장에게 요청하세요.</p>", status_code=200)`.

## Acceptance Criteria

```bash
# 1. 문법 / import 체크
uv run python -c "from app.auth import require_member_access; from app.routes import register_routes; print('OK')"

# 2. 기존 테스트가 깨지지 않는지 full regression
uv run pytest tests/test_aggregates.py tests/test_auth.py tests/test_log_routes.py tests/test_dashboard.py tests/test_export.py tests/test_my_export.py -x

# 3. Playwright e2e는 환경이 갖춰진 경우에만 실행 (실패 시 환경 문제일 가능성 → 스킵 허용)
uv run pytest tests/test_e2e_dashboard.py || echo "e2e skip ok"
```

## AC 검증 방법

위 AC 커맨드를 실행하라. 1~2번이 모두 통과하면 `/tasks/3-member-access/index.json`의 phase 1 status를 `"completed"`로 변경하라.
3번(e2e)은 환경 의존적이므로 통과/스킵 둘 다 허용. 실패가 명백히 R5 가드 때문이면 수정 후 재시도.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 index.json의 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- **DB 마이그레이션 금지**. `members.trainer_id`가 iter 1부터 owner FK로 작동하므로 스키마 변경 불요. `init_db()`나 `app/db.py`를 건드리지 마라.
- **테스트 파일 수정 금지**. 이번 phase는 `app/auth.py`, `app/routes.py`만 수정. `tests/test_member_access.py`는 Phase 2에서 작성한다.
- `PlainTextResponse` 본문은 정확히 `"forbidden"` 소문자 7byte. 대문자, 마침표 등 변형 금지 (Phase 2 테스트가 이 문자열에 의존).
- 404 본문은 기존 `"회원을 찾을 수 없습니다."` 문구 유지 (기존 GET/POST `/log` 테스트 회귀 방지).
- CTO 조건 4: **POST `/log` 가드는 form 파싱 전**. `await request.form()` 위에 위치해야 한다. 이유: 403 응답 시 부작용(form 파싱·validation·INSERT)이 일어나서는 안 된다.
- CTO 조건 1: mid 부재 → 404, tid 불일치 → 404, 타 트레이너 소유 → 403. 세 케이스가 섞이지 않도록 헬퍼 로직 순서를 엄격히 유지.
- `SELECT *` 금지. 정확히 `SELECT id, trainer_id, name FROM members WHERE id=?`. 이유: 스키마 변경 시 silent 영향 방지.
- 헬퍼를 `Response` 반환 또는 `HTTPException raise` 형태로 바꾸지 마라. 순수 튜플 반환 유지 (기존 HTMLResponse/PlainTextResponse 직접 반환 패턴과 맞물림).
- `login_required_redirect()`는 기존대로 argless. 호출 시그니처 변경 금지.
- 기존 `is_owner` 사용 패턴(iter 2~3 `/admin/export`, `/my/export`) 건드리지 마라. 이번 변경은 4 target 라우트 + `GET /`에 국한.
- 기존 테스트를 깨뜨리지 마라. 특히 `conftest.py`의 `authed_client` 픽스처는 `ADMIN_USERNAME=admin`으로 **is_owner=1 관장** 로그인이므로, R5 가드 도입 후에도 그대로 통과해야 한다 (관장 bypass + 기존 테스트가 쓰는 tid가 해당 회원의 소유 트레이너 ID와 일치하는지 확인).
