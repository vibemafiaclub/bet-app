import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app import db as db_module


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
