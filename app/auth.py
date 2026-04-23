import hashlib
import os
import secrets
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
    return bool(request.session.get("admin"))


def verify_credentials(username: str, password: str) -> bool:
    u_ok = secrets.compare_digest(username, os.environ["ADMIN_USERNAME"])
    p_ok = secrets.compare_digest(password, os.environ["ADMIN_PASSWORD"])
    return u_ok and p_ok


def login_required_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)
