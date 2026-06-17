"""
Idempotent migration for voice note handling (DAL-159).

1. Transcription storage fields on messages:
     transcription_text, transcription_language,
     transcription_confidence, transcription_provider
2. agent_voice_reply_holds — transcribed agent voice replies held below the
   confidence threshold awaiting a SEND confirm.

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_voice_note_handling.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS transcription_text TEXT",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS transcription_language TEXT",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS transcription_confidence DOUBLE PRECISION",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS transcription_provider TEXT",
    """
    CREATE TABLE IF NOT EXISTS agent_voice_reply_holds (
      hold_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      route_id TEXT NOT NULL REFERENCES agent_message_routes(route_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT NOT NULL,
      agent_user_id TEXT,
      agent_phone TEXT,
      envelope_token TEXT NOT NULL,
      transcript TEXT NOT NULL,
      transcription_language TEXT,
      transcription_confidence DOUBLE PRECISION,
      transcription_provider TEXT,
      status TEXT NOT NULL DEFAULT 'held',
      released_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_brokerage_id ON agent_voice_reply_holds(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_route_id ON agent_voice_reply_holds(route_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_conversation_id ON agent_voice_reply_holds(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_envelope_token ON agent_voice_reply_holds(envelope_token)",
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_buyer_phone ON agent_voice_reply_holds(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_agent_user_id ON agent_voice_reply_holds(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_voice_reply_holds_listing_id ON agent_voice_reply_holds(listing_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Voice note handling migration complete.")


if __name__ == "__main__":
    main()
