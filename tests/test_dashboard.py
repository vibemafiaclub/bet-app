import sqlite3
import pytest


def _setup(db_path, member_name="회원A"):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.execute(
        "INSERT INTO trainers (name, created_at) VALUES (?, ?)",
        ("트레이너A", "2026-01-01"),
    )
    tid = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
        (tid, member_name, "2026-01-01"),
    )
    mid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid, mid


def _insert_session(db_path, member_id, session_date):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.execute(
        "INSERT INTO pt_sessions (member_id, session_date, created_at) VALUES (?, ?, ?)",
        (member_id, session_date, "2026-01-01"),
    )
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


def _insert_set(db_path, session_id, exercise, weight_kg, reps, set_index=0):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO session_sets (session_id, exercise, weight_kg, reps, set_index) VALUES (?, ?, ?, ?, ?)",
        (session_id, exercise, weight_kg, reps, set_index),
    )
    conn.commit()
    conn.close()


def test_empty_member_returns_empty_contract(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    r = authed_client.get(f"/trainers/{tid}/members/{mid}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    assert data["member"] == {"id": mid, "name": "회원A"}
    assert data["max_weight"] == {"labels": [], "datasets": []}
    assert data["total_volume"] == {"labels": [], "data": []}


def test_chart_data_pivot_shape(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    sid1 = _insert_session(temp_db, mid, "2026-03-27")
    _insert_set(temp_db, sid1, "스쿼트", 60, 5, 0)
    _insert_set(temp_db, sid1, "벤치프레스", 50, 5, 1)
    sid2 = _insert_session(temp_db, mid, "2026-03-30")
    _insert_set(temp_db, sid2, "스쿼트", 62.5, 5, 0)
    _insert_set(temp_db, sid2, "벤치프레스", 52.5, 5, 1)

    r = authed_client.get(f"/trainers/{tid}/members/{mid}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    assert len(data["max_weight"]["labels"]) == 2
    assert len(data["max_weight"]["datasets"]) == 2
    for ds in data["max_weight"]["datasets"]:
        assert len(ds["data"]) == 2


def test_chart_data_labels_match(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    sid1 = _insert_session(temp_db, mid, "2026-03-27")
    _insert_set(temp_db, sid1, "스쿼트", 60, 5)
    sid2 = _insert_session(temp_db, mid, "2026-03-30")
    _insert_set(temp_db, sid2, "스쿼트", 62.5, 5)

    r = authed_client.get(f"/trainers/{tid}/members/{mid}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    assert data["max_weight"]["labels"] == data["total_volume"]["labels"]


def test_chart_data_max_weight_is_max_of_sets(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    sid = _insert_session(temp_db, mid, "2026-03-27")
    _insert_set(temp_db, sid, "스쿼트", 60, 5, 0)
    _insert_set(temp_db, sid, "스쿼트", 70, 3, 1)

    r = authed_client.get(f"/trainers/{tid}/members/{mid}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    squat_ds = next(ds for ds in data["max_weight"]["datasets"] if ds["label"] == "스쿼트")
    assert squat_ds["data"][0] == 70.0


def test_chart_data_volume_sums_reps(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    sid = _insert_session(temp_db, mid, "2026-03-27")
    _insert_set(temp_db, sid, "스쿼트", 60, 5, 0)
    _insert_set(temp_db, sid, "스쿼트", 70, 3, 1)

    r = authed_client.get(f"/trainers/{tid}/members/{mid}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    assert data["total_volume"]["data"][0] == 510.0


def test_chart_data_missing_exercise_yields_null(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    sid1 = _insert_session(temp_db, mid, "2026-03-27")
    _insert_set(temp_db, sid1, "벤치프레스", 50, 5)
    sid2 = _insert_session(temp_db, mid, "2026-03-30")
    _insert_set(temp_db, sid2, "스쿼트", 60, 5)

    r = authed_client.get(f"/trainers/{tid}/members/{mid}/chart-data.json")
    assert r.status_code == 200
    data = r.json()
    labels = data["max_weight"]["labels"]
    assert labels == ["2026-03-27", "2026-03-30"]

    bench_ds = next(ds for ds in data["max_weight"]["datasets"] if ds["label"] == "벤치프레스")
    squat_ds = next(ds for ds in data["max_weight"]["datasets"] if ds["label"] == "스쿼트")
    assert bench_ds["data"] == [50.0, None]
    assert squat_ds["data"] == [None, 60.0]


def test_dashboard_html_renders_canvases(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    r = authed_client.get(f"/trainers/{tid}/members/{mid}/dashboard")
    assert r.status_code == 200
    html = r.text
    assert 'id="max-weight-chart"' in html
    assert 'id="total-volume-chart"' in html


def test_dashboard_includes_chartjs_cdn(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    r = authed_client.get(f"/trainers/{tid}/members/{mid}/dashboard")
    assert r.status_code == 200
    assert "chart.js@4." in r.text


def test_unknown_member_returns_404(authed_client, temp_db):
    tid, mid = _setup(temp_db)
    r = authed_client.get(f"/trainers/{tid}/members/99999/chart-data.json")
    assert r.status_code == 404


def test_protected_route_requires_auth(client, temp_db):
    tid, mid = _setup(temp_db)
    r = client.get(
        f"/trainers/{tid}/members/{mid}/chart-data.json",
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
