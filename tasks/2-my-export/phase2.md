# Phase 2: `tests/test_my_export.py` 신규 + 컬럼 동등성 회귀 테스트

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/mission.md` — 프로젝트 mission (수정 금지)
- `/docs/spec.md` — 최신 spec. 특히 `## CSV Export` 섹션의 "관장 export" / "트레이너 본인 export" 2개 하위 섹션 계약을 정확히 숙지하라.
- `/docs/testing.md` — 테스트 정책. mock 금지, 실 SQLite `tmp_path`, `monkeypatch`로 env/전역 dict는 조작 가능(단 DB 자체 mock / `time.monotonic` 패치 금지).
- `/tasks/2-my-export/docs-diff.md` — 이번 task의 문서 변경 기록 (Phase 0 완료 후 자동 생성)

그리고 이전 phase의 작업물을 반드시 확인하라:

- `/tasks/2-my-export/phase0.md`, `/tasks/2-my-export/phase1.md`
- `/app/routes.py` — Phase 1에서 `_SESSIONS_CSV_COLUMNS` 상수, `_write_sessions_csv` 헬퍼, `/my/export/sessions.csv` 라우트가 추가됨
- `/app/main.py` L33 — `app.state.my_export_last_ts = {}` 초기화
- `/tests/test_export.py` — 기존 관장 export 테스트. 헬퍼 함수 스타일(`_insert_non_owner`, `_insert_member`, `_insert_session_with_set`, `_owner_trainer_id`), fixture 사용 패턴, `capsys` 패턴 모두 이걸 참고
- `/tests/conftest.py` — `temp_db`, `client`, `authed_client` fixture 정의. **변경 금지.**

이전 phase에서 만들어진 코드를 꼼꼼히 읽고, 설계 의도를 이해한 뒤 작업하라.

## 작업 내용

### 신규 파일 `/tests/test_my_export.py`

아래 9개 테스트 케이스를 정확히 구현하라. 모든 헬퍼는 **파일 내부**에 정의하라 (공용 모듈 추출 금지 — 현재 규모에서 중복 허용이 더 싸다). `tests/test_export.py`의 `_insert_non_owner`, `_insert_member`, `_insert_session_with_set` 스타일을 참고해 이 파일 전용으로 복제하라. `conftest.py`는 건드리지 마라.

#### 파일 상단 공통 헬퍼

- `def _insert_trainer(db_path, username, password, name, is_owner=0)` — `hash_password(password)`로 해싱 후 `INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (...)` 후 `lastrowid` 반환
- `def _insert_member(db_path, trainer_id, name="회원1")` — `INSERT INTO members`
- `def _insert_session_with_set(db_path, member_id, exercise, weight, reps, input_trainer_id=None, session_date="2026-04-10")` — pt_session + 1개 set
- `def _owner_trainer_id(db_path)` — `SELECT id FROM trainers WHERE is_owner=1 LIMIT 1`
- `def _login(client, username, password)` — POST `/login` → assert 303
- `def _logout(client)` — POST `/logout`

`from app.auth import hash_password` 와 `from app.db import get_connection` import 필요.

#### T1. `test_my_export_requires_login(temp_db, client)`
- 비로그인 상태로 `client.get("/my/export/sessions.csv", follow_redirects=False)`
- **검증**: `status_code == 303`, `r.headers["location"] == "/login"`

#### T2. `test_my_export_returns_only_own_rows(temp_db, client)`
- 비-owner 트레이너 A, B 각각 `_insert_trainer`로 생성 (username "a_t", "b_t")
- A의 회원 `_insert_member(db, a_id, "A회원")`, B의 회원 `_insert_member(db, b_id, "B회원")`
- A가 A회원에게 session 1건 입력 (`_insert_session_with_set(..., input_trainer_id=a_id, session_date="2026-04-10")`)
- B가 B회원에게 session 1건 입력 (`input_trainer_id=b_id, session_date="2026-04-11"`)
- A로 로그인 → `/my/export/sessions.csv` GET
- **검증**: 200, `content[:3] == b"\xef\xbb\xbf"` (BOM), CSV decode → header + 1 data row, data row의 `member_name == "A회원"`, `input_trainer_name == A의 name`. B의 row 없음.

#### T3. `test_my_export_owner_only_sees_own_input(temp_db, client)` (**CTO 조건 3**)
- 기본 관장 부트 시드로 owner가 이미 있음 (username "admin", password "pw1234"는 conftest의 client fixture가 세팅).
- 비-owner 트레이너 X `_insert_trainer(db, "staff_x", "xpw", "X직원")`
- 회원 1명 생성 (trainer_id = owner_id)
- 관장이 session 1건 입력 (`input_trainer_id=owner_id`, "2026-04-10")
- X가 session 1건 입력 (`input_trainer_id=x_id`, "2026-04-11")
- 관장으로 로그인 (username "admin" / password "pw1234")
- `/my/export/sessions.csv` GET
- **검증**: 200, CSV body에 관장의 row만. X의 row 없음. is_owner bypass 없음. (관장이 `/my/export`를 부르면 본인 입력분만 나오는지 검증.)

