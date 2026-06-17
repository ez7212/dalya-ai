from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.google_calendar import CalendarBusyWindow, set_calendar_provider_override
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.core.viewing_logistics import build_logistics_prefill, propose_viewing_slots
from app.db import crud
from app.db.session import Base, SessionLocal, engine, safe_commit
from app.main import app
from app.models.db_models import (
    DBAgentAvailabilityBlock,
    DBAgentProfile,
    DBAgentCalendarConnection,
    DBBrokerage,
    DBBrokerageMember,
    DBBuildingProfile,
    DBComplianceEvent,
    DBConversation,
    DBDraftReply,
    DBListing,
    DBListingLogistics,
    DBLeadAction,
    DBLeadAssignment,
    DBLeadTask,
    DBMessage,
    DBTenantConsent,
    DBTenantViewingConfirmation,
    DBViewing,
    DBViewingFeedback,
)


Base.metadata.create_all(bind=engine)


@pytest.fixture
def viewing_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"viewing-brokerage-{suffix}"
    owner_id = f"viewing-owner-{suffix}"
    agent_id = f"viewing-agent-{suffix}"
    other_agent_id = f"viewing-other-{suffix}"
    listing_id = f"viewing-listing-{suffix}"
    second_listing_id = f"viewing-listing-2-{suffix}"
    building_name = f"Marina Gate Tower 1 {suffix}"
    buyer_phone = f"+97155577{suffix[:4]}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Viewing Brokerage",
            slug=f"viewing-{suffix}",
            status="active",
            brokerage_ai_number=f"+97150000{suffix[:4]}",
            agents_ai_number=f"+97151111{suffix[:4]}",
        ))
        db.add_all([
            DBBrokerageMember(
                brokerage_id=brokerage_id,
                user_id=owner_id,
                email=f"{owner_id}@example.com",
                display_name="Owner",
                role="owner",
                status="active",
            ),
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
        ])
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id,
            user_id=agent_id,
            email=f"{agent_id}@example.com",
            full_name="Viewing Agent",
            display_name="Viewing Agent",
            whatsapp_phone=f"+97152222{suffix[:4]}",
            rera_broker_card_number=f"VIEW-{suffix}",
            verification_status="approved",
            onboarding_status="active",
        ))
        for current_listing_id, unit in [(listing_id, "1204"), (second_listing_id, "1205")]:
            db.add(DBListing(
                listing_id=current_listing_id,
                brokerage_id=brokerage_id,
                assigned_agent_id=agent_id,
                spa_data={
                    "project": "Marina Gate Tower 1",
                    "building_or_project": building_name,
                    "community": "Dubai Marina",
                    "unit_number": unit,
                    "developer": "Select Group",
                    "property_type": "Apartment",
                    "bedrooms": 2,
                    "parking": "1 basement bay",
                    "purchase_price_aed": 3_200_000,
                },
                community="Dubai Marina",
                seller_asking_price=3_400_000,
                negotiation_threshold_aed=3_250_000,
                commission_rate=0.015,
                property_type="ready",
                additional_fees=[],
                seller_qa=[],
                media_urls=[],
                unit_profile={},
                unit_profile_history=[],
                processing_stages={},
            ))
        safe_commit(db)

        conversation = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        conversation.buyer_name = "Sara"
        conversation.assigned_agent_id = agent_id
        conversation.detected_budget = 3_500_000
        conversation.ai_summary = {
            "one_line": "Sara wants a ready Dubai Marina apartment with easy viewing access.",
            "topics": ["parking", "finance", "viewing"],
        }
        db.add(DBMessage(
            conversation_id=conversation.conversation_id,
            role="user",
            content="Can I view this? Parking and finance matter.",
            intent="viewing_request",
        ))
        safe_commit(db)
        conversation_id = conversation.conversation_id

    try:
        yield {
            "brokerage_id": brokerage_id,
            "brokerage_ai_number": f"+97150000{suffix[:4]}",
            "owner_id": owner_id,
            "agent_id": agent_id,
            "other_agent_id": other_agent_id,
            "listing_id": listing_id,
            "second_listing_id": second_listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "building_name": building_name,
        }
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        set_calendar_provider_override(None)
        set_transport_override(None)
        with SessionLocal() as db:
            db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBViewingFeedback).filter(DBViewingFeedback.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBTenantViewingConfirmation).filter(DBTenantViewingConfirmation.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBTenantConsent).filter(DBTenantConsent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBViewing).filter(DBViewing.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBListingLogistics).filter(DBListingLogistics.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentCalendarConnection).filter(DBAgentCalendarConnection.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentAvailabilityBlock).filter(DBAgentAvailabilityBlock.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBDraftReply).filter(DBDraftReply.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadTask).filter(DBLeadTask.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id.in_([listing_id, second_listing_id])).delete(synchronize_session=False)
            db.query(DBBuildingProfile).filter(DBBuildingProfile.display_name == building_name).delete(synchronize_session=False)
            db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerageMember).filter(DBBrokerageMember.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
    )


