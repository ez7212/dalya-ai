from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_access import (
    BrokerageContext,
    capture_requested_brokerage_context,
    current_requested_brokerage_id,
    is_managing_agent,
    resolve_request_brokerage_context,
)
from app.db import crud
from app.db.session import get_db
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerageMember,
    DBConversation,
    DBListing,
    DBListingKnowledgeSummary,
    DBListingLogistics,
    DBOfferRecord,
    DBViewing,
)

router = APIRouter(dependencies=[Depends(capture_requested_brokerage_context)])


def _ensure_member_brokerage(user: CurrentUser, db: Session) -> BrokerageContext:
    return resolve_request_brokerage_context(
        db,
        user,
        current_requested_brokerage_id(),
    )


def _text_from_json(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _number_from_json(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _first_image_url(media_urls: Any) -> Optional[str]:
    if not isinstance(media_urls, list):
        return None
    for item in media_urls:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def _assigned_agent_name(db: Session, listing: DBListing) -> Optional[str]:
    if not listing.assigned_agent_id or not listing.brokerage_id:
        return None
    profile = (
        db.query(DBAgentProfile.display_name)
        .filter(
            DBAgentProfile.brokerage_id == listing.brokerage_id,
            DBAgentProfile.user_id == listing.assigned_agent_id,
        )
        .scalar()
    )
    if profile:
        return profile
    return (
        db.query(DBBrokerageMember.display_name)
        .filter(
            DBBrokerageMember.brokerage_id == listing.brokerage_id,
            DBBrokerageMember.user_id == listing.assigned_agent_id,
        )
        .scalar()
    )


def _listing_knowledge(db: Session, listing: DBListing) -> tuple[str, int, Optional[datetime]]:
    summary = (
        db.query(DBListingKnowledgeSummary)
        .filter(
            DBListingKnowledgeSummary.brokerage_id == listing.brokerage_id,
            DBListingKnowledgeSummary.listing_id == listing.listing_id,
        )
        .first()
    )
    # missing_fact_count is the number of gaps the AI summary actually flagged —
    # 0 until a summary exists. (It previously faked a "1" whenever a listing had
    # no buyer-safe facts, so every new listing read "1 missing facts" even though
    # no specific fact was missing.) The "needs_attention" status below still
    # signals a listing whose knowledge hasn't been built yet.
    missing_fact_count = 0
    if summary and isinstance(summary.missing_information, list):
        missing_fact_count = len(summary.missing_information)
    if missing_fact_count > 0 or summary is None or summary.status in ("needs_review", "needs_attention", "blocked", "stale"):
        return "needs_attention", missing_fact_count, summary.updated_at if summary else None
    return summary.status or "ready", missing_fact_count, summary.updated_at


def _listing_logistics(db: Session, listing: DBListing) -> tuple[str, Optional[datetime]]:
    if listing.property_type == "off_plan":
        return "not_required", None
    logistics = (
        db.query(DBListingLogistics)
        .filter(
            DBListingLogistics.brokerage_id == listing.brokerage_id,
            DBListingLogistics.listing_id == listing.listing_id,
        )
        .first()
    )
    if logistics is None:
        return "needs_attention", None
    if logistics.confirmed_at:
        return "ready", logistics.updated_at
    return "needs_attention", logistics.updated_at


def _listing_activity(db: Session, listing: DBListing) -> tuple[int, int, Optional[datetime], Optional[datetime]]:
    active_viewing_count = int(
        db.query(func.count(DBViewing.viewing_id))
        .filter(
            DBViewing.brokerage_id == listing.brokerage_id,
            DBViewing.listing_id == listing.listing_id,
            DBViewing.status.in_(("proposed", "confirmed")),
        )
        .scalar()
        or 0
    )
    open_offer_count = int(
        db.query(func.count(DBOfferRecord.offer_id))
        .filter(
            DBOfferRecord.brokerage_id == listing.brokerage_id,
            DBOfferRecord.listing_id == listing.listing_id,
            DBOfferRecord.superseded_by.is_(None),
        )
        .scalar()
        or 0
    )
    latest_offer = (
        db.query(func.max(DBOfferRecord.created_at))
        .filter(
            DBOfferRecord.brokerage_id == listing.brokerage_id,
            DBOfferRecord.listing_id == listing.listing_id,
        )
        .scalar()
    )
    latest_viewing = (
        db.query(func.max(DBViewing.updated_at))
        .filter(
            DBViewing.brokerage_id == listing.brokerage_id,
            DBViewing.listing_id == listing.listing_id,
        )
        .scalar()
    )
    return active_viewing_count, open_offer_count, latest_offer, latest_viewing


def _last_activity_at(*timestamps: Optional[datetime]) -> Optional[str]:
    values = [item for item in timestamps if item is not None]
    if not values:
        return None
    return max(values).isoformat()


def _listing_inventory_item(db: Session, listing: DBListing) -> dict[str, Any]:
    spa = listing.spa_data if isinstance(listing.spa_data, dict) else {}
    imported_raw = spa.get("imported_listing")
    imported = imported_raw if isinstance(imported_raw, dict) else {}
    stats = crud.get_listing_stats_fast(db, listing.listing_id)
    buyer_conversation_count = stats.get("total_conversations", 0)
    knowledge_status, missing_fact_count, knowledge_updated_at = _listing_knowledge(db, listing)
    logistics_status, logistics_updated_at = _listing_logistics(db, listing)
    active_viewing_count, open_offer_count, latest_offer_at, latest_viewing_at = _listing_activity(db, listing)
    latest_conversation_at = (
        db.query(func.max(DBConversation.updated_at))
        .filter(
            DBConversation.brokerage_id == listing.brokerage_id,
            DBConversation.listing_id == listing.listing_id,
        )
        .scalar()
    )

    size_sqft = _number_from_json(spa.get("bua_sqft")) or _number_from_json(imported.get("size_sqft"))
    price_per_sqft = _number_from_json(imported.get("price_per_sqft_aed"))
    if price_per_sqft is None and listing.seller_asking_price and size_sqft and size_sqft > 0:
        price_per_sqft = round(listing.seller_asking_price / size_sqft)

    title = (
        _text_from_json(imported.get("title"))
        or _text_from_json(spa.get("project"))
        or _text_from_json(spa.get("property_type"))
        or "Untitled listing"
    )
    community = _text_from_json(imported.get("community")) or listing.community
    if knowledge_status == "needs_attention":
        primary_next_action = "review_knowledge"
    elif logistics_status == "needs_attention":
        primary_next_action = "set_logistics"
    elif open_offer_count > 0:
        primary_next_action = "review_offers"
    elif active_viewing_count > 0:
        primary_next_action = "manage_viewings"
    elif buyer_conversation_count > 0:
        primary_next_action = "follow_up_buyers"
    else:
        primary_next_action = "open_listing"

    return {
        "id": listing.listing_id,
        "title": title,
        "property_type": listing.property_type,
        "community": community,
        "subcommunity": _text_from_json(imported.get("subcommunity")) or _text_from_json(spa.get("sub_community")),
        "building_or_project": _text_from_json(spa.get("project")),
        "unit_number": _text_from_json(spa.get("unit_number")),
        "bedrooms": spa.get("bedrooms"),
        "bathrooms": spa.get("bathrooms"),
        "size_sqft": size_sqft,
        "asking_price_aed": listing.seller_asking_price,
        "price_per_sqft_aed": price_per_sqft,
        "status": "live" if listing.seller_asking_price else "draft",
        "lead_count": buyer_conversation_count,
        "escalated_count": stats.get("escalated_leads", 0),
        "source_url": listing.source_url,
        "first_image_url": _first_image_url(listing.media_urls),
        "reference_document_count": len(listing.reference_documents or []),
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "last_activity_at": _last_activity_at(
            latest_conversation_at,
            latest_offer_at,
            latest_viewing_at,
            knowledge_updated_at,
            logistics_updated_at,
            listing.created_at,
        ),
        "assigned_agent_name": _assigned_agent_name(db, listing),
        "knowledge_status": knowledge_status,
        "missing_fact_count": missing_fact_count,
        "active_viewing_count": active_viewing_count,
        "open_offer_count": open_offer_count,
        "buyer_conversation_count": buyer_conversation_count,
        "logistics_status": logistics_status,
        "primary_next_action": primary_next_action,
    }


@router.get("/listings/mine")
async def my_listings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _ensure_member_brokerage(user, db)
    query = db.query(DBListing).filter(DBListing.brokerage_id == member.brokerage_id)
    if not is_managing_agent(member.role):
        query = query.filter(or_(DBListing.seller_id == user.id, DBListing.assigned_agent_id == user.id))

    listings = query.order_by(DBListing.created_at.desc()).all()
    items = [_listing_inventory_item(db, listing) for listing in listings]
    return {
        "listings": items,
        "total_listings": len(items),
        "total_conversations": sum(item["lead_count"] for item in items),
        "total_escalated": sum(item["escalated_count"] for item in items),
    }
