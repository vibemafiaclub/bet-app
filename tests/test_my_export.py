import csv
import io
from datetime import datetime

from app.auth import hash_password
from app.db import get_connection


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


def test_my_export_requires_login(temp_db, client):
    r = client.get("/my/export/sessions.csv", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_my_export_returns_only_own_rows(temp_db, client):
    a_id = _insert_trainer(temp_db, "a_t", "apw", "A트레이너")
    b_id = _insert_trainer(temp_db, "b_t", "bpw", "B트레이너")
    a_member = _insert_member(temp_db, a_id, "A회원")
    b_member = _insert_member(temp_db, b_id, "B회원")
    _insert_session_with_set(temp_db, a_member, "스쿼트", 60, 5, a_id, "2026-04-10")
    _insert_session_with_set(temp_db, b_member, "벤치프레스", 50, 5, b_id, "2026-04-11")

    _login(client, "a_t", "apw")

    r = client.get("/my/export/sessions.csv")
    assert r.status_code == 200
    assert r.content[:3] == b"\xef\xbb\xbf"

    csv_text = r.content[3:].decode("utf-8")
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert rows[0] == [
        "session_date", "member_name", "exercise", "weight_kg", "reps", "set_index", "input_trainer_name"
    ]
    assert len(rows) == 2
    assert rows[1][1] == "A회원"
    assert rows[1][2] == "스쿼트"
    assert rows[1][6] == "A트레이너"


def test_my_export_owner_only_sees_own_input(temp_db, client):
    owner_id = _owner_trainer_id(temp_db)
    x_id = _insert_trainer(temp_db, "staff_x", "xpw", "X직원")
    member = _insert_member(temp_db, owner_id, "공용회원")
    _insert_session_with_set(temp_db, member, "스쿼트", 60, 5, owner_id, "2026-04-10")
    _insert_session_with_set(temp_db, member, "벤치프레스", 50, 5, x_id, "2026-04-11")

    _login(client, "admin", "pw1234")

    r = client.get("/my/export/sessions.csv")
    assert r.status_code == 200

    csv_text = r.content[3:].decode("utf-8")
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert len(rows) == 2, "is_owner bypass 감지됨 — 관장 본인 row 1건만 나와야 함"
    assert rows[1][2] == "스쿼트"
    assert rows[1][6] == "admin"


def test_my_export_bom_and_headers(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    member = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member, "스쿼트", 60, 5, owner_id)

    r = authed_client.get("/my/export/sessions.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.content[:3] == b"\xef\xbb\xbf"
    disposition = r.headers["content-disposition"]
    assert 'filename="my_sessions_' in disposition
    assert disposition.endswith('.csv"')
    assert "_trainer_" not in disposition


def test_my_export_rate_limit_429(temp_db, authed_client):
    owner_id = _owner_trainer_id(temp_db)
    member = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member, "스쿼트", 60, 5, owner_id)

    r1 = authed_client.get("/my/export/sessions.csv")
    assert r1.status_code == 200

    r2 = authed_client.get("/my/export/sessions.csv")
    assert r2.status_code == 429
    assert "Too Many Requests" in r2.text


def test_my_export_rate_limit_independent_from_admin(temp_db, authed_client):
    # export_last_ts / my_export_last_ts 두 dict가 물리적으로 분리돼
    # 상호 영향이 없음을 직접 증명한다. 미래에 누가 dict 통합을 시도하면
    # 이 테스트가 회귀 신호를 낸다.
    owner_id = _owner_trainer_id(temp_db)
    member = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member, "스쿼트", 60, 5, owner_id)

    authed_client.app.state.export_last_ts.clear()
    authed_client.app.state.my_export_last_ts.clear()

    # 호출 A — 관장 dict 기록 개시 (관장 dict: 살아있음, 본인 dict: 비어있음)
    r_admin_first = authed_client.get("/admin/export/sessions.csv")
    assert r_admin_first.status_code == 200

    # 호출 B — 본인 dict 기록 개시. 관장 dict가 살아있어도 본인 dict는 독립.
    # (관장 dict: 살아있음, 본인 dict: 살아있음)
    r_my_first = authed_client.get("/my/export/sessions.csv")
    assert r_my_first.status_code == 200, "관장 rate limit이 본인 라우트에 전이됨"

    # 호출 C — 본인 dict 60초 제한 작동 (본인 dict: 살아있음)
    r_my_second = authed_client.get("/my/export/sessions.csv")
    assert r_my_second.status_code == 429

    # 호출 D — 관장 dict도 여전히 60초 살아있음
    r_admin_second = authed_client.get("/admin/export/sessions.csv")
    assert r_admin_second.status_code == 429