def test_listing_logistics_creates_building_prefill_consent_and_blocks_raw_lockbox(client, viewing_seed):
    seed = viewing_seed
    _as_user(seed["agent_id"])

    raw_lockbox_response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "keys": {
                "location": "lockbox",
                "lockbox_code": "1234",
            }
        },
    )
    assert raw_lockbox_response.status_code == 400

    response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "access": {
                "type": "security office",
                "noc_required": True,
                "advance_notice_hours": 4,
                "visitor_parking_pass_required": True,
                "buyer_emirates_id_preregistration_required": True,
                "security_office_hours": {"start": "09:00", "end": "17:00"},
            },
            "keys": {
                "location": "front office",
                "key_kit_checklist": ["unit key", "access card", "parking remote"],
            },
            "tenant": {
                "status": "tenanted",
                "name": "Tenant Name",
                "whatsapp_number": "+971500009999",
                "email": "tenant@example.com",
                "preferred_contact_method": "whatsapp",
                "notice_period_hours": 48,
            },
            "owner_permissions": {
                "viewing_restrictions": ["weekdays only"],
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["logistics"]
    assert payload["tenant"]["name"] == "Tenant Name"
    assert payload["access"]["security_office_hours"]["end"] == "17:00"

    with SessionLocal() as db:
        consent = (
            db.query(DBTenantConsent)
            .filter(DBTenantConsent.listing_id == seed["listing_id"])
            .one()
        )
        assert consent.opt_in_status == "pending"
        assert consent.lawful_basis == "listing_viewing_coordination"

        tenant_event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.listing_id == seed["listing_id"],
                DBComplianceEvent.event_type == "tenant_contact_recorded",
            )
            .one()
        )
        assert tenant_event.details["contact_key"] == "+971500009999"

        second_listing = db.get(DBListing, seed["second_listing_id"])
        prefill = build_logistics_prefill(db, second_listing)
        assert prefill["draft"]["access"]["type"] == "security office"
        assert prefill["draft"]["access"]["advance_notice_hours"] == 4
        assert prefill["contributor_count"] == 1


def test_tenant_pii_is_redacted_for_same_brokerage_non_assigned_agent(client, viewing_seed):
    seed = viewing_seed
    _as_user(seed["agent_id"])
    response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "tenant": {
                "status": "tenanted",
                "name": "Tenant Name",
                "whatsapp_number": "+971500009999",
                "email": "tenant@example.com",
                "notice_period_hours": 48,
            },
        },
    )
    assert response.status_code == 200

    _as_user(seed["other_agent_id"])
    redacted = client.get(f"/api/v1/agent/listings/{seed['listing_id']}/logistics")
    assert redacted.status_code == 200, redacted.text
    tenant = redacted.json()["logistics"]["tenant"]
    assert tenant["redacted"] is True
    assert tenant["name"] is None
    assert tenant["whatsapp_number"] is None
    assert tenant["email"] is None

    _as_user(seed["owner_id"])
    owner_view = client.get(f"/api/v1/agent/listings/{seed['listing_id']}/logistics")
    assert owner_view.status_code == 200
    assert owner_view.json()["logistics"]["tenant"]["name"] == "Tenant Name"


