"""
Activate agents that were created before the approval gate was removed.

If an agent profile is DLD-matched or verified and belongs to an active,
signup-enabled brokerage, this promotes the membership, profile, and chatbot
handoff config to active.
"""

from datetime import datetime

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentChatbotConfig,
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageMember,
)


def main() -> None:
    updated = 0
    now = datetime.utcnow()
    with SessionLocal() as db:
        profiles = (
            db.query(DBAgentProfile)
            .filter(DBAgentProfile.verification_status.in_(["dld_matched", "verified"]))
            .all()
        )
        for profile in profiles:
            brokerage = db.get(DBBrokerage, profile.brokerage_id)
            if not brokerage or brokerage.status != "active" or not brokerage.agent_signup_enabled:
                continue

            changed = False
            member = (
                db.query(DBBrokerageMember)
                .filter(
                    DBBrokerageMember.brokerage_id == profile.brokerage_id,
                    DBBrokerageMember.user_id == profile.user_id,
                )
                .first()
            )
            if member and member.status != "active":
                member.status = "active"
                member.updated_at = now
                changed = True

            if profile.onboarding_status != "active":
                profile.onboarding_status = "active"
                profile.updated_at = now
                changed = True

            config = (
                db.query(DBAgentChatbotConfig)
                .filter(DBAgentChatbotConfig.agent_profile_id == profile.profile_id)
                .first()
            )
            if config and not config.active:
                config.active = True
                config.settings = {
                    **(config.settings or {}),
                    "activation": "dld_brokerage_match_backfill",
                }
                config.updated_at = now
                changed = True

            if changed:
                updated += 1

        safe_commit(db)

    print(f"activated_profiles={updated}")


if __name__ == "__main__":
    main()
