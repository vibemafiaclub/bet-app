import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db, get_connection
from app.auth import hash_password

TODAY = date(2026, 4, 24)


def _weeks_ago(weeks: int, day_offset: int) -> str:
    return (TODAY - timedelta(weeks=weeks, days=day_offset)).isoformat()


def _session_dates() -> list[str]:
    dates = []
    for week in range(3, -1, -1):
        dates.append(_weeks_ago(week, 6))
        dates.append(_weeks_ago(week, 4))
        dates.append(_weeks_ago(week, 2))
    return dates


MEMBER_A_SESSIONS = [
    {
        "exercises": [
            ("스쿼트", [(60.0, 5), (60.0, 5), (60.0, 5)]),
            ("벤치프레스", [(50.0, 5), (50.0, 5), (50.0, 5)]),
            ("데드리프트", [(80.0, 5), (80.0, 5)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(60.0, 5), (60.0, 5), (62.5, 3)]),
            ("벤치프레스", [(50.0, 5), (52.5, 4), (52.5, 4)]),
            ("데드리프트", [(80.0, 5), (82.5, 4)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(62.5, 5), (62.5, 5), (65.0, 3)]),
            ("벤치프레스", [(52.5, 5), (52.5, 5), (55.0, 3)]),
            ("데드리프트", [(82.5, 5), (85.0, 4)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(65.0, 5), (65.0, 5), (65.0, 5)]),
            ("벤치프레스", [(55.0, 5), (55.0, 5), (55.0, 5)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(65.0, 5), (67.5, 4), (67.5, 4)]),
            ("데드리프트", [(85.0, 5), (87.5, 4)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(67.5, 5), (67.5, 5), (70.0, 3)]),
            ("벤치프레스", [(55.0, 5), (57.5, 4), (57.5, 4)]),
            ("데드리프트", [(87.5, 5), (90.0, 3)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(70.0, 5), (70.0, 5), (70.0, 5)]),
            ("벤치프레스", [(57.5, 5), (57.5, 5), (60.0, 3)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(70.0, 5), (72.5, 4), (72.5, 4)]),
            ("데드리프트", [(90.0, 5), (92.5, 3)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(72.5, 5), (72.5, 5), (75.0, 3)]),
            ("벤치프레스", [(60.0, 5), (60.0, 5), (62.5, 3)]),
            ("데드리프트", [(92.5, 5), (95.0, 3)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(75.0, 5), (75.0, 5), (75.0, 5)]),
            ("벤치프레스", [(62.5, 5), (62.5, 5), (65.0, 3)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(75.0, 5), (77.5, 4), (77.5, 4)]),
            ("데드리프트", [(95.0, 5), (97.5, 3)]),
        ]
    },
    {
        "exercises": [
            ("스쿼트", [(77.5, 5), (77.5, 5), (80.0, 3)]),
            ("벤치프레스", [(65.0, 5), (65.0, 5), (67.5, 3)]),
            ("데드리프트", [(97.5, 5), (100.0, 3)]),
        ]
    },
]

