from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import anthropic
from sqlalchemy.orm import Session

from app.db.session import safe_commit
from app.models.db_models import DBBuyerPreferenceProfile, DBListing


SONNET_MODEL = "claude-sonnet-4-6"
logger = logging.getLogger(__name__)


@dataclass
class ListingMatch:
    listing_id: str
    project: str
    unit_number: str
    property_type: str | None
    bedrooms: int | None
    community: str | None
    price_aed: float
    score: float
    reasons: list[str]
    traced_inquiry_listing_ids: list[str]

    def as_prompt_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "project": self.project,
            "unit_number": self.unit_number,
            "property_type": self.property_type,
            "bedrooms": self.bedrooms,
            "community": self.community,
            "price_aed": self.price_aed,
            "score": self.score,
            "reasons": self.reasons,
            "traced_inquiry_listing_ids": self.traced_inquiry_listing_ids,
        }


DEFAULT_STATED = {
    "bedrooms_min": None,
    "bedrooms_max": None,
    "size_sqft_min": None,
    "size_sqft_max": None,
    "price_min_aed": None,
    "price_max_aed": None,
    "property_types": [],
    "communities": [],
    "must_haves": [],
    "deal_breakers": [],
}


def get_or_create_preference_profile(
    db: Session,
    *,
    buyer_id: str,
    brokerage_id: str,
) -> DBBuyerPreferenceProfile:
    profile_id = _profile_id(brokerage_id, buyer_id)
    profile = db.get(DBBuyerPreferenceProfile, profile_id)
    if profile:
        return profile
    profile = DBBuyerPreferenceProfile(
        profile_id=profile_id,
        buyer_id=buyer_id,
        brokerage_id=brokerage_id,
        stated_preferences=dict(DEFAULT_STATED),
        inferred_preferences=dict(DEFAULT_STATED),
        inquiry_history=[],
    )
    db.add(profile)
    safe_commit(db)
    db.refresh(profile)
    return profile


