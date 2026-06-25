"""
Idempotent migration for agent-scoped community-research field overrides.

Creates agent_community_overrides — per-(brokerage, agent, project, field)
corrections to a project's community research. Private to the owning agent;
never mutates the shared knowledge base.

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_agent_community_overrides.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS agent_community_overrides (
      override_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT NOT NULL,
      project_key TEXT NOT NULL,
      field_key TEXT NOT NULL,
      value_text TEXT NOT NULL,
      note TEXT,
      buyer_safe BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_community_overrides_brokerage_id ON agent_community_overrides(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_community_overrides_agent_user_id ON agent_community_overrides(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_community_overrides_project_key ON agent_community_overrides(project_key)",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_community_override_scope_field
      ON agent_community_overrides(brokerage_id, agent_user_id, project_key, field_key)
    """,
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("agent_community_overrides migration complete.")


if __name__ == "__main__":
    main()
