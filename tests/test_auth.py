from datetime import datetime

import pytest

from app.auth import hash_password
from app.db import get_connection


def test_login_page_renders(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_wrong_credential_rerenders_form(client):
    r = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 200
    assert "올바르지 않습니다" in r.text


def test_correct_credential_sets_session_and_redirects(client):
    r = client.post(
        "/login",
        data={"username": "admin", "password": "pw1234"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_protected_route_redirects_when_unauth(client):
    r = client.get("/trainers/1/members/1/log", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_logout_clears_session(authed_client):
    r = authed_client.post("/logout", follow_redirects=False)
    assert r.status_code == 303
    r2 = authed_client.get("/trainers/1/members/1/log", follow_redirects=False)
    assert r2.status_code == 303
    assert "/login" in r2.headers["location"]


def test_missing_env_raises_runtime_error(temp_db, monkeypatch):
    monkeypatch.setenv("APP_SESSION_SECRET", "test-secret-xxxxxxxxxxxxxxxx")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw1234")
    import app.main  # noqa: ensure module is cached with valid env
    monkeypatch.delenv("APP_SESSION_SECRET")
    with pytest.raises(RuntimeError):
        app.main.create_app()


def test_boot_seeds_owner_when_absent(client, temp_db):
    """create_app 부팅 후 trainers에 is_owner=1, username=admin, password_hash 존재."""
    with get_connection(temp_db) as c:
        row = c.execute("SELECT username, password_hash FROM trainers WHERE is_owner=1").fetchone()
    assert row is not None
    assert row["username"] == "admin"
    assert row["password_hash"] is not None
    assert row["password_hash"] != ""


def test_boot_preserves_existing_owner_password(temp_db, monkeypatch):
    """기존 관장의 password_hash는 두 번째 부팅 시 유지된다."""
    monkeypatch.setenv("APP_SESSION_SECRET", "test-secret-xxxxxxxxxxxxxxxx")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw1234")
    from app.main import create_app

    create_app()
    with get_connection(temp_db) as c:
        hash1 = c.execute("SELECT password_hash FROM trainers WHERE is_owner=1").fetchone()["password_hash"]

    create_app()
    with get_connection(temp_db) as c:
        hash2 = c.execute("SELECT password_hash FROM trainers WHERE is_owner=1").fetchone()["password_hash"]

    assert hash1 == hash2


def test_boot_warns_on_username_mismatch(temp_db, monkeypatch, capsys):
    """is_owner=1 row의 username과 env ADMIN_USERNAME이 다르면 warn + skip."""
    with get_connection(temp_db) as c:
        c.execute(
            "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 1, ?)",
            ("alice", "alice", hash_password("apw"), datetime.utcnow().isoformat()),
        )

    monkeypatch.setenv("APP_SESSION_SECRET", "test-secret-xxxxxxxxxxxxxxxx")
    monkeypatch.setenv("ADMIN_USERNAME", "bob")
    monkeypatch.setenv("ADMIN_PASSWORD", "bobpw")
    from app.main import create_app

    app = create_app()
    assert app is not None

    captured = capsys.readouterr()
    assert "ADMIN_USERNAME mismatch" in captured.out

    with get_connection(temp_db) as c:
        alice_row = c.execute("SELECT is_owner FROM trainers WHERE username='alice'").fetchone()
        bob_row = c.execute("SELECT id FROM trainers WHERE username='bob'").fetchone()
    assert alice_row["is_owner"] == 1
    assert bob_row is None


def test_non_owner_trainer_login(client, temp_db):
    """non-owner 계정으로 로그인하면 보호 라우트에 접근 가능(session 활성)."""
    with get_connection(temp_db) as c:
        c.execute(
            "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 0, ?)",
            ("직원", "stafft", hash_password("spw"), datetime.utcnow().isoformat()),
        )

    r = client.post("/login", data={"username": "stafft", "password": "spw"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"

    r2 = client.get("/", follow_redirects=False)
    assert r2.status_code == 200
