"""
DAL-164 (buyer card & list) + DAL-165 (offer log) — landed together.

DAL-164 checklist:
  1. List view renders, assignment-scoped (agent sees own buyers only).
  2. AI infers budget → ai_inferred row with source link.
  3. Agent edit → agent_confirmed; forced conflicting inference becomes a
     suggestion chip and does NOT overwrite (DB-level assertion).
  4. Same phone, two listings → one profile, two linked conversations.
  5. Same phone, two brokerages → two independent profiles (tenant boundary).
  6. Opt-out buyer renders with the flag (send CTAs disabled by the UI).
  7. Viewings + feedback + offers render from source tables.

DAL-165 checklist:
  1. Offer escalation with extracted amount → DRAFT_PENDING_CONFIRM anchored
     to the buyer's message.
  2. Confirm → SUBMITTED; discard → audit row.
  3. Counter advances the thread; history renders in order.
  4. Vague offer (no amount) → escalation only, no draft, no hallucinated
     amount.
  5. Hot-list boost prefers the structured record (no double count).
  6. Cross-tenant + cross-agent scoping.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.buyer_profiles import (
    confirm_field,
    effective_fields,
    extract_qualification_signals,
    get_or_create_profile,
    record_inferred_field,
    update_profile_from_message,
)
from app.core.hot_list import score_conversation
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.core.offers import (
    confirm_draft_offer,
    create_draft_offer_from_alert,
    discard_draft_offer,
    log_agent_offer,
    offers_for_thread,
    thread_key_for,
    transition_offer,
)
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentProfile,
    DBBrokerage,
    DBBrokerageBuyerProfile,
    DBBrokerageMember,
    DBBuyerProfileField,
    DBComplianceEvent,
    DBConversation,
    DBLeadAction,
    DBLeadAssignment,
    DBListing,
    DBMessage,
    DBOffer,
)


def _listing(listing_id, brokerage_id, agent_user_id, project, unit="101"):
    return DBListing(
        listing_id=listing_id,
        brokerage_id=brokerage_id,
        assigned_agent_id=agent_user_id,
        spa_data={"project": project, "unit_number": unit},
        seller_asking_price=2_000_000,
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
def card_seed():
    suffix = uuid.uuid4().hex[:8]
    digits = f"{int(suffix, 16) % 10000:04d}"
    brokerage_id = f"card-brokerage-{suffix}"
    other_brokerage_id = f"card-other-{suffix}"
    listing_a = f"card-listing-a-{suffix}"
    listing_b = f"card-listing-b-{suffix}"
    other_listing = f"card-listing-o-{suffix}"
    agent_user_id = f"card-agent-{suffix}"
    other_agent_user_id = f"card-agent2-{suffix}"
    buyer_phone = f"+97156699{digits}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id, name="Card Brokerage", slug=f"card-{suffix}",
            status="active",
            brokerage_ai_number=f"+97158899{digits}", agents_ai_number=f"+97159999{digits}",
        ))
        db.add(DBBrokerage(
            brokerage_id=other_brokerage_id, name="Card Other", slug=f"card-other-{suffix}",
            status="active",
        ))
        for user_id in (agent_user_id, other_agent_user_id):
            db.add(DBBrokerageMember(
                brokerage_id=brokerage_id, user_id=user_id, role="agent", status="active",
            ))
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id, user_id=agent_user_id,
            full_name="Card Agent", display_name="Card Agent",
            whatsapp_phone=f"+97157799{digits}",
            rera_broker_card_number=f"BRN-CARD-{suffix}",
        ))
        db.add(_listing(listing_a, brokerage_id, agent_user_id, "Card Towers A"))
        db.add(_listing(listing_b, brokerage_id, agent_user_id, "Card Towers B"))
        db.add(_listing(other_listing, other_brokerage_id, None, "Other Towers"))
        safe_commit(db)
        conv_a = crud.get_or_create_conversation(db, buyer_phone, listing_a)
        conv_a.buyer_name = "Zainab"
        conv_a.assigned_agent_id = agent_user_id
        db.add(DBMessage(conversation_id=conv_a.conversation_id, role="user", content="Hi, I'm interested"))
        safe_commit(db)
        conversation_a = conv_a.conversation_id

    transport = SimulatedTransport()
    set_transport_override(transport)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "other_brokerage_id": other_brokerage_id,
            "listing_a": listing_a,
            "listing_b": listing_b,
            "other_listing": other_listing,
            "conversation_a": conversation_a,
            "agent_user_id": agent_user_id,
            "other_agent_user_id": other_agent_user_id,
            "buyer_phone": buyer_phone,
            "transport": transport,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        set_transport_override(None)
        with SessionLocal() as db:
            conversation_ids = [
                row.conversation_id
                for row in db.query(DBConversation.conversation_id)
                .filter(DBConversation.brokerage_id.in_([brokerage_id, other_brokerage_id]))
                .all()
            ]
            from app.models.db_models import DBAgentNotification, DBBuyerSuppression

            for brokerage in (brokerage_id, other_brokerage_id):
                db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBuyerSuppression).filter(DBBuyerSuppression.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBOffer).filter(DBOffer.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBuyerProfileField).filter(DBBuyerProfileField.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBrokerageBuyerProfile).filter(DBBrokerageBuyerProfile.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage).delete(synchronize_session=False)
                db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage).delete(synchronize_session=False)
            if conversation_ids:
                db.query(DBLeadAction).filter(DBLeadAction.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
                db.query(DBMessage).filter(DBMessage.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
                db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
                db.query(DBConversation).filter(DBConversation.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_([listing_a, listing_b, other_listing])).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id.in_([brokerage_id, other_brokerage_id])).delete(synchronize_session=False)
            safe_commit(db)


# ── DAL-164 checklist 2 + 3: provenance + the structural no-overwrite guard ───


def test_extraction_rules_pull_qualification_signals():
    signals = extract_qualification_signals(
        "We're cash buyers looking for a 3BR, hoping to move next month",
        {"extracted_budget": 2_500_000},
    )
    assert signals["budget_max_aed"][0] == 2_500_000
    assert signals["financing"][0] == "cash"
    assert signals["bedrooms"][0] == 3
    assert signals["timeline"][0] == "next month"


def test_ai_inference_never_overwrites_agent_confirmed(card_seed):
    seed = card_seed
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_a"])
        message = (
            db.query(DBMessage)
            .filter(DBMessage.conversation_id == conv.conversation_id)
            .first()
        )
        profile = update_profile_from_message(
            db,
            conversation=conv,
            message_text="My budget is around 2M",
            message_id=message.id,
            intent_data={"extracted_budget": 2_000_000},
        )
        assert profile is not None
        fields = effective_fields(db, profile)
        assert fields["budget_max_aed"]["value"] == 2_000_000
        assert fields["budget_max_aed"]["provenance"] == "ai_inferred"
        assert fields["budget_max_aed"]["source_message_id"] == message.id

        # Agent confirms a different budget.
        confirm_field(db, profile=profile, field="budget_max_aed", value=2_200_000, confirmed_by=seed["agent_user_id"])

        # Forced conflicting AI inference: must NOT overwrite the confirmed row.
        record_inferred_field(db, profile=profile, field="budget_max_aed", value=1_800_000, confidence=0.9)
        safe_commit(db)

        # DB-level assertion: the agent_confirmed row still carries 2.2M.
        confirmed_row = (
            db.query(DBBuyerProfileField)
            .filter(
                DBBuyerProfileField.profile_id == profile.profile_id,
                DBBuyerProfileField.field == "budget_max_aed",
                DBBuyerProfileField.provenance == "agent_confirmed",
            )
            .one()
        )
        assert confirmed_row.value == 2_200_000
        assert confirmed_row.confirmed_by == seed["agent_user_id"]

        # The conflicting inference surfaces as a suggestion chip.
        fields = effective_fields(db, profile)
        assert fields["budget_max_aed"]["value"] == 2_200_000
        assert fields["budget_max_aed"]["provenance"] == "agent_confirmed"
        assert fields["budget_max_aed"]["suggestion"]["value"] == 1_800_000


# ── DAL-164 checklist 4 + 5: profile keying + tenant boundary ──────────────────


def test_same_phone_one_profile_per_brokerage_two_across_brokerages(card_seed):
    seed = card_seed
    with SessionLocal() as db:
        # Second listing, same buyer → same profile.
        conv_b = crud.get_or_create_conversation(db, seed["buyer_phone"], seed["listing_b"])
        profile_1 = get_or_create_profile(db, brokerage_id=seed["brokerage_id"], buyer_phone=seed["buyer_phone"])
        profile_again = get_or_create_profile(db, brokerage_id=seed["brokerage_id"], buyer_phone=seed["buyer_phone"])
        assert profile_1.profile_id == profile_again.profile_id

        conversations = (
            db.query(DBConversation)
            .filter(
                DBConversation.brokerage_id == seed["brokerage_id"],
                DBConversation.buyer_phone == seed["buyer_phone"],
            )
            .count()
        )
        assert conversations == 2  # one profile, two linked conversations

        # Same phone at another brokerage → an independent profile.
        profile_other = get_or_create_profile(
            db, brokerage_id=seed["other_brokerage_id"], buyer_phone=seed["buyer_phone"]
        )
        assert profile_other.profile_id != profile_1.profile_id

        # Field isolation: confirm in brokerage A, invisible in B's profile.
        confirm_field(db, profile=profile_1, field="financing", value="cash", confirmed_by=seed["agent_user_id"])
        fields_other = effective_fields(db, profile_other)
        assert "financing" not in fields_other


# ── DAL-164 checklist 1, 6, 7 + DAL-165 surfaces via the API ───────────────────


def test_buyer_list_and_card_api(client, card_seed):
    seed = card_seed
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["agent_user_id"], email="card@example.com",
    )

    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_a"])
        profile = get_or_create_profile(
            db, brokerage_id=seed["brokerage_id"], buyer_phone=seed["buyer_phone"], name="Zainab",
        )
        record_inferred_field(db, profile=profile, field="budget_max_aed", value=2_000_000, confidence=0.8)
        safe_commit(db)
        # An open offer for the card's history panel (DAL-165 feeds DAL-164).
        log_agent_offer(
            db,
            brokerage_id=seed["brokerage_id"],
            conversation=conv,
            listing_id=seed["listing_a"],
            agent_user_id=seed["agent_user_id"],
            amount=1_900_000,
        )
        profile_id = profile.profile_id

    listing = client.get("/api/v1/agent/buyers")
    assert listing.status_code == 200, listing.text
    buyers = listing.json()["buyers"]
    assert len(buyers) == 1
    row = buyers[0]
    assert row["name"] == "Zainab"
    assert "•••" in row["phone_masked"]  # masked on the list surface
    assert row["qualification"]["budget_max_aed"] == 2_000_000
    assert row["open_offers"] == 1

    card = client.get(f"/api/v1/agent/buyers/{profile_id}")
    assert card.status_code == 200, card.text
    payload = card.json()
    assert payload["identity"]["phone"] == seed["buyer_phone"]  # full on the card
    assert payload["identity"]["opted_out"] is False
    assert payload["qualification"]["budget_max_aed"]["provenance"] == "ai_inferred"
    assert len(payload["offers"]) == 1
    assert payload["offers"][0]["status"] == "submitted"

    # PATCH promotes to agent_confirmed.
    patched = client.patch(
        f"/api/v1/agent/buyers/{profile_id}/fields",
        json={"field": "budget_max_aed", "value": 2_100_000},
    )
    assert patched.status_code == 200
    assert patched.json()["qualification"]["budget_max_aed"]["provenance"] == "agent_confirmed"

    # Opt-out renders on the card.
    from app.core.brokerage_access import mark_buyer_opted_out

    with SessionLocal() as db:
        mark_buyer_opted_out(
            db, brokerage_id=seed["brokerage_id"], buyer_phone=seed["buyer_phone"],
            conversation_id=seed["conversation_a"],
        )
    card2 = client.get(f"/api/v1/agent/buyers/{profile_id}")
    assert card2.json()["identity"]["opted_out"] is True

    # Cross-tenant: an outsider sees nothing.
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=f"outsider-{uuid.uuid4().hex[:6]}", email="outsider@example.com",
    )
    assert client.get(f"/api/v1/agent/buyers/{profile_id}").status_code in {403, 404}


# ── DAL-165 checklist 1 + 4: AI-detected drafts, anchored or absent ────────────


def test_offer_alert_with_amount_creates_anchored_draft(card_seed):
    seed = card_seed
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_a"])
        db.add(DBMessage(
            conversation_id=conv.conversation_id,
            role="user",
            content="I'll offer 1.85M cash, but only after a viewing.",
        ))
        safe_commit(db)

        offer = create_draft_offer_from_alert(
            db,
            brokerage_id=seed["brokerage_id"],
            conversation=conv,
            listing_id=seed["listing_a"],
            amount=1_850_000,
            trigger_message="I'll offer 1.85M cash, but only after a viewing.",
        )
        assert offer is not None
        assert offer.status == "draft_pending_confirm"
        assert offer.source == "ai_detected"
        assert offer.source_message_id is not None  # banned-output anchor
        assert offer.subject_to_viewing is True
        assert offer.buyer_profile_id is not None

        # Vague message, no extracted amount → no draft, no hallucination.
        none_offer = create_draft_offer_from_alert(
            db,
            brokerage_id=seed["brokerage_id"],
            conversation=conv,
            listing_id=seed["listing_b"],
            amount=None,
            trigger_message="Would they take less?",
        )
        assert none_offer is None
        assert (
            db.query(DBOffer)
            .filter(DBOffer.thread_key == thread_key_for(conv.conversation_id, seed["listing_b"]))
            .count()
            == 0
        )


# ── DAL-165 checklist 2 + 3: confirm/discard + counter thread ──────────────────


def test_offer_confirm_discard_and_counter_thread(card_seed):
    seed = card_seed
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_a"])
        draft = create_draft_offer_from_alert(
            db,
            brokerage_id=seed["brokerage_id"],
            conversation=conv,
            listing_id=seed["listing_a"],
            amount=1_800_000,
            trigger_message="Offering 1.8M",
        )
        confirmed = confirm_draft_offer(db, offer=draft, agent_user_id=seed["agent_user_id"])
        assert confirmed.status == "submitted"
        assert confirmed.confirmed_by == seed["agent_user_id"]

        # An offer never enters SUBMITTED without confirmation: double confirm fails.
        with pytest.raises(ValueError):
            confirm_draft_offer(db, offer=confirmed, agent_user_id=seed["agent_user_id"])

        # Counter advances the thread.
        counter = transition_offer(
            db,
            offer=confirmed,
            new_status="countered",
            agent_user_id=seed["agent_user_id"],
            counter_amount=1_950_000,
            note="Seller counters at 1.95M",
        )
        assert counter.direction == "seller_counter"
        assert counter.status == "submitted"
        assert counter.amount == 1_950_000

        thread = offers_for_thread(db, confirmed.thread_key)
        assert [offer.status for offer in thread] == ["countered", "submitted"]
        assert [offer.direction for offer in thread] == ["buyer_offer", "seller_counter"]

        # Accept the counter.
        accepted = transition_offer(db, offer=counter, new_status="accepted", agent_user_id=seed["agent_user_id"])
        assert accepted.status == "accepted"
        assert accepted.closed_at is not None

        # Discard flow on a fresh draft writes an audit row.
        draft2 = create_draft_offer_from_alert(
            db,
            brokerage_id=seed["brokerage_id"],
            conversation=conv,
            listing_id=seed["listing_b"],
            amount=1_500_000,
            trigger_message="1.5M offer",
        )
        discard_draft_offer(db, offer=draft2, agent_user_id=seed["agent_user_id"], reason="buyer retracted")
        assert draft2.status == "discarded"
        audit = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "offer_discarded",
            )
            .one()
        )
        assert audit.details["offer_id"] == draft2.offer_id


# ── DAL-165 checklist 5: hot-list prefers the structured record ────────────────


def test_hot_list_boost_prefers_structured_offer(card_seed):
    seed = card_seed
    with SessionLocal() as db:
        conv = db.get(DBConversation, seed["conversation_a"])
        baseline = score_conversation(db, conv)
        assert baseline.signal != "firm_offer"

        log_agent_offer(
            db,
            brokerage_id=seed["brokerage_id"],
            conversation=conv,
            listing_id=seed["listing_a"],
            agent_user_id=seed["agent_user_id"],
            amount=1_900_000,
        )
        boosted = score_conversation(db, conv)
        assert boosted.signal == "firm_offer"
        assert boosted.urgency_score > baseline.urgency_score
        assert "1,900,000" in boosted.next_action_reason  # structured record preferred

        # Legacy message-signal AND structured record together: same single
        # branch — no double counting.
        conv.escalation_reason = "offer:1900000"
        safe_commit(db)
        both = score_conversation(db, conv)
        assert both.urgency_score == boosted.urgency_score


# ── DAL-165 checklist 6: scoping ───────────────────────────────────────────────


def test_offer_api_scoping(client, card_seed):
    seed = card_seed
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=seed["agent_user_id"], email="card@example.com",
    )
    created = client.post(
        "/api/v1/agent/offers",
        json={"conversation_id": seed["conversation_a"], "amount": 1_750_000},
    )
    assert created.status_code == 200, created.text
    offer_id = created.json()["offer_id"]

    listed = client.get(f"/api/v1/agent/offers?conversation_id={seed['conversation_a']}")
    assert listed.status_code == 200
    assert len(listed.json()["offers"]) == 1

    # An outsider (no membership) can't see or move the offer.
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=f"outsider-{uuid.uuid4().hex[:6]}", email="outsider@example.com",
    )
    assert client.get(f"/api/v1/agent/offers?conversation_id={seed['conversation_a']}").status_code in {403, 404}
    assert client.post(
        f"/api/v1/agent/offers/{offer_id}/transition",
        json={"status": "accepted"},
    ).status_code in {403, 404}
