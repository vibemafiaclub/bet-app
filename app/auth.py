import hashlib
import os
import secrets
from datetime import datetime

from app.db import get_connection
from fastapi import Request
from fastapi.responses import RedirectResponse


def hash_password(password: str) -> str:
    """scrypt 기반 해싱. 포맷: 'scrypt$<salt_hex>$<hash_hex>'."""
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """stored가 'scrypt$<salt_hex>$<hash_hex>' 포맷이면 scrypt 재계산 후 compare_digest."""
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 3:
        return False
    algo, salt_hex, hash_hex = parts
    if algo != "scrypt":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    computed = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
    return secrets.compare_digest(computed, expected)


def is_authenticated(request: Request) -> bool:
    """session["user"]["trainer_id"]가 있으면 True."""
    return bool(request.session.get("user", {}).get("trainer_id"))


def is_owner(request: Request) -> bool:
    """session["user"]["is_owner"]가 True면 True."""
    return bool(request.session.get("user", {}).get("is_owner"))


def current_user(request: Request) -> dict | None:
    """session["user"] dict 반환, 없으면 None."""
    return request.session.get("user")


def verify_credentials(username: str, password: str) -> dict | None:
    """trainers 테이블에서 username 조회 → verify_password 성공 시
    {"trainer_id": int, "is_owner": bool} 반환, 실패 시 None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash, is_owner FROM trainers WHERE username=?",
            (username,),
        ).fetchone()
    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {"trainer_id": row["id"], "is_owner": bool(row["is_owner"])}


def login_required_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


def owner_required_redirect() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=303)


def ensure_owner_seed() -> None:
    """부팅 시 관장 시드. 로직은 spec의 `## 인증` 섹션을 따른다."""
    admin_username = os.environ["ADMIN_USERNAME"]
    admin_password = os.environ["ADMIN_PASSWORD"]

    with get_connection() as conn:
        owner_rows = conn.execute(
            "SELECT id, username, password_hash FROM trainers WHERE is_owner=1"
        ).fetchall()

        if len(owner_rows) == 0:
            existing = conn.execute(
                "SELECT id, password_hash FROM trainers WHERE username=?",
                (admin_username,),
            ).fetchone()

            if existing is None:
                conn.execute(
                    "INSERT INTO trainers (name, username, password_hash, is_owner, created_at) VALUES (?, ?, ?, 1, ?)",
                    (admin_username, admin_username, hash_password(admin_password), datetime.utcnow().isoformat()),
                )
                print(f"[auth] owner seeded: username={admin_username}", flush=True)
            else:
                if existing["password_hash"] is None:
                    conn.execute(
                        "UPDATE trainers SET is_owner=1, password_hash=? WHERE id=?",
                        (hash_password(admin_password), existing["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE trainers SET is_owner=1 WHERE id=?",
                        (existing["id"],),
                    )
                print(f"[auth] owner promoted: username={admin_username}", flush=True)
        else:
            matching = [r for r in owner_rows if r["username"] == admin_username]
            if not matching:
                db_username = owner_rows[0]["username"]
                print(
                    f"[warn] ADMIN_USERNAME mismatch: env={admin_username} db_owner={db_username}"
                    " — 관장 교체 절차 필요 (docs/user-intervention.md 참조)",
                    flush=True,
                )
