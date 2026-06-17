"""
Multi-tenant listings API.

Routes:
- POST /listings/draft-from-url        — scrape PF/Bayut → return prefilled draft
- POST /listings                       — create a listing (off-plan or finished)
- POST /listings/{id}/reference-documents  — attach reference docs to a listing
- GET  /onboarding/approved-brokerages — list brokerages an agent can register under

The off-plan SPA-upload flow stays in app/api/spa_parser.py — this module is
for the finished-property path and the unified "create" endpoint.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.core.brokerage_resolver import list_approved_brokerages
from app.core.listing_scraper import scrape_any
from app.core.ready_property_knowledge import (
    DOCUMENT_TYPES,
    process_listing_document,
    rebuild_knowledge_summary,
)
from app.db.session import get_db, safe_commit
from app.models.db_models import (
    DBBrokerageMember,
    DBCommunityResearch,
    DBListing,
    DBListingDocument,
    DBListingFact,
    DBListingKnowledgeSummary,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────


class DraftFromUrlRequest(BaseModel):
    url: str


class AdditionalFee(BaseModel):
    label: str
    amount_aed: Optional[float] = None
    paid_by: str = "buyer"
    public: bool = True  # Future feature (deferred): per-fee public/private toggle


class ReferenceDocument(BaseModel):
    kind: str          # title_deed | ejari | service_charge | dewa | noc | valuation | snagging | mortgage
    url: Optional[str] = None
    label: Optional[str] = None


class ListingDocumentCreateRequest(BaseModel):
    document_type: str = Field(..., description="Ready-property document type.")
    label: Optional[str] = None
    source_url: Optional[str] = None
    content_text: Optional[str] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ListingFactUpdateRequest(BaseModel):
    value_text: Optional[str] = None
    verified: Optional[bool] = None
    buyer_safe: Optional[bool] = None
    risk_flag: Optional[bool] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    notes: Optional[str] = None


class CreateListingRequest(BaseModel):
    property_type: str = Field(..., pattern="^(off_plan|ready)$")
    listing_title: Optional[str] = None
    listing_reference: Optional[str] = None
    portal_source: Optional[str] = None
    portal_listing_id: Optional[str] = None
    purpose: Optional[str] = None
    completion_status: Optional[str] = None
    furnishing: Optional[str] = None
    community: Optional[str] = None
    subcommunity: Optional[str] = None
    building_or_project: Optional[str] = None
    unit_number: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqft: Optional[float] = None
    plot_size_sqft: Optional[float] = None
    asking_price_aed: Optional[float] = None
    price_per_sqft_aed: Optional[float] = None
    developer: Optional[str] = None
    handover_date: Optional[str] = None
    amenities: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    permit_number: Optional[str] = None
    permit_validation_url: Optional[str] = None
    broker_name: Optional[str] = None
    broker_license: Optional[str] = None
    agent_name: Optional[str] = None
    agent_email: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_license: Optional[str] = None
    notification_threshold_aed: Optional[float] = None
    commission_rate: float = Field(..., ge=0.0, le=1.0)  # decimal e.g. 0.02 = 2%
    additional_fees: list[AdditionalFee] = Field(default_factory=list)
    source_url: Optional[str] = None
    reference_documents: list[ReferenceDocument] = Field(default_factory=list)
    seller_notes: Optional[str] = None
    seller_phone: Optional[str] = None
    # Optional override — by default the authenticated agent is the managing agent.
    managing_agent_user_id: Optional[str] = None
    spa_data: Optional[dict] = None  # populated by SPA parser for off_plan flow


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────


def _slugify_community(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return cleaned or None


def _ensure_member_brokerage(user_id: str, db: Session) -> DBBrokerageMember:
    """Resolve the authenticated user's active brokerage membership."""
    member = (
        db.query(DBBrokerageMember)
        .filter(
            DBBrokerageMember.user_id == user_id,
            DBBrokerageMember.status == "active",
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=403,
            detail="No active brokerage membership found. Complete agent onboarding first.",
        )
    return member


def _get_scoped_listing(listing_id: str, user: CurrentUser, db: Session) -> tuple[DBListing, DBBrokerageMember]:
    listing = db.get(DBListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    member = _ensure_member_brokerage(user.id, db)
    if listing.brokerage_id != member.brokerage_id:
        raise HTTPException(status_code=403, detail="Listing is not under your brokerage.")
    return listing, member


def _serialize_document(doc: DBListingDocument) -> dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "listing_id": doc.listing_id,
        "document_type": doc.document_type,
        "label": doc.label,
        "source_url": doc.source_url,
        "status": doc.status,
        "extracted_at": doc.extracted_at.isoformat() if doc.extracted_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        "metadata_json": doc.metadata_json or {},
        "content_preview": (doc.content_text or "")[:240],
    }


def _serialize_fact(fact: DBListingFact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "document_id": fact.document_id,
        "listing_id": fact.listing_id,
        "fact_key": fact.fact_key,
        "fact_group": fact.fact_group,
        "value_text": fact.value_text,
        "value_json": fact.value_json or {},
        "confidence": fact.confidence,
        "source": fact.source,
        "verified": fact.verified,
        "buyer_safe": fact.buyer_safe,
        "risk_flag": fact.risk_flag,
        "notes": fact.notes,
        "created_at": fact.created_at.isoformat() if fact.created_at else None,
        "updated_at": fact.updated_at.isoformat() if fact.updated_at else None,
    }


def _serialize_summary(summary: Optional[DBListingKnowledgeSummary]) -> Optional[dict[str, Any]]:
    if not summary:
        return None
    return {
        "summary_id": summary.summary_id,
        "listing_id": summary.listing_id,
        "buyer_safe_summary": summary.buyer_safe_summary,
        "internal_notes": summary.internal_notes,
        "missing_information": summary.missing_information or [],
        "risk_flags": summary.risk_flags or [],
        "status": summary.status,
        "metadata_json": summary.metadata_json or {},
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
        "updated_at": summary.updated_at.isoformat() if summary.updated_at else None,
    }


def _knowledge_payload(db: Session, listing: DBListing) -> dict[str, Any]:
    documents = (
        db.query(DBListingDocument)
        .filter(DBListingDocument.listing_id == listing.listing_id)
        .order_by(DBListingDocument.created_at.desc())
        .all()
    )
    facts = (
        db.query(DBListingFact)
        .filter(DBListingFact.listing_id == listing.listing_id)
        .order_by(DBListingFact.fact_group.asc(), DBListingFact.created_at.asc())
        .all()
    )
    summary = (
        db.query(DBListingKnowledgeSummary)
        .filter(DBListingKnowledgeSummary.listing_id == listing.listing_id)
        .first()
    )
    return {
        "listing_id": listing.listing_id,
        "document_types": DOCUMENT_TYPES,
        "documents": [_serialize_document(doc) for doc in documents],
        "facts": [_serialize_fact(fact) for fact in facts],
        "summary": _serialize_summary(summary),
    }


# ──────────────────────────────────────────────────────────────────────────
# Approved-brokerages list
# ──────────────────────────────────────────────────────────────────────────


@router.get("/onboarding/approved-brokerages")
async def approved_brokerages(
    db: Session = Depends(get_db),
):
    """Brokerages an agent is allowed to register under (signup-enabled + active)."""
    brokerages = list_approved_brokerages(db)
    return {
        "brokerages": [
            {
                "brokerage_id": b.brokerage_id,
                "name": b.name,
                "slug": b.slug,
                "real_estate_number": b.real_estate_number,
            }
            for b in brokerages
        ]
    }


# ──────────────────────────────────────────────────────────────────────────
# Scrape PF/Bayut → draft
# ──────────────────────────────────────────────────────────────────────────


@router.post("/listings/draft-from-url")
async def draft_listing_from_url(
    body: DraftFromUrlRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Scrape a Property Finder or Bayut URL and return a partial draft. Failures
    are non-fatal — the client renders a manual-entry form prefilled with
    whatever the scraper retrieved.
    """
    _ = user  # auth-gated; user identity used for audit only
    scraped = scrape_any(body.url)
    community_key = _slugify_community(scraped.community or scraped.building_or_project)
    return {
        "scrape": {
            "source": scraped.source,
            "source_url": scraped.source_url,
            "property_type": scraped.property_type,
            "listing_title": scraped.listing_title,
            "listing_reference": scraped.listing_reference,
            "portal_listing_id": scraped.portal_listing_id,
            "portal_reference": scraped.portal_reference,
            "purpose": scraped.purpose,
            "completion_status": scraped.completion_status,
            "furnishing": scraped.furnishing,
            "community": scraped.community,
            "community_key": community_key,
            "subcommunity": scraped.subcommunity,
            "building_or_project": scraped.building_or_project,
            "unit_number": scraped.unit_number,
            "bedrooms": scraped.bedrooms,
            "bathrooms": scraped.bathrooms,
            "size_sqft": scraped.size_sqft,
            "plot_size_sqft": scraped.plot_size_sqft,
            "asking_price_aed": scraped.asking_price_aed,
            "price_per_sqft_aed": scraped.price_per_sqft_aed,
            "latitude": scraped.latitude,
            "longitude": scraped.longitude,
            "developer": scraped.developer,
            "handover_date": scraped.handover_date,
            "permit_number": scraped.permit_number,
            "permit_validation_url": scraped.permit_validation_url,
            "broker_name": scraped.broker_name,
            "broker_license": scraped.broker_license,
            "agent_name": scraped.agent_name,
            "agent_email": scraped.agent_email,
            "agent_phone": scraped.agent_phone,
            "agent_license": scraped.agent_license,
            "amenities": scraped.amenities,
            "image_urls": scraped.image_urls,
            "description": scraped.description,
        },
        "draft": {
            "property_type": scraped.property_type or "ready",
            "listing_title": scraped.listing_title,
            "listing_reference": scraped.listing_reference,
            "portal_source": scraped.source,
            "portal_listing_id": scraped.portal_listing_id,
            "purpose": scraped.purpose,
            "completion_status": scraped.completion_status,
            "furnishing": scraped.furnishing,
            "community": scraped.community or community_key,
            "subcommunity": scraped.subcommunity,
            "building_or_project": scraped.building_or_project,
            "unit_number": scraped.unit_number,
            "bedrooms": scraped.bedrooms,
            "bathrooms": scraped.bathrooms,
            "size_sqft": scraped.size_sqft,
            "plot_size_sqft": scraped.plot_size_sqft,
            "asking_price_aed": scraped.asking_price_aed,
            "price_per_sqft_aed": scraped.price_per_sqft_aed,
            "developer": scraped.developer,
            "handover_date": scraped.handover_date,
            "amenities": scraped.amenities,
            "image_urls": scraped.image_urls,
            "description": scraped.description,
            "permit_number": scraped.permit_number,
            "permit_validation_url": scraped.permit_validation_url,
            "broker_name": scraped.broker_name,
            "broker_license": scraped.broker_license,
            "agent_name": scraped.agent_name,
            "agent_email": scraped.agent_email,
            "agent_phone": scraped.agent_phone,
            "agent_license": scraped.agent_license,
            "source_url": scraped.source_url,
        },
    }


# ──────────────────────────────────────────────────────────────────────────
# Create listing
# ──────────────────────────────────────────────────────────────────────────


@router.post("/listings")
async def create_listing(
    body: CreateListingRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a multi-tenant listing under the authenticated agent's brokerage.
    Supports both off_plan (with spa_data) and ready (PF/Bayut-sourced or manual).

    Triggers community research if no DBCommunityResearch row exists for the
    listing's community key. The listing goes live regardless of research
    state — missing community data is simply absent and never blocks publish.
    """
    member = _ensure_member_brokerage(user.id, db)
    brokerage_id = member.brokerage_id

    managing_agent_user_id = body.managing_agent_user_id or user.id
    community_key = _slugify_community(body.community)

    # SPA shim: ready listings still need a spa_data JSON to satisfy the existing
    # not-null column on `listings`. Synthesise a minimal one when missing.
    spa_data = body.spa_data or {
        "project": body.building_or_project or body.subcommunity or body.community or "Listing",
        "unit_number": body.unit_number or "—",
        "developer": body.developer or "",
        "property_type": body.listing_title or ("Ready Property" if body.property_type == "ready" else "Off-Plan"),
        "bedrooms": body.bedrooms,
        "bathrooms": body.bathrooms,
        "bua_sqft": body.size_sqft,
        "plot_sqft": body.plot_size_sqft,
        "purchase_price_aed": body.asking_price_aed or 0.0,
        "vat_percent": 0,
        "estimated_completion_date": body.handover_date,
        "noc_eligible": True if body.property_type == "ready" else None,
        "payment_schedule": [],
        "purchasers": [],
        "imported_listing": {
            "title": body.listing_title,
            "reference": body.listing_reference,
            "portal_source": body.portal_source,
            "portal_listing_id": body.portal_listing_id,
            "purpose": body.purpose,
            "completion_status": body.completion_status,
            "furnishing": body.furnishing,
            "community": body.community,
            "subcommunity": body.subcommunity,
            "price_per_sqft_aed": body.price_per_sqft_aed,
            "amenities": body.amenities,
            "description": body.description,
            "permit_number": body.permit_number,
            "permit_validation_url": body.permit_validation_url,
            "broker": {
                "name": body.broker_name,
                "license": body.broker_license,
            },
            "agent": {
                "name": body.agent_name,
                "email": body.agent_email,
                "phone": body.agent_phone,
                "license": body.agent_license,
            },
        },
    }

    listing_id = str(uuid.uuid4())
    listing = DBListing(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        assigned_agent_id=managing_agent_user_id,
        seller_id=user.id,
        seller_phone=body.seller_phone,
        spa_data=spa_data,
        community_data=None,
        seller_asking_price=body.asking_price_aed,
        seller_notes=body.seller_notes,
        negotiation_threshold_aed=body.notification_threshold_aed,
        notification_threshold_aed=body.notification_threshold_aed,
        commission_rate=body.commission_rate,
        additional_fees=[f.model_dump() for f in body.additional_fees],
        property_type=body.property_type,
        source_url=body.source_url,
        reference_documents=[d.model_dump() for d in body.reference_documents],
        community=community_key,
        media_urls=body.image_urls,
        processing_stages={},
        created_at=datetime.utcnow(),
    )
    db.add(listing)
    safe_commit(db)

    try:
        from app.core.remarketing import generate_buyer_matches_for_listing

        generate_buyer_matches_for_listing(db, listing=listing, limit=5)
    except Exception as exc:
        logger.warning("listings/create: failed to generate buyer re-marketing matches: %s", exc)

    # Trigger community research if we have no record for this community.
    community_research_status = None
    if community_key:
        existing = (
            db.query(DBCommunityResearch)
            .filter(DBCommunityResearch.project_name.ilike(f"%{body.community}%"))
            .first()
        )
        if not existing:
            try:
                research = DBCommunityResearch(
                    project_name=body.community or community_key,
                    developer="",
                    status="pending",
                )
                db.add(research)
                safe_commit(db)
                community_research_status = "queued"
            except Exception as exc:
                logger.warning("listings/create: failed to enqueue community research: %s", exc)
        else:
            community_research_status = existing.status

    return {
        "listing_id": listing_id,
        "brokerage_id": brokerage_id,
        "managing_agent_user_id": managing_agent_user_id,
        "property_type": body.property_type,
        "community_research_status": community_research_status,
        "status": "live",
    }


# ──────────────────────────────────────────────────────────────────────────
# Reference documents
# ──────────────────────────────────────────────────────────────────────────


@router.post("/listings/{listing_id}/reference-documents")
async def add_reference_documents(
    listing_id: str,
    documents: list[ReferenceDocument],
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attach reference documents (title deed, Ejari, service charge, NOC, etc.) to a listing."""
    listing = db.get(DBListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    member = _ensure_member_brokerage(user.id, db)
    if listing.brokerage_id != member.brokerage_id:
        raise HTTPException(status_code=403, detail="Listing is not under your brokerage.")

    existing = list(listing.reference_documents or [])
    for doc in documents:
        existing.append(doc.model_dump())
    listing.reference_documents = existing
    safe_commit(db)
    return {"listing_id": listing_id, "reference_documents": existing}


@router.post("/listings/{listing_id}/documents")
async def create_listing_document(
    listing_id: str,
    body: ListingDocumentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing, member = _get_scoped_listing(listing_id, user, db)
    document_type = body.document_type.strip().lower()
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported document_type. Use one of: {', '.join(DOCUMENT_TYPES)}")

    document = DBListingDocument(
        brokerage_id=member.brokerage_id,
        listing_id=listing.listing_id,
        document_type=document_type,
        label=body.label,
        source_url=body.source_url,
        content_text=body.content_text,
        status="pending",
        metadata_json=body.metadata_json or {},
    )
    db.add(document)
    safe_commit(db)
    db.refresh(document)
    facts = process_listing_document(db, document)
    summary = rebuild_knowledge_summary(db, listing)
    db.refresh(document)
    return {
        "document": _serialize_document(document),
        "facts": [_serialize_fact(fact) for fact in facts],
        "summary": _serialize_summary(summary),
    }


@router.get("/listings/{listing_id}/documents")
async def list_listing_documents(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing, _member = _get_scoped_listing(listing_id, user, db)
    documents = (
        db.query(DBListingDocument)
        .filter(DBListingDocument.listing_id == listing.listing_id)
        .order_by(DBListingDocument.created_at.desc())
        .all()
    )
    return {"listing_id": listing.listing_id, "documents": [_serialize_document(doc) for doc in documents]}


@router.post("/listings/{listing_id}/documents/{document_id}/reprocess")
async def reprocess_listing_document(
    listing_id: str,
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing, _member = _get_scoped_listing(listing_id, user, db)
    document = db.get(DBListingDocument, document_id)
    if not document or document.listing_id != listing.listing_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    facts = process_listing_document(db, document)
    summary = rebuild_knowledge_summary(db, listing)
    db.refresh(document)
    return {
        "document": _serialize_document(document),
        "facts": [_serialize_fact(fact) for fact in facts],
        "summary": _serialize_summary(summary),
    }


@router.get("/listings/{listing_id}/knowledge")
async def get_listing_knowledge(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing, _member = _get_scoped_listing(listing_id, user, db)
    return _knowledge_payload(db, listing)


@router.patch("/listings/{listing_id}/facts/{fact_id}")
async def update_listing_fact(
    listing_id: str,
    fact_id: str,
    body: ListingFactUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing, _member = _get_scoped_listing(listing_id, user, db)
    fact = db.get(DBListingFact, fact_id)
    if not fact or fact.listing_id != listing.listing_id:
        raise HTTPException(status_code=404, detail="Fact not found.")

    if body.value_text is not None:
        fact.value_text = body.value_text
    if body.verified is not None:
        fact.verified = body.verified
    if body.buyer_safe is not None:
        fact.buyer_safe = body.buyer_safe
    if body.risk_flag is not None:
        fact.risk_flag = body.risk_flag
    if body.confidence is not None:
        fact.confidence = body.confidence
    if body.notes is not None:
        fact.notes = body.notes
    fact.updated_at = datetime.utcnow()
    safe_commit(db)
    db.refresh(fact)
    summary = rebuild_knowledge_summary(db, listing)
    return {"fact": _serialize_fact(fact), "summary": _serialize_summary(summary)}


@router.post("/listings/{listing_id}/knowledge/regenerate")
async def regenerate_listing_knowledge(
    listing_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing, _member = _get_scoped_listing(listing_id, user, db)
    summary = rebuild_knowledge_summary(db, listing)
    payload = _knowledge_payload(db, listing)
    payload["summary"] = _serialize_summary(summary)
    return payload
