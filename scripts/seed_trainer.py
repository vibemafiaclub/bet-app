import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db, get_connection
from app.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description="Seed/upsert a trainer account")
    parser.add_argument("--name", required=True, help="Trainer display name")
    parser.add_argument("--username", required=True, help="Login username")
    parser.add_argument("--password", required=True, help="Plain text password")
    parser.add_argument("--owner", action="store_true", help="Set as owner (is_owner=1)")
    args = parser.parse_args()

    if not args.password:
        raise SystemExit("--password cannot be empty")

    init_db()

    pw_hash = hash_password(args.password)
    now_str = datetime.now().isoformat(timespec="seconds")
    created = False
    is_owner_val = 0

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM trainers WHERE username=?", (args.username,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE trainers SET name=?, password_hash=? WHERE username=?",
                (args.name, pw_hash, args.username),
            )
        else:
            conn.execute(
                "INSERT INTO trainers (name, username, password_hash, is_owner, created_at)"
                " VALUES (?, ?, ?, 0, ?)",
                (args.name, args.username, pw_hash, now_str),
            )
            created = True

        if args.owner:
            old_owners = conn.execute(
                "SELECT username FROM trainers WHERE is_owner=1 AND username != ?",
                (args.username,),
            ).fetchall()
            conn.execute("UPDATE trainers SET is_owner=0")
            conn.execute(
                "UPDATE trainers SET is_owner=1 WHERE username=?", (args.username,)
            )
            is_owner_val = 1
            demoted = {r["username"] for r in old_owners}
            print(
                f"[seed_trainer] is_owner transferred:"
                f" demoted={demoted} promoted={{{args.username!r}}}"
            )

    print(
        f"[seed_trainer] username={args.username} is_owner={is_owner_val} created={created}"
    )


if __name__ == "__main__":
    main()
