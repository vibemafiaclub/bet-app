import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", "./data/bet.db"))

@contextmanager
def get_connection(db_path: Path | None = None):
    """sqlite3 connection context manager. row_factory=Row, foreign_keys=ON."""
    path = db_path if db_path is not None else DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
""")
