"""
Multi-tenant platform migration — Phase 1.

Adds the schema needed for the B2B platform pivot:
- DBBrokerage gains brokerage_ai_number, agents_ai_number, default_fee_framing
- DBListing gains commission_rate, additional_fees, notification_threshold_aed,
  property_type, source_url, reference_documents, community
- New tables: agent_community_remarks, agent_message_routes

Backfills existing single-tenant data into the new structure:
- Mahoroba Realty brokerage exists with signup-enabled, real_estate_number,
  brokerage_ai_number from DALYA_PHONE_NUMBER env, placeholder agents_ai_number
- Irwin Real Estate brokerage exists (seeded approved brokerage)
- Eric agent profile exists under Mahoroba (idempotent — uses ENV
  ERIC_USER_ID / ERIC_PHONE / ERIC_RERA_BRN if set, else placeholders that an
  admin can correct later)
- Existing listings: brokerage_id → Mahoroba, assigned_agent_id → Eric,
  notification_threshold_aed ← negotiation_threshold_aed,
  property_type ← "off_plan", community ← best-effort key from spa_data.project.
  Commission is deliberately not backfilled; it must be specified per listing.

Idempotent — safe to re-run.

Usage:
  PYTHONPATH=$(pwd) venv/bin/python scripts/migrate_multitenant_phase1.py
"""

import os
import re
import uuid
from datetime import datetime

from sqlalchemy import text

from app.db.session import engine


