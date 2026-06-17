"""
Add composite indexes for the Agent Dashboard V1 read path.

The dashboard endpoint filters by brokerage/agent scope and then orders recent
or urgent rows. These indexes are additive and idempotent.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    "CREATE INDEX IF NOT EXISTS ix_brokerage_members_user_status_created ON brokerage_members(user_id, status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_agent_profiles_brokerage_user ON agent_profiles(brokerage_id, user_id)",
    "CREATE INDEX IF NOT EXISTS ix_messages_conversation_timestamp_desc ON messages(conversation_id, timestamp DESC)",
    """
    CREATE INDEX IF NOT EXISTS ix_lead_assignments_dashboard_hot
    ON lead_assignments(brokerage_id, status, urgency_score DESC, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_lead_tasks_dashboard_open
    ON lead_tasks(brokerage_id, status, snoozed_until, due_at, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_viewings_dashboard_schedule
    ON viewings(brokerage_id, status, scheduled_for, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_draft_replies_dashboard
    ON draft_replies(brokerage_id, status, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_ai_drafts_dashboard
    ON ai_drafts(brokerage_id, status, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_outreach_drafts_dashboard
    ON outreach_drafts(brokerage_id, status, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_campaigns_dashboard
    ON campaigns(brokerage_id, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_campaign_uploads_dashboard
    ON campaign_uploads(brokerage_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_campaign_recipients_dashboard
    ON campaign_recipients(brokerage_id, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_owner_leads_dashboard
    ON owner_leads(brokerage_id, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_marketing_pages_dashboard
    ON marketing_pages(brokerage_id, updated_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_marketing_events_dashboard_7d
    ON marketing_events(brokerage_id, occurred_at DESC)
    """,
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Agent dashboard performance indexes migration complete.")


if __name__ == "__main__":
    main()
