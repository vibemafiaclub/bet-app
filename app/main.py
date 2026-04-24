import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.auth import ensure_owner_seed
from app.db import init_db
from app.routes import register_routes

REQUIRED_ENV = ("APP_SESSION_SECRET", "ADMIN_USERNAME", "ADMIN_PASSWORD")


def _validate_env() -> None:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


def create_app() -> FastAPI:
    _validate_env()
    init_db()
    ensure_owner_seed()
    app = FastAPI()
    secure_cookie = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ["APP_SESSION_SECRET"],
        session_cookie="bet_session",
        https_only=secure_cookie,
        same_site="lax",
    )
    app.state.export_last_ts = {}
    app.state.my_export_last_ts = {}
    register_routes(app)
    return app


app = create_app()
