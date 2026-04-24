# Phase 2: tests

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` (iter 5 반영본. 특히 "트레이너간 회원 접근 격리 (partial, iter 5 live)" 섹션)
- `/docs/testing.md` (원칙: mock 금지, tmp_path SQLite only, `pytest.monkeypatch` 통한 env/모듈 attribute 조작은 허용)
- `/tasks/3-member-access/docs-diff.md` (이번 task의 docs diff)

그리고 이전 phase의 작업물을 반드시 확인하라:

- `/app/auth.py`에 Phase 1에서 추가된 `require_member_access(request, conn, tid, mid)` 헬퍼
- `/app/routes.py`에 Phase 1에서 적용된 4 라우트 가드 + `GET /` redirect 변경
- 기존 테스트 fixture: `/tests/conftest.py` — `temp_db`, `client`, `authed_client` (admin ADMIN_USERNAME=admin, ADMIN_PASSWORD=pw1234, is_owner=1로 자동 시드됨)

## 작업 내용

이번 phase는 **신규 테스트 파일 `tests/test_member_access.py` 작성 + 기존 테스트 전체 regression 확인**이다.

### 1. `tests/test_member_access.py` 신규 작성

**원칙:**
- mock 금지. `tmp_path` SQLite 실파일 사용 (conftest의 `temp_db` fixture 재사용).
- ORM 금지. 표준 `sqlite3` only.
- `TestClient`는 `client` fixture 재사용 (이미 `ensure_owner_seed()`로 admin 시드됨).
- `_login` / `_logout`은 **`follow_redirects=False`**로 303 단정. 기본값이 follow이므로 명시적으로 꺼야 한다.
- 추가 trainer는 `sqlite3.connect(str(temp_db))` + `INSERT INTO trainers (name, username, password_hash, is_owner, created_at)` + `app.auth.hash_password(password)`로 password_hash 생성. Connection은 사용 후 반드시 `close()`.

**파일 내부 private helper (conftest로 올리지 말 것):**

```python
def _seed_trainer(db_path, username: str, password: str, is_owner: int = 0) -> int:
    # INSERT trainers row, return new trainer id
def _seed_member(db_path, trainer_id: int, name: str) -> int:
    # INSERT members row, return new member id
def _login(client, username: str, password: str) -> None:
    # POST /login with follow_redirects=False, assert status == 303
def _logout(client) -> None:
    # POST /logout with follow_redirects=False, assert status == 303
