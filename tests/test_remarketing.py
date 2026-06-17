from __future__ import annotations

import pytest

from app.core.remarketing import generate_outreach_draft
from app.core.buyer_preferences import rank_listing_matches
from app.models.db_models import DBBuyerPreferenceProfile, DBListing


pytestmark = pytest.mark.no_db


def _listing(
    listing_id: str,
    brokerage_id: str,
    *,
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
            "project": "Marina Gate",
            "unit_number": "2304",
            "property_type": property_type,
            "bedrooms": bedrooms,
            "purchase_price_aed": price,
        },
    )


def _profile(profile_id: str, brokerage_id: str, community: str, bedrooms: int, low: int, high: int) -> DBBuyerPreferenceProfile:
    return DBBuyerPreferenceProfile(
        profile_id=profile_id,
        buyer_id=profile_id,
        brokerage_id=brokerage_id,
        stated_preferences={
            "bedrooms_min": bedrooms,
            "bedrooms_max": bedrooms,
            "price_min_aed": low,
            "price_max_aed": high,
            "property_types": ["apartment"],
            "communities": [community],
        },
        inferred_preferences={},
        inquiry_history=[
            {
                "listing_id": f"prior-{profile_id}",
                "community": community,
                "bedrooms": bedrooms,
                "property_type": "apartment",
                "price_aed": (low + high) / 2,
            }
        ],
    )


def test_reverse_matching_finds_only_relevant_buyer_profile_for_new_listing():
    new_listing = _listing("new-marina-2br", "mahoroba", community="Dubai Marina", bedrooms=2, price=2_800_000)
    marina_buyer = _profile("marina-buyer", "mahoroba", "Dubai Marina", 2, 2_500_000, 3_000_000)
    downtown_buyer = _profile("downtown-buyer", "mahoroba", "Downtown Dubai", 3, 4_000_000, 5_000_000)
    palm_buyer = _profile("palm-buyer", "mahoroba", "Palm Jumeirah", 5, 10_000_000, 20_000_000)
    other_brokerage_buyer = _profile("other-brokerage", "irwin", "Dubai Marina", 2, 2_500_000, 3_000_000)

    matches = []
    for profile in [marina_buyer, downtown_buyer, palm_buyer, other_brokerage_buyer]:
        matches.extend(rank_listing_matches(profile, [new_listing], limit=1))

    assert [match.listing_id for match in matches] == ["new-marina-2br"]


def test_fallback_outreach_draft_references_match_and_has_no_em_dash():
    listing = _listing("new-marina-2br", "mahoroba", community="Dubai Marina", bedrooms=2, price=2_800_000)
    profile = _profile("marina-buyer", "mahoroba", "Dubai Marina", 2, 2_500_000, 3_000_000)

    draft = generate_outreach_draft(
        profile=profile,
        listing=listing,
        reasons=["2 bedrooms matched", "price range matched", "Dubai Marina community matched"],
        traced_inquiry_listing_ids=["prior-marina-buyer"],
        use_claude=False,
    )

    assert "Dubai Marina" in draft
    assert "AED 2,800,000" in draft
    assert "Happy to send the details" in draft
    assert "\u2014" not in draft
    assert "--" not in draft