def test_availability_calendar_and_slot_proposal_respect_notice_windows(client, viewing_seed):
    seed = viewing_seed
    _as_user(seed["agent_id"])
    logistics_response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "access": {
                "type": "front desk",
                "advance_notice_hours": 4,
                "security_office_hours": {"start": "10:00", "end": "16:00"},
            },
            "tenant": {
                "status": "tenanted",
                "notice_period_hours": 48,
            },
        },
    )
    assert logistics_response.status_code == 200

    weekday = (datetime.utcnow() + timedelta(days=3)).weekday()
    availability_response = client.post(
        "/api/v1/agent/availability-blocks",
        json={
            "block_type": "working_hours",
            "weekday": weekday,
            "start_time": "09:00",
            "end_time": "17:00",
            "recurring": True,
            "metadata_json": {"prep_buffer_minutes": 20},
        },
    )
    assert availability_response.status_code == 200

    calendar_response = client.patch(
        "/api/v1/agent/calendar-connection",
        json={
            "provider": "google",
            "status": "not_connected",
            "selected_calendar_ids": ["primary"],
            "token_ref": "vault:agent-calendar-token",
            "scopes": ["calendar.freebusy", "calendar.events.owned"],
        },
    )
    assert calendar_response.status_code == 200
    assert calendar_response.json()["token_ref"] == "vault:agent-calendar-token"

    proposal = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/viewings/propose",
        json={
            "count": 2,
            "origin_community": "Downtown Dubai",
            "pair_lookup": {"downtown-dubai:dubai-marina": 40},
        },
    )
    assert proposal.status_code == 200, proposal.text
    slots = proposal.json()["slots"]
    assert slots
    first = datetime.fromisoformat(slots[0]["starts_at"])
    assert first >= datetime.utcnow().replace(second=0, microsecond=0) + timedelta(hours=47, minutes=55)
    assert first.hour >= 10
    assert first.hour < 16
    assert slots[0]["buffer_minutes"] >= 40
    assert slots[0]["tenant_notice_required"] is True
    assert "tenant_notice_48h" in slots[0]["constraints"]


def test_core_slot_proposals_apply_rush_hour_multiplier(viewing_seed):
    seed = viewing_seed
    now = datetime.utcnow().replace(hour=7, minute=0, second=0, microsecond=0)
    with SessionLocal() as db:
        listing = db.get(DBListing, seed["listing_id"])
        logistics = DBListingLogistics(
            brokerage_id=seed["brokerage_id"],
            listing_id=seed["listing_id"],
            agent_user_id=seed["agent_id"],
            access={"security_office_hours": {"start": "07:30", "end": "10:00"}},
            tenant={"status": "vacant"},
        )
        db.add(logistics)
        db.add(DBAgentAvailabilityBlock(
            brokerage_id=seed["brokerage_id"],
            agent_user_id=seed["agent_id"],
            block_type="working_hours",
            weekday=now.weekday(),
            start_time="07:30",
            end_time="10:00",
            recurring=True,
            metadata_json={"prep_buffer_minutes": 15},
        ))
        safe_commit(db)

        slots = propose_viewing_slots(
            db,
            brokerage_id=seed["brokerage_id"],
            agent_user_id=seed["agent_id"],
            listing=listing,
            logistics=logistics,
            now=now,
            origin_community="Downtown Dubai",
            pair_lookup={"downtown-dubai:dubai-marina": 40},
        )
        assert slots
        assert slots[0].buffer_minutes == 54