```

**12 시나리오 (각각 별도 `test_*` 함수):**

모든 시나리오는 기본 fixture: `def test_xxx(client, temp_db):` 시그니처. 필요 시 `authed_client`는 사용하지 말고 `client` + 명시적 `_login`만 사용하라 (관장/비관장 로그인을 테스트마다 다르게 해야 하므로).

1. **test_log_get_403_for_other_trainer_member** — `trainerA` / `trainerB` seed, `trainerB` 소유 회원 `midB` seed. `_login(client, "trainerA", ...)` 후 `GET /trainers/{tidB}/members/{midB}/log` → status 403, body contains `"forbidden"` (정확히 소문자).

2. **test_log_post_403_no_db_mutation** — #1과 동일 seed. `trainerA` 로그인 후 `POST /trainers/{tidB}/members/{midB}/log` with valid form (`session_date=2026-04-24`, `exercise=["스쿼트"]`, `weight_kg=["60"]`, `reps=["10"]`) → status 403. 직후 **`sqlite3.connect(temp_db)`로 별도 조회**:
   ```python
   conn = sqlite3.connect(str(temp_db))
   try:
       assert conn.execute("SELECT COUNT(*) FROM pt_sessions").fetchone()[0] == 0
       assert conn.execute("SELECT COUNT(*) FROM session_sets").fetchone()[0] == 0
   finally:
       conn.close()
   ```

3. **test_chart_data_403_for_other_trainer_member** — #1 세팅. `GET /trainers/{tidB}/members/{midB}/chart-data.json` → 403 + body `"forbidden"`.

4. **test_dashboard_403_for_other_trainer_member** — #1 세팅. `GET /trainers/{tidB}/members/{midB}/dashboard` → 403 + body `"forbidden"`.

5. **test_self_owned_member_all_routes_200** — `trainerA` seed, `midA` seed. `trainerA` 로그인. 4 라우트 각각 호출:
   - GET `/log` → 200, body contains `midA`에 해당하는 member name 또는 "log" 관련 구조
   - POST `/log` with valid form (1개 세트) → 200 (HTMX 부분 응답), INSERT 성공
   - GET `/chart-data.json` → 200, JSON에 `"member"` 키 존재
   - GET `/dashboard` → 200

6. **test_owner_bypass_other_trainer_member_all_routes_200** — `trainerA` seed, `midA` seed. `admin`(is_owner=1) 로그인. `GET /trainers/{tidA}/members/{midA}/log` + chart-data + dashboard → 각 200. **URL의 tid는 반드시 `tidA`**.

7. **test_owner_wrong_tid_returns_404** — `trainerA` seed (tid=N), `midA` seed. `admin` 로그인. `GET /trainers/999/members/{midA}/log` (tid=999, member의 실제 소유 tid와 불일치) → **404**, body contains `"회원을 찾을 수 없습니다"` (403 **아님** — URL 위조 판정 우선).

8. **test_unauthenticated_redirects_to_login** — 비로그인 상태. 4 라우트 각각 `follow_redirects=False` → status 303, header `location` == `/login`. POST `/log`도 동일.

9. **test_nonexistent_mid_returns_404** — `trainerA` 로그인. `GET /trainers/{tidA}/members/99999/log` → 404, body contains `"회원을 찾을 수 없습니다"`. 403이 **아님**을 명시적으로 단정 (`assert r.status_code == 404`, 별도 `assert r.status_code != 403`).

10. **test_index_redirect_for_non_owner** — `trainerA` seed, `midA` seed. `trainerA` 로그인. `GET /` with `follow_redirects=False` → status 303, header `location` == `/trainers/{tidA}/members/{midA}/log`.

11. **test_index_redirect_for_owner** — `trainerA` seed, `midA` seed (DB에서 첫 트레이너 = admin 자동 시드 id, 첫 회원 = admin의 회원이 없으므로 `trainerA`의 첫 회원). `admin` 로그인. `GET /` → 303. **관장의 기존 동작**: DB의 첫 트레이너 + 해당 트레이너의 첫 회원. 구체적 URL은 seed 순서에 의존하므로 assertion은 `assert r.status_code == 303`와 `assert "/trainers/" in r.headers["location"]`와 `assert "/log" in r.headers["location"]`로 유연하게 (관장 bypass 동작 확인이 목적).

12. **test_index_zero_members_non_owner_returns_info_page** — `trainerA` seed (members 0명). `trainerA` 로그인. `GET /` → status 200, body contains `"담당 회원이 아직 없습니다"`.

### 2. Regression 확인

Phase 2 말미에 다음을 실행:

```bash
uv run pytest tests/test_member_access.py -v
uv run pytest -x
```

기존 7 파일(test_aggregates, test_auth, test_log_routes, test_dashboard, test_e2e_dashboard, test_export, test_my_export) + 신규 1 파일 전체 green을 확인한다.

**E2E (Playwright) 처리:**
- `tests/test_e2e_dashboard.py`는 Playwright 환경 의존. 로컬/CI 환경에 Playwright chromium이 없으면 skip/fail 가능.
- 실패가 R5 가드로 인한 것인지(`authed_client`가 관장이라 bypass로 통과해야 정상), 아니면 환경 문제인지 구분.
- **기존 테스트 수정은 최소한**: 만약 e2e가 R5 가드로 깨진다면 원인은 "fixture가 `authed_client`를 쓰지만 URL의 tid가 실제 admin의 trainer_id와 불일치"일 가능성. 이 경우 해당 테스트의 URL 조립 부분만 조정. 다른 테스트 수정 금지.
- 환경 문제(chromium 미설치 등)로 실패 시 phase 완료 판정에 영향 없음 — index.json phase 2 `"notes"` 필드에 "e2e skipped due to env" 1줄 기록.

### 3. 실패 대응

- **3회 수정 시도 규칙**: 동일 실패 원인에 대한 수정 3회 실패 시 phase 2 `"status": "error"` 마킹 + `"error_message"`에 원인 요약.
- 새로운 실패가 드러나면 별개 카운트.
- 3회 내 해결 불가 시 phase 2 index.json에 `"failure"` 필드로 실패 원인 요약 남겨라 (다음 세션 진단 부담 감소).

## Acceptance Criteria

```bash
# 1. 신규 테스트 파일 전체 통과
uv run pytest tests/test_member_access.py -v

