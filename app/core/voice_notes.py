from __future__ import annotations

import tempfile
import os
from pathlib import Path
from typing import Iterable, Optional

import httpx

from app.core.transcription.models import PriceExtraction, TranscriptionContext, TranscriptionResult
from app.core.transcription.service import build_transcription_service


def transcription_result_metadata(
    result: TranscriptionResult,
    *,
    direction: str,
    audio_url: Optional[str] = None,
    media_asset_id: Optional[str] = None,
) -> dict:
    voice_note = {
        "direction": direction,
        "provider": result.provider,
        "raw_transcript": result.raw_transcript,
        "corrected_transcript": result.corrected_transcript,
        "prices": [price.model_dump() for price in result.prices],
        "low_confidence_segments": [
            segment.model_dump() for segment in result.low_confidence_segments
        ],
        "normalized_terms": list(result.normalized_terms),
        "cost_tracking": dict(result.cost_tracking),
        # Spec-named storage fields (DAL-159) — mirrored onto the message
        # record columns by crud.add_message.
        "transcription_text": result.corrected_transcript or result.raw_transcript,
        "transcription_language": result.language,
        "transcription_confidence": result.effective_confidence(),
        "transcription_provider": result.provider,
    }
    if media_asset_id:
        voice_note["media_asset_id"] = media_asset_id
    elif audio_url:
        voice_note["audio_url"] = audio_url
    return {
        "voice_note": {
            **voice_note,
        }
    }


def apply_voice_offer_intent(intent_data: dict, metadata: dict) -> dict:
    voice_note = (metadata or {}).get("voice_note") or {}
    prices = _price_extractions_from_metadata(voice_note.get("prices") or [])
    if not prices:
        return intent_data

    confident = [
        price for price in prices
        if price.amount is not None and price.confidence in {"high", "medium"}
    ]
    low_confidence = [
        price for price in prices
        if price.confidence == "low" or price.candidate_amounts
    ]

    next_data = dict(intent_data)
    if confident:
        selected = confident[0]
        next_data.update(
            {
                "intent": "offer_submission",
                "is_firm_offer": True,
                "extracted_offer_amount": selected.amount,
                "voice_offer_confidence": selected.confidence,
                "voice_offer_source_phrase": selected.source_phrase,
                "voice_offer_unit_inferred": selected.unit_inferred,
            }
        )
        return next_data

    if low_confidence:
        next_data["possible_voice_offer_requires_confirmation"] = True
        next_data["voice_offer_candidates"] = _candidate_amounts(low_confidence)
        next_data["voice_offer_source_phrase"] = ", ".join(
            price.source_phrase for price in low_confidence if price.source_phrase
        )
    return next_data


def needs_voice_amount_confirmation(intent_data: dict, metadata: dict) -> bool:
    voice_note = (metadata or {}).get("voice_note") or {}
    if not voice_note:
        return False
    return bool(intent_data.get("possible_voice_offer_requires_confirmation"))


def voice_amount_confirmation_response(intent_data: dict) -> str:
    candidates = [
        amount for amount in (intent_data.get("voice_offer_candidates") or [])
        if isinstance(amount, (int, float))
    ]
    if candidates:
        formatted = " or ".join(f"AED {amount:,.0f}" for amount in candidates[:3])
        return (
            "I heard a possible offer amount, but I want to confirm it before I record it. "
            f"Did you mean {formatted}?"
        )
    return (
        "I heard a possible offer amount, but the audio was not clear enough for me to record it. "
        "Could you confirm the exact AED amount in your next reply?"
    )


def transcribe_audio_file(
    audio_path: str | Path,
    *,
    content_type: Optional[str] = None,
    audio_type: str = "buyer_voice",
    context: Optional[TranscriptionContext] = None,
) -> TranscriptionResult:
    service = build_transcription_service()
    return service.transcribe(
        audio_path,
        content_type=content_type,
        audio_type=audio_type,
        context=context,
        delete_audio=True,
    )


async def download_media_to_tempfile(
    media_url: str,
    *,
    content_type: Optional[str] = None,
    suffix: Optional[str] = None,
    auth: Optional[tuple[str, str]] = None,
) -> Path:
    suffix = suffix or _suffix_for_content_type(content_type) or Path(media_url).suffix or ".audio"
    fd, temp_name = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    path = Path(temp_name)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(media_url, auth=auth)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def download_media_to_tempfile_sync(
    media_url: str,
    *,
    content_type: Optional[str] = None,
    suffix: Optional[str] = None,
    auth: Optional[tuple[str, str]] = None,
) -> Path:
    """
    Synchronous twin of download_media_to_tempfile for sync call sites (the
    agent relay). Local file paths (simulated transport) pass through directly.
    """
    if media_url.startswith("/") or media_url.startswith("file://"):
        return Path(media_url.removeprefix("file://"))
    suffix = suffix or _suffix_for_content_type(content_type) or Path(media_url).suffix or ".audio"
    fd, temp_name = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    path = Path(temp_name)
    with httpx.Client(timeout=30) as client:
        response = client.get(media_url, auth=auth)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def twilio_media_auth() -> Optional[tuple[str, str]]:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    return (sid, token) if sid and token else None


def _price_extractions_from_metadata(items: Iterable[dict]) -> list[PriceExtraction]:
    prices: list[PriceExtraction] = []
    for item in items:
        if isinstance(item, PriceExtraction):
            prices.append(item)
            continue
        if not isinstance(item, dict):
            continue
        try:
            prices.append(PriceExtraction.model_validate(item))
        except Exception:
            continue
    return prices


def _candidate_amounts(prices: Iterable[PriceExtraction]) -> list[int]:
    amounts: list[int] = []
    for price in prices:
        candidates = list(price.candidate_amounts)
        if price.amount is not None:
            candidates.append(price.amount)
        for amount in candidates:
            if amount not in amounts:
                amounts.append(amount)
    return amounts


def _suffix_for_content_type(content_type: Optional[str]) -> Optional[str]:
    mapping = {
        "audio/ogg": ".ogg",
        "audio/opus": ".opus",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
    }
    return mapping.get((content_type or "").split(";")[0].strip().lower())
