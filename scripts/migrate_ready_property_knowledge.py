"""
Add ready-property document, fact, and knowledge-summary tables.

This migration is additive and idempotent. It backs DAL-152 by storing
ready-property paperwork, extracted buyer-safe facts, and the summary injected
into Dalya's property advisor prompt.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS listing_documents (
      document_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      document_type TEXT NOT NULL,
      label TEXT,
      source_url TEXT,
      content_text TEXT,
      status TEXT NOT NULL DEFAULT 'processed',
      extracted_at TIMESTAMP WITHOUT TIME ZONE,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_listing_documents_brokerage_id ON listing_documents(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_documents_listing_id ON listing_documents(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_documents_document_type ON listing_documents(document_type)",
    "CREATE INDEX IF NOT EXISTS ix_listing_documents_status ON listing_documents(status)",
    """
    CREATE TABLE IF NOT EXISTS listing_facts (
      fact_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      document_id TEXT REFERENCES listing_documents(document_id),
      fact_key TEXT NOT NULL,
      fact_group TEXT NOT NULL,
      value_text TEXT NOT NULL,
      value_json JSONB DEFAULT '{}'::jsonb,
      confidence DOUBLE PRECISION NOT NULL DEFAULT 0.7,
      source TEXT NOT NULL DEFAULT 'document_extraction',
      verified BOOLEAN NOT NULL DEFAULT false,
      buyer_safe BOOLEAN NOT NULL DEFAULT true,
      risk_flag BOOLEAN NOT NULL DEFAULT false,
      notes TEXT,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_listing_fact_document_key UNIQUE (listing_id, document_id, fact_key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_brokerage_id ON listing_facts(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_listing_id ON listing_facts(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_document_id ON listing_facts(document_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_fact_key ON listing_facts(fact_key)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_fact_group ON listing_facts(fact_group)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_verified ON listing_facts(verified)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_buyer_safe ON listing_facts(buyer_safe)",
    "CREATE INDEX IF NOT EXISTS ix_listing_facts_risk_flag ON listing_facts(risk_flag)",
    """
    CREATE TABLE IF NOT EXISTS listing_knowledge_summaries (
      summary_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_safe_summary TEXT,
      internal_notes TEXT,
      missing_information JSONB DEFAULT '[]'::jsonb,
      risk_flags JSONB DEFAULT '[]'::jsonb,
      status TEXT NOT NULL DEFAULT 'ready',
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_listing_knowledge_summary_scope UNIQUE (brokerage_id, listing_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_listing_knowledge_summaries_brokerage_id ON listing_knowledge_summaries(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_knowledge_summaries_listing_id ON listing_knowledge_summaries(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_listing_knowledge_summaries_status ON listing_knowledge_summaries(status)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("ready_property_knowledge migration complete")


if __name__ == "__main__":
    main()
