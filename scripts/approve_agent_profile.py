"""
Approve an onboarded agent profile and activate their chatbot handoff config.

Usage:
  PYTHONPATH=$(pwd) venv/bin/python scripts/approve_agent_profile.py \
    --email agent@example.com

or:
  PYTHONPATH=$(pwd) venv/bin/python scripts/approve_agent_profile.py \
    --rera-card 12345
"""

import argparse
from datetime import datetime

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentChatbotConfig,
    DBAgentProfile,
    DBAgentVerification,
    DBBrokerageMember,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email")
    group.add_argument("--user-id")
    group.add_argument("--rera-card")
    parser.add_argument("--reviewed-by", default="dalya-admin")
    parser.add_argument("--note", default="Approved for pilot testing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        query = db.query(DBAgentProfile)
        if args.email:
            profile = query.filter(DBAgentProfile.email == args.email).first()
        elif args.user_id:
            profile = query.filter(DBAgentProfile.user_id == args.user_id).first()
        else:
            profile = query.filter(DBAgentProfile.rera_broker_card_number == args.rera_card).first()

        if not profile:
            raise SystemExit("No matching agent profile found.")

        now = datetime.utcnow()
        profile.verification_status = "verified"
        profile.onboarding_status = "active"
        profile.verification_notes = args.note
        profile.updated_at = now

        member = (
            db.query(DBBrokerageMember)
            .filter(
                DBBrokerageMember.brokerage_id == profile.brokerage_id,
                DBBrokerageMember.user_id == profile.user_id,
            )
            .first()
        )
        if member:
            member.status = "active"
            member.updated_at = now

        config = (
            db.query(DBAgentChatbotConfig)
            .filter(DBAgentChatbotConfig.agent_profile_id == profile.profile_id)
            .first()
        )
        if config:
            config.active = True
            config.handoff_display_name = profile.chatbot_display_name or profile.display_name
            config.escalation_whatsapp_phone = profile.chatbot_handoff_phone or profile.whatsapp_phone
            config.updated_at = now

        verification = DBAgentVerification(
            brokerage_id=profile.brokerage_id,
            agent_profile_id=profile.profile_id,
            user_id=profile.user_id,
            provider="manual",
            status="verified",
            rera_broker_card_number=profile.rera_broker_card_number,
            reviewed_by=args.reviewed_by,
            reviewed_at=now,
            notes=args.note,
            raw_response={"source": "approve_agent_profile.py"},
        )
        db.add(verification)

        safe_commit(db)

        print("agent approved")
        print(f"profile_id={profile.profile_id}")
        print(f"user_id={profile.user_id}")
        print(f"email={profile.email}")
        print(f"brokerage_id={profile.brokerage_id}")
        print(f"chatbot_config_active={bool(config and config.active)}")


if __name__ == "__main__":
    main()
