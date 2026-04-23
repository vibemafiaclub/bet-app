import os
import secrets
from fastapi import Request
from fastapi.responses import RedirectResponse


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("admin"))


def verify_credentials(username: str, password: str) -> bool:
    u_ok = secrets.compare_digest(username, os.environ["ADMIN_USERNAME"])
    p_ok = secrets.compare_digest(password, os.environ["ADMIN_PASSWORD"])
    return u_ok and p_ok


def login_required_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)
