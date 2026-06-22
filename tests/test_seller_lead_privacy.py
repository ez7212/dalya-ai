from __future__ import annotations

import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBConversation,
    DBLeadAssignment,
    DBListing,
    DBMessage,
)


def _listing(
    listing_id: str,
    brokerage_id: str,
    seller_id: str,
    project: str,
) -> DBListing:
    return DBListing(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        seller_id=seller_id,
        spa_data={"project": project, "unit_number": "1701"},
        seller_asking_price=3_200_000,
        negotiation_threshold_aed=3_000_000,
        commission_rate=0.02,
        property_type="ready",
        additional_fees=[],
        seller_qa=[],
        media_urls=[],
        unit_profile={},
        unit_profile_history=[],
        processing_stages={},
    )


@pytest.fixture
def seller_lead_seed():
    suffix = uuid.uuid4().hex[:8]
    digits = f"{int(suffix, 16) % 10000:04d}"
    brokerage_id = f"seller-leads-brokerage-{suffix}"
    other_brokerage_id = f"seller-leads-other-{suffix}"
    seller_id = f"seller-leads-seller-{suffix}"
    other_seller_id = f"seller-leads-other-seller-{suffix}"
    listing_id = f"seller-leads-listing-{suffix}"
    other_listing_id = f"seller-leads-other-listing-{suffix}"
    buyer_phone = f"+97150123{digits}"
    buyer_name = f"Privacy Buyer {suffix}"
    buyer_handle = f"wa.me/97150123{digits}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Seller Lead Brokerage",
            slug=f"seller-leads-{suffix}",
            status="active",
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id,
            name="Other Seller Lead Brokerage",
            slug=f"seller-leads-other-{suffix}",
            status="active",
        ))
        db.add(_listing(listing_id, brokerage_id, seller_id, "Seller Privacy Tower"))
        db.add(_listing(other_listing_id, other_brokerage_id, other_seller_id, "Other Privacy Tower"))
        safe_commit(db)

        conversation = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        assert conversation is not None
        conversation.buyer_name = buyer_name
        conversation.escalation_triggered = True
        conversation.escalation_reason = "viewing_request"
        db.add(DBMessage(
            conversation_id=conversation.conversation_id,
            role="user",
            content=f"This is {buyer_name}. WhatsApp me on {buyer_handle} or {buyer_phone}.",
            intent="viewing_request",
        ))
        db.add(DBMessage(
            conversation_id=conversation.conversation_id,
            role="assistant",
            content="I can help with viewing availability.",
        ))
        safe_commit(db)
        conversation_id = conversation.conversation_id

    try:
        yield {
            "listing_id": listing_id,
            "other_listing_id": other_listing_id,
            "seller_id": seller_id,
            "other_seller_id": other_seller_id,
            "buyer_phone": buyer_phone,
            "buyer_name": buyer_name,
            "buyer_handle": buyer_handle,
            "conversation_id": conversation_id,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        with SessionLocal() as db:
            db.query(DBLeadAssignment).filter(
                DBLeadAssignment.conversation_id == conversation_id,
            ).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(
                DBListing.listing_id.in_([listing_id, other_listing_id]),
            ).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(
                DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id]),
            ).delete(synchronize_session=False)
            safe_commit(db)


def test_seller_leads_anonymize_active_buyers(client, seller_lead_seed):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seller_lead_seed["seller_id"],
        email="seller@example.com",
    )

    response = client.get(f"/api/v1/seller/listings/{seller_lead_seed['listing_id']}/leads")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["lead_count"] == 1
    assert payload["escalated_count"] == 1
    assert payload["leads"] == [
        {
            "buyer_label": "Buyer 1",
            "messages": 2,
            "escalated": True,
            "last_active": payload["leads"][0]["last_active"],
        }
    ]
    leaked_payload = response.text
    assert seller_lead_seed["buyer_phone"] not in leaked_payload
    assert seller_lead_seed["buyer_name"] not in leaked_payload
    assert seller_lead_seed["buyer_handle"] not in leaked_payload
    assert seller_lead_seed["conversation_id"] not in leaked_payload
    assert "phone" not in payload["leads"][0]
    assert "name" not in payload["leads"][0]
    assert "conversation_id" not in payload["leads"][0]


def test_seller_leads_block_cross_seller_access(client, seller_lead_seed):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seller_lead_seed["other_seller_id"],
        email="other-seller@example.com",
    )

    response = client.get(f"/api/v1/seller/listings/{seller_lead_seed['listing_id']}/leads")

    assert response.status_code == 403
    leaked_payload = response.text
    assert seller_lead_seed["buyer_phone"] not in leaked_payload
    assert seller_lead_seed["buyer_name"] not in leaked_payload
    assert seller_lead_seed["buyer_handle"] not in leaked_payload
    assert seller_lead_seed["conversation_id"] not in leaked_payload
