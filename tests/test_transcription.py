from __future__ import annotations

from pathlib import Path

import pytest

from app.core.transcription.dictionary import load_transcription_dictionary
from app.core.transcription.models import ProviderTranscript, TranscriptionContext
from app.core.transcription.post_processor import RuleBasedTranscriptPostProcessor
from app.core.transcription.service import TranscriptionService


pytestmark = pytest.mark.no_db


class FakeProvider:
    name = "fake"

    def __init__(self, raw: str, fail: bool = False):
        self.raw = raw
        self.fail = fail

    def transcribe(self, audio, dictionary):
        if self.fail:
            raise RuntimeError("primary failed")
        return ProviderTranscript(
            provider=self.name,
            raw_transcript=self.raw,
            duration_seconds=12.5,
            provider_job_id="fake-job",
        )


def test_post_processor_corrects_seeded_real_estate_terms():
    dictionary = load_transcription_dictionary()
    processor = RuleBasedTranscriptPostProcessor()

    corrected, prices, low_segments, normalized_terms = processor.process(
        "buyer asked for no see status on email oasis and the sp a before transfer",
        dictionary,
        TranscriptionContext(asking_price_aed=2_500_000),
    )

    assert "NOC" in corrected
    assert "Emaar" in corrected
    assert "SPA" in corrected
    assert "NOC" in normalized_terms
    assert prices == []
    assert low_segments == []


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("I can offer two point five million", 2_500_000),
        ("I can offer AED 2.5", 2_500_000),
        ("I can offer 2.5M", 2_500_000),
        ("I can offer two M five", 2_500_000),
        ("I can offer two and a half million", 2_500_000),
        ("I can offer twenty five hundred thousand", 2_500_000),
    ],
)
def test_price_talk_variants_extract_structured_aed(phrase: str, expected: int):
    dictionary = load_transcription_dictionary()
    processor = RuleBasedTranscriptPostProcessor()

    _, prices, _, _ = processor.process(
        phrase,
        dictionary,
        TranscriptionContext(asking_price_aed=2_700_000),
    )

    assert any(price.amount == expected and price.currency == "AED" for price in prices)


def test_implicit_unit_uses_context_but_preserves_low_confidence_when_weak():
    dictionary = load_transcription_dictionary()
    processor = RuleBasedTranscriptPostProcessor()

    _, prices, low_segments, _ = processor.process(
        "I was thinking maybe 2.3",
        dictionary,
        TranscriptionContext(asking_price_aed=2_500_000),
    )

    assert prices[0].amount == 2_300_000
    assert prices[0].confidence == "low"
    assert prices[0].source_phrase == "2.3"
    assert prices[0].unit_inferred is True
    assert low_segments


def test_ambiguous_price_surfaces_candidates_without_picking_one():
    dictionary = load_transcription_dictionary()
    processor = RuleBasedTranscriptPostProcessor()

    _, prices, low_segments, _ = processor.process(
        "I was thinking maybe 2.2 or 2.3 with the current asking",
        dictionary,
        TranscriptionContext(asking_price_aed=2_500_000),
    )

    assert {price.amount for price in prices} >= {2_200_000, 2_300_000}
    assert all(price.confidence == "low" for price in prices if price.ambiguity_group)
    assert any(segment.candidates for segment in low_segments)


def test_service_deletes_audio_and_returns_structured_result(tmp_path: Path):
    audio_path = tmp_path / "voice-note.m4a"
    audio_path.write_bytes(b"fake audio")
    service = TranscriptionService(
        provider=FakeProvider("I can offer two point three"),
        dictionary=load_transcription_dictionary(),
        post_processor=RuleBasedTranscriptPostProcessor(),
    )

    result = service.transcribe(
        audio_path,
        context=TranscriptionContext(asking_price_aed=2_500_000),
    )

    assert result.raw_transcript == "I can offer two point three"
    assert result.corrected_transcript == "I can offer two point three"
    assert result.prices[0].amount == 2_300_000
    assert result.prices[0].confidence == "high"
    assert result.prices[0].source_phrase == "two point three"
    assert not audio_path.exists()


def test_service_fallback_provider_is_swappable(tmp_path: Path):
    audio_path = tmp_path / "voice-note.wav"
    audio_path.write_bytes(b"fake audio")
    service = TranscriptionService(
        provider=FakeProvider("unused", fail=True),
        fallback_provider=FakeProvider("I can offer 2.5M"),
        dictionary=load_transcription_dictionary(),
        post_processor=RuleBasedTranscriptPostProcessor(),
    )

    result = service.transcribe(
        audio_path,
        context=TranscriptionContext(asking_price_aed=2_600_000),
    )

    assert result.provider == "fake"
    assert result.prices[0].amount == 2_500_000
