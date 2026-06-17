"""
Add tenant viewing confirmation records.

This migration is additive and idempotent. It backs DAL-154 by tracking tenant
notice sends and tenant confirm/reschedule/decline replies per viewing.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS tenant_viewing_confirmations (
      confirmation_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      viewing_id TEXT NOT NULL REFERENCES viewings(viewing_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      tenant_contact_key TEXT NOT NULL,
      tenant_phone TEXT,
      status TEXT NOT NULL DEFAULT 'pending',
      notice_body TEXT,
      outbound_message_id TEXT,
      last_inbound_body TEXT,
      metadata_json JSONB DEFAULT '{}'::jsonb,
      sent_at TIMESTAMP WITHOUT TIME ZONE,
      responded_at TIMESTAMP WITHOUT TIME ZONE,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_tenant_viewing_confirmation_contact UNIQUE (brokerage_id, viewing_id, tenant_contact_key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_tenant_viewing_confirmations_brokerage_id ON tenant_viewing_confirmations(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_viewing_confirmations_viewing_id ON tenant_viewing_confirmations(viewing_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_viewing_confirmations_listing_id ON tenant_viewing_confirmations(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_viewing_confirmations_tenant_contact_key ON tenant_viewing_confirmations(tenant_contact_key)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_viewing_confirmations_tenant_phone ON tenant_viewing_confirmations(tenant_phone)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_viewing_confirmations_status ON tenant_viewing_confirmations(status)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("tenant_viewing_confirmations migration complete")


if __name__ == "__main__":
    main()
