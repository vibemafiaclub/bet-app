import csv
import io
import time
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.aggregates import max_weight_per_session, total_volume_per_session
from app.auth import (
    current_user,
    is_authenticated,
    is_owner,
    login_required_redirect,
    owner_required_redirect,
    require_member_access,
    verify_credentials,
)
from app.db import get_connection
from app.exercises import EXERCISES

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


_SESSIONS_CSV_COLUMNS = (
    "session_date",
    "member_name",
    "exercise",
    "weight_kg",
    "reps",
    "set_index",
    "input_trainer_name",
)


def _write_sessions_csv(conn, trainer_id_filter, buffer) -> int:
    """세션 row들을 CSV 포맷으로 buffer에 쓴다 (BOM 없음).

    `trainer_id_filter`가 None이면 전체 세션, 정수면 해당 trainer_id의 input 세션만.
    반환값은 header row를 제외한 data row 수 (감사 로그 `rows=N` 용).

    관장 export(`/admin/export/sessions.csv`)와 본인 export(`/my/export/sessions.csv`)
    양쪽이 이 함수를 공유하여 컬럼 drift를 코드 레벨에서 차단한다.
    헤더 row와 data row 모두 `_SESSIONS_CSV_COLUMNS` 단일 상수를 참조한다.
    """
    writer = csv.writer(buffer)
    writer.writerow(_SESSIONS_CSV_COLUMNS)

    base_sql = (
        "SELECT ps.session_date, m.name AS member_name, "
        "ss.exercise, ss.weight_kg, ss.reps, ss.set_index, "
        "COALESCE(t.name, '') AS input_trainer_name "
        "FROM session_sets ss "
        "JOIN pt_sessions ps ON ss.session_id = ps.id "
        "JOIN members m ON ps.member_id = m.id "
        "LEFT JOIN trainers t ON ps.input_trainer_id = t.id"
    )
    if trainer_id_filter is None:
        rows = conn.execute(
            base_sql + " ORDER BY ps.session_date, ps.id, ss.set_index"
        ).fetchall()
    else:
        rows = conn.execute(
            base_sql
            + " WHERE ps.input_trainer_id = ?"
            + " ORDER BY ps.session_date, ps.id, ss.set_index",
            (trainer_id_filter,),
        ).fetchall()

    for row in rows:
        writer.writerow(tuple(row[c] for c in _SESSIONS_CSV_COLUMNS))

    return len(rows)


