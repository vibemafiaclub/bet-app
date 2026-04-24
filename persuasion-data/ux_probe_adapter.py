"""persuasion-review 5a0 UX probe 어댑터 (이 프로젝트 전용).

계약: start(run_dir) -> env dict / stop(run_dir) -> None.
공통 plumbing은 `.claude/skills/persuasion-review/scripts/probe_harness.py` 를
재사용한다. run_simulation.py 가 skill scripts 경로를 sys.path 에 미리 주입하므로
여기서는 그냥 `from probe_harness import ...` 로 쓴다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 보통은 run_simulation.py가 skill scripts 디렉토리를 sys.path에 주입해서
# `from probe_harness import ...` 가 바로 성공한다.
# @TODO REMOVE LEGACY: 아래 fallback은 rename 직후 '아직 sys.path 주입을 안 하던
# 구 버전 run_simulation.py' 프로세스가 in-flight로 살아있을 때를 위한 호환 코드.
# 해당 상황이 사라지면(= 모든 진행 중 시뮬이 새 run_simulation.py로 재시작된 뒤) 삭제.
try:
    from probe_harness import (  # type: ignore[import-not-found]
        free_port,
        load_seed_result,
        spawn_and_wait_ready,
        stop_by_pidfile,
    )
except ImportError:
    import importlib.util as _il
    _harness_path = REPO_ROOT / ".claude" / "skills" / "persuasion-review" / "scripts" / "probe_harness.py"
    _spec = _il.spec_from_file_location("probe_harness", _harness_path)
    _mod = _il.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    free_port = _mod.free_port
    load_seed_result = _mod.load_seed_result
    spawn_and_wait_ready = _mod.spawn_and_wait_ready
    stop_by_pidfile = _mod.stop_by_pidfile

TASKS_PATH = REPO_ROOT / "persuasion-data" / "probe_tasks.md"
READY_TIMEOUT_SEC = 15
PROBE_USERNAME = "probeadmin"
PROBE_PASSWORD = "probepw"


def start(run_dir: Path) -> dict:
    probe_dir = run_dir / "probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    db_path = probe_dir / "bet.db"
    if db_path.exists():
        db_path.unlink()

    port = free_port()
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
        env=env,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if seed.returncode != 0:
        raise RuntimeError(f"seed failed (exit {seed.returncode}): {seed.stderr[-500:]}")
    seed_result = load_seed_result(seed.stdout)
    trainer_id = seed_result["trainer_id"]
    member_ids = seed_result.get("member_ids") or []
    member_id = member_ids[0] if member_ids else 1

    base_url = f"http://127.0.0.1:{port}"
    spawn_and_wait_ready(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        cwd=str(REPO_ROOT),
        ready_url=base_url + "/login",
        timeout_sec=READY_TIMEOUT_SEC,
        pidfile=probe_dir / "server.pid",
    )

    tasks_markdown = TASKS_PATH.read_text(encoding="utf-8").format(
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
    stop_by_pidfile(run_dir / "probe" / "server.pid")
