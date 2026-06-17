"""
Add brokerage-first agent onboarding tables.

Rollout rule:
- Dalya creates/approves the brokerage first.
- Agents can only join a brokerage with a registered brokerage signup code.
- Unknown brokerages are directed to contact Dalya instead of self-creating.
"""

from sqlalchemy import text

from app.db.session import engine


DDL = [
    "ALTER TABLE brokerages ADD COLUMN IF NOT EXISTS real_estate_number TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_brokerages_real_estate_number ON brokerages(real_estate_number)",
    "ALTER TABLE brokerages ADD COLUMN IF NOT EXISTS agent_signup_code TEXT",
    "ALTER TABLE brokerages ADD COLUMN IF NOT EXISTS agent_signup_enabled BOOLEAN NOT NULL DEFAULT false",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_brokerages_agent_signup_code ON brokerages(agent_signup_code)",
    """
    CREATE TABLE IF NOT EXISTS agent_profiles (
      profile_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      user_id TEXT NOT NULL,
      email TEXT,
      full_name TEXT NOT NULL,
      display_name TEXT NOT NULL,
      whatsapp_phone TEXT NOT NULL,
      rera_broker_card_number TEXT NOT NULL,
      rera_card_expiry TIMESTAMP WITHOUT TIME ZONE,
      broker_card_file_url TEXT,
      languages JSONB DEFAULT '[]'::jsonb,
      service_areas JSONB DEFAULT '[]'::jsonb,
      verification_status TEXT NOT NULL DEFAULT 'submitted',
      verification_provider TEXT NOT NULL DEFAULT 'manual',
      verification_notes TEXT,
      chatbot_display_name TEXT,
      chatbot_handoff_phone TEXT,
      onboarding_status TEXT NOT NULL DEFAULT 'submitted',
      settings JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_agent_profile_brokerage_user UNIQUE (brokerage_id, user_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_profiles_brokerage_id ON agent_profiles(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_profiles_user_id ON agent_profiles(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_profiles_email ON agent_profiles(email)",
    "CREATE INDEX IF NOT EXISTS ix_agent_profiles_whatsapp_phone ON agent_profiles(whatsapp_phone)",
    "CREATE INDEX IF NOT EXISTS ix_agent_profiles_rera_broker_card_number ON agent_profiles(rera_broker_card_number)",
    """
    CREATE TABLE IF NOT EXISTS agent_verifications (
      verification_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_profile_id TEXT NOT NULL REFERENCES agent_profiles(profile_id),
      user_id TEXT NOT NULL,
      provider TEXT NOT NULL DEFAULT 'manual',
      status TEXT NOT NULL DEFAULT 'submitted',
      rera_broker_card_number TEXT NOT NULL,
      raw_response JSONB DEFAULT '{}'::jsonb,
      reviewed_by TEXT,
      reviewed_at TIMESTAMP WITHOUT TIME ZONE,
      notes TEXT,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_verifications_brokerage_id ON agent_verifications(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_verifications_agent_profile_id ON agent_verifications(agent_profile_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_verifications_user_id ON agent_verifications(user_id)",
    """
    CREATE TABLE IF NOT EXISTS agent_chatbot_configs (
      config_id TEXT PRIMARY KEY,
      brokerage_id TEXT NOT NULL REFERENCES brokerages(brokerage_id),
      agent_profile_id TEXT NOT NULL REFERENCES agent_profiles(profile_id),
      agent_user_id TEXT NOT NULL,
      handoff_display_name TEXT NOT NULL,
      escalation_whatsapp_phone TEXT NOT NULL,
      fallback_user_id TEXT,
      active BOOLEAN NOT NULL DEFAULT false,
      settings JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
      CONSTRAINT uq_agent_chatbot_config_profile UNIQUE (agent_profile_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_agent_chatbot_configs_brokerage_id ON agent_chatbot_configs(brokerage_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_chatbot_configs_agent_user_id ON agent_chatbot_configs(agent_user_id)",
]


def main() -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    print("Agent onboarding schema migration complete.")


if __name__ == "__main__":
    main()
