"""
Idempotent migration for Smart Escalation threading.

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_escalation_threads.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS escalation_threads (
      thread_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_phone TEXT NOT NULL,
      agent_user_id TEXT,
      agent_phone TEXT,
      category TEXT NOT NULL,
      state TEXT NOT NULL DEFAULT 'debouncing',
      escalation_type TEXT NOT NULL,
      escalation_subtype TEXT,
      envelope_token TEXT,
      opened_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      alerted_at TIMESTAMP WITHOUT TIME ZONE,
      last_buyer_message_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      last_update_sent_at TIMESTAMP WITHOUT TIME ZONE,
      debounce_until TIMESTAMP WITHOUT TIME ZONE,
      max_debounce_until TIMESTAMP WITHOUT TIME ZONE,
      closed_at TIMESTAMP WITHOUT TIME ZONE,
      close_reason TEXT,
      question_count INTEGER NOT NULL DEFAULT 0,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_brokerage_id ON escalation_threads(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_conversation_id ON escalation_threads(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_listing_id ON escalation_threads(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_buyer_phone ON escalation_threads(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_agent_user_id ON escalation_threads(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_category ON escalation_threads(category)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_state ON escalation_threads(state)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_threads_envelope_token ON escalation_threads(envelope_token)",
    """
    CREATE INDEX IF NOT EXISTS ix_escalation_threads_open_match
    ON escalation_threads(brokerage_id, buyer_phone, listing_id, category, state)
    """,
    "DROP INDEX IF EXISTS uq_open_escalation_thread_scope",
    """
    CREATE UNIQUE INDEX uq_open_escalation_thread_scope
    ON escalation_threads(brokerage_id, buyer_phone, listing_id, category)
    WHERE state IN ('debouncing', 'open', 'updated') AND category <> 'offer'
    """,
    """
    CREATE TABLE IF NOT EXISTS escalation_thread_questions (
      question_id TEXT PRIMARY KEY,
      thread_id TEXT NOT NULL REFERENCES escalation_threads(thread_id),
      buyer_message_id INTEGER REFERENCES messages(id),
      question_text TEXT NOT NULL,
      category TEXT NOT NULL,
      escalation_subtype TEXT,
      sort_order INTEGER NOT NULL,
      added_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      resolved_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      CONSTRAINT uq_escalation_question_order UNIQUE(thread_id, sort_order)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_escalation_thread_questions_thread_id ON escalation_thread_questions(thread_id)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_thread_questions_buyer_message_id ON escalation_thread_questions(buyer_message_id)",
    "CREATE INDEX IF NOT EXISTS ix_escalation_thread_questions_category ON escalation_thread_questions(category)",
    "ALTER TABLE agent_message_routes ADD COLUMN IF NOT EXISTS thread_id TEXT REFERENCES escalation_threads(thread_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_thread_id ON agent_message_routes(thread_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Escalation threading migration complete.")


if __name__ == "__main__":
    main()
