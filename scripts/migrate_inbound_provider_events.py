"""
Idempotent migration for inbound provider replay protection (DAL-169).

Creates inbound_provider_events, a small ledger used before webhook routing so
duplicate provider deliveries cannot enqueue, relay, or send twice.

Run:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_inbound_provider_events.py
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS inbound_provider_events (
      event_id TEXT PRIMARY KEY,
      provider TEXT NOT NULL,
      endpoint TEXT NOT NULL,
      provider_event_id TEXT,
      payload_fingerprint TEXT NOT NULL,
      brokerage_id TEXT REFERENCES brokerages(brokerage_id),
      status TEXT NOT NULL DEFAULT 'processing',
      replay_count INTEGER NOT NULL DEFAULT 0,
      received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
      replayed_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_inbound_provider_event_id
      ON inbound_provider_events(provider, endpoint, provider_event_id)
      WHERE provider_event_id IS NOT NULL
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_inbound_provider_payload_fingerprint
      ON inbound_provider_events(provider, endpoint, payload_fingerprint)
    """,
    "CREATE INDEX IF NOT EXISTS ix_inbound_provider_events_provider ON inbound_provider_events(provider)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_provider_events_endpoint ON inbound_provider_events(endpoint)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_provider_events_brokerage_id ON inbound_provider_events(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_inbound_provider_events_received_at ON inbound_provider_events(received_at)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Inbound provider event migration complete.")


if __name__ == "__main__":
    main()
