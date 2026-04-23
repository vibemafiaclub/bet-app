import sqlite3
import pytest
from app.db import get_connection
from app.aggregates import max_weight_per_session, total_volume_per_session


def _insert_trainer(conn):
    cur = conn.execute(
        "INSERT INTO trainers (name, created_at) VALUES (?, ?)",
        ("테스트관장", "2026-01-01T00:00:00"),
    )
    return cur.lastrowid


def _insert_member(conn, trainer_id, name="테스트회원"):
    cur = conn.execute(
        "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
        (trainer_id, name, "2026-01-01T00:00:00"),
    )
    return cur.lastrowid


def _insert_session(conn, member_id, session_date):
    cur = conn.execute(
        "INSERT INTO pt_sessions (member_id, session_date, created_at) VALUES (?, ?, ?)",
        (member_id, session_date, "2026-01-01T00:00:00"),
    )
    return cur.lastrowid


def _insert_set(conn, session_id, exercise, weight_kg, reps, set_index):
    conn.execute(
        "INSERT INTO session_sets (session_id, exercise, weight_kg, reps, set_index) VALUES (?, ?, ?, ?, ?)",
        (session_id, exercise, weight_kg, reps, set_index),
    )


def test_empty_member_returns_empty_lists(temp_db):
    with get_connection(temp_db) as conn:
        trainer_id = _insert_trainer(conn)
        member_id = _insert_member(conn, trainer_id)

    with get_connection(temp_db) as conn:
        assert max_weight_per_session(conn, member_id) == []
        assert total_volume_per_session(conn, member_id) == []


def test_max_weight_picks_heaviest_set(temp_db):
    with get_connection(temp_db) as conn:
        trainer_id = _insert_trainer(conn)
        member_id = _insert_member(conn, trainer_id)
        session_id = _insert_session(conn, member_id, "2026-04-01")
        _insert_set(conn, session_id, "스쿼트", 60.0, 5, 0)
        _insert_set(conn, session_id, "스쿼트", 60.0, 5, 1)
        _insert_set(conn, session_id, "스쿼트", 70.0, 3, 2)

    with get_connection(temp_db) as conn:
        result = max_weight_per_session(conn, member_id)

    assert len(result) == 1
    assert result[0]["exercise"] == "스쿼트"
    assert result[0]["max_weight"] == 70.0


def test_total_volume_sums_weight_times_reps(temp_db):
    with get_connection(temp_db) as conn:
        trainer_id = _insert_trainer(conn)
        member_id = _insert_member(conn, trainer_id)
        session_id = _insert_session(conn, member_id, "2026-04-01")
        _insert_set(conn, session_id, "스쿼트", 60.0, 5, 0)
        _insert_set(conn, session_id, "스쿼트", 60.0, 5, 1)
        _insert_set(conn, session_id, "스쿼트", 70.0, 3, 2)

    with get_connection(temp_db) as conn:
        result = total_volume_per_session(conn, member_id)

    assert len(result) == 1
    assert result[0]["total_volume"] == pytest.approx(810.0)


def test_labels_ascending_by_date(temp_db):
    with get_connection(temp_db) as conn:
        trainer_id = _insert_trainer(conn)
        member_id = _insert_member(conn, trainer_id)
        session_id_1 = _insert_session(conn, member_id, "2026-04-10")
        _insert_set(conn, session_id_1, "벤치프레스", 50.0, 5, 0)
        session_id_2 = _insert_session(conn, member_id, "2026-04-03")
        _insert_set(conn, session_id_2, "벤치프레스", 48.0, 5, 0)

    with get_connection(temp_db) as conn:
        max_result = max_weight_per_session(conn, member_id)
        vol_result = total_volume_per_session(conn, member_id)

    assert max_result[0]["session_date"] == "2026-04-03"
    assert max_result[1]["session_date"] == "2026-04-10"
    assert vol_result[0]["session_date"] == "2026-04-03"
    assert vol_result[1]["session_date"] == "2026-04-10"


def test_check_constraint_rejects_negative_weight(temp_db):
    with get_connection(temp_db) as conn:
        trainer_id = _insert_trainer(conn)
        member_id = _insert_member(conn, trainer_id)
        session_id = _insert_session(conn, member_id, "2026-04-01")

    with pytest.raises(sqlite3.IntegrityError):
        with get_connection(temp_db) as conn:
            _insert_set(conn, session_id, "스쿼트", -5.0, 5, 0)


def test_check_constraint_rejects_unknown_exercise(temp_db):
    with get_connection(temp_db) as conn:
        trainer_id = _insert_trainer(conn)
        member_id = _insert_member(conn, trainer_id)
        session_id = _insert_session(conn, member_id, "2026-04-01")

    with pytest.raises(sqlite3.IntegrityError):
        with get_connection(temp_db) as conn:
            _insert_set(conn, session_id, "풀라인업", 60.0, 5, 0)
