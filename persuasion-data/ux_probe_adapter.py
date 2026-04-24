"""persuasion-review skill의 5a0 UX probe 어댑터 (이 프로젝트 전용).

skill은 서비스 기동 방법을 모르므로 이 어댑터가 그 책임을 진다. 계약 요약:

    start(run_dir) -> {base_url, python_bin, credentials, context, tasks_markdown}
    stop(run_dir)  -> None

상세 인터페이스는 `.claude/skills/persuasion-review/scripts/run_simulation.py`
상단 주석 (Stage 5a0 section) 참조.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
READY_TIMEOUT_SEC = 15
PROBE_USERNAME = "probeadmin"
PROBE_PASSWORD = "probepw"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(run_dir: Path) -> dict:
    probe_dir = run_dir / "probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    db_path = probe_dir / "bet.db"
    if db_path.exists():
        db_path.unlink()

    port = _free_port()
    env = {
        **os.environ,
        "DATABASE_PATH": str(db_path),
        "APP_SESSION_SECRET": "probe-secret-xxxxxxxxxxxxxxxx",
        "ADMIN_USERNAME": PROBE_USERNAME,
        "ADMIN_PASSWORD": PROBE_PASSWORD,
        "SESSION_COOKIE_SECURE": "0",
    }

    seed = subprocess.run(
        [sys.executable, "scripts/seed.py"],
        env=env, cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    if seed.returncode != 0:
        raise RuntimeError(f"seed failed (exit {seed.returncode}): {seed.stderr[-500:]}")
    m = re.search(r"TRAINER_ID=(\d+)\s+MEMBER_IDS=([\d,]+)", seed.stdout)
    if not m:
        raise RuntimeError(f"seed stdout missing ids: {seed.stdout[-500:]!r}")
    trainer_id = int(m.group(1))
    member_ids = [int(x) for x in m.group(2).split(",") if x]
    member_id = member_ids[0] if member_ids else 1

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env, cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + READY_TIMEOUT_SEC
    ready = False
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base_url + "/login", timeout=1).read()
            ready = True
            break
        except Exception:
            time.sleep(0.2)
    if not ready:
        _terminate(proc)
        raise RuntimeError(f"uvicorn did not become ready in {READY_TIMEOUT_SEC}s")

    (probe_dir / "server.pid").write_text(str(proc.pid), encoding="utf-8")

    tasks_markdown = _TASKS_TEMPLATE.format(
        base_url=base_url,
        username=PROBE_USERNAME,
        password=PROBE_PASSWORD,
        trainer_id=trainer_id,
        member_id=member_id,
    )

    return {
        "base_url": base_url,
        "python_bin": sys.executable,
        "credentials": {"username": PROBE_USERNAME, "password": PROBE_PASSWORD},
        "context": {"trainer_id": trainer_id, "member_id": member_id},
        "tasks_markdown": tasks_markdown,
    }


def stop(run_dir: Path) -> None:
    pidfile = run_dir / "probe" / "server.pid"
    if not pidfile.exists():
        return
    try:
        pid = int(pidfile.read_text(encoding="utf-8").strip())
    except Exception:
        pidfile.unlink(missing_ok=True)
        return
    _kill_pid(pid)
    pidfile.unlink(missing_ok=True)


def _terminate(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _kill_pid(pid: int) -> None:
    try:
        os.kill(pid, 15)
    except OSError:
        return
    for _ in range(25):
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.2)
    try:
        os.kill(pid, 9)
    except OSError:
        pass


_TASKS_TEMPLATE = """\
당신은 동네 소규모 헬스장의 **관장 겸 트레이너**다. 소속 트레이너의 PT 세션 기록을 데이터로 쌓아 잠재회원에게 발전 증거를 보여주겠다는 가치제안을 받았다. 지금부터 관장 입장에서 MVP를 처음 조작한다.

- base_url: {base_url}
- username: {username}
- password: {password}
- trainer_id: {trainer_id}
- member_id: {member_id}

## T1. 로그인
`base_url/login` 열기 → 위 계정으로 로그인. 로그인 후 어디로 떨어졌는지, 관장 입장에서 자연스러운지 관찰.
종료 시 screenshot 이름: `T1_after_login`

## T2. 세션 하나 기록
현재 보이는 회원에게 오늘 PT 세션을 하나 기록하라. 예: 스쿼트 60kg × 5회 1세트, 벤치프레스 50kg × 5회 1세트. "세트 추가" 류 버튼의 발견 용이성, 저장 후 피드백의 명확성을 관찰.
종료 시 screenshot: `T2_after_save`

## T3. 대시보드 열기
방금 입력한 회원의 발전 그래프를 열어라. **어떻게 이동해야 하는지 메뉴·링크로 찾을 수 있는가**. 그래프가 잠재회원에게 상담 테이블에서 보여줄 만한 수준인가.
종료 시 screenshot: `T3_dashboard`

## T4. 본인 입력분 CSV export
가치제안에 언급된 "트레이너 본인 CSV export"를 시도. **UI에 진입 경로가 있는가**, 없으면 URL을 직접 입력해야 하는가. 다운로드까지 성공하면 OK.
종료 시 screenshot: `T4_export`

## 종합 — 상담 테이블 관점
마지막에 "상담 테이블에서 잠재회원에게 이 화면을 자신있게 보여줄 생각이 드는가 / 소속 트레이너에게 쓰라고 줄 수 있겠는가"에 대한 솔직한 1문단.
"""
