import csv
import io
from datetime import datetime

from app.auth import hash_password
from app.db import get_connection


def _insert_non_owner(db_path, username="stafft", password="spw", name="직원"):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 0, ?)",
            (name, username, hash_password(password), datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def _insert_session_with_set(
    db_path, member_id, exercise, weight, reps, input_trainer_id=None, session_date="2026-04-10"
):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO pt_sessions (member_id, session_date, created_at, input_trainer_id) VALUES (?, ?, ?, ?)",
            (member_id, session_date, "2026-04-10T00:00:00", input_trainer_id),
        )
        session_id = cur.lastrowid
        c.execute(
            "INSERT INTO session_sets (session_id, exercise, weight_kg, reps, set_index) VALUES (?, ?, ?, ?, 0)",
            (session_id, exercise, weight, reps),
        )


def _insert_member(db_path, trainer_id, name="회원1"):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
            (trainer_id, name, "2026-04-01T00:00:00"),
        )
        return cur.lastrowid


def _owner_trainer_id(db_path):
    with get_connection(db_path) as c:
        return c.execute("SELECT id FROM trainers WHERE is_owner=1 LIMIT 1").fetchone()["id"]


def test_export_requires_owner(temp_db, client):
    _insert_non_owner(temp_db)
    r = client.post("/login", data={"username": "stafft", "password": "spw"}, follow_redirects=False)
    assert r.status_code == 303

    r = client.get("/admin/export/sessions.csv", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_export_returns_csv_with_bom(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    member_id = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member_id, "스쿼트", 60, 5, owner_id)

    r = authed_client.get("/admin/export/sessions.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.content[:3] == b"\xef\xbb\xbf"
    assert 'filename="sessions_' in r.headers["content-disposition"]
    assert r.headers["content-disposition"].endswith('.csv"')

    csv_text = r.content[3:].decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0] == [
        "session_date", "member_name", "exercise", "weight_kg", "reps", "set_index", "input_trainer_name"
    ]
    assert len(rows) == 2
    assert rows[1][1] == "회원1"
    assert rows[1][2] == "스쿼트"
    assert rows[1][6] == "admin"


def test_export_filter_by_trainer_id(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    non_owner_id = _insert_non_owner(temp_db)
    member_id = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member_id, "스쿼트", 60, 5, owner_id, "2026-04-10")
    _insert_session_with_set(temp_db, member_id, "벤치프레스", 50, 5, non_owner_id, "2026-04-11")

    r = authed_client.get(f"/admin/export/sessions.csv?trainer_id={non_owner_id}")
    assert r.status_code == 200

    csv_text = r.content[3:].decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[1][2] == "벤치프레스"
    assert rows[1][6] == "직원"
    assert f"_trainer_{non_owner_id}" in r.headers["content-disposition"]


def test_export_rate_limit_429(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    member_id = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member_id, "스쿼트", 60, 5, owner_id)

    r1 = authed_client.get("/admin/export/sessions.csv")
    assert r1.status_code == 200

    r2 = authed_client.get("/admin/export/sessions.csv")
    assert r2.status_code == 429
    assert "Too Many Requests" in r2.text


def test_export_rate_limit_resets_per_owner(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    member_id = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member_id, "스쿼트", 60, 5, owner_id)

    r1 = authed_client.get("/admin/export/sessions.csv")
    assert r1.status_code == 200

    authed_client.app.state.export_last_ts.clear()

    r2 = authed_client.get("/admin/export/sessions.csv")
    assert r2.status_code == 200


def test_export_stdout_log(temp_db, authed_client, capsys):
    owner_id = _owner_trainer_id(temp_db)
    member_id = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member_id, "스쿼트", 60, 5, owner_id)

    capsys.readouterr()
    authed_client.get("/admin/export/sessions.csv")

    captured = capsys.readouterr()
    assert f"[export] owner_id={owner_id}" in captured.out
    assert "target_trainer_id=all" in captured.out
    assert "rows=1" in captured.out


def test_export_null_input_trainer_id_row_has_empty_name(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    member_id = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member_id, "스쿼트", 60, 5, None)

    r = authed_client.get("/admin/export/sessions.csv")
    assert r.status_code == 200

    csv_text = r.content[3:].decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[1][6] == ""
