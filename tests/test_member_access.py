import sqlite3
from datetime import datetime

import app.auth as auth_module


def _seed_trainer(db_path, username: str, password: str, is_owner: int = 0) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, username, auth_module.hash_password(password), is_owner, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _seed_member(db_path, trainer_id: int, name: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
            (trainer_id, name, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _login(client, username: str, password: str) -> None:
    r = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert r.status_code == 303


def _logout(client) -> None:
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 303


def test_log_get_403_for_other_trainer_member(client, temp_db):
    _seed_trainer(temp_db, "trainerA", "pwA")
    tidB = _seed_trainer(temp_db, "trainerB", "pwB")
    midB = _seed_member(temp_db, tidB, "MemberB")
    _login(client, "trainerA", "pwA")
    r = client.get(f"/trainers/{tidB}/members/{midB}/log")
    assert r.status_code == 403
    assert "forbidden" in r.text


def test_log_post_403_no_db_mutation(client, temp_db):
    _seed_trainer(temp_db, "trainerA", "pwA")
    tidB = _seed_trainer(temp_db, "trainerB", "pwB")
    midB = _seed_member(temp_db, tidB, "MemberB")
    _login(client, "trainerA", "pwA")
    r = client.post(
        f"/trainers/{tidB}/members/{midB}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["스쿼트"],
            "weight_kg": ["60"],
            "reps": ["10"],
        },
    )
    assert r.status_code == 403
    conn = sqlite3.connect(str(temp_db))
    try:
        assert conn.execute("SELECT COUNT(*) FROM pt_sessions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM session_sets").fetchone()[0] == 0
    finally:
        conn.close()


def test_chart_data_403_for_other_trainer_member(client, temp_db):
    _seed_trainer(temp_db, "trainerA", "pwA")
    tidB = _seed_trainer(temp_db, "trainerB", "pwB")
    midB = _seed_member(temp_db, tidB, "MemberB")
    _login(client, "trainerA", "pwA")
    r = client.get(f"/trainers/{tidB}/members/{midB}/chart-data.json")
    assert r.status_code == 403
    assert "forbidden" in r.text


def test_dashboard_403_for_other_trainer_member(client, temp_db):
    _seed_trainer(temp_db, "trainerA", "pwA")
    tidB = _seed_trainer(temp_db, "trainerB", "pwB")
    midB = _seed_member(temp_db, tidB, "MemberB")
    _login(client, "trainerA", "pwA")
    r = client.get(f"/trainers/{tidB}/members/{midB}/dashboard")
    assert r.status_code == 403
    assert "forbidden" in r.text


def test_self_owned_member_all_routes_200(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    midA = _seed_member(temp_db, tidA, "MemberA")
    _login(client, "trainerA", "pwA")

    r = client.get(f"/trainers/{tidA}/members/{midA}/log")
    assert r.status_code == 200
    assert "MemberA" in r.text

    r = client.post(
        f"/trainers/{tidA}/members/{midA}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["스쿼트"],
            "weight_kg": ["60"],
            "reps": ["10"],
        },
    )
    assert r.status_code == 200

    r = client.get(f"/trainers/{tidA}/members/{midA}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    assert "member" in data

    r = client.get(f"/trainers/{tidA}/members/{midA}/dashboard")
    assert r.status_code == 200


def test_owner_bypass_other_trainer_member_all_routes_200(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    midA = _seed_member(temp_db, tidA, "MemberA")
    _login(client, "admin", "pw1234")

    r = client.get(f"/trainers/{tidA}/members/{midA}/log")
    assert r.status_code == 200

    r = client.get(f"/trainers/{tidA}/members/{midA}/chart-data.json")
    assert r.status_code == 200

    r = client.get(f"/trainers/{tidA}/members/{midA}/dashboard")
    assert r.status_code == 200


def test_owner_wrong_tid_returns_404(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    midA = _seed_member(temp_db, tidA, "MemberA")
    _login(client, "admin", "pw1234")
    r = client.get(f"/trainers/999/members/{midA}/log")
    assert r.status_code == 404
    assert "회원을 찾을 수 없습니다" in r.text


def test_unauthenticated_redirects_to_login(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    midA = _seed_member(temp_db, tidA, "MemberA")

    for url in [
        f"/trainers/{tidA}/members/{midA}/log",
        f"/trainers/{tidA}/members/{midA}/chart-data.json",
        f"/trainers/{tidA}/members/{midA}/dashboard",
    ]:
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/login"

    r = client.post(
        f"/trainers/{tidA}/members/{midA}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["스쿼트"],
            "weight_kg": ["60"],
            "reps": ["10"],
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_nonexistent_mid_returns_404(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    _login(client, "trainerA", "pwA")
    r = client.get(f"/trainers/{tidA}/members/99999/log")
    assert r.status_code == 404
    assert r.status_code != 403
    assert "회원을 찾을 수 없습니다" in r.text


def test_index_redirect_for_non_owner(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    midA = _seed_member(temp_db, tidA, "MemberA")
    _login(client, "trainerA", "pwA")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/trainers/{tidA}/members/{midA}/log"


def test_index_redirect_for_owner(client, temp_db):
    tidA = _seed_trainer(temp_db, "trainerA", "pwA")
    _seed_member(temp_db, tidA, "MemberA")
    conn = sqlite3.connect(str(temp_db))
    try:
        admin_tid = conn.execute("SELECT id FROM trainers WHERE is_owner=1 LIMIT 1").fetchone()[0]
    finally:
        conn.close()
    _seed_member(temp_db, admin_tid, "AdminMember")
    _login(client, "admin", "pw1234")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert "/trainers/" in r.headers["location"]
    assert "/log" in r.headers["location"]


def test_index_zero_members_non_owner_returns_info_page(client, temp_db):
    _seed_trainer(temp_db, "trainerA", "pwA")
    _login(client, "trainerA", "pwA")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 200
    assert "담당 회원이 아직 없습니다" in r.text
