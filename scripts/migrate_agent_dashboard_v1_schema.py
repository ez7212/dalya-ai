"""
Add the v1 agent dashboard foundation schema.

This migration is additive and idempotent. It keeps the existing conversation,
message, draft reply, and viewing tables intact, then adds the missing campaign,
owner-lead, outreach, and marketing-event tables used by the new dashboard plan.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS lead_tasks (
      task_id TEXT PRIMARY KEY,
      task_key TEXT,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      assigned_agent_id TEXT,
      task_type TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      status TEXT NOT NULL DEFAULT 'open',
      priority TEXT NOT NULL DEFAULT 'normal',
      source TEXT,
      due_at TIMESTAMP WITHOUT TIME ZONE,
      snoozed_until TIMESTAMP WITHOUT TIME ZONE,
      snooze_reason TEXT,
      completed_at TIMESTAMP WITHOUT TIME ZONE,
      completed_by TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "ALTER TABLE lead_tasks ALTER COLUMN conversation_id DROP NOT NULL",
    "ALTER TABLE lead_tasks ADD COLUMN IF NOT EXISTS task_key TEXT",
    "ALTER TABLE lead_tasks ADD COLUMN IF NOT EXISTS source TEXT",
    "ALTER TABLE lead_tasks ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMP WITHOUT TIME ZONE",
    "ALTER TABLE lead_tasks ADD COLUMN IF NOT EXISTS snooze_reason TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_lead_tasks_task_key ON lead_tasks(task_key) WHERE task_key IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_task_key ON lead_tasks(task_key)",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_snoozed_until ON lead_tasks(snoozed_until)",
    """
    CREATE TABLE IF NOT EXISTS ai_drafts (
      draft_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT,
      conversation_id TEXT REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      draft_type TEXT NOT NULL,
      title TEXT,
      body TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft',
      source TEXT NOT NULL DEFAULT 'agent_dashboard',
      confidence_score DOUBLE PRECISION,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_ai_drafts_brokerage_id ON ai_drafts(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_ai_drafts_agent_user_id ON ai_drafts(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_ai_drafts_conversation_id ON ai_drafts(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_ai_drafts_listing_id ON ai_drafts(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_ai_drafts_buyer_phone ON ai_drafts(buyer_phone)",
    """
    CREATE TABLE IF NOT EXISTS campaigns (
      campaign_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      owner_agent_id TEXT,
      name TEXT NOT NULL,
      campaign_type TEXT NOT NULL DEFAULT 'owner_acquisition',
      channel TEXT NOT NULL DEFAULT 'whatsapp',
      status TEXT NOT NULL DEFAULT 'draft',
      audience JSONB DEFAULT '{}'::jsonb,
      offer JSONB DEFAULT '{}'::jsonb,
      metrics JSONB DEFAULT '{}'::jsonb,
      starts_at TIMESTAMP WITHOUT TIME ZONE,
      ends_at TIMESTAMP WITHOUT TIME ZONE,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_campaigns_brokerage_id ON campaigns(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_campaigns_owner_agent_id ON campaigns(owner_agent_id)",
    """
    CREATE TABLE IF NOT EXISTS campaign_uploads (
      upload_id TEXT PRIMARY KEY,
      campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      uploaded_by TEXT,
      file_name TEXT NOT NULL,
      file_url TEXT,
      file_type TEXT,
      row_count INTEGER,
      status TEXT NOT NULL DEFAULT 'uploaded',
      parsed_summary JSONB DEFAULT '{}'::jsonb,
      error TEXT,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      processed_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_campaign_uploads_campaign_id ON campaign_uploads(campaign_id)",
    "CREATE INDEX IF NOT EXISTS ix_campaign_uploads_brokerage_id ON campaign_uploads(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_campaign_uploads_uploaded_by ON campaign_uploads(uploaded_by)",
    """
    CREATE TABLE IF NOT EXISTS owner_leads (
      owner_lead_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      campaign_id TEXT REFERENCES campaigns(campaign_id),
      assigned_agent_id TEXT,
      owner_name TEXT,
      owner_phone TEXT,
      owner_email TEXT,
      project TEXT,
      unit_number TEXT,
      property_type TEXT,
      estimated_value_aed DOUBLE PRECISION,
      intent TEXT,
      lead_source TEXT,
      stage TEXT NOT NULL DEFAULT 'new',
      priority TEXT NOT NULL DEFAULT 'normal',
      last_contacted_at TIMESTAMP WITHOUT TIME ZONE,
      next_follow_up_at TIMESTAMP WITHOUT TIME ZONE,
      notes TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_brokerage_id ON owner_leads(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_campaign_id ON owner_leads(campaign_id)",
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_assigned_agent_id ON owner_leads(assigned_agent_id)",
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_owner_phone ON owner_leads(owner_phone)",
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_owner_email ON owner_leads(owner_email)",
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_project ON owner_leads(project)",
    "CREATE INDEX IF NOT EXISTS ix_owner_leads_next_follow_up_at ON owner_leads(next_follow_up_at)",
    """
    CREATE TABLE IF NOT EXISTS campaign_recipients (
      recipient_id TEXT PRIMARY KEY,
      campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      owner_lead_id TEXT REFERENCES owner_leads(owner_lead_id),
      recipient_key TEXT NOT NULL,
      name TEXT,
      phone TEXT,
      email TEXT,
      channel TEXT NOT NULL DEFAULT 'whatsapp',
      status TEXT NOT NULL DEFAULT 'queued',
      last_message_at TIMESTAMP WITHOUT TIME ZONE,
      last_response_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_campaign_recipient_key UNIQUE (campaign_id, recipient_key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_campaign_recipients_campaign_id ON campaign_recipients(campaign_id)",
    "CREATE INDEX IF NOT EXISTS ix_campaign_recipients_brokerage_id ON campaign_recipients(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_campaign_recipients_owner_lead_id ON campaign_recipients(owner_lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_campaign_recipients_phone ON campaign_recipients(phone)",
    "CREATE INDEX IF NOT EXISTS ix_campaign_recipients_email ON campaign_recipients(email)",
    """
    CREATE TABLE IF NOT EXISTS outreach_drafts (
      outreach_draft_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      campaign_id TEXT REFERENCES campaigns(campaign_id),
      recipient_id TEXT REFERENCES campaign_recipients(recipient_id),
      owner_lead_id TEXT REFERENCES owner_leads(owner_lead_id),
      agent_user_id TEXT,
      channel TEXT NOT NULL DEFAULT 'whatsapp',
      subject TEXT,
      body TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft',
      source TEXT NOT NULL DEFAULT 'ai',
      sent_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_outreach_drafts_brokerage_id ON outreach_drafts(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_outreach_drafts_campaign_id ON outreach_drafts(campaign_id)",
    "CREATE INDEX IF NOT EXISTS ix_outreach_drafts_recipient_id ON outreach_drafts(recipient_id)",
    "CREATE INDEX IF NOT EXISTS ix_outreach_drafts_owner_lead_id ON outreach_drafts(owner_lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_outreach_drafts_agent_user_id ON outreach_drafts(agent_user_id)",
    """
    CREATE TABLE IF NOT EXISTS marketing_pages (
      page_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      campaign_id TEXT REFERENCES campaigns(campaign_id),
      slug TEXT NOT NULL,
      title TEXT NOT NULL,
      page_type TEXT NOT NULL DEFAULT 'campaign_landing',
      status TEXT NOT NULL DEFAULT 'draft',
      url TEXT,
      content JSONB DEFAULT '{}'::jsonb,
      metrics JSONB DEFAULT '{}'::jsonb,
      published_at TIMESTAMP WITHOUT TIME ZONE,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_marketing_pages_brokerage_id ON marketing_pages(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_pages_campaign_id ON marketing_pages(campaign_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_pages_slug ON marketing_pages(slug)",
    """
    CREATE TABLE IF NOT EXISTS marketing_events (
      event_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      page_id TEXT REFERENCES marketing_pages(page_id),
      campaign_id TEXT REFERENCES campaigns(campaign_id),
      owner_lead_id TEXT REFERENCES owner_leads(owner_lead_id),
      event_type TEXT NOT NULL,
      visitor_id TEXT,
      source TEXT,
      payload JSONB DEFAULT '{}'::jsonb,
      occurred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_marketing_events_brokerage_id ON marketing_events(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_events_page_id ON marketing_events(page_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_events_campaign_id ON marketing_events(campaign_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_events_owner_lead_id ON marketing_events(owner_lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_events_visitor_id ON marketing_events(visitor_id)",
    "CREATE INDEX IF NOT EXISTS ix_marketing_events_occurred_at ON marketing_events(occurred_at)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Agent dashboard v1 schema migration complete.")


if __name__ == "__main__":
    main()
