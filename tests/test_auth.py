import pytest


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
