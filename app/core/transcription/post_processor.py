from __future__ import annotations

import json
import logging
import os
import re
from typing import Protocol

import anthropic

from app.core.transcription.dictionary import TranscriptionDictionary
from app.core.transcription.models import LowConfidenceSegment, PriceExtraction, TranscriptionContext
from app.core.transcription.price_parser import extract_prices

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"


class TranscriptPostProcessor(Protocol):
    def process(
        self,
        raw_transcript: str,
        dictionary: TranscriptionDictionary,
        context: TranscriptionContext | None = None,
    ) -> tuple[str, list[PriceExtraction], list[LowConfidenceSegment], list[str]]:
        ...


class ClaudeTranscriptPostProcessor:
    def __init__(self, client: anthropic.Anthropic | None = None, enabled: bool | None = None):
        self.client = client
        self.enabled = enabled if enabled is not None else os.getenv("TRANSCRIPTION_CLAUDE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
        self.rule_based = RuleBasedTranscriptPostProcessor()

    def process(
        self,
        raw_transcript: str,
        dictionary: TranscriptionDictionary,
        context: TranscriptionContext | None = None,
    ) -> tuple[str, list[PriceExtraction], list[LowConfidenceSegment], list[str]]:
        corrected, prices, low_segments, normalized_terms = self.rule_based.process(
            raw_transcript,
            dictionary,
            context,
        )
        if not self.enabled or not os.getenv("ANTHROPIC_API_KEY"):
            return corrected, prices, low_segments, normalized_terms

        try:
            client = self.client or anthropic.Anthropic()
            response = client.messages.create(
                model=MODEL,
                max_tokens=1600,
                system=_system_prompt(dictionary),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "raw_transcript": raw_transcript,
                                "rule_based_corrected_transcript": corrected,
                                "rule_based_prices": [p.model_dump() for p in prices],
                                "rule_based_low_confidence_segments": [s.model_dump() for s in low_segments],
                                "context": (context or TranscriptionContext()).model_dump(),
                            },
                            ensure_ascii=True,
                        ),
                    }
                ],
            )
            payload = _loads_json(response.content[0].text)
            corrected = payload.get("corrected_transcript") or corrected
            prices = [PriceExtraction.model_validate(item) for item in payload.get("prices", [p.model_dump() for p in prices])]
            low_segments = [
                LowConfidenceSegment.model_validate(item)
                for item in payload.get("low_confidence_segments", [s.model_dump() for s in low_segments])
            ]
            normalized_terms = list(dict.fromkeys(payload.get("normalized_terms", normalized_terms)))
        except Exception as exc:
            logger.warning("Claude transcript post-processing failed; using rule-based fallback: %s", exc)

        return corrected, prices, low_segments, normalized_terms


class RuleBasedTranscriptPostProcessor:
    TERM_ALIASES = {
        "no see": "NOC",
        "n o c": "NOC",
        "sp a": "SPA",
        "s p a": "SPA",
        "okra": "Oqood",
        "accord": "Oqood",
        "a jury": "Ejari",
        "rara": "RERA",
        "track easy": "Trakheesi",
        "track he see": "Trakheesi",
        "email": "Emaar",
        "sob a": "Sobha",
        "soba": "Sobha",
        "sea haven": "SeaHaven",
    }

    def process(
        self,
        raw_transcript: str,
        dictionary: TranscriptionDictionary,
        context: TranscriptionContext | None = None,
    ) -> tuple[str, list[PriceExtraction], list[LowConfidenceSegment], list[str]]:
        corrected = raw_transcript.strip()
        normalized_terms: list[str] = []

        for wrong, right in self.TERM_ALIASES.items():
            corrected, count = re.subn(rf"\b{re.escape(wrong)}\b", right, corrected, flags=re.IGNORECASE)
            if count:
                normalized_terms.append(right)

        for term in dictionary.terms:
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            corrected, count = pattern.subn(term, corrected)
            if count:
                normalized_terms.append(term)

        prices, low_segments = extract_prices(corrected, context)
        return corrected, prices, low_segments, list(dict.fromkeys(normalized_terms))


def _system_prompt(dictionary: TranscriptionDictionary) -> str:
    return f"""You post-process Dubai real estate voice-note transcripts.

Return strict JSON with:
- corrected_transcript: terminology-normalized natural transcript.
- prices: array of objects with amount, currency, confidence, source_phrase, unit_inferred, ambiguity_group, candidate_amounts, note.
- low_confidence_segments: array of objects with source_phrase, reason, candidates.
- normalized_terms: array of exact dictionary terms corrected or confirmed.

Rules:
- Use this Dubai real estate dictionary:
{dictionary.as_prompt_context()}
- Correct terminology when context strongly supports it.
- Never silently choose between uncertain price candidates.
- Preserve every source phrase for price audit.
- If a number has an implicit unit, infer from context only when reasonable and flag confidence low unless strongly supported.
- Use AED as the currency for Dubai real estate prices.
- Output JSON only."""


def _loads_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Claude post-processing response must be a JSON object")
    return data