def update_buyer_preference_profile(
    db: Session,
    *,
    buyer_id: str,
    brokerage_id: str | None,
    buyer_message: str,
    listing: DBListing,
    use_claude: bool | None = None,
) -> DBBuyerPreferenceProfile | None:
    if not brokerage_id:
        return None
    profile = get_or_create_preference_profile(db, buyer_id=buyer_id, brokerage_id=brokerage_id)
    listing_attrs = listing_attributes(listing)

    inquiry = {
        "listing_id": listing.listing_id,
        "project": listing_attrs["project"],
        "unit_number": listing_attrs["unit_number"],
        "price_aed": listing_attrs["price_aed"],
        "bedrooms": listing_attrs["bedrooms"],
        "property_type": listing_attrs["property_type"],
        "community": listing_attrs["community"],
        "timestamp": datetime.utcnow().isoformat(),
    }
    profile.inquiry_history = _append_inquiry(profile.inquiry_history or [], inquiry)

    stated = _merge_preferences(
        dict(DEFAULT_STATED),
        profile.stated_preferences or {},
        _extract_rule_based_preferences(buyer_message),
    )

    if use_claude is None:
        use_claude = os.getenv("BUYER_PREFERENCE_CLAUDE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if use_claude and os.getenv("ANTHROPIC_API_KEY"):
        try:
            stated = _merge_preferences(
                dict(DEFAULT_STATED),
                stated,
                _extract_claude_preferences(
                    buyer_message=buyer_message,
                    current_profile={
                        "stated_preferences": stated,
                        "inferred_preferences": profile.inferred_preferences or {},
                        "inquiry_history": profile.inquiry_history or [],
                    },
                ),
            )
        except Exception as exc:
            logger.warning(
                "buyer_preference_claude_failed: %s message=%r",
                exc,
                buyer_message[:160],
            )

    inferred = infer_preferences_from_inquiries(profile.inquiry_history or [])
    profile.stated_preferences = stated
    profile.inferred_preferences = inferred
    profile.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(profile)
    return profile


def match_buyer_profile_to_listings(
    db: Session,
    *,
    profile: DBBuyerPreferenceProfile,
    current_listing_id: str | None = None,
    limit: int = 3,
) -> list[ListingMatch]:
    rows = (
        db.query(DBListing)
        .filter(DBListing.brokerage_id == profile.brokerage_id)
        .all()
    )
    return rank_listing_matches(profile, rows, current_listing_id=current_listing_id, limit=limit)


def rank_listing_matches(
    profile: DBBuyerPreferenceProfile,
    listings: list[DBListing],
    *,
    current_listing_id: str | None = None,
    limit: int = 3,
) -> list[ListingMatch]:
    stated = profile.stated_preferences or {}
    inferred = profile.inferred_preferences or {}
    inquiries = profile.inquiry_history or []
    scored: list[ListingMatch] = []

    for listing in listings:
        if listing.listing_id == current_listing_id:
            continue
        if listing.brokerage_id != profile.brokerage_id:
            continue
        attrs = listing_attributes(listing)
        price = attrs["price_aed"]
        if not price:
            continue

        score = 0.0
        reasons: list[str] = []

        bedrooms = attrs["bedrooms"]
        bed_min, bed_max = _range_for("bedrooms", stated, inferred)
        if bed_min is not None or bed_max is not None:
            if bedrooms is None or not _in_range(bedrooms, bed_min, bed_max):
                continue
            score += 3
            reasons.append(f"{bedrooms} bedrooms matched")

        price_min, price_max = _range_for("price", stated, inferred)
        if price_min is not None or price_max is not None:
            if not _in_range(price, price_min, price_max):
                continue
            score += 3
            midpoint = _midpoint(price_min, price_max)
            if midpoint:
                score += max(0, 2 - abs(price - midpoint) / max(midpoint, 1) * 4)
            reasons.append("price range matched")

        types = _combined_list("property_types", stated, inferred)
        if types:
            if not attrs["property_type"] or attrs["property_type"].lower() not in {t.lower() for t in types}:
                continue
            score += 2
            reasons.append(f"{attrs['property_type']} type matched")

        communities = _combined_list("communities", stated, inferred)
        if communities:
            haystack = " ".join([str(attrs["community"] or ""), str(attrs["project"] or "")]).lower()
            if not any(str(community).lower() in haystack for community in communities):
                continue
            score += 2
            reasons.append(f"{attrs['community'] or attrs['project']} community matched")

        traced = [
            item.get("listing_id")
            for item in inquiries
            if item.get("listing_id")
            and _inquiry_related_to_attrs(item, attrs)
        ]

        if score > 0:
            scored.append(
                ListingMatch(
                    listing_id=listing.listing_id,
                    project=attrs["project"] or "Unknown",
                    unit_number=attrs["unit_number"] or "?",
                    property_type=attrs["property_type"],
                    bedrooms=bedrooms,
                    community=attrs["community"],
                    price_aed=float(price),
                    score=round(score, 3),
                    reasons=reasons,
                    traced_inquiry_listing_ids=list(dict.fromkeys(traced)),
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def should_surface_alternative_listings(message: str) -> bool:
    text = message.lower()
    explicit = [
        "anything else",
        "something else",
        "other properties",
        "other listings",
        "else like this",
        "similar",
        "comparable",
        "comparable units",
        "comps",
        "same building",
        "same project",
        "alternatives",
        "compare",
    ]
    mismatch = [
        "too expensive",
        "too small",
        "too big",
        "different area",
        "different community",
        "not this one",
    ]
    return any(phrase in text for phrase in explicit + mismatch)


def infer_preferences_from_inquiries(inquiries: list[dict]) -> dict:
    inferred = dict(DEFAULT_STATED)
    prices = [float(i["price_aed"]) for i in inquiries if i.get("price_aed")]
    bedrooms = [int(i["bedrooms"]) for i in inquiries if i.get("bedrooms") is not None]
    communities = _mode_values([i.get("community") for i in inquiries])
    property_types = _mode_values([i.get("property_type") for i in inquiries])

    if prices:
        inferred["price_min_aed"] = min(prices)
        inferred["price_max_aed"] = max(prices)
    if bedrooms:
        inferred["bedrooms_min"] = min(bedrooms)
        inferred["bedrooms_max"] = max(bedrooms)
    inferred["communities"] = communities
    inferred["property_types"] = property_types
    return inferred


def listing_attributes(listing: DBListing) -> dict:
    spa = listing.spa_data or {}
    community = listing.community or spa.get("sub_community") or spa.get("community") or _infer_community(spa)
    return {
        "listing_id": listing.listing_id,
        "project": spa.get("project") or "",
        "unit_number": spa.get("unit_number") or "?",
        "property_type": _normalize_property_type(spa.get("property_type") or listing.property_type),
        "bedrooms": _coerce_int(spa.get("bedrooms")),
        "bua_sqft": spa.get("bua_sqft"),
        "community": community,
        "price_aed": float(listing.seller_asking_price or spa.get("purchase_price_aed") or 0),
    }


def _extract_rule_based_preferences(message: str) -> dict:
    prefs = dict(DEFAULT_STATED)
    text = message.lower()

    bed_match = re.search(r"\b([1-7])\s*(?:br|bed|bedroom|bedrooms)\b", text)
    if bed_match:
        bedrooms = int(bed_match.group(1))
        prefs["bedrooms_min"] = bedrooms
        prefs["bedrooms_max"] = bedrooms

    range_match = re.search(r"\b(?:under|below|max|maximum)\s*(?:aed\s*)?(\d+(?:\.\d+)?)\s*(m|million)?\b", text)
    if range_match:
        prefs["price_max_aed"] = int(float(range_match.group(1)) * (1_000_000 if range_match.group(2) else 1))

    between_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:m|million)?\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(m|million)\b", text)
    if between_match:
        prefs["price_min_aed"] = int(float(between_match.group(1)) * 1_000_000)
        prefs["price_max_aed"] = int(float(between_match.group(2)) * 1_000_000)

    for property_type in ["apartment", "villa", "townhouse", "penthouse"]:
        if property_type in text:
            prefs["property_types"] = [property_type]
            break

    known_communities = [
        "marina",
        "dubai marina",
        "jbr",
        "downtown",
        "palm",
        "palm jumeirah",
        "dubai harbour",
        "dubailand",
        "the oasis",
        "jvc",
    ]
    prefs["communities"] = [community for community in known_communities if community in text]
    return prefs


def _extract_claude_preferences(*, buyer_message: str, current_profile: dict) -> dict:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=1200,
        system="""Extract conservative Dubai real estate buyer preferences.

Return strict JSON with keys:
bedrooms_min, bedrooms_max, size_sqft_min, size_sqft_max, price_min_aed,
price_max_aed, property_types, communities, must_haves, deal_breakers.

Rules:
- Only update when the buyer explicitly states or strongly implies something new.
- Do not overwrite stronger stated preferences with weaker inference.
- Normalize property types to apartment, villa, townhouse, or penthouse.
- Normalize prices to AED integers.
- JSON only.""",
        messages=[
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "buyer_message": buyer_message,
                        "current_profile": current_profile,
                    },
                    ensure_ascii=True,
                ),
            }
        ],
    )
    return _loads_json(response.content[0].text)