MEMBER_B_SESSIONS = [
    {
        "exercises": [
            ("벤치프레스", [(60.0, 5), (60.0, 5), (60.0, 5)]),
            ("오버헤드프레스", [(40.0, 8), (40.0, 8), (40.0, 8)]),
            ("풀업", [(1.0, 5), (1.0, 5), (1.0, 5)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 6), (60.0, 6), (60.0, 6)]),
            ("오버헤드프레스", [(40.0, 9), (40.0, 9)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 7), (60.0, 7), (60.0, 6)]),
            ("풀업", [(1.0, 6), (1.0, 6), (1.0, 5)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 8), (60.0, 8), (60.0, 7)]),
            ("오버헤드프레스", [(40.0, 10), (40.0, 10), (40.0, 9)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 8), (60.0, 8), (60.0, 8)]),
            ("풀업", [(1.0, 7), (1.0, 7), (1.0, 6)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 9), (60.0, 9), (60.0, 8)]),
            ("오버헤드프레스", [(40.0, 11), (40.0, 10), (40.0, 10)]),
            ("풀업", [(1.0, 7), (1.0, 7), (1.0, 7)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 10), (60.0, 10), (60.0, 9)]),
            ("오버헤드프레스", [(42.5, 8), (42.5, 8), (42.5, 7)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(60.0, 10), (60.0, 10), (60.0, 10)]),
            ("풀업", [(1.0, 8), (1.0, 8), (1.0, 7)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(62.5, 8), (62.5, 8), (62.5, 7)]),
            ("오버헤드프레스", [(42.5, 9), (42.5, 9), (42.5, 8)]),
            ("풀업", [(1.0, 8), (1.0, 8), (1.0, 8)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(62.5, 9), (62.5, 9), (62.5, 8)]),
            ("오버헤드프레스", [(42.5, 10), (42.5, 10), (42.5, 9)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(62.5, 10), (62.5, 10), (62.5, 9)]),
            ("풀업", [(1.0, 9), (1.0, 9), (1.0, 8)]),
        ]
    },
    {
        "exercises": [
            ("벤치프레스", [(65.0, 8), (65.0, 8), (65.0, 7)]),
            ("오버헤드프레스", [(45.0, 8), (45.0, 8), (45.0, 7)]),
            ("풀업", [(1.0, 10), (1.0, 9), (1.0, 9)]),
        ]
    },
]

