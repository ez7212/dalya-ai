from __future__ import annotations

import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.chatbot_engine import ChatbotEngine
from app.core.ready_property_knowledge import ready_property_knowledge_for_prompt
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageMember,
    DBListing,
    DBListingDocument,
    DBListingFact,
    DBListingKnowledgeSummary,
)
from app.schemas.spa import SPAParseResult


@pytest.fixture
def ready_knowledge_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"ready-knowledge-brokerage-{suffix}"
    agent_id = f"ready-knowledge-agent-{suffix}"
    other_agent_id = f"ready-knowledge-other-{suffix}"
    listing_id = f"ready-knowledge-listing-{suffix}"

    with SessionLocal() as db:
        db.add(
            DBBrokerage(
                brokerage_id=brokerage_id,
                name="Ready Knowledge Brokerage",
                slug=f"ready-knowledge-{suffix}",
                status="active",
                brokerage_ai_number=f"+97158820{suffix[:4]}",
                agents_ai_number=f"+97159920{suffix[:4]}",
            )
        )
        db.add_all(
            [
                DBBrokerageMember(
                    brokerage_id=brokerage_id,
                    user_id=agent_id,
                    email=f"{agent_id}@example.com",
                    display_name="Agent",
                    role="agent",
                    status="active",
                ),
                DBBrokerageMember(
                    brokerage_id=brokerage_id,
                    user_id=other_agent_id,
                    email=f"{other_agent_id}@example.com",
                    display_name="Other Agent",
                    role="agent",
                    status="active",
                ),
            ]
        )
        db.add(
            DBListing(
                listing_id=listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=agent_id,
                seller_id=agent_id,
                spa_data={
                    "project": "Ready Knowledge Tower",
                    "unit_number": "1402",
                    "developer": "LIV",
                    "property_type": "Apartment",
                    "bedrooms": 2,
                    "bathrooms": 3,
                    "bua_sqft": 1475,
                    "purchase_price_aed": 3_000_000,
                    "property_status": "Ready",
                    "noc_eligible": True,
                    "payment_schedule": [],
                    "purchasers": [],
                },
                seller_asking_price=3_050_000,
                commission_rate=0.015,
                property_type="ready",
                additional_fees=[],
                seller_qa=[],
                media_urls=[],
                unit_profile={},
                unit_profile_history=[],
                processing_stages={},
                reference_documents=[],
            )
        )
        safe_commit(db)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "agent_id": agent_id,
            "other_agent_id": other_agent_id,
            "listing_id": listing_id,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        with SessionLocal() as db:
            db.query(DBListingKnowledgeSummary).filter(DBListingKnowledgeSummary.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBListingFact).filter(DBListingFact.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBListingDocument).filter(DBListingDocument.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )


def test_ready_property_document_extraction_summary_and_fact_controls(client, ready_knowledge_seed):
    seed = ready_knowledge_seed
    _as_user(seed["agent_id"])

    response = client.post(
        f"/api/v1/listings/{seed['listing_id']}/documents",
        json={
            "document_type": "service_charge_statement",
            "label": "2026 service charge and Ejari note",
                "content_text": (
                    "Service charge for 2026 is AED 18,000 annually. "
                    "The unit is tenanted under Ejari until 2026-12-31. "
                    "DEWA utility note: tenant contact is sara@example.com and +971 55 123 4567. "
                    "Parking allocation: 1 parking space on basement level B2."
                ),
            },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    fact_keys = {fact["fact_key"] for fact in body["facts"]}
    assert {"service_charge", "occupancy_status", "lease_expiry", "parking_allocation", "utility_notes"}.issubset(fact_keys)
    assert body["summary"]["buyer_safe_summary"]
    assert "sara@example.com" not in body["summary"]["buyer_safe_summary"]
    assert "+971 55 123 4567" not in body["summary"]["buyer_safe_summary"]
    assert "[redacted email]" in body["summary"]["buyer_safe_summary"]
    assert "[redacted phone]" in body["summary"]["buyer_safe_summary"]

    service_fact = next(fact for fact in body["facts"] if fact["fact_key"] == "service_charge")
    patch = client.patch(
        f"/api/v1/listings/{seed['listing_id']}/facts/{service_fact['fact_id']}",
        json={"verified": True, "notes": "Matched against statement total."},
    )

    assert patch.status_code == 200, patch.text
    assert patch.json()["fact"]["verified"] is True
    assert "verified" in patch.json()["summary"]["buyer_safe_summary"]

    knowledge = client.get(f"/api/v1/listings/{seed['listing_id']}/knowledge")
    assert knowledge.status_code == 200, knowledge.text
    assert knowledge.json()["summary"]["metadata_json"]["fact_count"] >= 4


def test_ready_property_knowledge_feeds_prompt_context_and_info_gap_detection(client, ready_knowledge_seed):
    seed = ready_knowledge_seed
    _as_user(seed["agent_id"])

    client.post(
        f"/api/v1/listings/{seed['listing_id']}/documents",
        json={
            "document_type": "agent_inspection_notes",
            "label": "Inspection notes",
            "content_text": (
                "Service charge is AED 18,000 per year. "
                "Vacant possession is available on transfer. "
                "There is 1 allocated parking bay and a marina view."
            ),
        },
    )

    with SessionLocal() as db:
        listing = db.get(DBListing, seed["listing_id"])
        spa = SPAParseResult(**listing.spa_data)
        missing = ChatbotEngine._missing_listing_fact_topics(
            listing,
            spa,
            "What are the service charges, is it vacant, parking, and view?",
        )
        prompt_payload = ready_property_knowledge_for_prompt(db, seed["listing_id"])

    assert "service charge" not in missing
    assert "occupancy status" not in missing
    assert "parking allocation" not in missing
    assert "view and orientation" not in missing
    assert prompt_payload is not None
    assert "Service charge" in (prompt_payload["buyer_safe_summary"] or "")

    with SessionLocal() as db:
        service_fact = (
            db.query(DBListingFact)
            .filter(
                DBListingFact.listing_id == seed["listing_id"],
                DBListingFact.fact_key == "service_charge",
            )
            .first()
        )
        service_fact.risk_flag = True
        service_fact.confidence = 0.4
        safe_commit(db)
        listing = db.get(DBListing, seed["listing_id"])
        spa = SPAParseResult(**listing.spa_data)
        risky_missing = ChatbotEngine._missing_listing_fact_topics(
            listing,
            spa,
            "What are the service charges?",
        )

    assert "service charge verification" in risky_missing


def test_ready_property_knowledge_is_brokerage_scoped(client, ready_knowledge_seed):
    seed = ready_knowledge_seed
    _as_user(seed["other_agent_id"])

    response = client.get(f"/api/v1/listings/{seed['listing_id']}/knowledge")

    assert response.status_code == 200
