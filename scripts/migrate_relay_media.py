"""
Idempotent migration for WhatsApp relay media (DAL-161).

Creates:
  agent_relay_sessions — ref sessions opened by quote-replies
  relay_outbox         — held / parked relay items with UNDO + expiry

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_relay_media.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS agent_relay_sessions (
      session_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT,
      agent_phone TEXT NOT NULL,
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      opened_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      last_activity_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      expires_at TIMESTAMP WITHOUT TIME ZONE,
      closed_reason TEXT,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_brokerage_id ON agent_relay_sessions(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_agent_phone ON agent_relay_sessions(agent_phone)",
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_conversation_id ON agent_relay_sessions(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_status ON agent_relay_sessions(status)",
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_expires_at ON agent_relay_sessions(expires_at)",
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_agent_user_id ON agent_relay_sessions(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_relay_sessions_listing_id ON agent_relay_sessions(listing_id)",
    """
    CREATE TABLE IF NOT EXISTS relay_outbox (
      item_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT,
      agent_phone TEXT NOT NULL,
      conversation_id TEXT REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      media_asset_id TEXT REFERENCES media_assets(media_asset_id),
      body TEXT,
      status TEXT NOT NULL DEFAULT 'held',
      routing_method TEXT,
      release_at TIMESTAMP WITHOUT TIME ZONE,
      parked_batch_id TEXT,
      sent_at TIMESTAMP WITHOUT TIME ZONE,
      cancelled_reason TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_brokerage_id ON relay_outbox(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_agent_phone ON relay_outbox(agent_phone)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_conversation_id ON relay_outbox(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_status ON relay_outbox(status)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_release_at ON relay_outbox(release_at)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_parked_batch_id ON relay_outbox(parked_batch_id)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_media_asset_id ON relay_outbox(media_asset_id)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_agent_user_id ON relay_outbox(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_relay_outbox_listing_id ON relay_outbox(listing_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Relay media migration complete.")


if __name__ == "__main__":
    main()
