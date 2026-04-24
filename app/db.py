import os
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "./data/bet.db"))


class _ConnectionContext:
    """Class-based context manager for sqlite3 connections.

    Unlike @contextmanager, the generator finalizer does not close the
    connection when the context manager object is GC'd without __exit__
    being called. This ensures the connection stays open when callers use
    .__enter__() directly (e.g., in tests).
    """

    def __init__(self, path: Path):
        self._path = path
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is not None:
            if exc_type is not None:
                self._conn.rollback()
            else:
                self._conn.commit()
            self._conn.close()
            self._conn = None
        return False


def get_connection(db_path: Path | None = None) -> _ConnectionContext:
    """sqlite3 connection context manager. row_factory=Row, foreign_keys=ON."""
    path = db_path if db_path is not None else DATABASE_PATH
    return _ConnectionContext(path)


def _migrate_iteration2(conn) -> None:
    cols_t = {r[1] for r in conn.execute("PRAGMA table_info(trainers)").fetchall()}
    if "username" not in cols_t:
        conn.execute("ALTER TABLE trainers ADD COLUMN username TEXT")
    if "password_hash" not in cols_t:
        conn.execute("ALTER TABLE trainers ADD COLUMN password_hash TEXT")
    if "is_owner" not in cols_t:
        conn.execute("ALTER TABLE trainers ADD COLUMN is_owner INTEGER NOT NULL DEFAULT 0")

    idx_names = {r[1] for r in conn.execute("PRAGMA index_list(trainers)").fetchall()}
    if "idx_trainers_username" not in idx_names:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_trainers_username"
            " ON trainers(username) WHERE username IS NOT NULL"
        )

    cols_s = {r[1] for r in conn.execute("PRAGMA table_info(pt_sessions)").fetchall()}
    if "input_trainer_id" not in cols_s:
        conn.execute(
            "ALTER TABLE pt_sessions ADD COLUMN input_trainer_id INTEGER REFERENCES trainers(id)"
        )


def init_db(db_path: Path | None = None) -> None:
    """CREATE TABLE IF NOT EXISTS for 4 tables. Idempotent."""
    path = db_path if db_path is not None else DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as conn:
        conn.executescript("""
CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id INTEGER NOT NULL REFERENCES trainers(id),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pt_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id),
    session_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES pt_sessions(id),
    exercise TEXT NOT NULL CHECK(exercise IN (
        '스쿼트','벤치프레스','데드리프트','오버헤드프레스','바벨로우',
        '풀업','레그프레스','랫풀다운','레그컬','덤벨컬'
    )),
    weight_kg REAL NOT NULL CHECK(weight_kg > 0),
    reps INTEGER NOT NULL CHECK(reps > 0),
    set_index INTEGER NOT NULL
);
-- iter 6: export_audit
CREATE TABLE IF NOT EXISTS export_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('owner_export', 'my_export')),
    actor_trainer_id INTEGER NOT NULL REFERENCES trainers(id),
    target_trainer_id INTEGER REFERENCES trainers(id),
    rows INTEGER NOT NULL
);
""")
        _migrate_iteration2(conn)
