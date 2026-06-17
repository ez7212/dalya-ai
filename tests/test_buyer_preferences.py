from __future__ import annotations

import pytest

from app.core.buyer_preferences import (
    infer_preferences_from_inquiries,
    rank_listing_matches,
    should_surface_alternative_listings,
)
from app.models.db_models import DBBuyerPreferenceProfile, DBListing


pytestmark = pytest.mark.no_db


def _listing(
    listing_id: str,
    brokerage_id: str,
    *,
    project: str,
    community: str,
    bedrooms: int,
    price: float,
    property_type: str = "Apartment",
) -> DBListing:
    return DBListing(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        community=community,
        seller_asking_price=price,
        spa_data={
            "project": project,
            "unit_number": listing_id[-2:],
            "property_type": property_type,
            "bedrooms": bedrooms,
            "purchase_price_aed": price,
        },
    )


def test_infers_preferences_from_repeated_marina_2br_inquiries():
    inquiries = [
        {
            "listing_id": "m-1",
            "community": "Dubai Marina",
            "bedrooms": 2,
            "property_type": "apartment",
            "price_aed": 2_500_000,
        },
        {
            "listing_id": "m-2",
            "community": "Dubai Marina",
            "bedrooms": 2,
            "property_type": "apartment",
            "price_aed": 2_800_000,
        },
        {
            "listing_id": "m-3",
            "community": "Dubai Marina",
            "bedrooms": 2,
            "property_type": "apartment",
            "price_aed": 3_000_000,
        },
    ]

    inferred = infer_preferences_from_inquiries(inquiries)

    assert inferred["bedrooms_min"] == 2
    assert inferred["bedrooms_max"] == 2
    assert inferred["price_min_aed"] == 2_500_000
    assert inferred["price_max_aed"] == 3_000_000
    assert inferred["communities"] == ["Dubai Marina"]
    assert inferred["property_types"] == ["apartment"]


def test_matching_returns_ranked_same_brokerage_inventory_only():
    profile = DBBuyerPreferenceProfile(
        profile_id="mahoroba:+9715000001",
        buyer_id="+9715000001",
        brokerage_id="mahoroba",
        stated_preferences={
            "bedrooms_min": 2,
            "bedrooms_max": 2,
            "price_min_aed": 2_500_000,
            "price_max_aed": 3_000_000,
            "property_types": ["apartment"],
            "communities": ["Dubai Marina"],
        },
        inferred_preferences={},
        inquiry_history=[
            {
                "listing_id": "old-marina",
                "community": "Dubai Marina",
                "bedrooms": 2,
                "property_type": "apartment",
                "price_aed": 2_700_000,
            }
        ],
    )
    listings = [
        _listing("current", "mahoroba", project="Marina Gate", community="Dubai Marina", bedrooms=2, price=2_700_000),
        _listing("match", "mahoroba", project="Marina Vista", community="Dubai Marina", bedrooms=2, price=2_800_000),
        _listing("wrong-brokerage", "irwin", project="Marina Quays", community="Dubai Marina", bedrooms=2, price=2_750_000),
        _listing("wrong-area", "mahoroba", project="Downtown Views", community="Downtown Dubai", bedrooms=2, price=2_800_000),
        _listing("wrong-beds", "mahoroba", project="Marina 3BR", community="Dubai Marina", bedrooms=3, price=2_900_000),
    ]

    matches = rank_listing_matches(profile, listings, current_listing_id="current", limit=3)

    assert [match.listing_id for match in matches] == ["match"]
    assert matches[0].traced_inquiry_listing_ids == ["old-marina"]
    assert any("price range" in reason for reason in matches[0].reasons)


def test_alternatives_only_surface_when_conversationally_appropriate():
    assert should_surface_alternative_listings("do you have anything else like this?")
    assert should_surface_alternative_listings("this is too expensive, any alternatives?")
    assert not should_surface_alternative_listings("what is the payment plan?")
    assert not should_surface_alternative_listings("is the NOC eligible?")
