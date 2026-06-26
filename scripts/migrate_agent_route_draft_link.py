"""
Idempotent migration: link agent message routes to a pushed reply draft.

Adds:
  agent_message_routes.draft_id   the DBDraftReply pushed to the agent's WhatsApp,
                                  so the inbound relay can discard that draft once
                                  the agent replies from their phone.

Run (local pilot / staging / prod, one DB at a time):
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_agent_route_draft_link.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    "ALTER TABLE agent_message_routes ADD COLUMN IF NOT EXISTS draft_id TEXT",
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_draft_id ON agent_message_routes(draft_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("agent_message_routes.draft_id migration applied.")


if __name__ == "__main__":
    main()
