"""DAL-173B — DealReadinessProfile core.

A pure, deterministic helper that converts an already-resolved buyer field
snapshot (plus optional conversation/listing context) into a readiness read
model: stage, missing fields, next best action, score, and priority band.

This module has NO side effects: it does not touch the database, send messages,
or mutate hot-list / lead ranking. It is the read model described in
docs/product/verified-facts-deal-readiness-spec.md (Part 2) and
docs/product/deal-readiness-v1.md (Parts B/C). DAL-173C2 uses it only as
optional chatbot planning metadata; it does not control sends or ranking.

Input `fields` is a flat mapping of field-name -> resolved value. Callers holding
the `effective_fields()` structure should pass
`{name: row["value"] for name, row in effective.items()}`. Field names reuse the
existing QUALIFICATION_FIELDS where they exist; new readiness fields (purpose,
viewing_availability, decision_makers, in_dubai_now, ...) are read if present.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


class ReadinessStage(str, Enum):
    NEW = "new"
    PARTIALLY_QUALIFIED = "partially_qualified"
    QUALIFIED = "qualified"
    HOT = "hot"
    VIEWING_READY = "viewing_ready"
    OFFER_READY = "offer_ready"
    AGENT_TAKEOVER_REQUIRED = "agent_takeover_required"


class NextBestAction(str, Enum):
    ASK_BUDGET = "ask_budget"
    ASK_PURPOSE = "ask_purpose"
    ASK_FINANCING = "ask_financing"
    ASK_TIMELINE = "ask_timeline"
    ASK_LOCATION = "ask_location"
    ASK_OTHER_AGENT_STATUS = "ask_other_agent_status"
    ASK_VIEWING_AVAILABILITY = "ask_viewing_availability"
    SEND_OPTIONS = "send_options"
    DRAFT_FOLLOW_UP = "draft_follow_up"
    AGENT_CALL_NOW = "agent_call_now"
    ESCALATE_TO_AGENT = "escalate_to_agent"
    PREPARE_VIEWING_BRIEF = "prepare_viewing_brief"
    PREPARE_OFFER_CONTEXT = "prepare_offer_context"
    CANNOT_ANSWER_NEEDS_AGENT = "cannot_answer_needs_agent"


class PriorityBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_QUESTION_BY_ACTION = {
    NextBestAction.ASK_BUDGET: "What budget range should I keep in mind?",
    NextBestAction.ASK_PURPOSE: "Is this mainly for you to live in, as an investment, or both?",
    NextBestAction.ASK_FINANCING: "Would this be cash or mortgage-backed?",
    NextBestAction.ASK_TIMELINE: "What buying timeline are you working with?",
    NextBestAction.ASK_LOCATION: "Which areas or property type are you focused on?",
    NextBestAction.ASK_OTHER_AGENT_STATUS: "Are you already working with another agent on this search?",
    NextBestAction.ASK_VIEWING_AVAILABILITY: "What viewing window works for you?",
}


def question_for_next_best_action(action: Optional[NextBestAction | str]) -> Optional[str]:
    """Return one conversational qualification question for ask-* readiness actions."""
    if action is None:
        return None
    if not isinstance(action, NextBestAction):
        try:
            action = NextBestAction(str(action))
        except ValueError:
            return None
    return _QUESTION_BY_ACTION.get(action)


@dataclass(frozen=True)
class DealReadinessProfile:
    stage: ReadinessStage
    missing_fields: list[str]
    next_best_action: NextBestAction
    next_best_action_reason: str
    score: int
    priority_band: PriorityBand
    present_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def next_best_question(self) -> Optional[str]:
        """One askable question for chatbot planning, or None for non-question actions."""
        return question_for_next_best_action(self.next_best_action)


# Field-name groups (reuse existing QUALIFICATION_FIELDS names).
_BUDGET_FIELDS = ("budget_min_aed", "budget_max_aed", "budget")
_LOCATION_FIELDS = ("target_areas", "preferred_locations", "property_type", "bedrooms")

# Score weights — deterministic.
_WEIGHTS = {
    "budget": 20,
    "financing": 15,
    "purpose": 10,
    "timeline": 10,
    "location": 10,
    "viewing_availability": 10,
    "decision_makers": 5,
    "in_dubai_now": 5,
    "other_agent_status": 5,
    "contact_preference": 5,
}


def fields_from_effective_fields(
    fields: Mapping[str, Any],
    *,
    fallback_budget_aed: Optional[Any] = None,
) -> dict[str, Any]:
    """Flatten buyer_profiles.effective_fields() into readiness input values.

    `effective_fields()` already applies confirmed-over-inferred precedence and
    keeps conflicting AI values as suggestion chips. This adapter intentionally
    reads only the effective `value`, so readiness remains a derived read model
    and never treats suggestions as confirmed truth.
    """
    flattened: dict[str, Any] = {}
    for field, entry in (fields or {}).items():
        if not isinstance(entry, Mapping):
            continue
        value = entry.get("value")
        if value is not None:
            flattened[field] = value

    has_budget = any(
        field in flattened
        for field in ("budget_min_aed", "budget_max_aed", "budget")
    )
    if not has_budget and fallback_budget_aed is not None:
        flattened["budget_max_aed"] = fallback_budget_aed
    return flattened


def _present(value: Any) -> bool:
    """A field counts as present when it has a meaningful, non-empty value."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"unknown", "unset"}
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _any_present(fields: Mapping[str, Any], names: tuple[str, ...]) -> bool:
    return any(_present(fields.get(name)) for name in names)


