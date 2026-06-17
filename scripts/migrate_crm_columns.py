"""
Migration: Add CRM columns to buyer_profiles table.
Run once: python scripts/migrate_crm_columns.py
"""

from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from sqlalchemy import text

STATEMENTS = [
    "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS lead_stage TEXT DEFAULT 'new';",
    "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS lead_source TEXT;",
    "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;",
    "ALTER TABLE buyer_profiles ADD COLUMN IF NOT EXISTS admin_notes JSONB DEFAULT '[]'::jsonb;",
]

if __name__ == "__main__":
    with SessionLocal() as db:
        for stmt in STATEMENTS:
            print(f"  Running: {stmt}")
            db.execute(text(stmt))
        db.commit()
    print("Migration complete.")
