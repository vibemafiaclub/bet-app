import pytest
from app.db import get_connection
from app.exercises import EXERCISES


def _seed_trainer_member(db_path):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO trainers (name, created_at) VALUES (?, ?)",
            ("트레이너1", "2026-01-01T00:00:00"),
        )
        tid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
            (tid, "회원1", "2026-01-01T00:00:00"),
        )
        mid = cur.lastrowid
    return tid, mid


def test_log_form_renders_with_exercise_options(temp_db, authed_client):
    tid, mid = _seed_trainer_member(temp_db)
    r = authed_client.get(f"/trainers/{tid}/members/{mid}/log")
    assert r.status_code == 200
    for ex in EXERCISES:
        assert ex in r.text


def test_post_log_creates_session_and_sets(temp_db, authed_client):
    tid, mid = _seed_trainer_member(temp_db)
    r = authed_client.post(
        f"/trainers/{tid}/members/{mid}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["스쿼트", "벤치프레스"],
            "weight_kg": ["60", "50"],
            "reps": ["5", "5"],
        },
    )
    assert r.status_code == 200

    with get_connection(temp_db) as conn:
        sessions = conn.execute(
            "SELECT * FROM pt_sessions WHERE member_id=?", (mid,)
        ).fetchall()
        sets = conn.execute(
            "SELECT ss.* FROM session_sets ss JOIN pt_sessions ps ON ss.session_id = ps.id WHERE ps.member_id=?",
            (mid,),
        ).fetchall()

    assert len(sessions) == 1
    assert len(sets) == 2


def test_post_log_skips_empty_rows(temp_db, authed_client):
    tid, mid = _seed_trainer_member(temp_db)
    r = authed_client.post(
        f"/trainers/{tid}/members/{mid}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["스쿼트", "", "벤치프레스"],
            "weight_kg": ["60", "", "50"],
            "reps": ["5", "", "5"],
        },
    )
    assert r.status_code == 200

    with get_connection(temp_db) as conn:
        sets = conn.execute(
            "SELECT ss.* FROM session_sets ss JOIN pt_sessions ps ON ss.session_id = ps.id WHERE ps.member_id=?",
            (mid,),
        ).fetchall()

    assert len(sets) == 2


def test_post_log_rejects_negative_weight(temp_db, authed_client):
    tid, mid = _seed_trainer_member(temp_db)
    r = authed_client.post(
        f"/trainers/{tid}/members/{mid}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["스쿼트"],
            "weight_kg": ["-5"],
            "reps": ["5"],
        },
    )
    assert r.status_code == 400


def test_post_log_rejects_unknown_exercise(temp_db, authed_client):
    tid, mid = _seed_trainer_member(temp_db)
    r = authed_client.post(
        f"/trainers/{tid}/members/{mid}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["풀라인업"],
            "weight_kg": ["60"],
            "reps": ["5"],
        },
    )
    assert r.status_code == 400


def test_post_log_rejects_when_all_rows_empty(temp_db, authed_client):
    tid, mid = _seed_trainer_member(temp_db)
    r = authed_client.post(
        f"/trainers/{tid}/members/{mid}/log",
        data={
            "session_date": "2026-04-24",
            "exercise": ["", ""],
            "weight_kg": ["", ""],
            "reps": ["", ""],
        },
    )
    assert r.status_code == 400
