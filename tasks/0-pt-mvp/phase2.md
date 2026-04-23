# Phase 2: FastAPI 앱 + 세션 인증 + 로그 입력 폼

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` — 라우트 목록, 인증, 운동 10종
- `/docs/testing.md` — 테스트 정책 (mock 금지, 실 SQLite)
- `/tasks/0-pt-mvp/docs-diff.md` — 이번 task의 문서 변경 기록

이전 phase 산출물 (반드시 코드를 읽고 이해하라):
- `/pyproject.toml`
- `/app/__init__.py`, `/app/db.py`, `/app/exercises.py`, `/app/aggregates.py`
- `/scripts/seed.py`
- `/tests/conftest.py`, `/tests/test_aggregates.py`

Phase 1에서 만들어진 `app.db.get_connection`과 `app.exercises.EXERCISES`를 그대로 활용한다.

## 작업 내용

### 1. FastAPI 엔트리 — `app/main.py`

```python
import os
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.db import init_db
from app.routes import register_routes

REQUIRED_ENV = ("APP_SESSION_SECRET", "ADMIN_USERNAME", "ADMIN_PASSWORD")

def _validate_env() -> None:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

def create_app() -> FastAPI:
    _validate_env()
    init_db()
    app = FastAPI()
    secure_cookie = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["APP_SESSION_SECRET"],
        session_cookie="bet_session",
        https_only=secure_cookie,
        same_site="lax",
    )
    register_routes(app)
    return app

app = create_app()
```

**부팅 시 env 3개 중 하나라도 없으면 RuntimeError**. 조용한 기본값 금지.

### 2. 인증 — `app/auth.py`

```python
import os
import secrets
from fastapi import Request
from fastapi.responses import RedirectResponse

def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("admin"))

def verify_credentials(username: str, password: str) -> bool:
    u_ok = secrets.compare_digest(username, os.environ["ADMIN_USERNAME"])
    p_ok = secrets.compare_digest(password, os.environ["ADMIN_PASSWORD"])
    return u_ok and p_ok

def login_required_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)
```

라우트 핸들러 내부에서 `if not is_authenticated(request): return login_required_redirect()` 패턴으로 보호. FastAPI Depends로 묶어도 되지만, 그 경우 `RedirectResponse`를 직접 리턴하도록 하라.

### 3. 라우트 등록 — `app/routes.py`

템플릿 디렉토리는 `app/templates/`. Jinja2Templates 인스턴스를 모듈 최상단에 생성.

필수 라우트:

- `GET /login` — 로그인 폼 (`login.html` 렌더). 이미 로그인 상태면 `/`로 redirect.
- `POST /login` — form data `username`, `password` 수신. `verify_credentials` 통과 시 `request.session["admin"] = True` + 303 `/` redirect. 실패 시 200 + `login.html` 재렌더 (에러 메시지 노출).
- `POST /logout` — `request.session.clear()` + 303 `/login` redirect.
- `GET /` — 인증 필요. 첫 멤버로 redirect: `trainers[0].id`, `members[0].id` 조회 후 `/trainers/{tid}/members/{mid}/log` 303 redirect. 멤버 없으면 간단한 "seed를 실행하세요" 문구 렌더.
- `GET /trainers/{tid}/members/{mid}/log` — 인증 필요. 회원 정보 조회해서 `log.html` 렌더. 운동 10종 select 옵션, "세트 추가" 버튼, 제출 버튼.
- `POST /trainers/{tid}/members/{mid}/log` — 인증 필요. form data:
  - `session_date` (YYYY-MM-DD)
  - `exercise[]`, `weight_kg[]`, `reps[]` (N개 병렬 배열)
  처리:
  1. 세트 행별로 (exercise, weight_kg, reps) 중 하나라도 비어있으면 해당 행 skip.
  2. 유효 행이 0개면 400 + 에러 문구.
  3. exercise가 `EXERCISES`에 없으면 400.
  4. weight_kg <= 0 또는 reps <= 0이면 400.
  5. INSERT `pt_sessions` 1건 + INSERT `session_sets` N건 (set_index=0..N-1).
  6. 성공 시 HTMX partial 응답: `<div id="entry-feedback">저장됨 (<a href="/trainers/{tid}/members/{mid}/dashboard">대시보드 보기</a>)</div>`

### 4. 템플릿

`app/templates/base.html` — `<!doctype html>`, Jinja2 `{% block content %}`, HTMX CDN(`htmx.org@1.9.x` pin) `<script>` 포함. 페이지 상단에 우측 로그아웃 `<form method="post" action="/logout">` 간단 버튼.

`app/templates/login.html` — `extends base`. `<form method="post" action="/login">` + username/password input + 제출. `{% if error %}` 에러 문구.

`app/templates/log.html` — `extends base`. 
- 상단에 회원 이름 + "이 회원 대시보드" 링크
- 폼: `<form hx-post="/trainers/{{tid}}/members/{{mid}}/log" hx-target="#entry-feedback">`
- session_date input (type=date, value=오늘)
- 세트 테이블: `id="sets"` 컨테이너. 초기 세트 행 1개.
- "세트 추가" 버튼: `hx-get="/partials/set-row?set_index={{next}}"` 로 서버에서 새 세트 행 partial을 받아 append (또는 클라이언트 JS로 DOM 복제 — JS도 허용). **간단함이 우선.**
- 세트 행 한 칸의 input name은 `exercise`, `weight_kg`, `reps` (브라우저가 form 전송 시 배열로 묶음).
- 제출 버튼
- `<div id="entry-feedback"></div>`

세트 행 HTMX partial 라우트(`GET /partials/set-row`)는 **선택**. 간단히 JS로 `<template>` 복제가 더 짧으면 그쪽을 택해도 된다. 단, 인증으로 보호해야 한다면 auth 체크 포함.

### 5. 라우트 테스트

`tests/conftest.py` 보강 — FastAPI 클라이언트 fixture 추가:

```python
import pytest
from fastapi.testclient import TestClient
# ... 기존 temp_db fixture 유지 ...

