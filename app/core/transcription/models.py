from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]


class TranscriptionContext(BaseModel):
    listing_id: Optional[str] = None
    asking_price_aed: Optional[float] = None
    recent_offer_amounts_aed: list[float] = Field(default_factory=list)
    recent_price_ranges_aed: list[tuple[float, float]] = Field(default_factory=list)


class AudioInput(BaseModel):
    path: Path
    content_type: Optional[str] = None
    audio_type: Optional[str] = None
    delete_after_processing: bool = True


class ProviderTranscript(BaseModel):
    provider: str
    raw_transcript: str
    duration_seconds: Optional[float] = None
    provider_job_id: Optional[str] = None
    provider_metadata: dict = Field(default_factory=dict)
    # Detected language (ISO 639-1 where the provider reports one) and an
    # overall 0..1 transcript confidence. Logged, never blocking (DAL-159).
    language: Optional[str] = None
    confidence: Optional[float] = None


class PriceExtraction(BaseModel):
    amount: Optional[int] = None
    currency: str = "AED"
    confidence: Confidence
    source_phrase: str
    unit_inferred: bool = False
    ambiguity_group: Optional[str] = None
    candidate_amounts: list[int] = Field(default_factory=list)
    note: Optional[str] = None


class LowConfidenceSegment(BaseModel):
    source_phrase: str
    reason: str
    candidates: list[str] = Field(default_factory=list)


class TranscriptionResult(BaseModel):
    provider: str
    raw_transcript: str
    corrected_transcript: str
    prices: list[PriceExtraction] = Field(default_factory=list)
    low_confidence_segments: list[LowConfidenceSegment] = Field(default_factory=list)
    normalized_terms: list[str] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    provider_job_id: Optional[str] = None
    cost_tracking: dict = Field(default_factory=dict)
    language: Optional[str] = None
    confidence: Optional[float] = None

    def effective_confidence(self) -> float:
        """
        Provider confidence when reported; otherwise a conservative heuristic
        from the post-processor's low-confidence segments. Used by the agent
        voice-reply SEND gate (DAL-159) — the only flow where confidence gates
        sending.
        """
        if self.confidence is not None:
            return float(self.confidence)
        return 0.85 if not self.low_confidence_segments else 0.5
