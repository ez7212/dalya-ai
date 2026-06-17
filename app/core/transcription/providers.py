from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Protocol

import httpx

from app.core.transcription.dictionary import TranscriptionDictionary
from app.core.transcription.models import AudioInput, ProviderTranscript


class TranscriptionProvider(Protocol):
    name: str

    def transcribe(self, audio: AudioInput, dictionary: TranscriptionDictionary) -> ProviderTranscript:
        ...


class MissingTranscriptionCredential(RuntimeError):
    pass


class SpeechmaticsProvider:
    name = "speechmatics"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 600,
        poll_interval_seconds: float = 3,
    ):
        self.api_key = api_key or os.getenv("SPEECHMATICS_API_KEY")
        self.base_url = (base_url or os.getenv("SPEECHMATICS_BASE_URL") or "https://asr.api.speechmatics.com/v2/jobs").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def transcribe(self, audio: AudioInput, dictionary: TranscriptionDictionary) -> ProviderTranscript:
        if not self.api_key:
            raise MissingTranscriptionCredential("SPEECHMATICS_API_KEY is required for live Speechmatics transcription")

        # Language auto-detect (DAL-159): Gulf buyers mix Arabic/English; Hindi/
        # Urdu likely. Detected language is logged, never blocking. Override
        # with SPEECHMATICS_LANGUAGE=en to pin a language.
        language = os.getenv("SPEECHMATICS_LANGUAGE", "auto")
        config = {
            "type": "transcription",
            "transcription_config": {
                "language": language,
                "additional_vocab": dictionary.provider_vocabulary(),
            },
        }
        if language == "auto":
            # Bias auto-detection toward the languages we expect on this market.
            config["language_identification_config"] = {
                "expected_languages": ["en", "ar", "hi", "ur", "ru"],
            }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=60) as client:
            with Path(audio.path).open("rb") as handle:
                response = client.post(
                    self.base_url,
                    headers=headers,
                    files={
                        "data_file": (Path(audio.path).name, handle, audio.content_type or "application/octet-stream"),
                        "config": (None, json.dumps(config), "application/json"),
                    },
                )
            response.raise_for_status()
            payload = response.json()
            job_id = str(payload.get("id") or payload.get("job", {}).get("id"))
            if not job_id:
                raise RuntimeError(f"Speechmatics did not return a job id: {payload}")

            started = time.monotonic()
            while True:
                job = client.get(f"{self.base_url}/{job_id}", headers=headers)
                job.raise_for_status()
                job_payload = job.json()
                status = _nested_status(job_payload)
                if status in {"done", "completed"}:
                    break
                if status in {"rejected", "failed", "error"}:
                    raise RuntimeError(f"Speechmatics transcription failed: {job_payload}")
                if time.monotonic() - started > self.timeout_seconds:
                    raise TimeoutError(f"Speechmatics transcription timed out for job {job_id}")
                time.sleep(self.poll_interval_seconds)

            transcript_response = client.get(f"{self.base_url}/{job_id}/transcript", headers=headers)
            transcript_response.raise_for_status()
            transcript_payload = transcript_response.json()

        return ProviderTranscript(
            provider=self.name,
            raw_transcript=_speechmatics_text(transcript_payload),
            duration_seconds=_speechmatics_duration(transcript_payload),
            provider_job_id=job_id,
            provider_metadata={"job": payload},
            language=_speechmatics_language(transcript_payload),
            confidence=_speechmatics_confidence(transcript_payload),
        )