def _merge_preferences(*parts: dict) -> dict:
    merged = dict(DEFAULT_STATED)
    for part in parts:
        for key, value in (part or {}).items():
            if value in (None, "", []):
                continue
            if isinstance(value, list):
                merged[key] = list(dict.fromkeys([*(merged.get(key) or []), *value]))
            else:
                merged[key] = value
    return merged


def _append_inquiry(history: list[dict], inquiry: dict) -> list[dict]:
    deduped = [item for item in history if item.get("listing_id") != inquiry["listing_id"]]
    deduped.append(inquiry)
    return deduped


def _profile_id(brokerage_id: str, buyer_id: str) -> str:
    safe_phone = re.sub(r"[^0-9A-Za-z]+", "_", buyer_id).strip("_")
    return f"{brokerage_id}:{safe_phone}"


def _range_for(prefix: str, stated: dict, inferred: dict) -> tuple[float | None, float | None]:
    if prefix == "price":
        return (
            stated.get("price_min_aed") or inferred.get("price_min_aed"),
            stated.get("price_max_aed") or inferred.get("price_max_aed"),
        )
    return (
        stated.get(f"{prefix}_min") or inferred.get(f"{prefix}_min"),
        stated.get(f"{prefix}_max") or inferred.get(f"{prefix}_max"),
    )


def _combined_list(key: str, stated: dict, inferred: dict) -> list[str]:
    return list(dict.fromkeys([*(stated.get(key) or []), *(inferred.get(key) or [])]))


def _in_range(value: float, low: float | None, high: float | None) -> bool:
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def _midpoint(low: float | None, high: float | None) -> float | None:
    if low is None or high is None:
        return None
    return (float(low) + float(high)) / 2


def _mode_values(values: list[Optional[str]], min_count: int = 2) -> list[str]:
    counts: dict[str, int] = {}
    originals: dict[str, str] = {}
    for value in values:
        if not value:
            continue
        key = str(value).lower()
        counts[key] = counts.get(key, 0) + 1
        originals[key] = str(value)
    return [originals[key] for key, count in counts.items() if count >= min_count]


def _inquiry_related_to_attrs(inquiry: dict, attrs: dict) -> bool:
    return (
        (inquiry.get("community") and attrs.get("community") and str(inquiry["community"]).lower() == str(attrs["community"]).lower())
        or (inquiry.get("bedrooms") is not None and inquiry.get("bedrooms") == attrs.get("bedrooms"))
        or (inquiry.get("property_type") and attrs.get("property_type") and str(inquiry["property_type"]).lower() == str(attrs["property_type"]).lower())
    )


def _infer_community(spa: dict) -> str | None:
    text = " ".join(str(spa.get(k) or "") for k in ("project", "sub_community", "developer")).lower()
    if "marina" in text:
        return "Dubai Marina"
    if "jbr" in text:
        return "JBR"
    if "downtown" in text:
        return "Downtown Dubai"
    if "palm" in text:
        return "Palm Jumeirah"
    if "seahaven" in text or "dubai harbour" in text:
        return "Dubai Harbour"
    if "oasis" in text or "ostra" in text:
        return "The Oasis"
    return spa.get("sub_community")


def _normalize_property_type(value: str | None) -> str | None:
    if not value:
        return None
    text = value.lower()
    for kind in ("apartment", "villa", "townhouse", "penthouse"):
        if kind in text:
            return kind
    return text


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _loads_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data
