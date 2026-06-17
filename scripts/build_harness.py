import argparse
from pathlib import Path
import sys

from sqlalchemy.exc import ProgrammingError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.safety import UnsafeTestDatabaseError, assert_safe_test_database, load_test_environment_file


def _print_seed(seed) -> None:
    print(f"brokerages={len(seed.brokerages)} agents={len(seed.agents)} listings={len(seed.listings)}")
    for listing in seed.listings:
        print(
            f"{listing.listing_id} {listing.brokerage_id} {listing.property_type} "
            f"AED {listing.asking_price_aed:,.0f} images={len(listing.media_urls)} agent={listing.assigned_agent_id}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or inspect the canonical multi-brokerage test harness.")
    parser.add_argument("action", choices=["plan", "build", "summary", "teardown"])
    args = parser.parse_args()
    load_test_environment_file()

    from tests.harness import build_harness, build_harness_plan, get_harness_seed, teardown_harness

    if args.action == "plan":
        _print_seed(build_harness_plan())
        return

    if args.action in {"build", "summary", "teardown"}:
        try:
            assert_safe_test_database(operation=f"scripts/build_harness.py {args.action}")
        except UnsafeTestDatabaseError as exc:
            raise SystemExit(f"\n*** DALYA TEST DATABASE SAFETY GUARD ***\n{exc}\n") from exc

    from app.db.session import SessionLocal

    try:
        with SessionLocal() as db:
            if args.action == "build":
                _print_seed(build_harness(db))
            elif args.action == "summary":
                _print_seed(get_harness_seed(db))
            elif args.action == "teardown":
                teardown_harness(db)
                print("harness teardown complete")
    except ProgrammingError as exc:
        message = str(exc)
        if "brokerage_ai_number" in message or "agents_ai_number" in message:
            raise SystemExit(
                "Database schema is missing multitenant brokerage/listing columns. "
                "Run the existing multitenant migration before seeding the harness "
                "(for example `venv/bin/python scripts/migrate_multitenant_phase1.py`)."
            ) from exc
        raise


if __name__ == "__main__":
    main()
