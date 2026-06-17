import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.safety import UnsafeTestDatabaseError, assert_safe_test_database, load_test_environment_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate deterministic Maps/KHDA enrichment for harness listings.")
    parser.add_argument("--prefix", default="HARNESS_listing_", help="Listing ID prefix to enrich.")
    args = parser.parse_args()

    load_test_environment_file()
    try:
        assert_safe_test_database(operation="scripts/enrich_harness_listings.py")
    except UnsafeTestDatabaseError as exc:
        raise SystemExit(f"\n*** DALYA TEST DATABASE SAFETY GUARD ***\n{exc}\n") from exc

    from app.core.listing_enrichment import persist_fixture_enrichment
    from app.db.session import SessionLocal, engine, safe_commit
    from app.db.session import Base
    from app.models.db_models import DBListing

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        listings = (
            db.query(DBListing)
            .filter(DBListing.listing_id.like(f"{args.prefix}%"))
            .order_by(DBListing.listing_id.asc())
            .all()
        )
        results = []
        for listing in listings:
            result = persist_fixture_enrichment(db, listing)
            if result:
                results.append(result)
        safe_commit(db)

    print(f"enriched={len(results)} listings")
    for result in results:
        print(
            f"{result['listing_id']} {result['profile_key']} "
            f"v{result['profile_version']} amenities={result['amenity_count']} "
            f"anchors={result['anchor_time_count']}"
        )


if __name__ == "__main__":
    main()
