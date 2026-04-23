import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app import db as db_module

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    """Module-scoped uvicorn subprocess with isolated DB + seed."""
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

    r = subprocess.run(
        [sys.executable, "scripts/seed.py"],
        env=env, cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, f"seed failed: {r.stderr}"
    m = re.search(r"TRAINER_ID=(\d+)\s+MEMBER_IDS=([\d,]+)", r.stdout)
    assert m, f"seed stdout missing id line: {r.stdout!r}"
    trainer_id = int(m.group(1))
    member_ids = [int(x) for x in m.group(2).split(",")]

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env, cwd=str(ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )

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


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """각 테스트마다 별도 temp sqlite file + init_db 실행."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    db_module.init_db(db_path)
    yield db_path


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
