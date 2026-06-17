from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Optional

import anthropic
from pydantic import BaseModel, Field


UNIT_PROFILE_CATEGORIES = [
    "layout",
    "condition",
    "view",
    "building_community_quirks",
    "ac_utilities",
    "parking",
    "neighbor_situation",
    "agent_subjective_notes",
]


class StructuredUnitProfile(BaseModel):
    layout: list[str] = Field(default_factory=list)
    condition: list[str] = Field(default_factory=list)
    view: list[str] = Field(default_factory=list)
    building_community_quirks: list[str] = Field(default_factory=list)
    ac_utilities: list[str] = Field(default_factory=list)
    parking: list[str] = Field(default_factory=list)
    neighbor_situation: list[str] = Field(default_factory=list)
    agent_subjective_notes: list[str] = Field(default_factory=list)
    provenance: str = "agent-authored"
    last_updated_at: Optional[str] = None


class UnitProfileStructurer:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("UNIT_PROFILE_CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
        self.client = anthropic.Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None

    def structure(
        self,
        transcript: str,
        *,
        existing_profile: Optional[dict[str, Any]] = None,
    ) -> StructuredUnitProfile:
        if self.client:
            try:
                return self._structure_with_claude(transcript, existing_profile or {})
            except Exception:
                pass
        return structure_unit_profile_deterministic(transcript, existing_profile=existing_profile)

    def _structure_with_claude(
        self,
        transcript: str,
        existing_profile: dict[str, Any],
    ) -> StructuredUnitProfile:
        prompt = f"""
You structure Dubai real estate agent inspection dictation into a listing unit profile.

Return only JSON with these keys:
layout, condition, view, building_community_quirks, ac_utilities, parking, neighbor_situation, agent_subjective_notes.

Each value must be a list of concise factual strings. Preserve specific nouns and numbers.
Do not invent facts. Keep subjective impressions only in agent_subjective_notes.

Existing profile JSON:
{json.dumps(existing_profile, ensure_ascii=False)}

New dictation transcript:
{transcript}
""".strip()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=900,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        data = json.loads(_extract_json_object(text))
        merged = merge_unit_profiles(existing_profile, data)
        return StructuredUnitProfile.model_validate(merged)


def structure_unit_profile_deterministic(
    transcript: str,
    *,
    existing_profile: Optional[dict[str, Any]] = None,
) -> StructuredUnitProfile:
    text = " ".join((transcript or "").split())
    profile: dict[str, list[str]] = {key: [] for key in UNIT_PROFILE_CATEGORIES}
    sentences = _split_sentences(text)
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ["bedroom", "layout", "kitchen", "maid", "study", "window"]):
            profile["layout"].append(sentence)
        if any(word in lower for word in ["upgrade", "upgraded", "condition", "wear", "snag", "counter", "quartz"]):
            profile["condition"].append(sentence)
        if any(word in lower for word in ["view", "facing", "sun", "sunset", "morning", "afternoon"]):
            profile["view"].append(sentence)
        if any(word in lower for word in ["elevator", "lift", "building", "community", "corridor", "breaks down"]):
            profile["building_community_quirks"].append(sentence)
        if any(word in lower for word in ["ac", "a/c", "daikin", "dewa", "chiller", "water pressure", "utilities"]):
            profile["ac_utilities"].append(sentence)
        if any(word in lower for word in ["parking", "basement", "garage", "bay", "assigned"]):
            profile["parking"].append(sentence)
        if any(word in lower for word in ["neighbor", "neighbour", "next door", "above", "below"]):
            profile["neighbor_situation"].append(sentence)
        if any(word in lower for word in ["feels", "i think", "my view", "best", "worst", "subjective"]):
            profile["agent_subjective_notes"].append(sentence)

    merged = merge_unit_profiles(existing_profile or {}, profile)
    return StructuredUnitProfile.model_validate(merged)


def merge_unit_profiles(
    existing_profile: Optional[dict[str, Any]],
    incoming_profile: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in UNIT_PROFILE_CATEGORIES:
        values: list[str] = []
        for source in [existing_profile or {}, incoming_profile or {}]:
            raw_values = source.get(key) or []
            if isinstance(raw_values, str):
                raw_values = [raw_values]
            for item in raw_values:
                value = str(item).strip()
                if value and value not in values:
                    values.append(value)
        merged[key] = values
    merged["provenance"] = "agent-authored"
    merged["last_updated_at"] = datetime.utcnow().isoformat()
    return merged


def append_unit_profile_history(
    existing_history: Optional[list[dict[str, Any]]],
    *,
    transcript: str,
    structured_profile: StructuredUnitProfile,
    source: str,
    agent_user_id: Optional[str],
    audio_url: Optional[str] = None,
    transcription_metadata: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    history = list(existing_history or [])
    history.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "agent_user_id": agent_user_id,
            "audio_url": audio_url,
            "transcript": transcript,
            "structured_delta": structured_profile.model_dump(),
            "provenance": "agent-authored",
            "transcription": transcription_metadata or {},
        }
    )
    return history


def format_unit_profile_for_prompt(unit_profile: Optional[dict[str, Any]]) -> str:
    if not unit_profile:
        return ""
    lines: list[str] = []
    labels = {
        "layout": "Layout",
        "condition": "Condition",
        "view": "View",
        "building_community_quirks": "Building/community quirks",
        "ac_utilities": "AC and utilities",
        "parking": "Parking",
        "neighbor_situation": "Neighbor situation",
        "agent_subjective_notes": "Agent subjective notes",
    }
    for key in UNIT_PROFILE_CATEGORIES:
        values = unit_profile.get(key) or []
        if isinstance(values, str):
            values = [values]
        clean_values = [str(v).strip() for v in values if str(v).strip()]
        if clean_values:
            lines.append(f"{labels[key]}:")
            lines.extend(f"- {value}" for value in clean_values)
    return "\n".join(lines)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|,\s+(?=(?:AC|A/C|the|two|one|master|kitchen|elevator|parking)\b)", text)
    return [part.strip(" .") + "." for part in parts if part.strip(" .")]


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in structuring response")
    return text[start:end + 1]
