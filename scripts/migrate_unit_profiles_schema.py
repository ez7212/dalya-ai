from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    statements = [
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS unit_profile JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS unit_profile_history JSONB DEFAULT '[]'::jsonb",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    print("unit_profiles schema migration applied")


if __name__ == "__main__":
    main()