class FakeCalendarProvider:
    def __init__(self):
        self.freebusy_calls = []
        self.upserts = []
        self.deletes = []

    def freebusy(self, connection, *, time_min, time_max):
        self.freebusy_calls.append((connection.connection_id, time_min, time_max))
        return [
            CalendarBusyWindow(
                starts_at=time_min + timedelta(hours=2),
                ends_at=time_min + timedelta(hours=3),
                calendar_id="primary",
            )
        ]

    def upsert_viewing_event(
        self,
        connection,
        *,
        viewing,
        listing,
        conversation,
        scheduled_for,
        duration_minutes=45,
        existing_event_id=None,
    ):
        self.upserts.append(
            {
                "viewing_id": viewing.viewing_id,
                "scheduled_for": scheduled_for,
                "existing_event_id": existing_event_id,
                "duration_minutes": duration_minutes,
            }
        )
        return {
            "provider": "google",
            "calendar_id": "primary",
            "event_id": existing_event_id or "google-event-1",
            "html_link": "https://calendar.google.test/event",
            "status": "confirmed",
            "synced_at": datetime.utcnow().isoformat(),
        }

    def delete_viewing_event(self, connection, *, event_id, calendar_id=None):
        self.deletes.append({"event_id": event_id, "calendar_id": calendar_id})
        return {
            "provider": "google",
            "calendar_id": calendar_id or "primary",
            "event_id": event_id,
            "deleted_at": datetime.utcnow().isoformat(),
        }


def test_google_calendar_freebusy_write_update_and_cancel(client, viewing_seed):
    seed = viewing_seed
    fake = FakeCalendarProvider()
    set_calendar_provider_override(fake)
    _as_user(seed["agent_id"])

    connection = client.patch(
        "/api/v1/agent/calendar-connection",
        json={
            "provider": "google",
            "status": "connected",
            "selected_calendar_ids": ["primary"],
            "token_ref": "env:TEST_GOOGLE_CALENDAR_TOKEN",
            "scopes": ["calendar.freebusy", "calendar.events.owned"],
        },
    )
    assert connection.status_code == 200, connection.text

    proposal = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/viewings/propose",
        json={"count": 1},
    )
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["calendar"]["status"] == "connected"
    assert proposal.json()["calendar"]["busy_count"] == 1
    assert fake.freebusy_calls

    viewing_id = proposal.json()["viewing_id"]
    scheduled_for = datetime.fromisoformat(proposal.json()["slots"][0]["starts_at"])
    confirm = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/confirm",
        json={"scheduled_for": scheduled_for.isoformat(), "duration_minutes": 60},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["metadata"]["confirmation_status"]["calendar"] == "synced"
    assert confirm.json()["metadata"]["calendar_event"]["event_id"] == "google-event-1"
    assert fake.upserts[-1]["existing_event_id"] is None
    assert fake.upserts[-1]["duration_minutes"] == 60

    updated_for = scheduled_for + timedelta(hours=1)
    updated = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/confirm",
        json={"scheduled_for": updated_for.isoformat(), "duration_minutes": 60},
    )
    assert updated.status_code == 200, updated.text
    assert fake.upserts[-1]["existing_event_id"] == "google-event-1"
    assert updated.json()["metadata"]["calendar_event"]["event_id"] == "google-event-1"

    cancelled = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/cancel",
        json={"reason": "Buyer requested a new day"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["confirmation_status"]["calendar"] == "deleted"
    assert fake.deletes[-1]["event_id"] == "google-event-1"


def test_viewing_confirmation_and_brief(client, viewing_seed):
    seed = viewing_seed
    _as_user(seed["agent_id"])
    logistics_response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "access": {"type": "front desk", "visitor_parking_pass_required": True},
            "keys": {"location": "front office", "key_kit_checklist": ["unit key", "access card"]},
            "tenant": {"status": "vacant"},
        },
    )
    assert logistics_response.status_code == 200
    proposal = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/viewings/propose",
        json={"count": 1},
    )
    assert proposal.status_code == 200, proposal.text
    viewing_id = proposal.json()["viewing_id"]
    scheduled_for = proposal.json()["slots"][0]["starts_at"]

    confirm_response = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/confirm",
        json={"scheduled_for": scheduled_for},
    )
    assert confirm_response.status_code == 200, confirm_response.text
    assert confirm_response.json()["status"] == "confirmed"
    assert confirm_response.json()["metadata"]["confirmation_status"]["calendar"] == "not_connected"

    brief_response = client.get(f"/api/v1/agent/viewings/{viewing_id}/brief")
    assert brief_response.status_code == 200, brief_response.text
    brief = brief_response.json()
    assert brief["buyer_profile"]["name"] == "Sara"
    assert "parking" in brief["buyer_profile"]["stated_priorities"]
    assert brief["logistics"]["access_type"] == "front desk"
    assert brief["logistics"]["key_location"] == "front office"
    assert brief["property"]["project"] == "Marina Gate Tower 1"


