from __future__ import annotations

import logging
import os
from pathlib import Path

from app.core.transcription.dictionary import TranscriptionDictionary, load_transcription_dictionary
from app.core.transcription.models import AudioInput, ProviderTranscript, TranscriptionContext, TranscriptionResult
from app.core.transcription.post_processor import ClaudeTranscriptPostProcessor, TranscriptPostProcessor
from app.core.transcription.providers import MissingTranscriptionCredential, TranscriptionProvider, build_provider

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".opus", ".mp3", ".m4a", ".wav", ".webm", ".ogg", ".aac", ".flac"}


class TranscriptionService:
    def __init__(
        self,
        provider: TranscriptionProvider,
        fallback_provider: TranscriptionProvider | None = None,
        dictionary: TranscriptionDictionary | None = None,
        post_processor: TranscriptPostProcessor | None = None,
    ):
        self.provider = provider
        self.fallback_provider = fallback_provider
        self.dictionary = dictionary or load_transcription_dictionary()
        self.post_processor = post_processor or ClaudeTranscriptPostProcessor()

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        content_type: str | None = None,
        audio_type: str | None = None,
        context: TranscriptionContext | None = None,
        delete_audio: bool = True,
    ) -> TranscriptionResult:
        path = Path(audio_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported audio format '{path.suffix}'. Expected one of {sorted(SUPPORTED_EXTENSIONS)}")

        audio = AudioInput(
            path=path,
            content_type=content_type,
            audio_type=audio_type,
            delete_after_processing=delete_audio,
        )
        try:
            provider_result = self._transcribe_with_failover(audio)
            corrected, prices, low_segments, normalized_terms = self.post_processor.process(
                provider_result.raw_transcript,
                self.dictionary,
                context or TranscriptionContext(),
            )
            result = TranscriptionResult(
                provider=provider_result.provider,
                raw_transcript=provider_result.raw_transcript,
                corrected_transcript=corrected,
                prices=prices,
                low_confidence_segments=low_segments,
                normalized_terms=normalized_terms,
                duration_seconds=provider_result.duration_seconds,
                provider_job_id=provider_result.provider_job_id,
                cost_tracking={
                    "provider": provider_result.provider,
                    "duration_seconds": provider_result.duration_seconds,
                    "audio_type": audio_type,
                },
                language=provider_result.language,
                confidence=provider_result.confidence,
            )
            logger.info(
                "Transcribed audio provider=%s duration_seconds=%s audio_type=%s language=%s confidence=%s",
                result.provider,
                result.duration_seconds,
                audio_type,
                result.language,
                result.confidence,
            )
            return result
        finally:
            if delete_audio and path.exists():
                path.unlink()

    def _transcribe_with_failover(self, audio: AudioInput) -> ProviderTranscript:
        try:
            return self.provider.transcribe(audio, self.dictionary)
        except Exception:
            if not self.fallback_provider:
                raise
            logger.exception(
                "Primary transcription provider %s failed; trying fallback %s",
                getattr(self.provider, "name", "unknown"),
                getattr(self.fallback_provider, "name", "unknown"),
            )
            return self.fallback_provider.transcribe(audio, self.dictionary)


def build_transcription_service(
    *,
    provider_name: str | None = None,
    fallback_provider_name: str | None = None,
) -> TranscriptionService:
    provider_by_audio_type = os.getenv("TRANSCRIPTION_PROVIDER_BY_AUDIO_TYPE", "")
    provider_name = provider_name or _provider_for_audio_type(provider_by_audio_type) or os.getenv("TRANSCRIPTION_PROVIDER", "speechmatics")
    fallback_provider_name = fallback_provider_name or os.getenv("TRANSCRIPTION_FALLBACK_PROVIDER", "assemblyai")
    fallback = None
    if fallback_provider_name and fallback_provider_name.strip().lower() != provider_name.strip().lower():
        fallback = build_provider(fallback_provider_name)
    return TranscriptionService(
        provider=build_provider(provider_name),
        fallback_provider=fallback,
    )


def _provider_for_audio_type(mapping: str) -> str | None:
    # Reserved for callers that set an audio-type-specific mapping before
    # construction, e.g. "buyer_voice:speechmatics,agent_dictation:assemblyai".
    current_type = os.getenv("TRANSCRIPTION_AUDIO_TYPE")
    if not mapping or not current_type:
        return None
    for item in mapping.split(","):
        if ":" not in item:
            continue
        audio_type, provider = item.split(":", 1)
        if audio_type.strip() == current_type:
            return provider.strip()
    return None