#### T4. `test_my_export_bom_and_headers(temp_db, authed_client)`
- owner가 본인에게 session 1건 insert
- `authed_client.get("/my/export/sessions.csv")`
- **검증**:
  - `content_type`이 "text/csv"로 시작
  - `content[:3] == b"\xef\xbb\xbf"`
  - `content-disposition`에 `filename="my_sessions_`로 시작하는 부분 포함, `.csv"`로 끝남
  - trainer_id 접미사가 들어가지 **않음**: `"_trainer_"` 문자열이 disposition에 없어야 함

#### T5. `test_my_export_rate_limit_429(temp_db, authed_client)`
- owner에게 session 1건 insert
- 1회 호출 → 200
- 2회 호출 → 429, `"Too Many Requests"` 가 body에 포함

#### T6. `test_my_export_rate_limit_independent_from_admin(temp_db, authed_client)` (**DX1 + CTO 조건 2 직접 검증**)

이 테스트는 `app.state.export_last_ts`와 `app.state.my_export_last_ts`가 물리적으로 분리돼 상호 영향이 없음을 명시적으로 증명한다. 미래에 누가 "최적화"한답시고 dict를 통합하면 여기서 빨간불이 뜨도록 설계.

- owner에게 session 1건 insert
- 시작 전 양쪽 dict clear (`authed_client.app.state.export_last_ts.clear()`, `authed_client.app.state.my_export_last_ts.clear()`)
- 호출 A: `/admin/export/sessions.csv` → 200 (관장 dict에 owner_id 등록)
  - 주석: 이 시점 관장 dict는 "살아있음", 본인 dict는 비어있음
- 호출 B: 즉시 `/my/export/sessions.csv` → 200 (본인 dict에 owner_id 등록). 관장 dict가 살아있어도 본인 dict는 독립이므로 429 아님.
  - 주석: 이 시점 양쪽 dict 모두 살아있음
- 호출 C: 즉시 `/my/export/sessions.csv` 재호출 → 429 (본인 dict 60초 제한)
  - 주석: 본인 dict 60초 살아있음 — 429
- 호출 D: 즉시 `/admin/export/sessions.csv` 재호출 → 429 (관장 dict도 여전히 60초 살아있음)
  - 주석: 관장 dict 60초 살아있음 — 429

#### T7. `test_my_export_stdout_log(temp_db, authed_client, capsys)`
- owner에게 session 2건 insert (같은 input_trainer_id=owner_id)
- `capsys.readouterr()`로 이전 출력 비우기
- `/my/export/sessions.csv` GET
- `captured = capsys.readouterr()`
- **검증**: `f"[my-export] trainer_id={owner_id}" in captured.out`, `"rows=2" in captured.out`

#### T8. `test_my_export_empty_when_no_input_rows(temp_db, authed_client, capsys)`
- 회원만 insert. session 0건.
- `/my/export/sessions.csv` GET
- **검증**: 200, CSV body에 header row 1개만 (data row 0건). 감사 로그 `rows=0`.

#### T9. `test_my_export_admin_column_parity_regression(temp_db, client)` (**CTO 조건 3: 컬럼 동등성 bit-exact 회귀**)

이 테스트는 관장 `/admin/export?trainer_id=X` body와 X로 로그인한 `/my/export` body가 **BOM 포함 bit-exact 일치**함을 증명해 공통 헬퍼 `_write_sessions_csv`의 drift를 자동 포착한다.

**주석으로 의도 명시**: "양쪽 dict clear는 안전망 — rate limit 분리 자체는 T6에서 검증한다. 본 테스트의 비교 대상은 응답 body만이며 Content-Disposition은 라우트별로 의도적으로 다르므로 별도 검증한다."

구현:
- non-owner 트레이너 X `_insert_trainer(db, "staff_x", "xpw", "X직원")`
- X의 회원 1명 `_insert_member(db, x_id, "X회원")`
- X가 session 2건 입력 (서로 다른 세션_date: "2026-04-10", "2026-04-11"; input_trainer_id=x_id)
- 양쪽 dict clear: `client.app.state.export_last_ts.clear()`, `client.app.state.my_export_last_ts.clear()`
- 관장으로 로그인 (conftest의 `authed_client` 대신 본 테스트는 `client` fixture를 받아 수동 로그인/로그아웃 관리)
  - `_login(client, "admin", "pw1234")`