def test_viewing_list_detail_notification_drafts_status_and_tenant_reply(client, viewing_seed, monkeypatch):
    seed = viewing_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    _as_user(seed["agent_id"])
    logistics_response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "access": {
                "type": "front desk",
                "visitor_parking_pass_required": True,
                "security_office_hours": {"start": "09:00", "end": "17:00"},
            },
            "keys": {"location": "agent has", "key_kit_checklist": ["unit key"]},
            "tenant": {
                "status": "tenanted",
                "name": "Tenant Name",
                "whatsapp_number": "+971500009999",
                "notice_period_hours": 48,
            },
        },
    )
    assert logistics_response.status_code == 200
    proposal = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/viewings/propose",
        json={"count": 1},
    )
    assert proposal.status_code == 200, proposal.text
    viewing_id = proposal.json()["viewing_id"]
    scheduled_for = proposal.json()["slots"][0]["starts_at"]

    confirm_response = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/confirm",
        json={"scheduled_for": scheduled_for},
    )
    assert confirm_response.status_code == 200

    listed = client.get("/api/v1/agent/viewings")
    assert listed.status_code == 200, listed.text
    rows = listed.json()["viewings"]
    assert any(row["viewing_id"] == viewing_id for row in rows)

    detail = client.get(f"/api/v1/agent/viewings/{viewing_id}")
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["buyer"]["name"] == "Sara"
    assert detail_payload["listing"]["project"] == "Marina Gate Tower 1"
    assert detail_payload["logistics_summary"]["tenant_status"] == "tenanted"

    drafts = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/notification-drafts",
        json={},
    )
    assert drafts.status_code == 200, drafts.text
    draft_payload = drafts.json()
    assert draft_payload["auto_sent"] is False
    draft_types = {draft["type"] for draft in draft_payload["drafts"]}
    assert {
        "buyer_confirmation_t24",
        "buyer_reminder_t1",
        "tenant_notice",
        "running_late",
        "reschedule",
    }.issubset(draft_types)
    tenant_notice = next(d for d in draft_payload["drafts"] if d["type"] == "tenant_notice")
    assert tenant_notice["recipient"] == "+971500009999"
    assert "48 hours" in tenant_notice["body"]
    running_late = next(d for d in draft_payload["drafts"] if d["type"] == "running_late")
    assert "10 minutes late" in running_late["body"]

    buyer_confirmation_send = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/notifications/buyer_confirmation_t24/send",
        json={},
    )
    assert buyer_confirmation_send.status_code == 200, buyer_confirmation_send.text
    assert buyer_confirmation_send.json()["confirmation_status"]["buyer"] == "notice_sent"
    assert any(
        msg.direction == "to_buyer"
        and msg.to_number == seed["buyer_phone"]
        and "confirming your viewing" in msg.body
        for msg in transport.outbox
    )

    send_tenant = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/tenant-notice/send",
        json={},
    )
    assert send_tenant.status_code == 200, send_tenant.text
    tenant_payload = send_tenant.json()
    assert tenant_payload["tenant_confirmation"]["status"] == "notice_sent"
    assert tenant_payload["confirmation_status"]["tenant"] == "notice_sent"
    assert any(
        msg.direction == "to_buyer"
        and msg.to_number == "+971500009999"
        and "Please confirm whether this time works" in msg.body
        for msg in transport.outbox
    )

    reschedule_send = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/notifications/reschedule/send",
        json={},
    )
    assert reschedule_send.status_code == 200, reschedule_send.text
    assert reschedule_send.json()["confirmation_status"]["reschedule"] == "sent"
    reschedule_messages = [
        msg for msg in transport.outbox
        if msg.direction == "to_buyer" and "need to reschedule" in msg.body
    ]
    assert {msg.to_number for msg in reschedule_messages}.issuperset({seed["buyer_phone"], "+971500009999"})

    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")
    tenant_reply = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "From": "whatsapp:+971500009999",
            "To": f"whatsapp:{seed['brokerage_ai_number']}",
            "Body": "Confirmed, this time works.",
            "MessageSid": f"tenant-reply-{uuid.uuid4().hex[:8]}",
            "NumMedia": "0",
        },
    )
    assert tenant_reply.status_code == 200, tenant_reply.text

    after_reply = client.get(f"/api/v1/agent/viewings/{viewing_id}")
    assert after_reply.status_code == 200
    assert after_reply.json()["confirmation_status"]["tenant"] == "confirmed"
    assert after_reply.json()["tenant_confirmation"]["status"] == "confirmed"
    assert "Confirmed" in after_reply.json()["tenant_confirmation"]["last_inbound_body"]
    assert any(msg.direction == "to_agents_ai" and msg.escalation_type == "tenant_viewing_reply" for msg in transport.outbox)

    status_update = client.patch(
        f"/api/v1/agent/viewings/{viewing_id}/confirmation-status",
        json={"buyer": "confirmed", "tenant": "draft_sent", "calendar": "provider_pending"},
    )
    assert status_update.status_code == 200
    assert status_update.json()["confirmation_status"]["buyer"] == "confirmed"

    updated_detail = client.get(f"/api/v1/agent/viewings/{viewing_id}")
    assert updated_detail.status_code == 200
    assert updated_detail.json()["confirmation_status"]["tenant"] == "draft_sent"
    assert len(updated_detail.json()["notification_drafts"]) >= 5

    complete_response = client.post(f"/api/v1/agent/viewings/{viewing_id}/complete")
    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json()["status"] == "completed"

    with SessionLocal() as db:
        assert (
            db.query(DBLeadTask)
            .filter(DBLeadTask.task_key == f"post-viewing-feedback:{viewing_id}")
            .first()
            is not None
        )
        assert (
            db.query(DBDraftReply)
            .filter(
                DBDraftReply.conversation_id == seed["conversation_id"],
                DBDraftReply.intent == "post_viewing_feedback",
            )
            .first()
            is not None
        )
        events = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type.in_([
                    "viewing_notification_drafts_generated",
                    "viewing_confirmation_status_updated",
                    "viewing_notification_sent",
                    "tenant_viewing_notice_sent",
                    "tenant_viewing_reply_received",
                    "viewing_completed",
                ]),
            )
            .all()
        )
        assert {
            "viewing_notification_drafts_generated",
            "viewing_confirmation_status_updated",
            "viewing_notification_sent",
            "tenant_viewing_notice_sent",
            "tenant_viewing_reply_received",
            "viewing_completed",
        }.issubset({event.event_type for event in events})


