"""
Idempotent migration for portal lead ingestion (DAL-163).

Creates lead_ingests — ingested PF/Bayut leads with parser versioning,
listing resolution state, first-touch tracking, and the raw email retained
as PDPL consent-basis evidence.

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_lead_ingest.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS lead_ingests (
      ingest_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      source TEXT NOT NULL DEFAULT 'unknown',
      parser_version TEXT,
      status TEXT NOT NULL DEFAULT 'ingested',
      buyer_name TEXT,
      buyer_phone TEXT,
      buyer_message TEXT,
      portal_listing_ref TEXT,
      portal_listing_url TEXT,
      listing_id TEXT REFERENCES listings(listing_id),
      listing_resolution TEXT,
      conversation_id TEXT REFERENCES conversations(conversation_id),
      first_touch_sent BOOLEAN NOT NULL DEFAULT FALSE,
      first_touch_template TEXT,
      nudge_draft_id TEXT,
      error TEXT,
      raw_payload JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_lead_ingests_brokerage_id ON lead_ingests(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_ingests_buyer_phone ON lead_ingests(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_lead_ingests_status ON lead_ingests(status)",
    "CREATE INDEX IF NOT EXISTS ix_lead_ingests_listing_id ON lead_ingests(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_ingests_conversation_id ON lead_ingests(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_ingests_created_at ON lead_ingests(created_at)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Lead ingest migration complete.")


if __name__ == "__main__":
    main()