- `admin_resp = client.get(f"/admin/export/sessions.csv?trainer_id={x_id}")` → 200
- 양쪽 dict clear 한 번 더 (또 다른 라우트 호출을 준비, rate limit 영향 배제):
  - `client.app.state.export_last_ts.clear()`
  - `client.app.state.my_export_last_ts.clear()`
- 관장 로그아웃: `_logout(client)`
- X로 로그인: `_login(client, "staff_x", "xpw")`
- `my_resp = client.get("/my/export/sessions.csv")` → 200
- **body bit-exact 검증**:
  ```python
  assert admin_resp.content == my_resp.content, \
      "관장 /admin/export?trainer_id=X body와 X /my/export body가 다르다 — 헬퍼 drift 발생"
  ```
- **Content-Disposition 차이 검증 (별도)**:
  ```python
  assert admin_resp.headers["content-disposition"] != my_resp.headers["content-disposition"]
  assert f"_trainer_{x_id}" in admin_resp.headers["content-disposition"]
  assert "my_sessions_" in my_resp.headers["content-disposition"]
  assert "_trainer_" not in my_resp.headers["content-disposition"]
  ```

## Acceptance Criteria

아래 커맨드를 순서대로 실행해서 전부 exit 0이어야 한다.

```bash
# 신규 테스트 파일 전원 green
uv run pytest tests/test_my_export.py -x -q

# 기존 테스트 suite 그대로 유지 (e2e 제외 — 환경 의존)
uv run pytest tests/ --ignore=tests/test_e2e_dashboard.py -x -q

# 신규 파일이 정확한 케이스 이름을 포함
test -f tests/test_my_export.py
grep -q 'def test_my_export_requires_login' tests/test_my_export.py
grep -q 'def test_my_export_returns_only_own_rows' tests/test_my_export.py
grep -q 'def test_my_export_owner_only_sees_own_input' tests/test_my_export.py
grep -q 'def test_my_export_bom_and_headers' tests/test_my_export.py
grep -q 'def test_my_export_rate_limit_429' tests/test_my_export.py
grep -q 'def test_my_export_rate_limit_independent_from_admin' tests/test_my_export.py
grep -q 'def test_my_export_stdout_log' tests/test_my_export.py
grep -q 'def test_my_export_empty_when_no_input_rows' tests/test_my_export.py
grep -q 'def test_my_export_admin_column_parity_regression' tests/test_my_export.py
```

## AC 검증 방법

위 AC 커맨드를 순서대로 실행하라. 전부 exit 0이면 `/tasks/2-my-export/index.json`의 phase 2 status를 `"completed"`로 변경하라.

수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고 `"error_message"` 필드에 원인을 기록하라.

## 주의사항

- `conftest.py`는 **수정하지 마라.** 기존 `temp_db`, `client`, `authed_client` fixture를 그대로 사용.
- `tests/test_export.py`는 **수정하지 마라.** 기존 7케이스는 Phase 1에서 이미 green 유지 중.
- 헬퍼 함수는 `tests/test_my_export.py` 내부에 정의 (CTO 조건 4: 공용 모듈 추출 금지, 중복 허용).
- T9의 비교 주석에 "양쪽 dict clear는 안전망, 분리 검증은 T6"임을 반드시 코드 주석으로 남겨라. 누락 시 미래 독자가 "T9에서 rate limit 분리를 검증하는가?" 혼동.
- T9에서 body 비교와 Content-Disposition 차이 검증을 **두 단계로 분리**해 작성하라 (한 assert에 섞지 마라).
- T6에서 각 4개 호출 직전/직후에 어느 dict가 살아있어야 하는지 주석으로 남겨라. 이 테스트는 미래에 회귀 가능성이 가장 큰 테스트.
- `_login`에서 `follow_redirects=False` + `assert 303`. 로그인 성공 후 `/`로 redirect를 따라가지 않는다.
- 관장 계정은 conftest가 `ADMIN_USERNAME=admin, ADMIN_PASSWORD=pw1234`로 환경변수 세팅하고 `create_app()`이 부트 시드한다. 테스트에서 `admin` / `pw1234`로 로그인 가능.
- **`time.monotonic`를 패치하지 마라.** testing.md 정책 금지. T5/T6는 실시간으로 연속 호출해 429를 유도.
- **DB를 mock하지 마라.** 실 SQLite temp file (`tmp_path` via `temp_db` fixture).
- E2E (Playwright) 추가 금지. iteration 3 범위 외.
- 기존 test_export.py 테스트를 깨뜨리지 마라.
