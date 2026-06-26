"""
Seller API Router — authenticated endpoints for listing owners.

All endpoints require a valid Supabase JWT. Sellers can only access
their own listings (verified via listing.seller_id == user.id).

CRITICAL: Never expose buyer phone numbers, names, or PII in any response.
Use anonymized labels like "Buyer 1", "Buyer 2" ordered by first contact.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.seller_activity import build_seller_activity_payload
from app.api.seller_conversations import (
    build_listing_conversations_payload,
    build_listing_offers_payload,
)
from app.core.auth import CurrentUser, get_current_user
from app.core.chatbot_engine import engine
from app.db import crud
from app.db.session import get_db, safe_commit
from app.models.db_models import DBListing

router = APIRouter()


class ListingUpdate(BaseModel):
    seller_asking_price: Optional[float] = None
    negotiation_threshold_aed: Optional[float] = None
    seller_notes: Optional[str] = None


@router.get("/seller/listings")
async def get_my_listings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all listings owned by the authenticated seller."""
    from app.core.listing_stages import STAGE_ORDER

    listings = crud.get_listings_for_seller(db, user.id)
    results = []
    total_conversations = 0
    total_escalated = 0
    for listing in listings:
        spa = listing.spa_data or {}
        stats = crud.get_listing_stats_fast(db, listing.listing_id)
        convs = stats.get("total_conversations", 0)
        esc = stats.get("escalated_leads", 0)
        total_conversations += convs
        total_escalated += esc

        # Compute derived status from processing stages
        stages = listing.processing_stages or {}
        ai_live_status = (stages.get("ai_advisor_live") or {}).get("status", "pending")
        if ai_live_status == "complete":
            derived_status = "active"
        else:
            # Find first stage that's in_progress or blocked
            derived_status = "pending_review"
            for stage_key in STAGE_ORDER:
                stage = stages.get(stage_key) or {}
                if stage.get("status") == "blocked":
                    derived_status = "blocked"
                    break

        results.append({
            "id": listing.listing_id,
            "property_name": spa.get("project", "Unknown"),
            "unit_number": spa.get("unit_number", "—"),
            "asking_price": listing.seller_asking_price,
            "status": derived_status,
            "lead_count": convs,
            "escalated_count": esc,
            "last_activity": None,
        })
    return {
        "listings": results,
        "total_conversations": total_conversations,
        "total_escalated": total_escalated,
    }


@router.patch("/seller/listings/{listing_id}")
async def update_my_listing(
    listing_id: str,
    body: ListingUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update seller-configurable fields on a listing the user owns."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    if body.seller_asking_price is not None:
        listing.seller_asking_price = body.seller_asking_price
    if body.negotiation_threshold_aed is not None:
        listing.negotiation_threshold_aed = body.negotiation_threshold_aed
    if body.seller_notes is not None:
        listing.seller_notes = body.seller_notes
    safe_commit(db)

    return {"success": True, "listing_id": listing_id}


@router.get("/seller/listings/{listing_id}/leads")
async def get_my_listing_leads(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return full listing details + conversation stats for a listing the user owns."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    spa = listing.spa_data or {}
    stats = crud.get_listing_stats_fast(db, listing_id)

    from app.core.listing_stages import serialize_stages
    from app.core.agent_community_overrides import find_research

    project_name = spa.get("project")
    research = find_research(db, project_name) if project_name else None
    community_research_status = research.status if research else None

    return {
        "id": listing.listing_id,
        "property_name": spa.get("project", "Unknown"),
        "developer": spa.get("developer", "Unknown"),
        "unit_number": spa.get("unit_number", "—"),
        "sub_community": spa.get("sub_community"),
        "property_type": spa.get("property_type"),
        "property_status": spa.get("property_status"),
        "bedrooms": spa.get("bedrooms"),
        "bathrooms": spa.get("bathrooms"),
        "bua_sqft": spa.get("bua_sqft"),
        "plot_sqft": spa.get("plot_sqft"),
        "total_price": spa.get("purchase_price_aed"),
        "asking_price": listing.seller_asking_price,
        "negotiation_threshold": listing.negotiation_threshold_aed,
        "seller_notes": listing.seller_notes,
        "unit_profile": listing.unit_profile or {},
        "unit_profile_history": listing.unit_profile_history or [],
        "noc_eligible": spa.get("noc_eligible"),
        "total_paid_percent": spa.get("total_paid_percent"),
        "handover_date": spa.get("estimated_completion_date"),
        "payment_schedule": spa.get("payment_schedule", []),
        "status": "active",
        "lead_count": stats.get("total_conversations", 0),
        "escalated_count": stats.get("escalated_leads", 0),
        "leads": stats.get("active_buyers", []),
        "processing_stages": serialize_stages(
            listing.processing_stages, community_research_status=community_research_status
        ),
    }


# ── Conversation summaries (anonymized) ──────────────────────────────────────

@router.get("/seller/listings/{listing_id}/conversations")
async def get_listing_conversations(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return anonymized conversation summaries for a listing. No buyer PII."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    return build_listing_conversations_payload(db, listing_id)


# ── Offers endpoint (anonymized) ─────────────────────────────────────────────

@router.get("/seller/listings/{listing_id}/offers")
async def get_listing_offers(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all offers received on a listing. No buyer PII."""
    listing = crud.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")

    return build_listing_offers_payload(db, listing_id, listing)


# ── Activity feed (anonymized, cross-listing) ────────────────────────────────

@router.get("/seller/activity")
async def get_seller_activity(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reverse-chronological activity feed across all seller listings. No buyer PII."""
    return build_seller_activity_payload(db, user.id)
