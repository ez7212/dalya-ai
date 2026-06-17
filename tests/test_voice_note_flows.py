"""
DAL-159 — Voice note handling in buyer + agent flows.

Covers the spec verification checklist:
  1. Inbound buyer voice note → transcribed → fed to the concierge as text,
     transcription stored on the message record.
  2. Arabic voice note → language detected and stored (RTL render handled via
     dir="auto" on the dashboard timeline).
  3. Transcription failure → one polite fallback, media_unprocessable
     escalation, no AI answer attempted — never silent.
  4. Agent voice reply (high confidence) → text delivered to buyer + echo.
  5. Agent voice reply (low confidence) → held; SEND releases it.
  6. Voice note bundles with surrounding text in the debounce window.
  7. Duplicate webhook MessageSid on a media message handled idempotently.
  8. Provider failover: forced primary failure → fallback used and recorded.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.core.agent_relay import handle_agent_send_keyword, relay_agent_reply
from app.core.debounce_worker import (
    MEDIA_FALLBACK_EN,
    _handle_batch,
    _prepare_voice_inbound,
)
from app.core.messaging import set_transport_override
from app.core.messaging.simulated_transport import SimulatedTransport
from app.core.transcription.models import (
    AudioInput,
    LowConfidenceSegment,
    ProviderTranscript,
    TranscriptionResult,
)
from app.core.transcription.service import TranscriptionService
from app.db import crud
from app.db.session import SessionLocal, safe_commit
from app.models.db_models import (
    DBAgentMessageRoute,
    DBAgentProfile,
    DBAgentVoiceReplyHold,
    DBBrokerage,
    DBComplianceEvent,
    DBConversation,
    DBEscalationThread,
    DBEscalationThreadQuestion,
    DBLeadAction,
    DBLeadAssignment,
    DBLeadTask,
    DBListing,
    DBMessage,
    DBMessageQueue,
)


def _fake_result(
    transcript: str,
    *,
    language: str = "en",
    confidence: float | None = 0.95,
    provider: str = "speechmatics",
    low_segments: list[LowConfidenceSegment] | None = None,
) -> TranscriptionResult:
    return TranscriptionResult(
        provider=provider,
        raw_transcript=transcript,
        corrected_transcript=transcript,
        language=language,
        confidence=confidence,
        low_confidence_segments=low_segments or [],
    )


@pytest.fixture
def voice_seed():
    suffix = uuid.uuid4().hex[:8]
    brokerage_id = f"vox-brokerage-{suffix}"
    listing_id = f"vox-listing-{suffix}"
    buyer_phone = f"+97156633{suffix[:4]}"
    agent_phone = f"+97157733{suffix[:4]}"
    brokerage_ai_number = f"+97158833{suffix[:4]}"
    agents_ai_number = f"+97159933{suffix[:4]}"
    agent_user_id = f"vox-agent-{suffix}"
    token = f"V{suffix.upper()}"

    with SessionLocal() as db:
        db.add(DBBrokerage(
            brokerage_id=brokerage_id,
            name="Voice Brokerage",
            slug=f"vox-{suffix}",
            status="active",
            brokerage_ai_number=brokerage_ai_number,
            agents_ai_number=agents_ai_number,
        ))
        db.add(DBAgentProfile(
            brokerage_id=brokerage_id,
            user_id=agent_user_id,
            full_name="Voice Agent",
            display_name="Voice Agent",
            whatsapp_phone=agent_phone,
            rera_broker_card_number=f"BRN-VOX-{suffix}",
        ))
        db.add(DBListing(
            listing_id=listing_id,
            brokerage_id=brokerage_id,
            assigned_agent_id=agent_user_id,
            spa_data={
                "project": "Voice Heights",
                "unit_number": "808",
                "developer": "Emaar",
                "property_type": "Apartment",
                "bedrooms": 2,
                "purchase_price_aed": 2_000_000,
            },
            seller_asking_price=2_000_000,
            negotiation_threshold_aed=1_900_000,
            commission_rate=0.02,
            property_type="ready",
            additional_fees=[],
            seller_qa=[],
            media_urls=[],
            unit_profile={},
            unit_profile_history=[],
            processing_stages={},
        ))
        safe_commit(db)
        conv = crud.get_or_create_conversation(db, buyer_phone, listing_id)
        conv.buyer_name = "Fatima"
        db.add(DBAgentMessageRoute(
            brokerage_id=brokerage_id,
            conversation_id=conv.conversation_id,
            listing_id=listing_id,
            buyer_phone=buyer_phone,
            agent_user_id=agent_user_id,
            agent_phone=agent_phone,
            agents_ai_envelope_token=token,
            escalation_type="info_gap",
            tags=["info_gap"],
            expires_at=datetime.utcnow() + timedelta(days=7),
        ))
        safe_commit(db)
        conversation_id = conv.conversation_id

    transport = SimulatedTransport()
    set_transport_override(transport)

    try:
        yield {
            "brokerage_id": brokerage_id,
            "listing_id": listing_id,
            "conversation_id": conversation_id,
            "buyer_phone": buyer_phone,
            "agent_phone": agent_phone,
            "brokerage_ai_number": brokerage_ai_number,
            "agents_ai_number": agents_ai_number,
            "agent_user_id": agent_user_id,
            "token": token,
            "transport": transport,
        }
    finally:
        set_transport_override(None)
        with SessionLocal() as db:
            from app.models.db_models import DBAgentNotification, DBAgentRelaySession, DBRelayOutboxItem

            db.query(DBComplianceEvent).filter(DBComplianceEvent.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentNotification).filter(DBAgentNotification.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBRelayOutboxItem).filter(DBRelayOutboxItem.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentRelaySession).filter(DBAgentRelaySession.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBAgentVoiceReplyHold).filter(DBAgentVoiceReplyHold.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBLeadAction).filter(DBLeadAction.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadTask).filter(DBLeadTask.conversation_id == conversation_id).delete(synchronize_session=False)
            thread_ids = [
                row.thread_id
                for row in db.query(DBEscalationThread.thread_id)
                .filter(DBEscalationThread.brokerage_id == brokerage_id)
                .all()
            ]
            if thread_ids:
                db.query(DBEscalationThreadQuestion).filter(
                    DBEscalationThreadQuestion.thread_id.in_(thread_ids)
                ).delete(synchronize_session=False)
            db.query(DBAgentMessageRoute).filter(DBAgentMessageRoute.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBEscalationThread).filter(DBEscalationThread.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBMessageQueue).filter(
                DBMessageQueue.from_number.in_([buyer_phone, agent_phone])
            ).delete(synchronize_session=False)
            db.query(DBMessage).filter(DBMessage.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBLeadAssignment).filter(DBLeadAssignment.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBConversation).filter(DBConversation.conversation_id == conversation_id).delete(synchronize_session=False)
            db.query(DBListing).filter(DBListing.listing_id == listing_id).delete(synchronize_session=False)
            db.query(DBAgentProfile).filter(DBAgentProfile.brokerage_id == brokerage_id).delete(synchronize_session=False)
            db.query(DBBrokerage).filter(DBBrokerage.brokerage_id == brokerage_id).delete(synchronize_session=False)
            safe_commit(db)


# ── Checklist 1 + 2: buyer voice → transcript body + stored fields ─────────────


def test_buyer_voice_note_produces_transcript_body_and_storage_fields(voice_seed, monkeypatch):
    seed = voice_seed
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result("Is the unit still available for viewing this week?"),
    )

    body, metadata = asyncio.run(_prepare_voice_inbound(
        combined_body="",
        listing_id=seed["listing_id"],
        media_urls=[],
        media_content_types=[],
        metadata_items=[{"audio_path": "/tmp/fake-voice.ogg", "content_type": "audio/ogg"}],
    ))

    assert body == "Is the unit still available for viewing this week?"
    voice_note = metadata["voice_note"]
    assert voice_note["transcription_text"] == body
    assert voice_note["transcription_language"] == "en"
    assert voice_note["transcription_confidence"] == 0.95
    assert voice_note["transcription_provider"] == "speechmatics"

    # The concierge persists inbound metadata via crud.add_message — the
    # transcription fields land as message-record columns.
    with SessionLocal() as db:
        message = crud.add_message(
            db,
            conversation_id=seed["conversation_id"],
            role="user",
            content=body,
            intent="general_enquiry",
            metadata_json=metadata,
        )
        assert message.transcription_text == body
        assert message.transcription_language == "en"
        assert message.transcription_confidence == 0.95
        assert message.transcription_provider == "speechmatics"


def test_arabic_voice_note_language_detected_and_stored(voice_seed, monkeypatch):
    seed = voice_seed
    arabic_text = "هل الوحدة ما زالت متاحة؟"
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result(arabic_text, language="ar", confidence=0.9),
    )

    body, metadata = asyncio.run(_prepare_voice_inbound(
        combined_body="",
        listing_id=seed["listing_id"],
        media_urls=[],
        media_content_types=[],
        metadata_items=[{"audio_path": "/tmp/fake-voice-ar.ogg", "content_type": "audio/ogg"}],
    ))

    assert body == arabic_text
    assert metadata["voice_note"]["transcription_language"] == "ar"

    with SessionLocal() as db:
        message = crud.add_message(
            db,
            conversation_id=seed["conversation_id"],
            role="user",
            content=body,
            metadata_json=metadata,
        )
        assert message.transcription_language == "ar"
        assert message.transcription_text == arabic_text


# ── Checklist 6: voice bundles with surrounding text ───────────────────────────


def test_voice_note_bundles_with_surrounding_text(voice_seed, monkeypatch):
    seed = voice_seed
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result("And what about parking?"),
    )

    body, metadata = asyncio.run(_prepare_voice_inbound(
        combined_body="Also, what floor is it on?",
        listing_id=seed["listing_id"],
        media_urls=[],
        media_content_types=[],
        metadata_items=[{"audio_path": "/tmp/fake-voice2.ogg", "content_type": "audio/ogg"}],
    ))

    assert body == "Also, what floor is it on?\nAnd what about parking?"
    assert metadata["voice_note"]["transcription_text"] == "And what about parking?"


# ── Checklist 3: failure → fallback once + media_unprocessable, never silent ──


def test_transcription_failure_sends_fallback_and_escalates(voice_seed, monkeypatch):
    seed = voice_seed
    transport = seed["transport"]

    def _boom(*args, **kwargs):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr("app.core.voice_notes.transcribe_audio_file", _boom)

    asyncio.run(_handle_batch(
        phone=seed["buyer_phone"],
        combined_body="",
        listing_id=seed["listing_id"],
        to_number=seed["brokerage_ai_number"],
        message_sid=f"vox-fail-{uuid.uuid4().hex[:8]}",
        media_urls=[],
        media_content_types=["audio/ogg"],
        metadata_items=[{"audio_path": "/tmp/fake-broken.ogg", "content_type": "audio/ogg"}],
        ids=[],
    ))

    # Exactly one buyer-facing message: the polite fallback. No AI answer.
    buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(buyer_messages) == 1
    assert buyer_messages[0].body == MEDIA_FALLBACK_EN

    with SessionLocal() as db:
        thread = (
            db.query(DBEscalationThread)
            .filter(
                DBEscalationThread.brokerage_id == seed["brokerage_id"],
                DBEscalationThread.escalation_type == "media_unprocessable",
            )
            .one()
        )
        # Failure events bypass debounce — the agent is alerted immediately.
        assert thread.state == "open"
        event = (
            db.query(DBComplianceEvent)
            .filter(
                DBComplianceEvent.brokerage_id == seed["brokerage_id"],
                DBComplianceEvent.event_type == "buyer_media_unprocessable",
            )
            .one()
        )
        assert "provider exploded" in event.details["error"]

    # The escalation envelope reached the agent on Agents AI.
    forwards = transport.messages_to_agents_ai()
    assert any("couldn't process" in send.body for send in forwards)


def test_video_note_is_unprocessable_not_silent(voice_seed):
    seed = voice_seed
    transport = seed["transport"]

    asyncio.run(_handle_batch(
        phone=seed["buyer_phone"],
        combined_body="",
        listing_id=seed["listing_id"],
        to_number=seed["brokerage_ai_number"],
        message_sid=f"vox-video-{uuid.uuid4().hex[:8]}",
        media_urls=["https://media.example.com/video.mp4"],
        media_content_types=["video/mp4"],
        metadata_items=[],
        ids=[],
    ))

    buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(buyer_messages) == 1
    assert buyer_messages[0].body == MEDIA_FALLBACK_EN
    with SessionLocal() as db:
        assert (
            db.query(DBEscalationThread)
            .filter(
                DBEscalationThread.brokerage_id == seed["brokerage_id"],
                DBEscalationThread.escalation_type == "media_unprocessable",
            )
            .count()
            == 1
        )


# ── Checklist 4: agent voice reply, high confidence → text + echo ─────────────


def test_agent_voice_reply_high_confidence_sends_text_and_echo(voice_seed, monkeypatch):
    seed = voice_seed
    transport = seed["transport"]
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result(
            "Yes, the unit is available. I can do a viewing tomorrow at 5pm.",
            confidence=0.93,
        ),
    )

    inbound = transport.inject_agent_voice_reply(
        envelope_token=seed["token"],
        audio_url="/tmp/agent-voice.ogg",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        result = relay_agent_reply(db, brokerage=brokerage, inbound=inbound)

    assert result.relayed is True
    buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
    assert len(buyer_messages) == 1
    assert buyer_messages[0].body == "Yes, the unit is available. I can do a viewing tomorrow at 5pm."
    assert buyer_messages[0].media_url is None  # B1: text, never agent audio

    echoes = [send for send in transport.messages_to_agents_ai() if "Sent as text:" in send.body]
    assert len(echoes) == 1

    with SessionLocal() as db:
        message = (
            db.query(DBMessage)
            .filter(
                DBMessage.conversation_id == seed["conversation_id"],
                DBMessage.intent == "agent_relay",
            )
            .one()
        )
        assert message.transcription_provider == "speechmatics"
        assert message.transcription_confidence == 0.93
        route = (
            db.query(DBAgentMessageRoute)
            .filter(DBAgentMessageRoute.agents_ai_envelope_token == seed["token"])
            .one()
        )
        assert route.consumed_at is not None


# ── Checklist 5: low confidence → held until SEND ──────────────────────────────


def test_agent_voice_reply_low_confidence_held_then_send_releases(voice_seed, monkeypatch):
    seed = voice_seed
    transport = seed["transport"]
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result(
            "Tell her we can maybe do one point nine",
            confidence=0.42,
        ),
    )

    inbound = transport.inject_agent_voice_reply(
        envelope_token=seed["token"],
        audio_url="/tmp/agent-voice-low.ogg",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        result = relay_agent_reply(db, brokerage=brokerage, inbound=inbound)

        assert result.relayed is False
        assert result.status == "agent_voice_reply_held"
        # Nothing reached the buyer; the agent got the transcript + SEND prompt.
        assert transport.messages_to_buyer(seed["buyer_phone"]) == []
        prompts = [send for send in transport.messages_to_agents_ai() if "Reply SEND" in send.body]
        assert len(prompts) == 1
        assert "one point nine" in prompts[0].body

        hold = (
            db.query(DBAgentVoiceReplyHold)
            .filter(DBAgentVoiceReplyHold.brokerage_id == seed["brokerage_id"])
            .one()
        )
        assert hold.status == "held"
        assert hold.transcription_confidence == 0.42
        route = (
            db.query(DBAgentMessageRoute)
            .filter(DBAgentMessageRoute.agents_ai_envelope_token == seed["token"])
            .one()
        )
        assert route.consumed_at is None  # held, not consumed

    # Agent confirms with SEND on the same thread.
    send_inbound = transport.inject_agent_reply(
        envelope_token=seed["token"],
        body_without_token="SEND",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        release = handle_agent_send_keyword(db, brokerage=brokerage, inbound=send_inbound)

        assert release is not None
        assert release.relayed is True
        buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
        assert len(buyer_messages) == 1
        assert buyer_messages[0].body == "Tell her we can maybe do one point nine"

        hold = (
            db.query(DBAgentVoiceReplyHold)
            .filter(DBAgentVoiceReplyHold.brokerage_id == seed["brokerage_id"])
            .one()
        )
        assert hold.status == "sent"
        assert hold.released_at is not None


def test_send_keyword_with_no_hold_prompts_and_never_reaches_buyer(voice_seed):
    seed = voice_seed
    transport = seed["transport"]

    send_inbound = transport.inject_agent_reply(
        envelope_token=seed["token"],
        body_without_token="SEND",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )
    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        result = handle_agent_send_keyword(db, brokerage=brokerage, inbound=send_inbound)

    assert result is not None
    assert result.status == "agent_voice_send_no_hold"
    assert transport.messages_to_buyer(seed["buyer_phone"]) == []
    prompts = [send for send in transport.messages_to_agents_ai() if "no voice note" in send.body.lower()]
    assert prompts


def test_typed_reply_supersedes_pending_hold(voice_seed, monkeypatch):
    seed = voice_seed
    transport = seed["transport"]
    monkeypatch.setattr(
        "app.core.voice_notes.transcribe_audio_file",
        lambda *args, **kwargs: _fake_result("unclear mumbling", confidence=0.3),
    )

    voice_inbound = transport.inject_agent_voice_reply(
        envelope_token=seed["token"],
        audio_url="/tmp/agent-voice-mumble.ogg",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )
    typed_inbound = transport.inject_agent_reply(
        envelope_token=seed["token"],
        body_without_token="Let me call you to discuss.",
        agents_ai_number=seed["agents_ai_number"],
        agent_phone=seed["agent_phone"],
    )

    with SessionLocal() as db:
        brokerage = db.get(DBBrokerage, seed["brokerage_id"])
        held = relay_agent_reply(db, brokerage=brokerage, inbound=voice_inbound)
        assert held.status == "agent_voice_reply_held"
        typed = relay_agent_reply(db, brokerage=brokerage, inbound=typed_inbound)
        assert typed.relayed is True

        hold = (
            db.query(DBAgentVoiceReplyHold)
            .filter(DBAgentVoiceReplyHold.brokerage_id == seed["brokerage_id"])
            .one()
        )
        assert hold.status == "cancelled"
        assert hold.metadata_json["cancel_reason"] == "superseded_by_reply"

    buyer_messages = transport.messages_to_buyer(seed["buyer_phone"])
    assert [send.body for send in buyer_messages] == ["Let me call you to discuss."]


# ── Checklist 7: duplicate media MessageSid is idempotent ──────────────────────


def test_duplicate_media_message_sid_enqueued_once(client, monkeypatch, voice_seed):
    seed = voice_seed
    monkeypatch.setattr("app.api.whatsapp.TWILIO_AUTH_TOKEN", "")
    message_sid = f"vox-dup-{uuid.uuid4().hex[:8]}"

    for _ in range(2):
        response = client.post(
            "/api/v1/whatsapp/webhook",
            data={
                "From": f"whatsapp:{seed['buyer_phone']}",
                "To": f"whatsapp:{seed['brokerage_ai_number']}",
                "Body": "",
                "MessageSid": message_sid,
                "NumMedia": "1",
                "MediaUrl0": "https://media.example.com/voice.ogg",
                "MediaContentType0": "audio/ogg",
            },
        )
        assert response.status_code == 200, response.text

    with SessionLocal() as db:
        queued = db.query(DBMessageQueue).filter(DBMessageQueue.message_sid == message_sid).count()
        assert queued == 1  # one queue row → one transcription, no double billing


# ── Checklist 8: provider failover records the fallback provider ──────────────


class _FailingProvider:
    name = "speechmatics"

    def transcribe(self, audio: AudioInput, dictionary) -> ProviderTranscript:
        raise RuntimeError("forced primary failure")


class _WorkingProvider:
    name = "assemblyai"

    def transcribe(self, audio: AudioInput, dictionary) -> ProviderTranscript:
        return ProviderTranscript(
            provider=self.name,
            raw_transcript="fallback transcript",
            language="en",
            confidence=0.88,
        )


class _PassthroughPostProcessor:
    def process(self, transcript, dictionary, context):
        return transcript, [], [], []


def test_provider_failover_uses_fallback_and_records_provider(tmp_path: Path):
    audio = tmp_path / "sample.ogg"
    audio.write_bytes(b"fake-audio")

    service = TranscriptionService(
        provider=_FailingProvider(),
        fallback_provider=_WorkingProvider(),
        post_processor=_PassthroughPostProcessor(),
    )
    result = service.transcribe(audio, content_type="audio/ogg", audio_type="buyer_voice")

    assert result.provider == "assemblyai"
    assert result.raw_transcript == "fallback transcript"
    assert result.language == "en"
    assert result.confidence == 0.88
