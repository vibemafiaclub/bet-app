# Phase 4: Playwright E2E + DoD 스크린샷

## 사전 준비

먼저 아래 문서들을 반드시 읽고 프로젝트의 전체 아키텍처와 설계 의도를 완전히 이해하라:

- `/docs/spec.md` — DoD 섹션: 스크린샷 경로 = `iterations/1-20260424_020912/artifacts/dashboard.png`
- `/docs/testing.md` — Playwright 정책 (teardown에서 process.terminate, 임시 DB cleanup)
- `/tasks/0-pt-mvp/docs-diff.md`

이전 phase 산출물 (반드시 코드를 읽고 이해하라):
- `/app/main.py` (create_app, env 검증)
- `/app/routes.py` (로그인/로그 폼/대시보드/chart-data)
- `/scripts/seed.py` (stdout 포맷: `TRAINER_ID=<id> MEMBER_IDS=<a,b,c>`)
- `/app/templates/dashboard.html` (canvas id: `max-weight-chart`, `total-volume-chart`)
- `/tests/conftest.py`

## 작업 내용

### 1. Playwright 브라우저 준비

AC 커맨드 첫 줄에 `uv run playwright install chromium`을 포함. 런너 세션에서 이게 먼저 성공해야 한다.

### 2. uvicorn 서브프로세스 fixture — `tests/e2e_conftest.py` 또는 `tests/conftest.py` 보강

**주의**: 기존 `temp_db`/`client`/`authed_client` fixture는 건드리지 마라. E2E용은 별도 fixture로 분리.

```python
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """
    Module-scoped uvicorn subprocess with isolated DB + seed.
    teardown: terminate + wait(timeout=5), remove temp db.
    """
    tmp = tmp_path_factory.mktemp("e2e")
    db_path = tmp / "bet.db"
    port = _free_port()
    env = {
        **os.environ,
        "DATABASE_PATH": str(db_path),
        "APP_SESSION_SECRET": "e2e-secret-xxxxxxxxxxxxxxxx",
        "ADMIN_USERNAME": "e2eadmin",
        "ADMIN_PASSWORD": "e2epw",
        "SESSION_COOKIE_SECURE": "0",
    }

    # 1) seed로 DB 준비. stdout에서 trainer/member id 추출.
    r = subprocess.run(
        [sys.executable, "scripts/seed.py"],
        env=env, cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, f"seed failed: {r.stderr}"
    m = re.search(r"TRAINER_ID=(\d+)\s+MEMBER_IDS=([\d,]+)", r.stdout)
    assert m, f"seed stdout missing id line: {r.stdout!r}"
    trainer_id = int(m.group(1))
    member_ids = [int(x) for x in m.group(2).split(",")]

    # 2) uvicorn 기동
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env, cwd=str(ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )

    # 3) readiness poll (최대 15초)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base + "/login", timeout=1).read()
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("uvicorn did not become ready in 15s")

    try:
        yield {
            "base": base,
            "trainer_id": trainer_id,
            "member_ids": member_ids,
            "username": "e2eadmin",
            "password": "e2epw",
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        # tmp_path_factory auto-cleanup handles db_path
```

### 3. E2E 테스트 — `tests/test_e2e_dashboard.py`

```python
import os
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "iterations" / "1-20260424_020912" / "artifacts"
SCREENSHOT_PATH = ARTIFACT_DIR / "dashboard.png"

def test_dashboard_renders_and_screenshot_saved(live_server):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    base = live_server["base"]
    tid = live_server["trainer_id"]
    mid = live_server["member_ids"][0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            # 1) login
            page.goto(f"{base}/login")
            page.fill('input[name="username"]', live_server["username"])
            page.fill('input[name="password"]', live_server["password"])
            page.click('button[type="submit"], input[type="submit"]')
            page.wait_for_load_state("networkidle")

            # 2) navigate to dashboard
            page.goto(f"{base}/trainers/{tid}/members/{mid}/dashboard")

            # 3) wait for both canvases
            page.wait_for_selector("canvas#max-weight-chart", timeout=10_000)
            page.wait_for_selector("canvas#total-volume-chart", timeout=10_000)

            # 4) wait until Chart.js finished drawing (chart instance attached)
            page.wait_for_function(
                """() => {
                    if (typeof Chart === 'undefined') return false;
                    const a = Chart.getChart('max-weight-chart');
                    const b = Chart.getChart('total-volume-chart');
                    return a && b
                      && a.data.labels && a.data.labels.length > 0
                      && b.data.labels && b.data.labels.length > 0;
                }""",
                timeout=10_000,
            )

            # 5) screenshot
            page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        finally:
            browser.close()

    assert SCREENSHOT_PATH.exists(), f"screenshot not saved: {SCREENSHOT_PATH}"
    assert SCREENSHOT_PATH.stat().st_size > 10_000, "screenshot suspiciously small"
```