MEMBER_C_SESSIONS = [
    {
        "exercises": [
            ("레그프레스", [(100.0, 10), (100.0, 10), (100.0, 10)]),
            ("랫풀다운", [(50.0, 10), (50.0, 10), (50.0, 10)]),
            ("레그컬", [(30.0, 10), (30.0, 10), (30.0, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(105.0, 10), (105.0, 10), (105.0, 10)]),
            ("랫풀다운", [(52.5, 10), (52.5, 10), (52.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(110.0, 10), (110.0, 10), (110.0, 10)]),
            ("레그컬", [(32.5, 10), (32.5, 10), (32.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(115.0, 10), (115.0, 10), (115.0, 10)]),
            ("랫풀다운", [(55.0, 10), (55.0, 10), (55.0, 10)]),
            ("레그컬", [(35.0, 10), (35.0, 10), (35.0, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(120.0, 10), (120.0, 10), (120.0, 10)]),
            ("랫풀다운", [(57.5, 10), (57.5, 10), (57.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(125.0, 10), (125.0, 10), (125.0, 10)]),
            ("레그컬", [(37.5, 10), (37.5, 10), (37.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(130.0, 10), (130.0, 10), (130.0, 10)]),
            ("랫풀다운", [(60.0, 10), (60.0, 10), (60.0, 10)]),
            ("레그컬", [(40.0, 10), (40.0, 10), (40.0, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(135.0, 10), (135.0, 10), (135.0, 10)]),
            ("랫풀다운", [(62.5, 10), (62.5, 10), (62.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(140.0, 10), (140.0, 10), (140.0, 10)]),
            ("레그컬", [(42.5, 10), (42.5, 10), (42.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(145.0, 10), (145.0, 10), (145.0, 10)]),
            ("랫풀다운", [(65.0, 10), (65.0, 10), (65.0, 10)]),
            ("레그컬", [(45.0, 10), (45.0, 10), (45.0, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(150.0, 10), (150.0, 10), (150.0, 10)]),
            ("랫풀다운", [(67.5, 10), (67.5, 10), (67.5, 10)]),
        ]
    },
    {
        "exercises": [
            ("레그프레스", [(155.0, 10), (155.0, 10), (155.0, 10)]),
            ("랫풀다운", [(70.0, 10), (70.0, 10), (70.0, 10)]),
            ("레그컬", [(47.5, 10), (47.5, 10), (47.5, 10)]),
        ]
    },
]


def main():
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_username:
        print("[seed.py] WARN: ADMIN_USERNAME not set, using fallback 'admin' for trainer.username.")
    if not admin_password:
        print(
            "[seed.py] WARN: ADMIN_PASSWORD not set — password_hash left NULL."
            " ensure_owner_seed will fill it on app boot based on env."
        )

    init_db()

    effective_username = admin_username or "admin"
    display_name = effective_username

    now_str = TODAY.isoformat() + "T00:00:00"
    dates = _session_dates()

    with get_connection() as conn:
        owner_row = conn.execute(
            "SELECT id, username, password_hash FROM trainers WHERE is_owner=1 ORDER BY id LIMIT 1"
        ).fetchone()

        if owner_row:
            trainer_id = owner_row["id"]
            if admin_username and not owner_row["username"]:
                pw_hash = hash_password(admin_password) if (admin_password and owner_row["password_hash"] is None) else owner_row["password_hash"]
                conn.execute(
                    "UPDATE trainers SET username=?, password_hash=? WHERE id=?",
                    (admin_username, pw_hash, trainer_id),
                )
        else:
            legacy_row = conn.execute(
                "SELECT id, password_hash FROM trainers WHERE name=?", ("김관장",)
            ).fetchone()
            if legacy_row:
                trainer_id = legacy_row["id"]
                pw_hash = hash_password(admin_password) if (admin_password and legacy_row["password_hash"] is None) else legacy_row["password_hash"]
                conn.execute(
                    "UPDATE trainers SET username=?, is_owner=1, password_hash=? WHERE id=?",
                    (effective_username, pw_hash, trainer_id),
                )
            else:
                pw_hash = hash_password(admin_password) if admin_password else None
                cur = conn.execute(
                    "INSERT INTO trainers (name, username, password_hash, is_owner, created_at)"
                    " VALUES (?, ?, ?, 1, ?)",
                    (display_name, effective_username, pw_hash, now_str),
                )
                trainer_id = cur.lastrowid

        member_ids = []
        for name in ("회원A", "회원B", "회원C"):
            row = conn.execute(
                "SELECT id FROM members WHERE trainer_id=? AND name=?",
                (trainer_id, name),
            ).fetchone()
            if row:
                member_ids.append(row["id"])
            else:
                cur = conn.execute(
                    "INSERT INTO members (trainer_id, name, created_at) VALUES (?, ?, ?)",
                    (trainer_id, name, now_str),
                )
                member_ids.append(cur.lastrowid)

        all_sessions = [MEMBER_A_SESSIONS, MEMBER_B_SESSIONS, MEMBER_C_SESSIONS]

        for member_id, sessions_data in zip(member_ids, all_sessions):
            existing = conn.execute(
                "SELECT COUNT(*) FROM pt_sessions WHERE member_id=?",
                (member_id,),
            ).fetchone()[0]
            if existing > 0:
                continue

            for i, session_info in enumerate(sessions_data):
                session_date = dates[i]
                cur = conn.execute(
                    "INSERT INTO pt_sessions (member_id, session_date, created_at) VALUES (?, ?, ?)",
                    (member_id, session_date, now_str),
                )
                session_id = cur.lastrowid

                set_index = 0
                for exercise, sets in session_info["exercises"]:
                    for weight_kg, reps in sets:
                        conn.execute(
                            "INSERT INTO session_sets (session_id, exercise, weight_kg, reps, set_index) VALUES (?, ?, ?, ?, ?)",
                            (session_id, exercise, weight_kg, reps, set_index),
                        )
                        set_index += 1

    # probe_harness.load_seed_result() 계약: 마지막 비공백 줄은 단일 JSON 오브젝트.
    print(json.dumps({"trainer_id": trainer_id, "member_ids": member_ids}))


if __name__ == "__main__":
    main()