def test_my_export_stdout_log(temp_db, authed_client, capsys):
    owner_id = _owner_trainer_id(temp_db)
    member = _insert_member(temp_db, owner_id)
    _insert_session_with_set(temp_db, member, "스쿼트", 60, 5, owner_id, "2026-04-10")
    _insert_session_with_set(temp_db, member, "벤치프레스", 50, 5, owner_id, "2026-04-11")

    capsys.readouterr()
    authed_client.get("/my/export/sessions.csv")

    captured = capsys.readouterr()
    assert f"[my-export] trainer_id={owner_id}" in captured.out
    assert "rows=2" in captured.out


def test_my_export_empty_when_no_input_rows(temp_db, authed_client, capsys):
    owner_id = _owner_trainer_id(temp_db)
    _insert_member(temp_db, owner_id)

    capsys.readouterr()
    r = authed_client.get("/my/export/sessions.csv")
    assert r.status_code == 200

    csv_text = r.content[3:].decode("utf-8")
    rows = list(csv.reader(io.StringIO(csv_text)))
    assert len(rows) == 1, "header row 1개만 나와야 함"

    captured = capsys.readouterr()
    assert "rows=0" in captured.out


def test_my_export_admin_column_parity_regression(temp_db, client):
    # CTO 조건 3 — 공통 헬퍼 drift 회귀 감시.
    # 양쪽 dict clear는 안전망이며, rate limit 분리 자체는
    # test_my_export_rate_limit_independent_from_admin에서 검증한다.
    # 본 테스트의 비교 대상은 응답 body만이며 Content-Disposition은
    # 라우트별로 의도적으로 다르므로 별도 검증한다.
    x_id = _insert_trainer(temp_db, "staff_x", "xpw", "X직원")
    x_member = _insert_member(temp_db, x_id, "X회원")
    _insert_session_with_set(temp_db, x_member, "스쿼트", 60, 5, x_id, "2026-04-10")
    _insert_session_with_set(temp_db, x_member, "벤치프레스", 50, 5, x_id, "2026-04-11")

    client.app.state.export_last_ts.clear()
    client.app.state.my_export_last_ts.clear()

    _login(client, "admin", "pw1234")
    admin_resp = client.get(f"/admin/export/sessions.csv?trainer_id={x_id}")
    assert admin_resp.status_code == 200

    client.app.state.export_last_ts.clear()
    client.app.state.my_export_last_ts.clear()
    _logout(client)

    _login(client, "staff_x", "xpw")
    my_resp = client.get("/my/export/sessions.csv")
    assert my_resp.status_code == 200

    # body bit-exact 검증 (BOM 포함 전체)
    assert admin_resp.content == my_resp.content, (
        "관장 /admin/export?trainer_id=X body와 X /my/export body가 다르다 — 공통 헬퍼 drift 발생"
    )

    # Content-Disposition 차이는 의도된 것 — 별도 검증
    admin_disposition = admin_resp.headers["content-disposition"]
    my_disposition = my_resp.headers["content-disposition"]
    assert admin_disposition != my_disposition
    assert f"_trainer_{x_id}" in admin_disposition
    assert "my_sessions_" in my_disposition
    assert "_trainer_" not in my_disposition
