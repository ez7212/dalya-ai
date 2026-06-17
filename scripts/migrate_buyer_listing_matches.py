"""
Add buyer-to-new-listing re-marketing matches for DAL-9.

Records are persisted so the listing detail page and future hot-list surface can
consume the same data shape.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    """
    CREATE TABLE IF NOT EXISTS buyer_listing_matches (
      match_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_profile_id TEXT NOT NULL REFERENCES buyer_preference_profiles(profile_id),
      buyer_id TEXT NOT NULL,
      match_score DOUBLE PRECISION NOT NULL DEFAULT 0,
      aligned_preferences JSONB DEFAULT '[]'::jsonb,
      traced_inquiry_listing_ids JSONB DEFAULT '[]'::jsonb,
      outreach_draft TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft',
      metadata_json JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_buyer_listing_match UNIQUE (listing_id, buyer_profile_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_buyer_listing_matches_brokerage_id ON buyer_listing_matches(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_listing_matches_listing_id ON buyer_listing_matches(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_listing_matches_buyer_profile_id ON buyer_listing_matches(buyer_profile_id)",
    "CREATE INDEX IF NOT EXISTS ix_buyer_listing_matches_buyer_id ON buyer_listing_matches(buyer_id)",
]


def main():
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("buyer_listing_matches migration applied")


if __name__ == "__main__":
    main()
