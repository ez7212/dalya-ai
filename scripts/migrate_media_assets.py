"""
Idempotent migration for outbound media (DAL-160).

Creates media_assets — brokerage-scoped storage records for media sent into
buyer conversations (composer uploads, listing assets, relay inbound).

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_media_assets.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS media_assets (
      media_asset_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT,
      conversation_id TEXT REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      mime_type TEXT NOT NULL,
      size_bytes INTEGER NOT NULL DEFAULT 0,
      storage_ref TEXT NOT NULL,
      sha256 TEXT,
      original_filename TEXT,
      source TEXT NOT NULL DEFAULT 'composer_upload',
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_media_assets_brokerage_id ON media_assets(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_media_assets_agent_user_id ON media_assets(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_media_assets_conversation_id ON media_assets(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_media_assets_listing_id ON media_assets(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_media_assets_sha256 ON media_assets(sha256)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Media assets migration complete.")


if __name__ == "__main__":
    main()
