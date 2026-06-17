"""
Idempotent migration for live conversation takeover (DAL-158).

Adds the AI-mode kill-switch columns to conversations:
  ai_mode               active | agent_controlled (default active)
  ai_mode_changed_at    when the mode last flipped
  ai_mode_changed_by    agent user_id who flipped it
  ai_mode_change_source dashboard | whatsapp

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_conversation_ai_mode.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_mode TEXT NOT NULL DEFAULT 'active'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_mode_changed_at TIMESTAMP WITHOUT TIME ZONE",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_mode_changed_by TEXT",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_mode_change_source TEXT",
    "CREATE INDEX IF NOT EXISTS ix_conversations_ai_mode ON conversations(ai_mode)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Conversation AI-mode (takeover) migration complete.")


if __name__ == "__main__":
    main()
