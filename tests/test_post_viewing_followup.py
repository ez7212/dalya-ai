"""
DAL-166 — Post-viewing follow-up draft CTA (flagged optional).

Checklist:
  1. Draft appears in the queue with feedback grounding.
  2. Alternatives only from the same brokerage (isolation).
  3. Zero-match case produces no fabricated listings.
  4. Flag off → CTA absent (endpoint 404), no behavior change.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.buyer_profiles import confirm_field, get_or_create_profile
from app.core.post_viewing_followup import (
    create_feedback_follow_up_draft,
    find_alternative_listings,
)
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerProfileField,
    DBComplianceEvent,
    DBConversation,
    DBDraftReply,
    DBLeadAssignment,
    DBListing,
    DBMessage,
    DBViewing,
    DBViewingFeedback,
)


def _listing(listing_id, brokerage_id, project, price, bedrooms=2):
    return DBListing(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        spa_data={"project": project, "unit_number": "10", "bedrooms": bedrooms},
        seller_asking_price=price,
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
def followup_seed():
    suffix = uuid.uuid4().hex[:8]
    digits = f"{int(suffix, 16) % 10000:04d}"
    brokerage_id = f"fup-brokerage-{suffix}"
    other_brokerage_id = f"fup-other-{suffix}"
    viewed = f"fup-viewed-{suffix}"
    alt_match = f"fup-alt-{suffix}"
    alt_pricey = f"fup-pricey-{suffix}"
    other_alt = f"fup-other-alt-{suffix}"
    agent_user_id = f"fup-agent-{suffix}"
    buyer_phone = f"+97156611{digits}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id, name="Followup Brokerage", slug=f"fup-{suffix}", status="active",
            brokerage_ai_number=f"+97158811{digits}",
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id, name="Followup Other", slug=f"fup-other-{suffix}", status="active",
        ))
        db.add(DBBrokerageMember(
            brokerage_id=brokerage_id, user_id=agent_user_id, role="agent", status="active",
        ))
        db.add(_listing(viewed, brokerage_id, "Viewed Villas", 2_000_000))
        db.add(_listing(alt_match, brokerage_id, "Alt Gardens", 1_900_000))
        db.add(_listing(alt_pricey, brokerage_id, "Pricey Palms", 5_000_000))
        # Same criteria, OTHER brokerage — must never appear.
        db.add(_listing(other_alt, other_brokerage_id, "Other Gardens", 1_850_000))
        safe_commit(db)
        conv = crud.get_or_create_conversation(db, buyer_phone, viewed)
        conv.buyer_name = "Maya"
        conv.assigned_agent_id = agent_user_id
        safe_commit(db)
        viewing = DBViewing(
            brokerage_id=brokerage_id,
            conversation_id=conv.conversation_id,
            listing_id=viewed,
            buyer_phone=buyer_phone,
            agent_user_id=agent_user_id,
            status="completed",
        )
        db.add(viewing)
        db.flush()
        db.add(DBViewingFeedback(
            brokerage_id=brokerage_id,
            viewing_id=viewing.viewing_id,
            conversation_id=conv.conversation_id,
            listing_id=viewed,
            buyer_phone=buyer_phone,
            participant_type="buyer",
            status="received",
            score=6,
            summary="Liked the layout but the road noise was a concern.",
        ))
        safe_commit(db)
        viewing_id = viewing.viewing_id
        conversation_id = conv.conversation_id

    try:
        yield {
            "brokerage_id": brokerage_id,
            "other_brokerage_id": other_brokerage_id,
            "viewed": viewed,
            "alt_match": alt_match,
            "alt_pricey": alt_pricey,
            "other_alt": other_alt,
            "agent_user_id": agent_user_id,
            "buyer_phone": buyer_phone,
            "viewing_id": viewing_id,
            "conversation_id": conversation_id,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        with SessionLocal() as db:
            for brokerage in (brokerage_id, other_brokerage_id):
                db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBDraftReply).filter(DBDraftReply.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBViewingFeedback).filter(DBViewingFeedback.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBViewing).filter(DBViewing.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBuyerProfileField).filter(DBBuyerProfileField.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_([viewed, alt_match, alt_pricey, other_alt])).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id])).delete(synchronize_session=False)
            safe_commit(db)


def test_draft_grounded_on_feedback_with_same_brokerage_alternatives(followup_seed):
    seed = followup_seed
    with SessionLocal() as db:
        profile = get_or_create_profile(
            db, brokerage_id=seed["brokerage_id"], buyer_phone=seed["buyer_phone"]
        )
        confirm_field(db, profile=profile, field="budget_max_aed", value=2_000_000, confirmed_by=seed["agent_user_id"])
        confirm_field(db, profile=profile, field="bedrooms", value=2, confirmed_by=seed["agent_user_id"])

        viewing = db.get(DBViewing, seed["viewing_id"])
        draft = create_feedback_follow_up_draft(
            db,
            brokerage_id=seed["brokerage_id"],
            viewing=viewing,
            agent_user_id=seed["agent_user_id"],
        )
        assert draft.status == "draft"  # review-only, normal approval flow
        assert draft.source == "post_viewing_followup_cta"
        assert "road noise" in draft.draft_text  # feedback grounding
        assert "Alt Gardens" in draft.draft_text  # within confirmed budget+beds
        assert "Pricey Palms" not in draft.draft_text  # over budget
        # Isolation: same-criteria listing from another brokerage never appears.
        assert "Other Gardens" not in draft.draft_text
        alternatives = draft.metadata_json["alternative_listing_ids"]
        assert alternatives == [seed["alt_match"]]


def test_zero_match_produces_plain_follow_up(followup_seed):
    seed = followup_seed
    with SessionLocal() as db:
        # No confirmed qualification at all → no alternatives, never padded.
        viewing = db.get(DBViewing, seed["viewing_id"])
        draft = create_feedback_follow_up_draft(
            db,
            brokerage_id=seed["brokerage_id"],
            viewing=viewing,
            agent_user_id=seed["agent_user_id"],
        )
        assert draft.metadata_json["alternative_listing_ids"] == []
        assert "Alt Gardens" not in draft.draft_text
        assert "next steps" in draft.draft_text


def test_alternatives_filter_uses_confirmed_fields_only(followup_seed):
    seed = followup_seed
    with SessionLocal() as db:
        # Only ai_inferred (not confirmed) budget → alternatives stay empty.
        from app.core.buyer_profiles import record_inferred_field

        profile = get_or_create_profile(
            db, brokerage_id=seed["brokerage_id"], buyer_phone=seed["buyer_phone"]
        )
        record_inferred_field(db, profile=profile, field="budget_max_aed", value=2_000_000, confidence=0.9)
        safe_commit(db)
        matches = find_alternative_listings(
            db,
            brokerage_id=seed["brokerage_id"],
            exclude_listing_id=seed["viewed"],
            confirmed={},  # confirmed-only contract
        )
        assert matches == []


def test_flag_off_endpoint_absent_flag_on_creates_draft(client, monkeypatch, followup_seed):
    seed = followup_seed
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["agent_user_id"], email="fup@example.com",
    )

    # Flag off → CTA absent (endpoint 404), no behavior change.
    monkeypatch.delenv("FEATURE_FOLLOWUP_DRAFT_CTA", raising=False)
    off = client.post(f"/api/v1/agent/viewings/{seed['viewing_id']}/feedback/draft-follow-up", json={})
    assert off.status_code == 404
    with SessionLocal() as db:
        assert (
            db.query(DBDraftReply)
            .filter(DBDraftReply.brokerage_id == seed["brokerage_id"])
            .count()
            == 0
        )

    # Flag on → review-only draft lands in the queue.
    monkeypatch.setenv("FEATURE_FOLLOWUP_DRAFT_CTA", "true")
    on = client.post(f"/api/v1/agent/viewings/{seed['viewing_id']}/feedback/draft-follow-up", json={})
    assert on.status_code == 200, on.text
    payload = on.json()
    assert payload["status"] == "draft"
    with SessionLocal() as db:
        draft = (
            db.query(DBDraftReply)
            .filter(DBDraftReply.brokerage_id == seed["brokerage_id"])
            .one()
        )
        assert draft.source == "post_viewing_followup_cta"