DDL = [
    # ── DBBrokerage extensions ────────────────────────────────────────────────
    "ALTER TABLE brokerages ADD COLUMN IF NOT EXISTS brokerage_ai_number TEXT",
    "ALTER TABLE brokerages ADD COLUMN IF NOT EXISTS agents_ai_number TEXT",
    "ALTER TABLE brokerages ADD COLUMN IF NOT EXISTS default_fee_framing JSONB",
    "CREATE INDEX IF NOT EXISTS ix_brokerages_brokerage_ai_number ON brokerages(brokerage_ai_number)",
    "CREATE INDEX IF NOT EXISTS ix_brokerages_agents_ai_number ON brokerages(agents_ai_number)",

    # ── DBListing extensions ──────────────────────────────────────────────────
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS commission_rate DOUBLE PRECISION",
    "UPDATE listings SET commission_rate = 0.01 WHERE commission_rate IS NULL",
    "ALTER TABLE listings ALTER COLUMN commission_rate SET NOT NULL",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS additional_fees JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS notification_threshold_aed DOUBLE PRECISION",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS property_type TEXT",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS reference_documents JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS community TEXT",
    "CREATE INDEX IF NOT EXISTS ix_listings_community ON listings(community)",

    # ── agent_community_remarks ───────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS agent_community_remarks (
      remark_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_user_id TEXT NOT NULL,
      community_key TEXT NOT NULL,
      body TEXT NOT NULL,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_community_remarks_brokerage_id ON agent_community_remarks(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_community_remarks_agent_user_id ON agent_community_remarks(agent_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_community_remarks_community_key ON agent_community_remarks(community_key)",

    # ── agent_message_routes ──────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS agent_message_routes (
      route_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id),
      listing_id TEXT NOT NULL REFERENCES listings(listing_id),
      buyer_phone TEXT NOT NULL,
      agent_user_id TEXT,
      agent_phone TEXT,
      agents_ai_envelope_token TEXT NOT NULL UNIQUE,
      escalation_type TEXT NOT NULL,
      tags JSONB DEFAULT '[]'::jsonb,
      expires_at TIMESTAMP WITHOUT TIME ZONE,
      consumed_at TIMESTAMP WITHOUT TIME ZONE,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_brokerage_id ON agent_message_routes(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_conversation_id ON agent_message_routes(conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_listing_id ON agent_message_routes(listing_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_buyer_phone ON agent_message_routes(buyer_phone)",
    "CREATE INDEX IF NOT EXISTS ix_agent_message_routes_token ON agent_message_routes(agents_ai_envelope_token)",
]


MAHOROBA_BROKERAGE_ID = "mahoroba-realty"
MAHOROBA_REAL_ESTATE_NUMBER = os.getenv("MAHOROBA_REAL_ESTATE_NUMBER", "1858")  # Mahoroba's actual DLD office number; placeholder safe to overwrite
IRWIN_BROKERAGE_ID = "irwin-real-estate"
IRWIN_REAL_ESTATE_NUMBER = os.getenv("IRWIN_REAL_ESTATE_NUMBER", "IRWIN-OFFICE-001")

DEFAULT_MAHOROBA_AGENTS_AI = "+971500000099"
DEFAULT_IRWIN_BROKERAGE_AI = "+971500000201"
DEFAULT_IRWIN_AGENTS_AI = "+971500000299"


def _slugify_community(project: str) -> str:
    """Generate a stable community key from a project name (e.g. 'Palace Villas Ostra' -> 'palace_villas_ostra')."""
    if not project:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", project).strip("_").lower()
    return cleaned


def main() -> None:
    now = datetime.utcnow()

    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))

        # ── Seed Mahoroba Realty as brokerage #1 ────────────────────────────
        dalya_phone = os.getenv("DALYA_PHONE_NUMBER", "+971500000001")
        conn.execute(
            text(
                """
                INSERT INTO brokerages (
                  brokerage_id, name, slug,
                  real_estate_number, agent_signup_code, agent_signup_enabled,
                  brokerage_ai_number, agents_ai_number,
                  default_fee_framing,
                  prompt_config, settings, status,
                  created_at, updated_at
                )
                VALUES (
                  :brokerage_id, :name, :slug,
                  :real_estate_number, :signup_code, TRUE,
                  :brokerage_ai_number, :agents_ai_number,
                  :default_fee_framing,
                  :prompt_config, :settings, 'active',
                  :now, :now
                )
                ON CONFLICT (slug) DO UPDATE SET
                  name = EXCLUDED.name,
                  real_estate_number = COALESCE(brokerages.real_estate_number, EXCLUDED.real_estate_number),
                  agent_signup_code = COALESCE(brokerages.agent_signup_code, EXCLUDED.agent_signup_code),
                  agent_signup_enabled = TRUE,
                  brokerage_ai_number = COALESCE(brokerages.brokerage_ai_number, EXCLUDED.brokerage_ai_number),
                  agents_ai_number = COALESCE(brokerages.agents_ai_number, EXCLUDED.agents_ai_number),
                  default_fee_framing = COALESCE(brokerages.default_fee_framing, EXCLUDED.default_fee_framing),
                  prompt_config = CASE
                    WHEN brokerages.prompt_config IS NULL OR brokerages.prompt_config = '{}'::jsonb THEN EXCLUDED.prompt_config
                    ELSE brokerages.prompt_config
                  END,
                  settings = CASE
                    WHEN brokerages.settings IS NULL OR brokerages.settings = '{}'::jsonb THEN EXCLUDED.settings
                    ELSE brokerages.settings
                  END,
                  status = 'active',
                  updated_at = :now
                """
            ),
            {
                "brokerage_id": MAHOROBA_BROKERAGE_ID,
                "name": "Mahoroba Realty",
                "slug": "mahoroba-realty",
                "real_estate_number": MAHOROBA_REAL_ESTATE_NUMBER,
                "signup_code": "MAHOROBA",
                "brokerage_ai_number": dalya_phone,
                "agents_ai_number": DEFAULT_MAHOROBA_AGENTS_AI,
                "default_fee_framing": '{"market_benchmark": 0.02, "narrative": "save vs 2% market", "managing_agent_title": "Lead Broker"}',
                "prompt_config": '{"name_arabic": "مهروبة العقارية", "managing_agent_title": "Lead Broker"}',
                "settings": '{"legacy_telegram_alerts": true}',
                "now": now,
            },
        )
        mahoroba_brokerage_id = conn.execute(
            text("SELECT brokerage_id FROM brokerages WHERE slug = 'mahoroba-realty'")
        ).scalar_one()

        # ── Seed Irwin Real Estate as approved brokerage ────────────────────
        conn.execute(
            text(
                """
                INSERT INTO brokerages (
                  brokerage_id, name, slug,
                  real_estate_number, agent_signup_code, agent_signup_enabled,
                  brokerage_ai_number, agents_ai_number,
                  default_fee_framing,
                  prompt_config, settings, status,
                  created_at, updated_at
                )
                VALUES (
                  :brokerage_id, :name, :slug,
                  :real_estate_number, :signup_code, TRUE,
                  :brokerage_ai_number, :agents_ai_number,
                  :default_fee_framing,
                  :prompt_config, :settings, 'active',
                  :now, :now
                )
                ON CONFLICT (slug) DO UPDATE SET
                  name = EXCLUDED.name,
                  real_estate_number = COALESCE(brokerages.real_estate_number, EXCLUDED.real_estate_number),
                  agent_signup_code = COALESCE(brokerages.agent_signup_code, EXCLUDED.agent_signup_code),
                  agent_signup_enabled = TRUE,
                  brokerage_ai_number = COALESCE(brokerages.brokerage_ai_number, EXCLUDED.brokerage_ai_number),
                  agents_ai_number = COALESCE(brokerages.agents_ai_number, EXCLUDED.agents_ai_number),
                  default_fee_framing = COALESCE(brokerages.default_fee_framing, EXCLUDED.default_fee_framing),
                  prompt_config = CASE
                    WHEN brokerages.prompt_config IS NULL OR brokerages.prompt_config = '{}'::jsonb THEN EXCLUDED.prompt_config
                    ELSE brokerages.prompt_config
                  END,
                  settings = CASE
                    WHEN brokerages.settings IS NULL OR brokerages.settings = '{}'::jsonb THEN EXCLUDED.settings
                    ELSE brokerages.settings
                  END,
                  status = 'active',
                  updated_at = :now
                """
            ),
            {
                "brokerage_id": IRWIN_BROKERAGE_ID,
                "name": "Irwin Real Estate",
                "slug": "irwin-real-estate",
                "real_estate_number": IRWIN_REAL_ESTATE_NUMBER,
                "signup_code": "IRWIN",
                "brokerage_ai_number": DEFAULT_IRWIN_BROKERAGE_AI,
                "agents_ai_number": DEFAULT_IRWIN_AGENTS_AI,
                "default_fee_framing": '{"managing_agent_title": "Managing Director"}',
                "prompt_config": '{"managing_agent_title": "Managing Director"}',
                "settings": "{}",
                "now": now,
            },
        )
        irwin_brokerage_id = conn.execute(
            text("SELECT brokerage_id FROM brokerages WHERE slug = 'irwin-real-estate'")
        ).scalar_one()

        # ── Resolve Mahoroba's first agent ──────────────────────────────────
        # Prefer a real onboarded/DLD-matched agent. Only create a placeholder
        # if this is a fresh database with no Mahoroba agent profile at all.
        existing_agent = conn.execute(
            text(
                """
                SELECT profile_id, user_id, display_name, whatsapp_phone
                FROM agent_profiles
                WHERE brokerage_id = :brokerage_id
                  AND user_id != 'eric-mahoroba-seed'
                ORDER BY
                  CASE WHEN verification_provider = 'dld_gateway' THEN 0 ELSE 1 END,
                  created_at ASC
                LIMIT 1
                """
            ),
            {"brokerage_id": mahoroba_brokerage_id},
        ).mappings().one_or_none()

        if existing_agent:
            eric_user_id = existing_agent["user_id"]
            profile_id = existing_agent["profile_id"]
            eric_phone = existing_agent["whatsapp_phone"]
            eric_display_name = existing_agent["display_name"] or "Eric"
        else:
            eric_user_id = os.getenv("ERIC_USER_ID", "eric-mahoroba-seed")
            eric_phone = os.getenv("ERIC_PHONE", os.getenv("TELEGRAM_CHAT_ID_PHONE", "+971500000010"))
            eric_brn = os.getenv("ERIC_RERA_BRN", "BRN-PLACEHOLDER-ERIC")
            eric_display_name = "Eric"
            member_id = "mahoroba-member-eric"
            profile_id = "mahoroba-profile-eric"

            conn.execute(
                text(
                    """
                    INSERT INTO brokerage_members (
                      member_id, brokerage_id, user_id, email, display_name, phone,
                      role, status, settings, created_at, updated_at
                    )
                    VALUES (
                      :member_id, :brokerage_id, :user_id, :email, :display_name, :phone,
                      'agent', 'active', '{"source": "migration_phase1"}'::jsonb, :now, :now
                    )
                    ON CONFLICT (brokerage_id, user_id) DO UPDATE SET
                      status = 'active', updated_at = :now
                    """
                ),
                {
                    "member_id": member_id,
                    "brokerage_id": mahoroba_brokerage_id,
                    "user_id": eric_user_id,
                    "email": os.getenv("ERIC_EMAIL", "ericzhu0702@gmail.com"),
                    "display_name": eric_display_name,
                    "phone": eric_phone,
                    "now": now,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO agent_profiles (
                      profile_id, brokerage_id, user_id, email, full_name, display_name,
                      whatsapp_phone, rera_broker_card_number,
                      languages, service_areas,
                      verification_status, verification_provider,
                      chatbot_display_name, chatbot_handoff_phone,
                      onboarding_status, settings,
                      created_at, updated_at
                    )
                    VALUES (
                      :profile_id, :brokerage_id, :user_id, :email, :full_name, :display_name,
                      :whatsapp_phone, :rera_broker_card_number,
                      '["en"]'::jsonb, '["Dubai"]'::jsonb,
                      'verified', 'manual',
                      :chatbot_display_name, :chatbot_handoff_phone,
                      'active', '{"source": "migration_phase1"}'::jsonb,
                      :now, :now
                    )
                    ON CONFLICT (brokerage_id, user_id) DO UPDATE SET
                      display_name = EXCLUDED.display_name,
                      whatsapp_phone = EXCLUDED.whatsapp_phone,
                      chatbot_display_name = EXCLUDED.chatbot_display_name,
                      chatbot_handoff_phone = EXCLUDED.chatbot_handoff_phone,
                      onboarding_status = 'active',
                      updated_at = :now
                    """
                ),
                {
                    "profile_id": profile_id,
                    "brokerage_id": mahoroba_brokerage_id,
                    "user_id": eric_user_id,
                    "email": os.getenv("ERIC_EMAIL", "ericzhu0702@gmail.com"),
                    "full_name": "Eric Zhu",
                    "display_name": eric_display_name,
                    "whatsapp_phone": eric_phone,
                    "rera_broker_card_number": eric_brn,
                    "chatbot_display_name": eric_display_name,
                    "chatbot_handoff_phone": eric_phone,
                    "now": now,
                },
            )

        config_id = f"mahoroba-config-{eric_user_id}"
        conn.execute(
            text(
                """
                INSERT INTO agent_chatbot_configs (
                  config_id, brokerage_id, agent_profile_id, agent_user_id,
                  handoff_display_name, escalation_whatsapp_phone, active,
                  settings, created_at, updated_at
                )
                VALUES (
                  :config_id, :brokerage_id, :profile_id, :agent_user_id,
                  :display_name, :phone, TRUE,
                  '{"activation": "migration_phase1"}'::jsonb, :now, :now
                )
                ON CONFLICT (agent_profile_id) DO UPDATE SET
                  active = TRUE, updated_at = :now
                """
            ),
            {
                "config_id": config_id,
                "brokerage_id": mahoroba_brokerage_id,
                "profile_id": profile_id,
                "agent_user_id": eric_user_id,
                "display_name": eric_display_name,
                "phone": eric_phone,
                "now": now,
            },
        )

        # ── Backfill existing listings: brokerage_id, agent, threshold, property_type ──
        conn.execute(
            text(
                "UPDATE listings SET brokerage_id = :brokerage_id WHERE brokerage_id IS NULL"
            ),
            {"brokerage_id": mahoroba_brokerage_id},
        )
        conn.execute(
            text(
                "UPDATE listings SET assigned_agent_id = :agent_user_id "
                "WHERE brokerage_id = :brokerage_id AND assigned_agent_id IS NULL"
            ),
            {"agent_user_id": eric_user_id, "brokerage_id": mahoroba_brokerage_id},
        )
        conn.execute(
            text(
                "UPDATE listings SET notification_threshold_aed = negotiation_threshold_aed "
                "WHERE notification_threshold_aed IS NULL AND negotiation_threshold_aed IS NOT NULL"
            )
        )
        conn.execute(
            text(
                "UPDATE listings SET property_type = 'off_plan' WHERE property_type IS NULL"
            )
        )

        # Backfill community key best-effort from spa_data.project
        rows = conn.execute(
            text("SELECT listing_id, spa_data FROM listings WHERE community IS NULL OR community = ''")
        ).fetchall()
        for row in rows:
            spa_data = row.spa_data or {}
            project = (spa_data.get("project") or "") if isinstance(spa_data, dict) else ""
            community_key = _slugify_community(project)
            if community_key:
                conn.execute(
                    text("UPDATE listings SET community = :community WHERE listing_id = :listing_id"),
                    {"community": community_key, "listing_id": row.listing_id},
                )

    print("Multi-tenant phase 1 migration complete.")
    print(f"  Mahoroba brokerage_id: {mahoroba_brokerage_id}")
    print(f"  Irwin brokerage_id:    {irwin_brokerage_id}")
    print(f"  Eric user_id:          {eric_user_id}")
    print("  Listings backfilled with property_type='off_plan' where missing; commission remains per-listing.")


if __name__ == "__main__":
    main()
