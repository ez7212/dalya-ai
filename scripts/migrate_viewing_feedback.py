"""Add durable post-viewing feedback capture records.

Usage:
  PYTHONPATH=. venv/bin/python scripts/migrate_viewing_feedback.py
"""

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS viewing_feedback (
      feedback_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      viewing_id TEXT NOT NULL REFERENCES viewings(viewing_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      agent_user_id TEXT,
      participant_type TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'requested',
      score INTEGER,
      sentiment TEXT,
      temperature TEXT,
      financing_status TEXT,
      next_action TEXT,
      summary TEXT,
      raw_body TEXT,
      structured_json JSONB DEFAULT '{}'::jsonb,
      source TEXT NOT NULL DEFAULT 'post_viewing_capture',
      requested_at TIMESTAMP,
      responded_at TIMESTAMP,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
      CONSTRAINT uq_viewing_feedback_participant UNIQUE (viewing_id, participant_type)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_brokerage_id ON viewing_feedback(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_viewing_id ON viewing_feedback(viewing_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_conversation_id ON viewing_feedback(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_listing_id ON viewing_feedback(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_buyer_phone ON viewing_feedback(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_agent_user_id ON viewing_feedback(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_participant_type ON viewing_feedback(participant_type)",
    "CREATE INDEX IF NOT EXISTS ix_viewing_feedback_status ON viewing_feedback(status)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.exec_driver_sql(statement)
    print("viewing_feedback migration complete")


if __name__ == "__main__":
    main()
