"""
Add brokerage-scoped buyer preference profiles for DAL-6.

This intentionally leaves the legacy `buyer_profiles` table in place for CRM
compatibility. The new table is the source of truth for brokerage-scoped buyer
preferences and cross-listing matching.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS buyer_preference_profiles (
      profile_id TEXT PRIMARY KEY,
      buyer_id TEXT NOT NULL,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      stated_preferences JSONB DEFAULT '{}'::jsonb,
      inferred_preferences JSONB DEFAULT '{}'::jsonb,
      inquiry_history JSONB DEFAULT '[]'::jsonb,
      notes TEXT,
      last_alternative_surface_at TIMESTAMP WITHOUT TIME ZONE,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_buyer_preference_profile_scope UNIQUE (brokerage_id, buyer_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_buyer_preference_profiles_buyer_id ON buyer_preference_profiles(buyer_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_preference_profiles_brokerage_id ON buyer_preference_profiles(brokerage_id)",
]


def main():
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("buyer_preference_profiles migration applied")


if __name__ == "__main__":
    main()