def compute_readiness(
    fields: Mapping[str, Any],
    *,
    conversation_ctx: Optional[Mapping[str, Any]] = None,
    listing_ctx: Optional[Mapping[str, Any]] = None,
) -> DealReadinessProfile:
    """Derive a DealReadinessProfile from a buyer field snapshot.

    Pure and deterministic: identical inputs always produce an identical result,
    and no input is mutated. `conversation_ctx` may carry intent signals
    (viewing_intent, offer_intent, responsive, urgent, legal_question,
    agent_takeover) and `listing_ctx` indicates a specific listing of interest.
    """
    ctx = dict(conversation_ctx or {})
    listing = dict(listing_ctx or {})

    has_budget = _any_present(fields, _BUDGET_FIELDS)
    has_financing = _present(fields.get("financing"))
    has_purpose = _present(fields.get("purpose"))
    has_timeline = _present(fields.get("timeline"))
    has_location = _any_present(fields, _LOCATION_FIELDS)
    has_viewing_availability = _present(fields.get("viewing_availability"))
    has_decision_makers = _present(fields.get("decision_makers"))
    has_other_agent_status = _present(fields.get("other_agent_status"))

    purpose_value = str(fields.get("purpose") or "").strip().lower()
    is_end_user = purpose_value in {"end_use", "end_user", "both"}

    has_listing = bool(listing) or _present(fields.get("listing_id"))
    viewing_intent = bool(ctx.get("viewing_intent"))
    offer_intent = bool(ctx.get("offer_intent"))
    responsive = bool(ctx.get("responsive"))
    urgent = bool(ctx.get("urgent")) or str(fields.get("urgency") or "").lower() == "high"
    legal_question = bool(ctx.get("legal_question"))
    agent_takeover = bool(ctx.get("agent_takeover"))
    video_ok = bool(ctx.get("video_viewing_ok"))
    in_dubai = str(fields.get("in_dubai_now") or "").strip().lower()
    in_dubai_ok = in_dubai != "no" or video_ok

    # ── Score (deterministic) ──────────────────────────────────────────────
    score = 0
    if has_budget:
        score += _WEIGHTS["budget"]
    if has_financing:
        score += _WEIGHTS["financing"]
    if has_purpose:
        score += _WEIGHTS["purpose"]
    if has_timeline:
        score += _WEIGHTS["timeline"]
    if has_location:
        score += _WEIGHTS["location"]
    if has_viewing_availability:
        score += _WEIGHTS["viewing_availability"]
    if has_decision_makers:
        score += _WEIGHTS["decision_makers"]
    if _present(fields.get("in_dubai_now")):
        score += _WEIGHTS["in_dubai_now"]
    if has_other_agent_status:
        score += _WEIGHTS["other_agent_status"]
    if _present(fields.get("contact_preference")):
        score += _WEIGHTS["contact_preference"]
    if viewing_intent:
        score += 5
    if offer_intent:
        score += 10
    if urgent:
        score += 5
    if responsive:
        score += 5
    score = max(0, min(100, score))

    band = PriorityBand.HIGH if score >= 70 else PriorityBand.MEDIUM if score >= 40 else PriorityBand.LOW

    # ── Qualification gates ────────────────────────────────────────────────
    qualified = has_budget and has_financing and (has_purpose or has_location)
    partially = has_budget or has_purpose or has_financing or has_location
    other_agent_status_relevant = partially or viewing_intent or offer_intent

    # ── Stage (most-advanced first) ────────────────────────────────────────
    if agent_takeover or legal_question:
        stage = ReadinessStage.AGENT_TAKEOVER_REQUIRED
    elif offer_intent and has_budget and has_financing and has_listing:
        stage = ReadinessStage.OFFER_READY
    elif viewing_intent and has_listing and has_viewing_availability and in_dubai_ok:
        stage = ReadinessStage.VIEWING_READY
    elif qualified and (viewing_intent or offer_intent or urgent) and responsive:
        stage = ReadinessStage.HOT
    elif qualified:
        stage = ReadinessStage.QUALIFIED
    elif partially:
        stage = ReadinessStage.PARTIALLY_QUALIFIED
    else:
        stage = ReadinessStage.NEW

    # ── Missing fields ─────────────────────────────────────────────────────
    missing: list[str] = []
    if not has_budget:
        missing.append("budget")
    if not has_purpose:
        missing.append("purpose")
    if not has_financing:
        missing.append("financing")
    if not has_timeline:
        missing.append("timeline")
    if not has_location:
        missing.append("location")
    # Stage/intent-relevant fields.
    if (viewing_intent or offer_intent) and not has_viewing_availability:
        missing.append("viewing_availability")
    if (offer_intent or stage is ReadinessStage.OFFER_READY) and not has_decision_makers:
        missing.append("decision_makers")
    if other_agent_status_relevant and not has_other_agent_status:
        missing.append("other_agent_status")
    # End-users: surface family-fit fields as helpful-missing.
    if is_end_user and not _present(fields.get("family_size")):
        missing.append("family_size")

    # ── Next best action (priority order, intent overrides) ─────────────────
    if agent_takeover:
        nba, reason = NextBestAction.ESCALATE_TO_AGENT, "Agent takeover requested or required."
    elif legal_question:
        nba, reason = NextBestAction.CANNOT_ANSWER_NEEDS_AGENT, "Legal/process question needs an agent or verified facts."
    elif stage is ReadinessStage.OFFER_READY:
        nba, reason = NextBestAction.PREPARE_OFFER_CONTEXT, "Offer-ready: assemble offer context for the agent."
    elif offer_intent:
        nba, reason = NextBestAction.ESCALATE_TO_AGENT, "Offer intent detected; Dalya never negotiates autonomously."
    elif stage is ReadinessStage.VIEWING_READY:
        nba, reason = NextBestAction.PREPARE_VIEWING_BRIEF, "Viewing-ready: assemble the viewing brief."
    elif viewing_intent and not has_viewing_availability:
        nba, reason = NextBestAction.ASK_VIEWING_AVAILABILITY, "Viewing intent but no availability captured."
    elif not has_budget:
        nba, reason = NextBestAction.ASK_BUDGET, "Budget is the first qualification field."
    elif not has_purpose:
        nba, reason = NextBestAction.ASK_PURPOSE, "Capture end-use vs investment before logistics."
    elif not has_financing:
        nba, reason = NextBestAction.ASK_FINANCING, "Cash vs mortgage gates buyer strength."
    elif not has_timeline:
        nba, reason = NextBestAction.ASK_TIMELINE, "Timeline separates call-now from nurture."
    elif not has_location:
        nba, reason = NextBestAction.ASK_LOCATION, "Need a location/property focus to match stock."
    elif other_agent_status_relevant and not has_other_agent_status:
        nba, reason = (
            NextBestAction.ASK_OTHER_AGENT_STATUS,
            "Clarify whether the buyer is already working with another agent.",
        )
    elif stage is ReadinessStage.HOT:
        nba, reason = NextBestAction.AGENT_CALL_NOW, "Qualified and high-intent — call now."
    elif stage is ReadinessStage.QUALIFIED:
        nba, reason = NextBestAction.SEND_OPTIONS, "Qualified — send matching options."
    else:
        nba, reason = NextBestAction.DRAFT_FOLLOW_UP, "Soft next step; draft a follow-up for the agent."

    present_fields = {
        name: fields.get(name)
        for name in (
            *(_BUDGET_FIELDS),
            "financing",
            "purpose",
            "timeline",
            *(_LOCATION_FIELDS),
            "viewing_availability",
            "decision_makers",
            "in_dubai_now",
            "other_agent_status",
            "contact_preference",
            "family_size",
            "urgency",
        )
        if _present(fields.get(name))
    }

    return DealReadinessProfile(
        stage=stage,
        missing_fields=missing,
        next_best_action=nba,
        next_best_action_reason=reason,
        score=score,
        priority_band=band,
        present_fields=present_fields,
    )


def serialize_readiness(profile: DealReadinessProfile) -> dict:
    """JSON-safe representation for API payloads."""
    return {
        "stage": profile.stage.value,
        "missing_fields": list(profile.missing_fields),
        "next_best_action": profile.next_best_action.value,
        "next_best_action_reason": profile.next_best_action_reason,
        "score": profile.score,
        "priority_band": profile.priority_band.value,
        "present_fields": dict(profile.present_fields),
    }
