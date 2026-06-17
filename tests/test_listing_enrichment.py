from types import SimpleNamespace

import pytest

from app.core.listing_enrichment import (
    GOOGLE_PLACES_FIELD_MASK,
    PROFILE_FIXTURES,
    normalize_school_name,
    profile_for_listing,
)
from app.core.prompt_builder import build_system_prompt
from app.schemas.spa import SPAParseResult


pytestmark = pytest.mark.no_db


def test_fixture_profiles_cover_all_ten_harness_urls():
    assert len(PROFILE_FIXTURES) == 10

    for profile in PROFILE_FIXTURES.values():
        assert profile.amenities
        assert profile.anchor_times
        assert all(
            "enterprise" not in str(fact.metadata_json.get("sku", "")).lower()
            or "non_enterprise" in str(fact.metadata_json.get("sku", "")).lower()
            for fact in profile.amenities
        )
        for fact in profile.amenities:
            if fact.source == "google_places":
                assert set(GOOGLE_PLACES_FIELD_MASK) == {
                    "places.id",
                    "places.displayName",
                    "places.location",
                    "places.primaryType",
                }
                assert fact.google_place_id
                assert fact.primary_type


def test_offplan_profiles_include_planned_and_existing_provenance():
    oasis = PROFILE_FIXTURES["14395274"]

    assert any(fact.source == "developer_brochure" and fact.status == "planned" for fact in oasis.amenities)
    assert any(fact.source == "google_places" and fact.status == "existing" for fact in oasis.amenities)


def test_khda_rating_requires_named_school_match_metadata():
    rated = [
        fact
        for profile in PROFILE_FIXTURES.values()
        for fact in profile.amenities
        if fact.khda_rating
    ]

    assert rated
    assert all(fact.category == "school" for fact in rated)
    assert all((fact.match_confidence or 0) >= 0.85 for fact in rated)
    assert normalize_school_name("Dubai British School Jumeirah Park") == "british jumeirah park"


def test_profile_for_listing_matches_by_source_url_or_portal_id():
    listing = SimpleNamespace(
        source_url="https://www.propertyfinder.ae/en/plp/buy/villa-for-sale-dubai-town-square-shams-townhouses-92275744.html",
        spa_data={"imported_listing": {"portal_listing_id": "92275744"}},
    )

    profile = profile_for_listing(listing)

    assert profile is not None
    assert profile.profile_key == "shams_town_square"


def test_prompt_builder_renders_neighborhood_enrichment_with_provenance():
    spa = SPAParseResult.model_validate({
        "project": "Address Harbour Point",
        "unit_number": "3105",
        "developer": "Emaar",
        "property_type": "Apartment",
        "purchase_price_aed": 4_300_000,
        "property_status": "Ready",
        "payment_schedule": [],
        "purchasers": [],
    })
    prompt = build_system_prompt(
        spa,
        seller_asking_price=4_300_000,
        property_type="ready",
        listing_amenities=[
            {
                "category": "school",
                "name": "Swiss International Scientific School in Dubai",
                "source": "google_places",
                "status": "existing",
                "drive_time_min": 13,
                "khda_rating": "Good",
                "khda_rating_year": 2024,
                "curriculum": "IB",
                "match_confidence": 0.92,
            },
            {
                "category": "planned",
                "name": "Future retail promenade",
                "source": "developer_brochure",
                "status": "planned",
            },
        ],
        listing_anchor_times=[
            {"anchor_key": "downtown_dubai", "anchor_name": "Downtown Dubai", "drive_time_min": 14, "distance_km": 10}
        ],
    )

    assert "NEIGHBORHOOD ENRICHMENT (PRECOMPUTED)" in prompt
    assert "source=google_places" in prompt
    assert "status=planned" in prompt
    assert "KHDA Good" in prompt
    assert "Downtown Dubai: 14 min drive" in prompt