**케이스 하나로 충분.** 로그인+캔버스 2개 존재+data 채워짐+스크린샷 저장 — 조건부 조건 #6의 DoD 증거.

## Acceptance Criteria

```bash
$RUN="uv run"; command -v uv >/dev/null 2>&1 || RUN=""

# Chromium 바이너리 설치 (이미 있으면 no-op)
$RUN playwright install chromium

# E2E 테스트 실행
$RUN pytest tests/test_e2e_dashboard.py -v -s

# 스크린샷 산출물 확인
test -f iterations/1-20260424_020912/artifacts/dashboard.png
test $(stat -f%z iterations/1-20260424_020912/artifacts/dashboard.png 2>/dev/null || stat -c%s iterations/1-20260424_020912/artifacts/dashboard.png) -gt 10000

# 기존 테스트 여전히 통과
$RUN pytest tests/test_aggregates.py tests/test_auth.py tests/test_log_routes.py tests/test_dashboard.py -v
```

## AC 검증 방법

위 커맨드 모두 통과하면 `/tasks/0-pt-mvp/index.json`의 phase 4 status를 `"completed"`로 변경하라.
수정 3회 이상 실패 시 status `"error"` + `"error_message"` 기록.

일반적 실패 원인과 1차 대응:
- `playwright install chromium` 다운로드 실패 → `PLAYWRIGHT_BROWSERS_PATH=0` 환경변수로 재시도.
- 포트 충돌 → `_free_port()` 재호출.
- uvicorn readiness 타임아웃 → `proc.stdout`을 읽어 에러를 먼저 출력하도록 fixture 보강.
- canvas selector 안 잡힘 → Phase 3 산출물(`dashboard.html`) id 확인. `max-weight-chart` / `total-volume-chart` 여야 한다.
- `Chart.getChart` undefined → CDN 로드 타임 이슈일 수 있음. `page.wait_for_load_state("networkidle")` 후 재시도.

## 주의사항

- **기존 테스트를 깨뜨리지 마라.** conftest 보강 시 기존 fixture 이름/시그니처 유지.
- **fixture teardown 필수.** `proc.terminate() + wait(timeout=5) + fallback kill`. 누락 시 CI에서 프로세스 leak.
- **스크린샷 경로는 정확히** `iterations/1-20260424_020912/artifacts/dashboard.png`. spec.md의 DoD와 일치해야 한다.
- **uvicorn 기동을 `app.main:app`로** — `create_app()` 호출하는 팩토리 기동은 env 순서 이슈 있을 수 있다. 모듈 최상단에 `app = create_app()` 있으면 그대로 사용.
- **`pytest-asyncio` 자동 모드 유지.** 기존 `pyproject.toml`의 `asyncio_mode = "auto"` 건드리지 마라.
- `tests/e2e_conftest.py`로 파일 분리해도 좋지만, pytest는 테스트 파일과 같은 `tests/` 디렉토리 내 `conftest.py`를 자동 로드한다. **별도 파일명으로 만들면 pytest가 인식하지 못한다.** 결론: `tests/conftest.py`에 fixture를 **추가**하라 (기존 fixture 유지).
- `sync_playwright` 사용(async 금지). FastAPI 테스트가 async여도 Playwright는 sync API로 충분.
- **스크린샷 빈파일 방지.** 파일 크기 10KB 이상이어야 AC 통과.
