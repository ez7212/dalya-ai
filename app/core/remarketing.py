from __future__ import annotations

import json
import os
import re
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

from app.core.buyer_preferences import listing_attributes, rank_listing_matches
from app.db.session import safe_commit
from app.models.db_models import DBBuyerListingMatch, DBBuyerPreferenceProfile, DBListing


SONNET_MODEL = "claude-sonnet-4-6"


def generate_buyer_matches_for_listing(
    db: Session,
    *,
    listing: DBListing,
    limit: int = 5,
    use_claude: bool | None = None,
) -> list[DBBuyerListingMatch]:
    if not listing.brokerage_id:
        return []

    profiles = (
        db.query(DBBuyerPreferenceProfile)
        .filter(DBBuyerPreferenceProfile.brokerage_id == listing.brokerage_id)
        .all()
    )
    candidates: list[tuple[DBBuyerPreferenceProfile, object]] = []
    for profile in profiles:
        matches = rank_listing_matches(profile, [listing], limit=1)
        if matches:
            candidates.append((profile, matches[0]))

    candidates.sort(key=lambda item: item[1].score, reverse=True)
    selected = candidates[:limit]
    created: list[DBBuyerListingMatch] = []

    for profile, match in selected:
        draft = generate_outreach_draft(
            profile=profile,
            listing=listing,
            reasons=match.reasons,
            traced_inquiry_listing_ids=match.traced_inquiry_listing_ids,
            use_claude=use_claude,
        )
        existing = (
            db.query(DBBuyerListingMatch)
            .filter(
                DBBuyerListingMatch.listing_id == listing.listing_id,
                DBBuyerListingMatch.buyer_profile_id == profile.profile_id,
            )
            .first()
        )
        if existing:
            existing.match_score = match.score
            existing.aligned_preferences = match.reasons
            existing.traced_inquiry_listing_ids = match.traced_inquiry_listing_ids
            existing.outreach_draft = draft
            existing.updated_at = datetime.utcnow()
            row = existing
        else:
            row = DBBuyerListingMatch(
                brokerage_id=listing.brokerage_id,
                listing_id=listing.listing_id,
                buyer_profile_id=profile.profile_id,
                buyer_id=profile.buyer_id,
                match_score=match.score,
                aligned_preferences=match.reasons,
                traced_inquiry_listing_ids=match.traced_inquiry_listing_ids,
                outreach_draft=draft,
                metadata_json={
                    "source": "new_listing_remarketing",
                    "future_outbound": "Route through approved Brokerage AI re-engagement templates in v2.",
                },
            )
            db.add(row)
        created.append(row)

    safe_commit(db)
    for row in created:
        db.refresh(row)
    return created


def list_buyer_matches_for_listing(
    db: Session,
    *,
    listing_id: str,
    brokerage_id: str,
    limit: int = 5,
) -> list[DBBuyerListingMatch]:
    return (
        db.query(DBBuyerListingMatch)
        .filter(
            DBBuyerListingMatch.listing_id == listing_id,
            DBBuyerListingMatch.brokerage_id == brokerage_id,
        )
        .order_by(DBBuyerListingMatch.match_score.desc())
        .limit(limit)
        .all()
    )


def generate_outreach_draft(
    *,
    profile: DBBuyerPreferenceProfile,
    listing: DBListing,
    reasons: list[str],
    traced_inquiry_listing_ids: list[str],
    use_claude: bool | None = None,
) -> str:
    if use_claude is None:
        use_claude = os.getenv("REMARKETING_CLAUDE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if use_claude and os.getenv("ANTHROPIC_API_KEY"):
        try:
            return _generate_claude_draft(profile, listing, reasons, traced_inquiry_listing_ids)
        except Exception:
            pass
    return _fallback_draft(profile, listing, reasons, traced_inquiry_listing_ids)


def serialize_buyer_match(row: DBBuyerListingMatch) -> dict:
    return {
        "match_id": row.match_id,
        "buyer_id": row.buyer_id,
        "buyer_profile_id": row.buyer_profile_id,
        "match_score": row.match_score,
        "aligned_preferences": row.aligned_preferences or [],
        "traced_inquiry_listing_ids": row.traced_inquiry_listing_ids or [],
        "outreach_draft": row.outreach_draft,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _generate_claude_draft(
    profile: DBBuyerPreferenceProfile,
    listing: DBListing,
    reasons: list[str],
    traced_inquiry_listing_ids: list[str],
) -> str:
    attrs = listing_attributes(listing)
    response = anthropic.Anthropic().messages.create(
        model=SONNET_MODEL,
        max_tokens=450,
        system="""Draft a WhatsApp outreach message from a Dubai real estate agent to a buyer.

Rules:
- Human, helpful, concise.
- No em dashes.
- No AI tells.
- Mention the listing and one specific reason it fits.
- Soft CTA only, such as offering details or a viewing.
- Do not claim the buyer asked for this exact listing unless the context proves it.
- Return only the message text.""",
        messages=[
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "buyer_id": profile.buyer_id,
                        "stated_preferences": profile.stated_preferences,
                        "inferred_preferences": profile.inferred_preferences,
                        "inquiry_history": profile.inquiry_history,
                        "new_listing": attrs,
                        "match_reasons": reasons,
                        "traced_inquiry_listing_ids": traced_inquiry_listing_ids,
                    },
                    ensure_ascii=True,
                ),
            }
        ],
    )
    return _sanitize_draft(response.content[0].text)


def _fallback_draft(
    profile: DBBuyerPreferenceProfile,
    listing: DBListing,
    reasons: list[str],
    traced_inquiry_listing_ids: list[str],
) -> str:
    attrs = listing_attributes(listing)
    bedrooms = f"{attrs['bedrooms']}BR " if attrs.get("bedrooms") else ""
    community = attrs.get("community") or attrs.get("project")
    price = f"AED {attrs['price_aed']:,.0f}" if attrs.get("price_aed") else "the current price"
    reason = _human_reason(reasons)
    trace = ""
    if traced_inquiry_listing_ids:
        trace = " It lines up with the kind of property you were looking at before."
    return _sanitize_draft(
        f"Hi, we just listed a {bedrooms}{attrs.get('property_type') or 'property'} in {community} at {price}. "
        f"{reason}.{trace} Happy to send the details or arrange a viewing if it looks relevant."
    )


def _human_reason(reasons: list[str]) -> str:
    joined = " ".join(reasons).lower()
    parts = []
    if "bedroom" in joined:
        parts.append("bedroom count")
    if "price" in joined:
        parts.append("budget range")
    if "type" in joined:
        parts.append("property type")
    if "community" in joined:
        parts.append("preferred area")
    if not parts:
        return "It looks close to your previous search"
    return "It matches your " + ", ".join(parts)


def _sanitize_draft(text: str) -> str:
    cleaned = re.sub(r"[\u2013\u2014]", ",", text).strip()
    return cleaned.replace("AI", "Dalya")
