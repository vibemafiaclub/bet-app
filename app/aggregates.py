import sqlite3


def max_weight_per_session(conn: sqlite3.Connection, member_id: int) -> list[dict]:
    """
    Returns:
      [
        {"session_date": "YYYY-MM-DD", "exercise": "스쿼트", "max_weight": 70.0},
        ...
      ]
    세션 날짜 오름차순, 같은 날짜 내에서는 exercise 이름 오름차순.
    """
    rows = conn.execute(
        """
        SELECT ps.session_date, ss.exercise, MAX(ss.weight_kg) AS max_weight
        FROM session_sets ss
        JOIN pt_sessions ps ON ps.id = ss.session_id
        WHERE ps.member_id = ?
        GROUP BY ps.session_date, ss.exercise
        ORDER BY ps.session_date ASC, ss.exercise ASC
        """,
        (member_id,),
    ).fetchall()
    return [{"session_date": r["session_date"], "exercise": r["exercise"], "max_weight": r["max_weight"]} for r in rows]


def total_volume_per_session(conn: sqlite3.Connection, member_id: int) -> list[dict]:
    """
    Returns:
      [
        {"session_date": "YYYY-MM-DD", "total_volume": 810.0},
        ...
      ]
    session 단위로 Σ(weight_kg × reps). 날짜 오름차순.
    동일 날짜에 세션이 2개면 각각 별도 row.
    """
    rows = conn.execute(
        """
        SELECT ps.session_date, SUM(ss.weight_kg * ss.reps) AS total_volume
        FROM session_sets ss
        JOIN pt_sessions ps ON ps.id = ss.session_id
        WHERE ps.member_id = ?
        GROUP BY ps.id
        ORDER BY ps.session_date ASC
        """,
        (member_id,),
    ).fetchall()
    return [{"session_date": r["session_date"], "total_volume": r["total_volume"]} for r in rows]