def register_routes(app: FastAPI) -> None:

    @app.get("/login")
    async def get_login(request: Request):
        if is_authenticated(request):
            return RedirectResponse(url="/", status_code=303)
        return templates.TemplateResponse(request, "login.html")

    @app.post("/login")
    async def post_login(request: Request):
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        user = verify_credentials(username, password)
        if user is not None:
            request.session["user"] = user
            return RedirectResponse(url="/", status_code=303)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status_code=200,
        )

    @app.post("/logout")
    async def post_logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/")
    async def index(request: Request):
        if not is_authenticated(request):
            return login_required_redirect()
        if is_owner(request):
            with get_connection() as conn:
                trainer_row = conn.execute(
                    "SELECT id FROM trainers ORDER BY id LIMIT 1"
                ).fetchone()
                if not trainer_row:
                    return HTMLResponse("<p>seed를 실행하세요</p>")
                trainer_id = trainer_row["id"]
                member_row = conn.execute(
                    "SELECT id FROM members WHERE trainer_id=? ORDER BY id LIMIT 1",
                    (trainer_id,),
                ).fetchone()
                if not member_row:
                    return HTMLResponse("<p>seed를 실행하세요</p>")
                member_id = member_row["id"]
            return RedirectResponse(
                url=f"/trainers/{trainer_id}/members/{member_id}/log", status_code=303
            )
        user = current_user(request)
        self_tid = user["trainer_id"]
        with get_connection() as conn:
            member_row = conn.execute(
                "SELECT id FROM members WHERE trainer_id=? ORDER BY id LIMIT 1",
                (self_tid,),
            ).fetchone()
        if member_row:
            mid = member_row["id"]
            return RedirectResponse(url=f"/trainers/{self_tid}/members/{mid}/log", status_code=303)
        return HTMLResponse("<p>담당 회원이 아직 없습니다. 관장에게 요청하세요.</p>", status_code=200)

    @app.get("/trainers/{tid}/members/{mid}/log")
    async def get_log(request: Request, tid: int, mid: int):
        with get_connection() as conn:
            ok, status, member = require_member_access(request, conn, tid, mid)
            if not ok:
                if status is None:
                    return login_required_redirect()
                if status == 403:
                    return PlainTextResponse("forbidden", status_code=403)
                return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
            return templates.TemplateResponse(
                request,
                "log.html",
                {
                    "tid": tid,
                    "mid": mid,
                    "member_name": member["name"],
                    "exercises": EXERCISES,
                    "today": date.today().isoformat(),
                },
            )

    @app.post("/trainers/{tid}/members/{mid}/log")
    async def post_log(request: Request, tid: int, mid: int):
        with get_connection() as conn:
            ok, status, member = require_member_access(request, conn, tid, mid)
            if not ok:
                if status is None:
                    return login_required_redirect()
                if status == 403:
                    return PlainTextResponse("forbidden", status_code=403)
                return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
        form = await request.form()
        session_date = str(form.get("session_date", ""))
        exercises_raw = form.getlist("exercise")
        weight_kgs_raw = form.getlist("weight_kg")
        repss_raw = form.getlist("reps")

        valid_rows = []
        for ex, wkg, r in zip(exercises_raw, weight_kgs_raw, repss_raw):
            ex = ex.strip()
            wkg = wkg.strip()
            r = r.strip()
            if not ex and not wkg and not r:
                continue
            if not ex or not wkg or not r:
                continue
            valid_rows.append((ex, wkg, r))

        if not valid_rows:
            return HTMLResponse(
                "<p>유효한 세트가 없습니다. 데이터를 입력하세요.</p>", status_code=400
            )

        for ex, wkg, r in valid_rows:
            if ex not in EXERCISES:
                return HTMLResponse(f"<p>알 수 없는 운동: {ex}</p>", status_code=400)
            try:
                w = float(wkg)
                rp = int(r)
            except ValueError:
                return HTMLResponse(
                    "<p>중량 또는 횟수 형식이 올바르지 않습니다.</p>", status_code=400
                )
            if w <= 0:
                return HTMLResponse(
                    "<p>중량은 0보다 커야 합니다.</p>", status_code=400
                )
            if rp <= 0:
                return HTMLResponse(
                    "<p>횟수는 0보다 커야 합니다.</p>", status_code=400
                )

        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO pt_sessions (member_id, session_date, created_at, input_trainer_id) VALUES (?, ?, ?, ?)",
                (mid, session_date, now, current_user(request)["trainer_id"]),
            )
            session_id = cur.lastrowid
            for i, (ex, wkg, r) in enumerate(valid_rows):
                conn.execute(
                    "INSERT INTO session_sets (session_id, exercise, weight_kg, reps, set_index) VALUES (?, ?, ?, ?, ?)",
                    (session_id, ex, float(wkg), int(r), i),
                )

        return HTMLResponse(
            f'<div id="entry-feedback">저장됨 (<a href="/trainers/{tid}/members/{mid}/dashboard">대시보드 보기</a>)</div>'
        )

    @app.get("/trainers/{tid}/members/{mid}/chart-data.json")
    async def get_chart_data(request: Request, tid: int, mid: int):
        with get_connection() as conn:
            ok, status, member = require_member_access(request, conn, tid, mid)
            if not ok:
                if status is None:
                    return login_required_redirect()
                if status == 403:
                    return PlainTextResponse("forbidden", status_code=403)
                return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
            max_weight_rows = max_weight_per_session(conn, mid)
            volume_rows = total_volume_per_session(conn, mid)

        labels = sorted({r["session_date"] for r in max_weight_rows})

        exercise_map: dict[str, dict[str, float]] = {}
        for row in max_weight_rows:
            ex = row["exercise"]
            if ex not in exercise_map:
                exercise_map[ex] = {}
            exercise_map[ex][row["session_date"]] = row["max_weight"]

        datasets = [
            {"label": ex, "data": [exercise_map[ex].get(dt) for dt in labels]}
            for ex in sorted(exercise_map)
        ]

        volume_by_date: dict[str, float] = {}
        for row in volume_rows:
            dt = row["session_date"]
            volume_by_date[dt] = volume_by_date.get(dt, 0.0) + row["total_volume"]

        return JSONResponse({
            "member": {"id": member["id"], "name": member["name"]},
            "max_weight": {"labels": labels, "datasets": datasets},
            "total_volume": {"labels": labels, "data": [volume_by_date.get(dt, 0.0) for dt in labels]},
        })

    @app.get("/trainers/{tid}/members/{mid}/dashboard")
    async def get_dashboard(request: Request, tid: int, mid: int):
        with get_connection() as conn:
            ok, status, member = require_member_access(request, conn, tid, mid)
            if not ok:
                if status is None:
                    return login_required_redirect()
                if status == 403:
                    return PlainTextResponse("forbidden", status_code=403)
                return HTMLResponse("회원을 찾을 수 없습니다.", status_code=404)
            return templates.TemplateResponse(
                request,
                "dashboard.html",
                {"tid": tid, "mid": mid, "member_name": member["name"]},
            )

    @app.get("/admin/export/sessions.csv")
    async def get_export_sessions(request: Request, trainer_id: int | None = None):
        if not is_authenticated(request):
            return login_required_redirect()
        if not is_owner(request):
            return owner_required_redirect()

        owner_id = current_user(request)["trainer_id"]
        export_last_ts = request.app.state.export_last_ts

        now_ts = time.monotonic()
        if owner_id in export_last_ts and now_ts - export_last_ts[owner_id] < 60:
            return Response(
                "Too Many Requests: retry in 60s",
                status_code=429,
                media_type="text/plain; charset=utf-8",
            )

        buf = io.StringIO()
        with get_connection() as conn:
            rows_count = _write_sessions_csv(conn, trainer_id, buf)
            conn.execute(
                "INSERT INTO export_audit (created_at, action, actor_trainer_id, target_trainer_id, rows)"
                " VALUES (?, 'owner_export', ?, ?, ?)",
                (datetime.utcnow().isoformat(), owner_id, trainer_id, rows_count),
            )

        csv_content = "﻿" + buf.getvalue()
        today_str = date.today().strftime("%Y%m%d")
        if trainer_id is not None:
            filename = f"sessions_{today_str}_trainer_{trainer_id}.csv"
        else:
            filename = f"sessions_{today_str}.csv"

        print(
            f"[export] owner_id={owner_id} target_trainer_id={trainer_id if trainer_id is not None else 'all'} rows={rows_count}",
            flush=True,
        )

        export_last_ts[owner_id] = time.monotonic()

        return Response(
            content=csv_content.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/my/export/sessions.csv")
    async def get_my_export_sessions(request: Request):
        if not is_authenticated(request):
            return login_required_redirect()

        trainer_id = current_user(request)["trainer_id"]
        my_export_last_ts = request.app.state.my_export_last_ts

        now_ts = time.monotonic()
        if trainer_id in my_export_last_ts and now_ts - my_export_last_ts[trainer_id] < 60:
            return Response(
                "Too Many Requests: retry in 60s",
                status_code=429,
                media_type="text/plain; charset=utf-8",
            )

        buf = io.StringIO()
        with get_connection() as conn:
            rows_count = _write_sessions_csv(conn, trainer_id, buf)
            conn.execute(
                "INSERT INTO export_audit (created_at, action, actor_trainer_id, target_trainer_id, rows)"
                " VALUES (?, 'my_export', ?, ?, ?)",
                (datetime.utcnow().isoformat(), trainer_id, trainer_id, rows_count),
            )

        csv_content = "﻿" + buf.getvalue()
        today_str = date.today().strftime("%Y%m%d")
        filename = f"my_sessions_{today_str}.csv"

        print(
            f"[my-export] trainer_id={trainer_id} rows={rows_count}",
            flush=True,
        )

        my_export_last_ts[trainer_id] = time.monotonic()

        return Response(
            content=csv_content.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