@pytest.fixture
def client(temp_db, monkeypatch):
    """각 테스트마다 temp_db 기반 FastAPI TestClient."""
    monkeypatch.setenv("APP_SESSION_SECRET", "test-secret-xxxxxxxxxxxxxxxx")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw1234")
    from app.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c

@pytest.fixture
def authed_client(client):
    r = client.post("/login", data={"username": "admin", "password": "pw1234"}, follow_redirects=False)
    assert r.status_code == 303
    return client
```

`tests/test_auth.py` — 케이스:
- `test_login_page_renders` — GET /login → 200
- `test_wrong_credential_rerenders_form` — 잘못된 pw → 200 + HTML에 에러 문구 포함
- `test_correct_credential_sets_session_and_redirects` — 정상 → 303 + location `/`
- `test_protected_route_redirects_when_unauth` — 미인증으로 `/trainers/1/members/1/log` GET → 303 `/login`
- `test_logout_clears_session` — 로그인 후 POST /logout → 303 → 이후 보호 라우트 접근 시 303 /login
- `test_missing_env_raises_runtime_error` — 환경변수 1개라도 없을 때 `create_app()` 호출 → `RuntimeError`

`tests/test_log_routes.py` — 케이스 (모두 `authed_client` + `temp_db`에 trainer/member를 직접 INSERT한 후):
- `test_log_form_renders_with_exercise_options` — GET /log → 200 + HTML에 10종 운동명 포함
- `test_post_log_creates_session_and_sets` — POST 성공 → pt_sessions 1건 + session_sets N건 DB에 생성 + 200 응답
- `test_post_log_skips_empty_rows` — 3행 중 1행 빈 세트 → session_sets 2건만 생성
- `test_post_log_rejects_negative_weight` — weight_kg=-5 → 400
- `test_post_log_rejects_unknown_exercise` — exercise="풀라인업" → 400
- `test_post_log_rejects_when_all_rows_empty` — 모든 행 비어있음 → 400

## Acceptance Criteria

```bash
$RUN="uv run"; command -v uv >/dev/null 2>&1 || RUN=""

# 문법 체크
$RUN python -c "from app.main import create_app"  # 이건 env 없으면 RuntimeError 정상

# 인증/로그 라우트 테스트
$RUN pytest tests/test_auth.py tests/test_log_routes.py -v

# 기존 테스트 여전히 통과
$RUN pytest tests/test_aggregates.py -v
```

(uv 없으면 `python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'` 선행)

## AC 검증 방법

위 커맨드를 순서대로 실행하라. 모두 통과하면 `/tasks/0-pt-mvp/index.json`의 phase 2 status를 `"completed"`로 변경하라.
수정 3회 이상 시도해도 실패하면 status를 `"error"`로 변경하고 `"error_message"` 필드에 원인을 기록하라.

## 주의사항

- **인증 확장 금지.** 어드민 계정 1개, 평문 비교, 세션 쿠키만. bcrypt/JWT/OAuth/권한 분리/rate limit 도입 금지.
- **`secrets.compare_digest` 사용 필수** — `==` 로 비교하지 마라 (타이밍 공격 방지).
- **fail-fast.** env 미설정 상태에서 조용히 기본값으로 넘어가지 마라. `create_app()`에서 RuntimeError.
- **CSRF 보호는 이번 스프린트 외.** 하드코딩 어드민 1명 + same-site lax 쿠키로 충분하다고 spec에 명시되어 있다.
- **비밀번호 해시 저장소 금지.** 환경변수 평문 비교에서 멈춰라.
- **Rate limit 금지.** brute-force 보호는 명시적 제외 항목이다.
- log 폼의 HTMX target은 반드시 `#entry-feedback` 한 곳. 다른 id 쓰지 마라 (Phase 3/4가 이 id에 의존할 수 있음).
- 기존 `tests/conftest.py`의 `temp_db` fixture를 깨뜨리지 마라. **추가만 하라.**
- 기존 `tests/test_aggregates.py`가 계속 green이어야 한다.
- 템플릿에서 10종 운동 하드코딩 금지 — `app.exercises.EXERCISES` 참조.