class AssemblyAIProvider:
    name = "assemblyai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 600,
        poll_interval_seconds: float = 3,
    ):
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.base_url = (base_url or os.getenv("ASSEMBLYAI_BASE_URL") or "https://api.assemblyai.com").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def transcribe(self, audio: AudioInput, dictionary: TranscriptionDictionary) -> ProviderTranscript:
        if not self.api_key:
            raise MissingTranscriptionCredential("ASSEMBLYAI_API_KEY is required for live AssemblyAI transcription")

        headers = {"authorization": self.api_key}
        with httpx.Client(timeout=60) as client:
            with Path(audio.path).open("rb") as handle:
                upload = client.post(
                    f"{self.base_url}/v2/upload",
                    headers=headers,
                    content=handle,
                )
            upload.raise_for_status()
            audio_url = upload.json()["upload_url"]
            # Language auto-detect (DAL-159) unless ASSEMBLYAI_LANGUAGE pins one.
            pinned_language = os.getenv("ASSEMBLYAI_LANGUAGE")
            request_payload = {
                "audio_url": audio_url,
                "speech_models": ["universal-3-pro"],
                "keyterms_prompt": dictionary.provider_vocabulary(),
            }
            if pinned_language:
                request_payload["language_code"] = pinned_language
            else:
                request_payload["language_detection"] = True
            create = client.post(
                f"{self.base_url}/v2/transcript",
                headers=headers,
                json=request_payload,
            )
            create.raise_for_status()
            transcript_id = create.json()["id"]

            started = time.monotonic()
            while True:
                response = client.get(f"{self.base_url}/v2/transcript/{transcript_id}", headers=headers)
                response.raise_for_status()
                payload = response.json()
                status = payload.get("status")
                if status == "completed":
                    confidence = payload.get("confidence")
                    return ProviderTranscript(
                        provider=self.name,
                        raw_transcript=payload.get("text") or "",
                        duration_seconds=payload.get("audio_duration"),
                        provider_job_id=transcript_id,
                        provider_metadata={"transcript": payload},
                        language=payload.get("language_code"),
                        confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
                    )
                if status == "error":
                    raise RuntimeError(f"AssemblyAI transcription failed: {payload.get('error')}")
                if time.monotonic() - started > self.timeout_seconds:
                    raise TimeoutError(f"AssemblyAI transcription timed out for job {transcript_id}")
                time.sleep(self.poll_interval_seconds)


def build_provider(name: str) -> TranscriptionProvider:
    normalized = name.strip().lower()
    if normalized == "speechmatics":
        return SpeechmaticsProvider()
    if normalized in {"assemblyai", "assembly_ai"}:
        return AssemblyAIProvider()
    raise ValueError(f"Unknown transcription provider: {name}")


def _nested_status(payload: dict) -> str:
    status = payload.get("status") or payload.get("job", {}).get("status")
    return str(status or "").lower()


def _speechmatics_text(payload: dict) -> str:
    if isinstance(payload.get("text"), str):
        return payload["text"]
    words: list[str] = []
    for result in payload.get("results", []):
        alternatives = result.get("alternatives") or []
        if alternatives and alternatives[0].get("content"):
            words.append(alternatives[0]["content"])
    text = " ".join(words)
    return (
        text.replace(" ,", ",")
        .replace(" .", ".")
        .replace(" ?", "?")
        .replace(" !", "!")
        .strip()
    )


def _speechmatics_duration(payload: dict) -> float | None:
    end_times = [
        result.get("end_time")
        for result in payload.get("results", [])
        if isinstance(result.get("end_time"), (int, float))
    ]
    return max(end_times) if end_times else None


def _speechmatics_language(payload: dict) -> str | None:
    metadata = payload.get("metadata") or {}
    config = metadata.get("transcription_config") or {}
    language = config.get("language")
    if language and language != "auto":
        return str(language)
    identification = metadata.get("language_identification") or {}
    results = identification.get("results") or []
    if results and isinstance(results[0], dict) and results[0].get("alternatives"):
        best = results[0]["alternatives"][0]
        if isinstance(best, dict) and best.get("language"):
            return str(best["language"])
    # Per-word language tags (code-switching) — take the dominant one.
    languages = [
        alternative.get("language")
        for result in payload.get("results", [])
        for alternative in (result.get("alternatives") or [])[:1]
        if alternative.get("language")
    ]
    if languages:
        return max(set(languages), key=languages.count)
    return None


def _speechmatics_confidence(payload: dict) -> float | None:
    confidences = [
        alternative.get("confidence")
        for result in payload.get("results", [])
        for alternative in (result.get("alternatives") or [])[:1]
        if isinstance(alternative.get("confidence"), (int, float))
    ]
    if not confidences:
        return None
    return sum(confidences) / len(confidences)
