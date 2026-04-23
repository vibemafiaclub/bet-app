import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db, get_connection


def main():
    init_db()

    with get_connection() as conn:
        admin_username = os.environ.get("ADMIN_USERNAME")
        owner_row = None

        if admin_username:
            owner_row = conn.execute(
                "SELECT id FROM trainers WHERE username=? AND is_owner=1",
                (admin_username,),
            ).fetchone()

        if owner_row is None:
            owner_row = conn.execute(
                "SELECT id FROM trainers WHERE is_owner=1 ORDER BY id LIMIT 1"
            ).fetchone()

        if owner_row is None:
            print(
                "[backfill] ERROR: no is_owner=1 trainer exists.\n"
                "  Run `uv run python -m scripts.seed_trainer"
                " --name \"관장이름\" --username <u> --password <pw> --owner` first.",
                file=sys.stderr,
            )
            sys.exit(1)

        owner_id = owner_row["id"]
        cur = conn.execute(
            "UPDATE pt_sessions SET input_trainer_id=? WHERE input_trainer_id IS NULL",
            (owner_id,),
        )
        updated = cur.rowcount

    print(f"[backfill] updated={updated} rows (owner_trainer_id={owner_id})")


if __name__ == "__main__":
    main()
