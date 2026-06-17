from app.core.messaging.simulated_transport import SimulatedTransport
from app.core.messaging.types import OutboundBuyerMessage
from app.core.voice_notes import (
    apply_voice_offer_intent,
    needs_voice_amount_confirmation,
    transcription_result_metadata,
    voice_amount_confirmation_response,
)
from app.core.transcription.models import (
    LowConfidenceSegment,
    PriceExtraction,
    TranscriptionResult,
)
import pytest


@pytest.mark.no_db
def test_high_confidence_voice_price_overrides_offer_intent():
    result = TranscriptionResult(
        provider="fixture",
        raw_transcript="can I offer two point eight million",
        corrected_transcript="Can I offer AED 2.8 million?",
        prices=[
            PriceExtraction(
                amount=2_800_000,
                confidence="high",
                source_phrase="two point eight million",
            )
        ],
    )
    metadata = transcription_result_metadata(
        result,
        direction="buyer_to_property_advisor",
        audio_url="file:///tmp/offer.ogg",
    )

    intent_data = apply_voice_offer_intent({"intent": "general_enquiry"}, metadata)

    assert intent_data["intent"] == "offer_submission"
    assert intent_data["is_firm_offer"] is True
    assert intent_data["extracted_offer_amount"] == 2_800_000
    assert intent_data["voice_offer_confidence"] == "high"
    assert intent_data["voice_offer_source_phrase"] == "two point eight million"


@pytest.mark.no_db
def test_low_confidence_voice_price_requires_confirmation():
    result = TranscriptionResult(
        provider="fixture",
        raw_transcript="I was thinking maybe 2.2 or 2.3",
        corrected_transcript="I was thinking maybe 2.2 or 2.3.",
        prices=[
            PriceExtraction(
                amount=None,
                confidence="low",
                source_phrase="2.2 or 2.3",
                candidate_amounts=[2_200_000, 2_300_000],
                ambiguity_group="voice-price-1",
            )
        ],
        low_confidence_segments=[
            LowConfidenceSegment(
                source_phrase="2.2 or 2.3",
                reason="ambiguous_offer_amount",
                candidates=["AED 2,200,000", "AED 2,300,000"],
            )
        ],
    )
    metadata = transcription_result_metadata(
        result,
        direction="buyer_to_property_advisor",
    )

    intent_data = apply_voice_offer_intent({"intent": "general_enquiry"}, metadata)

    assert needs_voice_amount_confirmation(intent_data, metadata) is True
    assert "extracted_offer_amount" not in intent_data
    assert intent_data["voice_offer_candidates"] == [2_200_000, 2_300_000]
    response = voice_amount_confirmation_response(intent_data)
    assert "AED 2,200,000 or AED 2,300,000" in response


@pytest.mark.no_db
def test_simulated_transport_supports_voice_note_media():
    transport = SimulatedTransport()

    inbound = transport.inject_buyer_voice_note(
        from_buyer="+971501111111",
        to_brokerage_ai_number="+971502222222",
        audio_path="/tmp/sample.ogg",
        body="",
    )
    assert inbound.media_urls == ["/tmp/sample.ogg"]
    assert inbound.raw["MediaContentType0"] == "audio/ogg"

    transport.send_to_buyer(
        OutboundBuyerMessage(
            brokerage_id="brokerage-1",
            brokerage_ai_number="+971502222222",
            buyer_phone="+971501111111",
            body="",
            conversation_id="conv-1",
            listing_id="listing-1",
            media_url="https://cdn.example.com/agent-note.ogg",
        )
    )
    sent = transport.messages_to_buyer("+971501111111")[0]
    assert sent.media_url == "https://cdn.example.com/agent-note.ogg"
