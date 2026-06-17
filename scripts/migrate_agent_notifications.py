"""
Idempotent migration for the agent notification framework (DAL-162).

Creates agent_notifications — the single audit/dedupe/digest record for every
agent-facing push (or recorded suppression).

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_agent_notifications.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS agent_notifications (
      notification_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      urgency TEXT NOT NULL DEFAULT 'immediate',
      status TEXT NOT NULL DEFAULT 'sent',
      conversation_id TEXT REFERENCES conversations(conversation_id),
      viewing_id TEXT REFERENCES viewings(viewing_id),
      listing_id TEXT REFERENCES listings(listing_id),
      dedupe_key TEXT UNIQUE,
      body TEXT,
      deep_link TEXT,
      whatsapp_message_sid TEXT,
      sent_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_brokerage_id ON agent_notifications(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_agent_user_id ON agent_notifications(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_event_type ON agent_notifications(event_type)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_status ON agent_notifications(status)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_conversation_id ON agent_notifications(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_viewing_id ON agent_notifications(viewing_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_listing_id ON agent_notifications(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_dedupe_key ON agent_notifications(dedupe_key)",
    "CREATE INDEX IF NOT EXISTS ix_agent_notifications_created_at ON agent_notifications(created_at)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Agent notifications migration complete.")


if __name__ == "__main__":
    main()
