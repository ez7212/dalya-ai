"""
Idempotent migration for buyer cards + offer log (DAL-164 / DAL-165).

Creates:
  brokerage_buyer_profiles — (brokerage_id, phone)-keyed buyer profiles
  buyer_profile_fields     — field-level qualification rows with provenance
  offers                   — first-class offer records with thread state

Backfill over existing conversations:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_buyer_profiles_offers.py --backfill
"""

import sys

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS brokerage_buyer_profiles (
      profile_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      buyer_phone TEXT NOT NULL,
      name TEXT,
      language TEXT,
      source TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      CONSTRAINT uq_brokerage_buyer_profile UNIQUE (brokerage_id, buyer_phone)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_brokerage_buyer_profiles_brokerage_id ON brokerage_buyer_profiles(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_brokerage_buyer_profiles_buyer_phone ON brokerage_buyer_profiles(buyer_phone)",
    """
    CREATE TABLE IF NOT EXISTS buyer_profile_fields (
      field_id TEXT PRIMARY KEY,
      profile_id TEXT NOT NULL REFERENCES brokerage_buyer_profiles(profile_id),
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      field TEXT NOT NULL,
      value JSONB,
      provenance TEXT NOT NULL,
      confidence DOUBLE PRECISION,
      source_message_id INTEGER REFERENCES messages(id),
      confirmed_by TEXT,
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      CONSTRAINT uq_buyer_profile_field_provenance UNIQUE (profile_id, field, provenance)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_buyer_profile_fields_profile_id ON buyer_profile_fields(profile_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_profile_fields_brokerage_id ON buyer_profile_fields(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_profile_fields_field ON buyer_profile_fields(field)",
    """
    CREATE TABLE IF NOT EXISTS offers (
      offer_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT,
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_profile_id TEXT REFERENCES brokerage_buyer_profiles(profile_id),
      buyer_phone TEXT NOT NULL,
      thread_key TEXT NOT NULL,
      amount DOUBLE PRECISION,
      direction TEXT NOT NULL DEFAULT 'buyer_offer',
      status TEXT NOT NULL DEFAULT 'draft_pending_confirm',
      conditions TEXT,
      financing_contingent BOOLEAN NOT NULL DEFAULT FALSE,
      subject_to_viewing BOOLEAN NOT NULL DEFAULT FALSE,
      source TEXT NOT NULL DEFAULT 'agent_logged',
      source_message_id INTEGER REFERENCES messages(id),
      thread_id TEXT REFERENCES escalation_threads(thread_id),
      confirmed_at TIMESTAMP WITHOUT TIME ZONE,
      confirmed_by TEXT,
      closed_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_offers_brokerage_id ON offers(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_offers_conversation_id ON offers(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_offers_listing_id ON offers(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_offers_buyer_phone ON offers(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_offers_thread_key ON offers(thread_key)",
    "CREATE INDEX IF NOT EXISTS ix_offers_status ON offers(status)",
    "CREATE INDEX IF NOT EXISTS ix_offers_agent_user_id ON offers(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_offers_buyer_profile_id ON offers(buyer_profile_id)",
    "CREATE INDEX IF NOT EXISTS ix_offers_thread_id ON offers(thread_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Buyer profiles + offers migration complete.")

    if "--backfill" in sys.argv:
        from app.core.buyer_profiles import backfill_profiles_from_conversations
        from app.db.session import SessionLocal

        with SessionLocal() as db:
            created = backfill_profiles_from_conversations(db)
        print(f"Backfilled {created} buyer profile(s) from existing conversations.")


if __name__ == "__main__":
    main()