# 2. 전체 regression (e2e는 환경 의존적이므로 별도 처리 — 주의사항 참조)
uv run pytest -x --ignore=tests/test_e2e_dashboard.py

# 3. e2e는 환경 가능할 때만 확인
uv run pytest tests/test_e2e_dashboard.py || echo "e2e env-dependent, skipped"
```

## AC 검증 방법

위 AC 1~2번이 모두 통과하면 `/tasks/3-member-access/index.json`의 phase 2 status를 `"completed"`로 변경하라.
3번(e2e)은 통과/스킵 허용. R5 가드가 명백히 e2e를 깨뜨린 경우는 고쳐야 하지만 chromium 미설치 등 환경 문제는 허용.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고, 에러 내용을 index.json의 해당 phase에 `"error_message"` 필드로 기록하라.

## 주의사항

- **mock 금지**. `unittest.mock`, `pytest-mock`, monkeypatch로 DB 자체 패치 금지. env 주입, 모듈 attribute 조작만 허용 (기존 `temp_db` fixture 패턴 따라).
- **ORM 금지**. SQLAlchemy·Peewee·Tortoise 등 일절 금지. 표준 `sqlite3` only.
- **`time.monotonic` 패치 금지** (rate limit 관련 없지만 원칙 확인).
- **기존 테스트 파일(`test_log_routes.py`, `test_dashboard.py` 등) 수정 금지**가 기본. 단, R5 가드로 인한 명백한 regression이 발생하고 fixture의 숨은 가정을 최소 조정해야만 해결되는 경우에만 예외 허용. 그 경우 phase 2 index.json `"notes"` 필드에 수정 이유 1줄 명시.
- **POST form 데이터 전송 시** `httpx.TestClient`의 form encoding: `data={"session_date": "...", "exercise": ["스쿼트"], "weight_kg": ["60"], "reps": ["10"]}` 패턴. 기존 `test_log_routes.py`의 패턴 참조.
- **`_login` helper**: `follow_redirects=False` 필수. 기본값이 follow이면 로그인 후 `/` redirect가 자동 추적되어 200으로 반환되어 303 단정 실패.
- **시나리오 #2 DB 조회**: 반드시 `sqlite3.connect(str(temp_db))`로 별도 connection 생성 + `try/finally`로 `close()`. SQLite lock 회피.
- **시나리오 #8 URL**: `(tidA, midA)` 실제 seed된 ID 사용. placeholder `(1, 1)`은 seed 순서 의존성으로 flaky.
- **#6 URL tid**: 반드시 `tidA` (회원 `midA`의 실제 소유 트레이너 ID). 잘못된 tid를 쓰면 Q3 규칙에 의해 404 — 하지만 이 시나리오는 200 확인이 목적이므로 URL 정합성을 맞춰야 한다.
- **#7 URL tid**: 반드시 **999 같은 존재하지 않는 tid 숫자**를 써서 `row["trainer_id"] != tid` 분기를 타게 하라. 다른 실제 트레이너 ID를 쓰면 "존재하는 tid + 불일치"로 여전히 404지만 의도 불명. 테스트 이름과 의도에 맞게 `999`를 쓰는 게 명확.
- body assertion과 status code를 2-axis로 묶어 단정. 하나만 검증하면 미래 문구 변경 시 silent 통과 위험.
- Playwright 설치 유무 체크: `uv run pytest tests/test_e2e_dashboard.py --collect-only`로 수집 가능 여부 확인 후 실행.
- 기존 `_setup`/helper 패턴과 일관성 유지 (기존 `test_export.py`, `test_my_export.py` 참조).
