from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    statements = [
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE message_queue ADD COLUMN IF NOT EXISTS media_urls JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE message_queue ADD COLUMN IF NOT EXISTS media_content_types JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE message_queue ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'::jsonb",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    print("voice_notes schema migration applied")


if __name__ == "__main__":
    main()