def test_post_viewing_feedback_request_reply_and_agent_capture(client, viewing_seed, monkeypatch):
    seed = viewing_seed
    transport = SimulatedTransport()
    set_transport_override(transport)
    _as_user(seed["agent_id"])

    logistics_response = client.patch(
        f"/api/v1/agent/listings/{seed['listing_id']}/logistics",
        json={
            "access": {"type": "front desk"},
            "keys": {"location": "agent has"},
            "tenant": {"status": "vacant"},
        },
    )
    assert logistics_response.status_code == 200
    proposal = client.post(
        f"/api/v1/agent/leads/{seed['conversation_id']}/viewings/propose",
        json={"count": 1},
    )
    assert proposal.status_code == 200, proposal.text
    viewing_id = proposal.json()["viewing_id"]
    scheduled_for = datetime.utcnow() - timedelta(hours=6)

    confirm_response = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/confirm",
        json={"scheduled_for": scheduled_for.isoformat(), "duration_minutes": 45},
    )
    assert confirm_response.status_code == 200, confirm_response.text

    complete_response = client.post(f"/api/v1/agent/viewings/{viewing_id}/complete")
    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json()["post_viewing"]["status"] == "not_requested"

    request_due = client.post("/api/v1/agent/viewings/post-viewing/request-due", json={})
    assert request_due.status_code == 200, request_due.text
    assert request_due.json()["requested_count"] == 1
    assert any(
        msg.direction == "to_buyer"
        and msg.to_number == seed["buyer_phone"]
        and "How did it feel on a 1-10 scale" in msg.body
        for msg in transport.outbox
    )
    assert any(msg.direction == "to_agents_ai" and msg.escalation_type == "post_viewing_feedback" for msg in transport.outbox)

    detail_after_request = client.get(f"/api/v1/agent/viewings/{viewing_id}")
    assert detail_after_request.status_code == 200
    assert detail_after_request.json()["status"] == "feedback_requested"
    assert detail_after_request.json()["post_viewing"]["buyer"]["status"] == "requested"

    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")
    buyer_reply = client.post(
        "/api/v1/whatsapp/webhook",
        data={
            "From": f"whatsapp:{seed['buyer_phone']}",
            "To": f"whatsapp:{seed['brokerage_ai_number']}",
            "Body": "9/10, loved the view and layout. Interested to discuss an offer.",
            "MessageSid": f"post-viewing-buyer-{uuid.uuid4().hex[:8]}",
            "NumMedia": "0",
        },
    )
    assert buyer_reply.status_code == 200, buyer_reply.text

    agent_feedback = client.post(
        f"/api/v1/agent/viewings/{viewing_id}/feedback/agent",
        json={
            "raw_body": "Buyer is hot, cash ready, wants to negotiate an offer today.",
            "score": 9,
            "temperature": "hot",
            "financing_status": "cash",
            "next_action": "discuss_offer",
        },
    )
    assert agent_feedback.status_code == 200, agent_feedback.text
    assert agent_feedback.json()["post_viewing"]["status"] == "completed"

    final_detail = client.get(f"/api/v1/agent/viewings/{viewing_id}")
    assert final_detail.status_code == 200
    payload = final_detail.json()
    assert payload["status"] == "feedback_completed"
    assert payload["post_viewing"]["buyer"]["score"] == 9
    assert payload["post_viewing"]["buyer"]["next_action"] == "discuss_offer"
    assert payload["post_viewing"]["agent"]["temperature"] == "hot"

    with SessionLocal() as db:
        buyer_feedback = (
            db.query(DBViewingFeedback)
            .filter(
                DBViewingFeedback.viewing_id == viewing_id,
                DBViewingFeedback.participant_type == "buyer",
            )
            .first()
        )
        assert buyer_feedback is not None
        assert buyer_feedback.status == "received"
        assert buyer_feedback.structured_json["offer_interest"] is True
        assignment = (
            db.query(DBLeadAssignment)
            .filter(DBLeadAssignment.conversation_id == seed["conversation_id"])
            .first()
        )
        assert assignment is not None
        assert assignment.next_action == "discuss_offer"
        assert assignment.signal == "post_viewing_hot"
        assert (
            db.query(DBLeadTask)
            .filter(DBLeadTask.task_key == f"post-viewing-next-action:{viewing_id}")
            .first()
            is not None
        )
        original_task = (
            db.query(DBLeadTask)
            .filter(DBLeadTask.task_key == f"post-viewing-feedback:{viewing_id}")
            .first()
        )
        assert original_task is not None
        assert original_task.status == "done"
        event_types = {
            event.event_type
            for event in db.query(DBComplianceEvent)
            .filter(DBComplianceEvent.brokerage_id == seed["brokerage_id"])
            .all()
        }
        assert "post_viewing_feedback_requested" in event_types
        assert "post_viewing_buyer_feedback_received" in event_types
        assert "post_viewing_agent_feedback_received" in event_types
