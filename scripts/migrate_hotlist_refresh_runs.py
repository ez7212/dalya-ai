"""
Add persisted hot-list refresh run records.

This migration is additive and idempotent. It backs DAL-151 by storing manual
and scheduled refresh attempts, run status, and the resulting assignment/task/
draft counts shown in the agent workspace.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS hotlist_refresh_runs (
      run_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      requested_by_user_id TEXT,
      trigger TEXT NOT NULL DEFAULT 'manual',
      status TEXT NOT NULL DEFAULT 'running',
      brokerage_timezone TEXT NOT NULL DEFAULT 'Asia/Dubai',
      refresh_date TEXT,
      assignment_count INTEGER NOT NULL DEFAULT 0,
      task_count INTEGER NOT NULL DEFAULT 0,
      draft_count INTEGER NOT NULL DEFAULT 0,
      error TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      completed_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_hotlist_refresh_runs_brokerage_id ON hotlist_refresh_runs(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_hotlist_refresh_runs_requested_by_user_id ON hotlist_refresh_runs(requested_by_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_hotlist_refresh_runs_status ON hotlist_refresh_runs(status)",
    "CREATE INDEX IF NOT EXISTS ix_hotlist_refresh_runs_refresh_date ON hotlist_refresh_runs(refresh_date)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("hotlist_refresh_runs migration complete")


if __name__ == "__main__":
    main()
