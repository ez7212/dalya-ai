"""
Create or update a brokerage signup code for controlled agent onboarding.

Usage:
  PYTHONPATH=$(pwd) python3 scripts/create_brokerage_signup.py \
    --name "Mahoroba Realty" \
    --slug mahoroba-realty

  # Defaults code to MAHOROBA from primary name.
  # Explicit code remains available for exceptions:
  # --code FAM-PROPERTIES
"""

import argparse
import uuid
from datetime import datetime

from app.db.session import SessionLocal, safe_commit
from app.models.db_models import DBBrokerage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--code")
    parser.add_argument("--primary-name")
    parser.add_argument("--contact-name")
    parser.add_argument("--contact-email")
    parser.add_argument("--contact-phone")
    parser.add_argument("--rera-license")
    parser.add_argument("--real-estate-number")
    return parser.parse_args()


def default_signup_code(name: str) -> str:
    primary = name.strip().split()[0]
    return primary.upper().replace("&", "AND")


def main() -> None:
    args = parse_args()
    code_source = args.code or args.primary_name or args.name
    code = default_signup_code(code_source)
    now = datetime.utcnow()

    with SessionLocal() as db:
        brokerage = (
            db.query(DBBrokerage)
            .filter(DBBrokerage.slug == args.slug)
            .first()
        )
        if not brokerage:
            brokerage = DBBrokerage(
                brokerage_id=str(uuid.uuid4()),
                name=args.name,
                slug=args.slug,
                status="active",
                created_at=now,
                updated_at=now,
            )
            db.add(brokerage)

        brokerage.name = args.name
        brokerage.agent_signup_code = code
        brokerage.agent_signup_enabled = True
        brokerage.status = "active"
        brokerage.primary_contact_name = args.contact_name
        brokerage.primary_contact_email = args.contact_email
        brokerage.primary_contact_phone = args.contact_phone
        brokerage.rera_license_number = args.rera_license
        brokerage.real_estate_number = args.real_estate_number
        brokerage.updated_at = now
        safe_commit(db)
        db.refresh(brokerage)

        print("brokerage signup enabled")
        print(f"brokerage_id={brokerage.brokerage_id}")
        print(f"name={brokerage.name}")
        print(f"slug={brokerage.slug}")
        print(f"real_estate_number={brokerage.real_estate_number}")
        print(f"agent_signup_code={brokerage.agent_signup_code}")


if __name__ == "__main__":
    main()
