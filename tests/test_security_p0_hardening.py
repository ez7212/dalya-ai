from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.messaging import set_transport_override
from app.core.messaging.factory import get_transport
from app.core.pii_redaction import redact_pii
from app.db.session import SessionLocal, safe_commit
from app.main import app
from app.models.db_models import (
    DBBrokerage,
    DBBrokerageMember,
    DBConversation,
    DBInboundProviderEvent,
    DBListing,
    DBMessageQueue,
)


def _twilio_form(message_sid: str, body: str = "Hello") -> dict:
    return {
        "From": "whatsapp:+971501234567",
        "To": "whatsapp:+971500000001",
        "Body": body,
        "MessageSid": message_sid,
        "NumMedia": "0",
    }


def test_debug_routes_are_blocked_in_production(client, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("ENABLE_PRODUCTION_DEBUG_ROUTES", raising=False)

    assert client.get("/admin-dashboard").status_code == 404
    assert client.get("/api/v1/parse-spa/does-not-exist").status_code == 404
    assert client.post(
        "/api/v1/whatsapp/send-test",
        params={
            "listing_id": "listing",
            "buyer_phone": "+971501234567",
            "message": "hello",
        },
    ).status_code == 404


def test_debug_routes_stay_blocked_when_production_debug_flag_is_set(client, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.setenv("ENABLE_PRODUCTION_DEBUG_ROUTES", "true")

    assert client.get("/admin-dashboard").status_code == 404
    assert client.post(
        "/api/v1/whatsapp/send-test",
        params={
            "listing_id": "listing",
            "buyer_phone": "+971501234567",
            "message": "hello",
        },
    ).status_code == 404


def test_missing_environment_marker_defaults_to_production_safety(client, monkeypatch):
    monkeypatch.delenv("DALYA_ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "true")

    assert client.get("/admin-dashboard").status_code == 404


def test_health_hides_internal_checks_in_production(client, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")

    response = client.get("/health")

    assert response.status_code == 200
    assert "checks" not in response.json()


def test_whatsapp_webhook_fails_closed_without_token_in_production(client, monkeypatch):
    import app.api.whatsapp as whatsapp_api

    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.setattr(whatsapp_api, "TWILIO_AUTH_TOKEN", "")

    response = client.post("/api/v1/whatsapp/webhook", data=_twilio_form("prod-missing-token"))

    assert response.status_code == 503
    assert "verification is not configured" in response.text


def test_lead_ingest_fails_closed_without_secret_in_production(client, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("LEAD_INGEST_SECRET", raising=False)

    response = client.post(
        "/api/v1/leads/ingest/email",
        json={"to": "leads+missing@dalya.ai", "body": "Phone: +971501234567"},
    )

    assert response.status_code == 503
    assert "verification is not configured" in response.text


def test_lead_ingest_replays_are_idempotent(client, monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("LEAD_INGEST_SECRET", "test-secret")
    provider_event_id = f"lead-event-{uuid.uuid4().hex}"
    payload = {
        "to": f"leads+missing-{provider_event_id}@dalya.ai",
        "body": f"Phone: +971501234567\nReference: {provider_event_id}",
    }

    first = client.post(
        "/api/v1/leads/ingest/email",
        headers={
            "x-ingest-secret": "test-secret",
            "x-provider": "mailgun",
            "x-provider-event-id": provider_event_id,
        },
        json=payload,
    )
    second = client.post(
        "/api/v1/leads/ingest/email",
        headers={
            "x-ingest-secret": "test-secret",
            "x-provider": "mailgun",
            "x-provider-event-id": provider_event_id,
        },
        json=payload,
    )

    assert first.status_code == 404
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    with SessionLocal() as db:
        event = (
            db.query(DBInboundProviderEvent)
            .filter_by(provider="mailgun", provider_event_id=provider_event_id)
            .first()
        )
        assert event is not None
        assert event.replay_count == 1
        assert event.status == "processed"


def test_twilio_stale_processing_event_can_retry_after_crash_window(client, monkeypatch):
    import app.api.whatsapp as whatsapp_api

    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setattr(whatsapp_api, "TWILIO_AUTH_TOKEN", "")
    message_sid = f"SM{uuid.uuid4().hex}"

    with SessionLocal() as db:
        db.query(DBMessageQueue).filter(DBMessageQueue.message_sid == message_sid).delete()
        db.query(DBInboundProviderEvent).filter(
            DBInboundProviderEvent.provider == "twilio",
            DBInboundProviderEvent.provider_event_id == message_sid,
        ).delete()
        db.add(
            DBInboundProviderEvent(
                provider="twilio",
                endpoint="whatsapp/webhook",
                provider_event_id=message_sid,
                payload_fingerprint=f"stale-processing-test-{message_sid}",
                status="processing",
                received_at=datetime.utcnow() - timedelta(minutes=10),
            )
        )
        safe_commit(db)

    retry = client.post("/api/v1/whatsapp/webhook", data=_twilio_form(message_sid))
    duplicate = client.post("/api/v1/whatsapp/webhook", data=_twilio_form(message_sid))

    assert retry.status_code == 200
    assert duplicate.status_code == 200
    with SessionLocal() as db:
        assert db.query(DBMessageQueue).filter_by(message_sid=message_sid).count() == 1
        event = (
            db.query(DBInboundProviderEvent)
            .filter_by(provider="twilio", provider_event_id=message_sid)
            .first()
        )
        assert event is not None
        assert event.status == "processed"
        assert event.replay_count == 2


def test_lead_ingest_failed_event_can_retry(client, monkeypatch):
    import app.api.leads as leads_api

    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setenv("LEAD_INGEST_SECRET", "test-secret")
    provider_event_id = f"lead-failure-{uuid.uuid4().hex}"
    payload = {
        "to": f"leads+missing-{provider_event_id}@dalya.ai",
        "body": f"Phone: +971501234567\nReference: {provider_event_id}",
    }
    original_ingest = leads_api.ingest_lead_email

    def _explode(*args, **kwargs):
        raise RuntimeError("simulated post-ledger failure")

    monkeypatch.setattr(leads_api, "ingest_lead_email", _explode)
    with pytest.raises(RuntimeError, match="simulated post-ledger failure"):
        client.post(
            "/api/v1/leads/ingest/email",
            headers={
                "x-ingest-secret": "test-secret",
                "x-provider": "mailgun",
                "x-provider-event-id": provider_event_id,
            },
            json=payload,
        )

    with SessionLocal() as db:
        event = (
            db.query(DBInboundProviderEvent)
            .filter_by(provider="mailgun", provider_event_id=provider_event_id)
            .first()
        )
        assert event is not None
        assert event.status == "failed"

    monkeypatch.setattr(leads_api, "ingest_lead_email", original_ingest)

    retry = client.post(
        "/api/v1/leads/ingest/email",
        headers={
            "x-ingest-secret": "test-secret",
            "x-provider": "mailgun",
            "x-provider-event-id": provider_event_id,
        },
        json=payload,
    )

    assert retry.status_code == 404
    with SessionLocal() as db:
        event = (
            db.query(DBInboundProviderEvent)
            .filter_by(provider="mailgun", provider_event_id=provider_event_id)
            .first()
        )
        assert event.status == "processed"
        assert event.replay_count >= 1


def test_twilio_message_sid_replay_is_idempotent(client, monkeypatch):
    import app.api.whatsapp as whatsapp_api

    monkeypatch.setenv("DALYA_ENV", "test")
    monkeypatch.setattr(whatsapp_api, "TWILIO_AUTH_TOKEN", "")
    message_sid = f"SM{uuid.uuid4().hex}"

    with SessionLocal() as db:
        db.query(DBMessageQueue).filter(DBMessageQueue.message_sid == message_sid).delete()
        db.query(DBInboundProviderEvent).filter(
            DBInboundProviderEvent.provider == "twilio",
            DBInboundProviderEvent.provider_event_id == message_sid,
        ).delete()
        safe_commit(db)

    first = client.post("/api/v1/whatsapp/webhook", data=_twilio_form(message_sid))
    second = client.post("/api/v1/whatsapp/webhook", data=_twilio_form(message_sid))

    assert first.status_code == 200
    assert second.status_code == 200
    with SessionLocal() as db:
        assert db.query(DBMessageQueue).filter_by(message_sid=message_sid).count() == 1
        event = (
            db.query(DBInboundProviderEvent)
            .filter_by(provider="twilio", provider_event_id=message_sid)
            .first()
        )
        assert event is not None
        assert event.replay_count == 1


def test_redact_pii_removes_buyer_phone_email_and_long_tokens():
    value = "Buyer +971 50 123 4567 emailed sara@example.com with token abcdef1234567890abcdef12"

    redacted = redact_pii(value)

    assert "+971" not in redacted
    assert "sara@example.com" not in redacted
    assert "abcdef1234567890abcdef12" not in redacted
    assert "[redacted phone]" in redacted
    assert "[redacted email]" in redacted
    assert "[redacted token]" in redacted


def test_production_blocks_simulated_and_dialog360_transports(monkeypatch):
    monkeypatch.setenv("DALYA_ENV", "production")
    set_transport_override(None)
    try:
        monkeypatch.setenv("MESSAGING_TRANSPORT", "simulated")
        with pytest.raises(RuntimeError, match="Simulated messaging transport"):
            get_transport()

        set_transport_override(None)
        monkeypatch.setenv("MESSAGING_TRANSPORT", "dialog360")
        with pytest.raises(RuntimeError, match="360dialog"):
            get_transport()
    finally:
        set_transport_override(None)


def test_production_twilio_transport_requires_credentials(monkeypatch):
    from app.core.messaging.twilio_transport import TwilioTransport

    monkeypatch.setenv("DALYA_ENV", "production")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="TWILIO_ACCOUNT_SID"):
        TwilioTransport()


def test_cross_tenant_lead_detail_is_not_visible_and_share_target_must_be_member(client):
    suffix = uuid.uuid4().hex[:8]
    brokerage_a = f"sec-a-{suffix}"
    brokerage_b = f"sec-b-{suffix}"
    owner_user = f"owner-{suffix}"
    outsider_user = f"outsider-{suffix}"
    listing_b = f"listing-b-{suffix}"
    conversation_b = f"conversation-b-{suffix}"

    with SessionLocal() as db:
        db.add_all([
            DBBrokerage(brokerage_id=brokerage_a, name="Security A", slug=brokerage_a, status="active"),
            DBBrokerage(brokerage_id=brokerage_b, name="Security B", slug=brokerage_b, status="active"),
            DBBrokerageMember(
                brokerage_id=brokerage_a,
                user_id=owner_user,
                role="owner",
                status="active",
            ),
            DBListing(
                listing_id=listing_b,
                brokerage_id=brokerage_b,
                spa_data={"project": "Tenant B", "unit_number": "B-1"},
                seller_asking_price=1_500_000,
                commission_rate=0.01,
                property_type="ready",
            ),
            DBConversation(
                conversation_id=conversation_b,
                listing_id=listing_b,
                brokerage_id=brokerage_b,
                buyer_phone="+971509999999",
            ),
        ])
        safe_commit(db)

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=owner_user,
        email=f"{owner_user}@example.com",
    )
    try:
        hidden = client.get(f"/api/v1/agent/leads/{conversation_b}")
        assert hidden.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # Same tenant conversation: owner can see it, but cannot share to a non-member.
    listing_a = f"listing-a-{suffix}"
    conversation_a = f"conversation-a-{suffix}"
    with SessionLocal() as db:
        db.add_all([
            DBListing(
                listing_id=listing_a,
                brokerage_id=brokerage_a,
                spa_data={"project": "Tenant A", "unit_number": "A-1"},
                seller_asking_price=1_700_000,
                commission_rate=0.01,
                property_type="ready",
            ),
            DBConversation(
                conversation_id=conversation_a,
                listing_id=listing_a,
                brokerage_id=brokerage_a,
                buyer_phone="+971508888888",
            ),
        ])
        safe_commit(db)

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=owner_user,
        email=f"{owner_user}@example.com",
    )
    try:
        response = client.post(
            f"/api/v1/agent/leads/{conversation_a}/shares",
            json={"agent_user_id": outsider_user, "access_level": "viewer"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
