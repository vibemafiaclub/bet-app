# ORDER BY ea.id DESC는 AUTOINCREMENT id에 의존한다. id 컬럼 정의 변경 시 아래 시나리오 #7 (LIMIT)이 깨질 수 있다.
import csv
import io
import sqlite3
from datetime import datetime

from app.auth import hash_password
from app.db import get_connection
from app.routes import MY_AUDIT_LOG_LIMIT


def _insert_trainer(db_path, username, password, name, is_owner=0):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, username, hash_password(password), is_owner, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def _insert_member(db_path, trainer_id, name="회원1"):
    with get_connection(db_path) as c:
        cur = c.execute(
            "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
            (trainer_id, name, "2026-04-01T00:00:00"),
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


def _owner_trainer_id(db_path):
    with get_connection(db_path) as c:
        return c.execute("SELECT id FROM trainers WHERE is_owner=1 LIMIT 1").fetchone()["id"]


def _login(client, username, password):
    r = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert r.status_code == 303, f"login failed: {r.status_code} {r.text}"


def _logout(client):
    client.post("/logout", follow_redirects=False)


def _fetch_audit_rows(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM export_audit ORDER BY id").fetchall()
    finally:
        conn.close()


def _count_audit_rows(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM export_audit").fetchone()[0]
    finally:
        conn.close()


def test_admin_export_with_trainer_id_inserts_audit_row(temp_db, client):
    x_id = _insert_trainer(temp_db, "staff_x", "xpw", "X직원")
    x_member = _insert_member(temp_db, x_id)
    _insert_session_with_set(temp_db, x_member, "스쿼트", 60, 5, x_id)
    _insert_session_with_set(temp_db, x_member, "벤치프레스", 50, 5, x_id, session_date="2026-04-11")

    _login(client, "admin", "pw1234")
    client.app.state.export_last_ts.clear()

    r = client.get(f"/admin/export/sessions.csv?trainer_id={x_id}")
    assert r.status_code == 200

    rows = _fetch_audit_rows(temp_db)
    assert len(rows) == 1
    assert rows[0]["action"] == "owner_export"
    assert rows[0]["actor_trainer_id"] == _owner_trainer_id(temp_db)
    assert rows[0]["target_trainer_id"] == x_id
    assert rows[0]["rows"] == 2


def test_admin_export_without_trainer_id_inserts_audit_row_target_null(temp_db, client):
    owner_id = _owner_trainer_id(temp_db)
    x_id = _insert_trainer(temp_db, "staff_x", "xpw", "X직원")
    owner_member = _insert_member(temp_db, owner_id, "관장회원")
    x_member = _insert_member(temp_db, x_id, "X회원")
    _insert_session_with_set(temp_db, owner_member, "스쿼트", 60, 5, owner_id)
    _insert_session_with_set(temp_db, x_member, "벤치프레스", 50, 5, x_id, session_date="2026-04-11")

    _login(client, "admin", "pw1234")
    client.app.state.export_last_ts.clear()

    r = client.get("/admin/export/sessions.csv")
    assert r.status_code == 200

    rows = _fetch_audit_rows(temp_db)
    assert len(rows) == 1
    assert rows[0]["action"] == "owner_export"
    assert rows[0]["target_trainer_id"] is None
    assert rows[0]["rows"] == 2


def test_my_export_inserts_audit_row_with_self_actor_target(temp_db, client):
    a_id = _insert_trainer(temp_db, "a_t", "apw", "A트레이너")
    a_member = _insert_member(temp_db, a_id)
    _insert_session_with_set(temp_db, a_member, "스쿼트", 60, 5, input_trainer_id=a_id)

    _login(client, "a_t", "apw")
    client.app.state.my_export_last_ts.clear()

    r = client.get("/my/export/sessions.csv")
    assert r.status_code == 200

    rows = _fetch_audit_rows(temp_db)
    assert len(rows) == 1
    assert rows[0]["action"] == "my_export"
    assert rows[0]["actor_trainer_id"] == a_id
    assert rows[0]["target_trainer_id"] == a_id
    assert rows[0]["rows"] == 1


def test_my_audit_log_filters_rows_correctly(temp_db, client):
    # 3 OR 조건별 매핑:
    # target = a_id: 0 row (아무도 A를 target으로 뽑지 않음)
    # actor = a_id: 0 row
    # owner_export AND target IS NULL: 1 row (row2)
    a_id = _insert_trainer(temp_db, "a_t", "apw", "A트레이너")
    b_id = _insert_trainer(temp_db, "b_t", "bpw", "B트레이너")
    c_id = _insert_trainer(temp_db, "c_t", "cpw", "C트레이너")

    a_member = _insert_member(temp_db, a_id, "A회원")
    b_member = _insert_member(temp_db, b_id, "B회원")
    c_member = _insert_member(temp_db, c_id, "C회원")

    _insert_session_with_set(temp_db, a_member, "스쿼트", 60, 5, a_id)
    _insert_session_with_set(temp_db, b_member, "벤치프레스", 50, 5, b_id)
    _insert_session_with_set(temp_db, c_member, "데드리프트", 80, 5, c_id)

    _login(client, "admin", "pw1234")
    client.app.state.export_last_ts.clear()
    client.get(f"/admin/export/sessions.csv?trainer_id={b_id}")  # row1: owner_export, target=b_id

    client.app.state.export_last_ts.clear()
    client.get("/admin/export/sessions.csv")  # row2: owner_export, target=NULL
    _logout(client)

    _login(client, "c_t", "cpw")
    client.app.state.my_export_last_ts.clear()
    client.get("/my/export/sessions.csv")  # row3: my_export, actor=target=c_id
    _logout(client)

    _login(client, "a_t", "apw")
    r = client.get("/my/audit-log")
    assert r.status_code == 200

    # A의 /my/audit-log: target IS NULL owner_export 1건만 표시
    assert r.text.count('data-action="owner_export"') == 1
    assert r.text.count('data-action="my_export"') == 0
    assert "B트레이너" not in r.text
    assert "C트레이너" not in r.text
    assert "전체 대상(본인 포함)" in r.text


def test_my_audit_log_unauthenticated_redirects_to_login(temp_db, client):
    r = client.get("/my/audit-log", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_owner_self_target_and_null_both_visible_in_audit_log(temp_db, client):
    # 3 OR 조건 매핑:
    # row1: target = owner_id → target match ✓
    # row2: target IS NULL + owner_export → third-clause match ✓
    # row3: actor = owner_id AND target = owner_id → actor & target match ✓
    _login(client, "admin", "pw1234")
    owner_id = _owner_trainer_id(temp_db)

    x_id = _insert_trainer(temp_db, "staff_x", "xpw", "X직원")
    owner_member = _insert_member(temp_db, owner_id, "관장회원")
    x_member = _insert_member(temp_db, x_id, "X회원")
    _insert_session_with_set(temp_db, owner_member, "스쿼트", 60, 5, owner_id)
    _insert_session_with_set(temp_db, x_member, "벤치프레스", 50, 5, x_id, session_date="2026-04-11")

    client.app.state.export_last_ts.clear()
    client.get(f"/admin/export/sessions.csv?trainer_id={owner_id}")  # row1: owner_export, target=owner_id

    client.app.state.export_last_ts.clear()
    client.get("/admin/export/sessions.csv")  # row2: owner_export, target=NULL

    client.app.state.my_export_last_ts.clear()
    client.get("/my/export/sessions.csv")  # row3: my_export, actor=target=owner_id

    r = client.get("/my/audit-log")
    assert r.status_code == 200

    assert r.text.count('data-action="owner_export"') == 2
    assert r.text.count('data-action="my_export"') == 1


def test_my_audit_log_respects_limit_100(temp_db, client):
    _login(client, "admin", "pw1234")
    owner_id = _owner_trainer_id(temp_db)

    with get_connection(temp_db) as conn:
        for i in range(MY_AUDIT_LOG_LIMIT + 5):
            conn.execute(
                "INSERT INTO export_audit (created_at, action, actor_trainer_id, target_trainer_id, rows)"
                " VALUES (?, 'my_export', ?, ?, 1)",
                (f"2026-04-{(i % 28) + 1:02d}T00:00:00", owner_id, owner_id),
            )

    r = client.get("/my/audit-log")
    assert r.status_code == 200
    assert r.text.count('data-action="my_export"') == MY_AUDIT_LOG_LIMIT


def test_rows_column_matches_write_sessions_csv_return(temp_db, client):
    _login(client, "admin", "pw1234")
    owner_id = _owner_trainer_id(temp_db)

    member = _insert_member(temp_db, owner_id, "관장회원")
    _insert_session_with_set(temp_db, member, "스쿼트", 60, 5, owner_id, "2026-04-10")
    _insert_session_with_set(temp_db, member, "벤치프레스", 50, 5, owner_id, "2026-04-11")
    _insert_session_with_set(temp_db, member, "데드리프트", 80, 5, owner_id, "2026-04-12")

    client.app.state.export_last_ts.clear()
    r = client.get("/admin/export/sessions.csv")
    assert r.status_code == 200

    csv_text = r.content[3:].decode("utf-8")
    reader_rows = list(csv.reader(io.StringIO(csv_text)))
    assert len(reader_rows) == 4  # header 1 + data 3

    audit_rows = _fetch_audit_rows(temp_db)
    assert audit_rows[0]["rows"] == 3
    assert audit_rows[0]["rows"] == len(reader_rows) - 1
