"""
CRM API Router — admin-only endpoints for buyer lead management.

All endpoints require admin authentication via Depends(require_admin).
Phone numbers in URL paths arrive URL-encoded (+971 → %2B971) and are decoded here.
"""

from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case, and_
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_admin
from app.db.session import get_db, safe_commit, set_service_db_session_context
from app.models.db_models import (
    DBBuyerProfile,
    DBConversation,
    DBMessage,
    DBListingInquiry,
    DBListing,
)

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class BuyerUpdate(BaseModel):
    lead_stage: Optional[str] = None
    tags: Optional[list] = None
    lead_source: Optional[str] = None


class NoteCreate(BaseModel):
    note: str


# ── Helpers ───────────────────────────────────────────────────────────────────

STAGE_ORDER = ["new", "engaged", "qualified", "offer", "negotiation", "closed_won", "closed_lost"]


def _decode_phone(phone: str) -> str:
    return unquote(phone)


def _set_admin_db_context(db: Session) -> None:
    set_service_db_session_context(db, is_platform_admin=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/admin/buyers")
async def list_buyers(
    stage: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("last_active", pattern="^(last_active|created_at|name)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all buyers with aggregated stats, paginated and filterable."""
    _set_admin_db_context(db)

    # Subquery: count of distinct listings inquired per buyer
    inquiries_sq = (
        select(
            DBListingInquiry.buyer_phone,
            func.count(DBListingInquiry.id).label("listings_inquired"),
        )
        .group_by(DBListingInquiry.buyer_phone)
        .subquery()
    )

    # Subquery: total messages + last_active per buyer
    messages_sq = (
        select(
            DBConversation.buyer_phone,
            func.count(DBMessage.id).label("total_messages"),
            func.max(DBMessage.timestamp).label("last_active"),
        )
        .join(DBMessage, DBMessage.conversation_id == DBConversation.conversation_id)
        .group_by(DBConversation.buyer_phone)
        .subquery()
    )

    # Main query
    query = (
        select(
            DBBuyerProfile.phone,
            DBBuyerProfile.name,
            DBBuyerProfile.lead_stage,
            DBBuyerProfile.lead_source,
            DBBuyerProfile.budget_aed,
            DBBuyerProfile.bedroom_preferences,
            DBBuyerProfile.area_preferences,
            DBBuyerProfile.purpose,
            DBBuyerProfile.tags,
            DBBuyerProfile.created_at,
            func.coalesce(inquiries_sq.c.listings_inquired, 0).label("listings_inquired"),
            func.coalesce(messages_sq.c.total_messages, 0).label("total_messages"),
            messages_sq.c.last_active,
        )
        .outerjoin(inquiries_sq, inquiries_sq.c.buyer_phone == DBBuyerProfile.phone)
        .outerjoin(messages_sq, messages_sq.c.buyer_phone == DBBuyerProfile.phone)
    )

    # Filters
    if stage:
        query = query.where(DBBuyerProfile.lead_stage == stage)
    if tag:
        # JSONB contains — works for PostgreSQL
        query = query.where(DBBuyerProfile.tags.op("@>")(f'["{tag}"]'))
    if search:
        like_pattern = f"%{search}%"
        query = query.where(
            DBBuyerProfile.name.ilike(like_pattern)
            | DBBuyerProfile.phone.ilike(like_pattern)
        )

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar()

    # Sort
    if sort == "last_active":
        query = query.order_by(messages_sq.c.last_active.desc().nullslast())
    elif sort == "created_at":
        query = query.order_by(DBBuyerProfile.created_at.desc())
    elif sort == "name":
        query = query.order_by(DBBuyerProfile.name.asc().nullslast())

    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    rows = db.execute(query).all()

    buyers = []
    for r in rows:
        buyers.append({
            "phone": r.phone,
            "name": r.name,
            "lead_stage": r.lead_stage,
            "lead_source": r.lead_source,
            "budget_aed": r.budget_aed,
            "bedroom_preferences": r.bedroom_preferences,
            "area_preferences": r.area_preferences,
            "purpose": r.purpose,
            "tags": r.tags,
            "listings_inquired": r.listings_inquired,
            "total_messages": r.total_messages,
            "last_active": r.last_active.isoformat() if r.last_active else None,
        })

    return {
        "buyers": buyers,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/admin/buyers/stats")
async def buyer_stats(
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Summary counts by lead stage."""
    _set_admin_db_context(db)
    one_week_ago = datetime.utcnow() - timedelta(days=7)

    rows = db.execute(
        select(
            func.count().label("total_buyers"),
            func.count().filter(DBBuyerProfile.created_at >= one_week_ago).label("new_this_week"),
            func.count().filter(DBBuyerProfile.lead_stage == "engaged").label("engaged"),
            func.count().filter(DBBuyerProfile.lead_stage == "qualified").label("qualified"),
            func.count().filter(DBBuyerProfile.lead_stage == "offer").label("offers_made"),
            func.count().filter(DBBuyerProfile.lead_stage == "negotiation").label("in_negotiation"),
        )
        .select_from(DBBuyerProfile)
    ).one()

    return {
        "total_buyers": rows.total_buyers,
        "new_this_week": rows.new_this_week,
        "engaged": rows.engaged,
        "qualified": rows.qualified,
        "offers_made": rows.offers_made,
        "in_negotiation": rows.in_negotiation,
    }


@router.get("/admin/buyers/{phone}")
async def get_buyer(
    phone: str,
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Full buyer detail with conversations and inquiries."""
    _set_admin_db_context(db)
    phone = _decode_phone(phone)

    profile = db.get(DBBuyerProfile, phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Buyer not found")

    # Conversations with aggregated stats
    conv_rows = db.execute(
        select(
            DBConversation.conversation_id,
            DBConversation.listing_id,
            DBConversation.escalation_triggered,
            DBConversation.escalation_reason,
            DBConversation.created_at,
            DBConversation.updated_at,
            func.count(DBMessage.id).label("message_count"),
        )
        .outerjoin(DBMessage, DBMessage.conversation_id == DBConversation.conversation_id)
        .where(DBConversation.buyer_phone == phone)
        .group_by(
            DBConversation.conversation_id,
            DBConversation.listing_id,
            DBConversation.escalation_triggered,
            DBConversation.escalation_reason,
            DBConversation.created_at,
            DBConversation.updated_at,
        )
        .order_by(DBConversation.updated_at.desc())
    ).all()

    # For each conversation, get listing name and last message preview
    conversations = []
    for cr in conv_rows:
        listing = db.get(DBListing, cr.listing_id)
        listing_name = (listing.spa_data or {}).get("project", "Unknown") if listing else "Unknown"

        # Last message preview
        last_msg = db.execute(
            select(DBMessage.content, DBMessage.role)
            .where(DBMessage.conversation_id == cr.conversation_id)
            .order_by(DBMessage.timestamp.desc())
            .limit(1)
        ).first()

        conversations.append({
            "conversation_id": cr.conversation_id,
            "listing_id": cr.listing_id,
            "listing_name": listing_name,
            "message_count": cr.message_count,
            "escalation_triggered": cr.escalation_triggered,
            "escalation_reason": cr.escalation_reason,
            "last_message_preview": last_msg.content[:120] if last_msg else None,
            "last_message_role": last_msg.role if last_msg else None,
            "created_at": cr.created_at.isoformat() if cr.created_at else None,
            "updated_at": cr.updated_at.isoformat() if cr.updated_at else None,
        })

    # Inquiries
    inquiries = [
        {
            "listing_id": inq.listing_id,
            "project": inq.project,
            "unit_number": inq.unit_number,
            "price_aed": inq.price_aed,
            "first_contact": inq.first_contact.isoformat() if inq.first_contact else None,
        }
        for inq in (profile.inquiries or [])
    ]

    return {
        "phone": profile.phone,
        "name": profile.name,
        "lead_stage": profile.lead_stage,
        "lead_source": profile.lead_source,
        "budget_aed": profile.budget_aed,
        "bedroom_preferences": profile.bedroom_preferences,
        "area_preferences": profile.area_preferences,
        "purpose": profile.purpose,
        "tags": profile.tags,
        "admin_notes": profile.admin_notes,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "conversations": conversations,
        "inquiries": inquiries,
    }


@router.get("/admin/buyers/{phone}/conversations")
async def list_buyer_conversations(
    phone: str,
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all conversations for a buyer."""
    _set_admin_db_context(db)
    phone = _decode_phone(phone)

    rows = db.execute(
        select(
            DBConversation.conversation_id,
            DBConversation.listing_id,
            DBConversation.buyer_name,
            DBConversation.escalation_triggered,
            DBConversation.escalation_reason,
            DBConversation.created_at,
            DBConversation.updated_at,
            func.count(DBMessage.id).label("message_count"),
        )
        .outerjoin(DBMessage, DBMessage.conversation_id == DBConversation.conversation_id)
        .where(DBConversation.buyer_phone == phone)
        .group_by(
            DBConversation.conversation_id,
            DBConversation.listing_id,
            DBConversation.buyer_name,
            DBConversation.escalation_triggered,
            DBConversation.escalation_reason,
            DBConversation.created_at,
            DBConversation.updated_at,
        )
        .order_by(DBConversation.updated_at.desc())
    ).all()

    conversations = []
    for r in rows:
        listing = db.get(DBListing, r.listing_id)
        listing_name = (listing.spa_data or {}).get("project", "Unknown") if listing else "Unknown"
        conversations.append({
            "conversation_id": r.conversation_id,
            "listing_id": r.listing_id,
            "listing_name": listing_name,
            "buyer_name": r.buyer_name,
            "message_count": r.message_count,
            "escalation_triggered": r.escalation_triggered,
            "escalation_reason": r.escalation_reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    return {"conversations": conversations}


@router.get("/admin/buyers/{phone}/messages/{conversation_id}")
async def get_conversation_messages(
    phone: str,
    conversation_id: str,
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Full message transcript for a specific conversation."""
    _set_admin_db_context(db)
    phone = _decode_phone(phone)

    # Verify conversation belongs to this buyer
    conv = db.execute(
        select(DBConversation)
        .where(
            DBConversation.conversation_id == conversation_id,
            DBConversation.buyer_phone == phone,
        )
    ).scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.execute(
        select(
            DBMessage.id,
            DBMessage.role,
            DBMessage.content,
            DBMessage.intent,
            DBMessage.timestamp,
        )
        .where(DBMessage.conversation_id == conversation_id)
        .order_by(DBMessage.timestamp.asc())
    ).all()

    return {
        "conversation_id": conversation_id,
        "listing_id": conv.listing_id,
        "buyer_phone": phone,
        "buyer_name": conv.buyer_name,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in messages
        ],
    }


@router.patch("/admin/buyers/{phone}")
async def update_buyer(
    phone: str,
    body: BuyerUpdate,
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update lead_stage, tags, or lead_source for a buyer."""
    _set_admin_db_context(db)
    phone = _decode_phone(phone)

    profile = db.get(DBBuyerProfile, phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Buyer not found")

    if body.lead_stage is not None:
        if body.lead_stage not in STAGE_ORDER:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage. Must be one of: {', '.join(STAGE_ORDER)}",
            )
        profile.lead_stage = body.lead_stage
    if body.tags is not None:
        profile.tags = body.tags
    if body.lead_source is not None:
        profile.lead_source = body.lead_source

    profile.updated_at = datetime.utcnow()
    safe_commit(db)

    return {"success": True, "phone": phone}


@router.post("/admin/buyers/{phone}/notes")
async def add_note(
    phone: str,
    body: NoteCreate,
    _admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Append a timestamped admin note."""
    _set_admin_db_context(db)
    phone = _decode_phone(phone)

    profile = db.get(DBBuyerProfile, phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Buyer not found")

    notes = list(profile.admin_notes or [])
    notes.append({
        "note": body.note,
        "at": datetime.utcnow().isoformat(),
    })
    profile.admin_notes = notes
    profile.updated_at = datetime.utcnow()
    safe_commit(db)

    return {"success": True, "total_notes": len(notes)}
