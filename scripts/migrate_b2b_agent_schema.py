"""
Add the B2B brokerage and agent-workflow schema.

This migration is intentionally idempotent. It creates the new agent workflow
tables, adds brokerage/agent scope columns to legacy tables, and backfills
existing rows into one pilot brokerage so the current database remains usable.
"""

import os
from datetime import datetime

from sqlalchemy import text

from app.db.session import engine


DEFAULT_BROKERAGE_ID = os.getenv("DEFAULT_BROKERAGE_ID", "dalya-internal")
DEFAULT_BROKERAGE_SLUG = os.getenv("DEFAULT_BROKERAGE_SLUG", "dalya-internal")
DEFAULT_BROKERAGE_NAME = os.getenv("DEFAULT_BROKERAGE_NAME", "Dalya Internal Pilot")


DDL = [
    """
    CREATE TABLE IF NOT EXISTS brokerages (
      brokerage_id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      slug TEXT NOT NULL UNIQUE,
      primary_contact_name TEXT,
      primary_contact_email TEXT,
      primary_contact_phone TEXT,
      rera_license_number TEXT,
      escalation_contact_name TEXT,
      escalation_contact_title TEXT,
      escalation_contact_phone TEXT,
      prompt_config JSONB DEFAULT '{}'::jsonb,
      settings JSONB DEFAULT '{}'::jsonb,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_brokerages_slug ON brokerages(slug)",
    """
    CREATE TABLE IF NOT EXISTS brokerage_members (
      member_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      user_id TEXT NOT NULL,
      email TEXT,
      display_name TEXT,
      phone TEXT,
      role TEXT NOT NULL DEFAULT 'agent',
      status TEXT NOT NULL DEFAULT 'active',
      settings JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_brokerage_member_user UNIQUE (brokerage_id, user_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_brokerage_members_brokerage_id ON brokerage_members(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_brokerage_members_user_id ON brokerage_members(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_brokerage_members_email ON brokerage_members(email)",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS brokerage_id TEXT REFERENCES brokerages(brokerage_id)",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS assigned_agent_id TEXT",
    "CREATE INDEX IF NOT EXISTS ix_listings_brokerage_id ON listings(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_listings_assigned_agent_id ON listings(assigned_agent_id)",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS brokerage_id TEXT REFERENCES brokerages(brokerage_id)",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS assigned_agent_id TEXT",
    "CREATE INDEX IF NOT EXISTS ix_conversations_brokerage_id ON conversations(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_conversations_assigned_agent_id ON conversations(assigned_agent_id)",
    "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS brokerage_id TEXT REFERENCES brokerages(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_profiles_brokerage_id ON buyer_profiles(brokerage_id)",
    "ALTER TABLE listing_inquiries ADD COLUMN IF NOT EXISTS brokerage_id TEXT REFERENCES brokerages(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_inquiries_brokerage_id ON listing_inquiries(brokerage_id)",
    "ALTER TABLE suspicious_activity ADD COLUMN IF NOT EXISTS brokerage_id TEXT REFERENCES brokerages(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_suspicious_activity_brokerage_id ON suspicious_activity(brokerage_id)",
    "ALTER TABLE offer_records ADD COLUMN IF NOT EXISTS brokerage_id TEXT REFERENCES brokerages(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_offer_records_brokerage_id ON offer_records(brokerage_id)",
    """
    CREATE TABLE IF NOT EXISTS lead_assignments (
      assignment_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_phone TEXT NOT NULL,
      assigned_agent_id TEXT,
      assigned_by TEXT,
      status TEXT NOT NULL DEFAULT 'new',
      signal TEXT,
      urgency_score INTEGER NOT NULL DEFAULT 0,
      next_action TEXT,
      next_action_reason TEXT,
      due_at TIMESTAMP WITHOUT TIME ZONE,
      last_agent_action_at TIMESTAMP WITHOUT TIME ZONE,
      last_buyer_message_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_lead_assignment_conversation UNIQUE (conversation_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_lead_assignments_brokerage_id ON lead_assignments(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_assignments_conversation_id ON lead_assignments(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_assignments_listing_id ON lead_assignments(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_assignments_buyer_phone ON lead_assignments(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_lead_assignments_assigned_agent_id ON lead_assignments(assigned_agent_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_assignments_due_at ON lead_assignments(due_at)",
    """
    CREATE TABLE IF NOT EXISTS lead_tasks (
      task_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      assigned_agent_id TEXT,
      task_type TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      status TEXT NOT NULL DEFAULT 'open',
      priority TEXT NOT NULL DEFAULT 'normal',
      due_at TIMESTAMP WITHOUT TIME ZONE,
      completed_at TIMESTAMP WITHOUT TIME ZONE,
      completed_by TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_brokerage_id ON lead_tasks(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_conversation_id ON lead_tasks(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_listing_id ON lead_tasks(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_buyer_phone ON lead_tasks(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_assigned_agent_id ON lead_tasks(assigned_agent_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_tasks_due_at ON lead_tasks(due_at)",
    """
    CREATE TABLE IF NOT EXISTS lead_actions (
      action_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      agent_user_id TEXT,
      action_type TEXT NOT NULL,
      outcome TEXT,
      note TEXT,
      payload JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_lead_actions_brokerage_id ON lead_actions(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_actions_conversation_id ON lead_actions(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_actions_listing_id ON lead_actions(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_actions_buyer_phone ON lead_actions(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_lead_actions_agent_user_id ON lead_actions(agent_user_id)",
    """
    CREATE TABLE IF NOT EXISTS viewings (
      viewing_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_phone TEXT NOT NULL,
      agent_user_id TEXT,
      scheduled_for TIMESTAMP WITHOUT TIME ZONE,
      status TEXT NOT NULL DEFAULT 'proposed',
      tenant_notice_required BOOLEAN NOT NULL DEFAULT false,
      tenant_notice_sent_at TIMESTAMP WITHOUT TIME ZONE,
      access_notes TEXT,
      post_viewing_notes TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_viewings_brokerage_id ON viewings(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewings_conversation_id ON viewings(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewings_listing_id ON viewings(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewings_buyer_phone ON viewings(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_viewings_agent_user_id ON viewings(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_viewings_scheduled_for ON viewings(scheduled_for)",
    """
    CREATE TABLE IF NOT EXISTS draft_replies (
      draft_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT REFERENCES listings(listing_id),
      buyer_phone TEXT,
      agent_user_id TEXT,
      intent TEXT NOT NULL,
      draft_text TEXT NOT NULL,
      source TEXT NOT NULL DEFAULT 'template',
      status TEXT NOT NULL DEFAULT 'draft',
      sent_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_draft_replies_brokerage_id ON draft_replies(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_draft_replies_conversation_id ON draft_replies(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_draft_replies_listing_id ON draft_replies(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_draft_replies_buyer_phone ON draft_replies(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_draft_replies_agent_user_id ON draft_replies(agent_user_id)",
]


BACKFILL = [
    """
    INSERT INTO brokerages (
      brokerage_id,
      name,
      slug,
      status,
      created_at,
      updated_at
    )
    VALUES (
      :brokerage_id,
      :brokerage_name,
      :brokerage_slug,
      'active',
      :now,
      :now
    )
    ON CONFLICT (brokerage_id) DO UPDATE
      SET name = EXCLUDED.name,
          slug = EXCLUDED.slug,
          updated_at = EXCLUDED.updated_at
    """,
    "UPDATE listings SET brokerage_id = :brokerage_id WHERE brokerage_id IS NULL",
    """
    UPDATE conversations
    SET brokerage_id = listings.brokerage_id
    FROM listings
    WHERE conversations.listing_id = listings.listing_id
      AND conversations.brokerage_id IS NULL
    """,
    "UPDATE buyer_profiles SET brokerage_id = :brokerage_id WHERE brokerage_id IS NULL",
    """
    UPDATE listing_inquiries
    SET brokerage_id = listings.brokerage_id
    FROM listings
    WHERE listing_inquiries.listing_id = listings.listing_id
      AND listing_inquiries.brokerage_id IS NULL
    """,
    """
    UPDATE suspicious_activity
    SET brokerage_id = listings.brokerage_id
    FROM listings
    WHERE suspicious_activity.listing_id = listings.listing_id
      AND suspicious_activity.brokerage_id IS NULL
    """,
    """
    UPDATE offer_records
    SET brokerage_id = listings.brokerage_id
    FROM listings
    WHERE offer_records.listing_id = listings.listing_id
      AND offer_records.brokerage_id IS NULL
    """,
]


def main() -> None:
    params = {
        "brokerage_id": DEFAULT_BROKERAGE_ID,
        "brokerage_slug": DEFAULT_BROKERAGE_SLUG,
        "brokerage_name": DEFAULT_BROKERAGE_NAME,
        "now": datetime.utcnow(),
    }
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
        for statement in BACKFILL:
            conn.execute(text(statement), params)
    print(f"B2B agent schema migration complete. default_brokerage={DEFAULT_BROKERAGE_ID}")


if __name__ == "__main__":
    main()
