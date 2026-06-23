from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Optional, Protocol

from app.core.deal_readiness import (
    DealReadinessProfile,
    NextBestAction,
    ReadinessStage,
    compute_readiness,
    fields_from_effective_fields,
    serialize_readiness,
)

if TYPE_CHECKING:
    from app.models.db_models import DBConversation


MAX_READINESS_RANKING_DELTA: Final = 15

_STAGE_RANKING_DELTAS: Final = {
    ReadinessStage.HOT: 8,
    ReadinessStage.VIEWING_READY: 10,
    ReadinessStage.OFFER_READY: 12,
}

_ACTION_RANKING_DELTAS: Final = {
    NextBestAction.PREPARE_VIEWING_BRIEF: 3,
    NextBestAction.PREPARE_OFFER_CONTEXT: 3,
    NextBestAction.AGENT_CALL_NOW: 2,
}

_STAGE_REASON_LABELS: Final = {
    ReadinessStage.HOT: "Hot",
    ReadinessStage.VIEWING_READY: "Viewing-ready",
    ReadinessStage.OFFER_READY: "Offer-ready",
}


@dataclass(frozen=True, slots=True)
class ReadinessRankingInput:
    delta: int
    reason: Optional[str]


class HotListScoreLike(Protocol):
    signal: str
    urgency_score: int
    next_action: str
    base_urgency_score: Optional[int]
    readiness_ranking_delta: Optional[int]


def readiness_ranking_input(profile: DealReadinessProfile) -> ReadinessRankingInput:
    if profile.stage not in _STAGE_RANKING_DELTAS:
        return ReadinessRankingInput(delta=0, reason=None)
    if "budget" in profile.missing_fields or "financing" in profile.missing_fields:
        return ReadinessRankingInput(delta=0, reason=None)

    delta = _STAGE_RANKING_DELTAS[profile.stage] + _ACTION_RANKING_DELTAS.get(
        profile.next_best_action,
        0,
    )
    if profile.score >= 70:
        delta += 2
    bounded_delta = max(0, min(MAX_READINESS_RANKING_DELTA, delta))
    if bounded_delta == 0:
        return ReadinessRankingInput(delta=0, reason=None)

    return ReadinessRankingInput(
        delta=bounded_delta,
        reason=f"{_STAGE_REASON_LABELS[profile.stage]} DealReadiness added +{bounded_delta}.",
    )


def readiness_profile_for_hot_list(
    *,
    effective_buyer_fields: dict,
    conversation: DBConversation,
    score: HotListScoreLike,
) -> DealReadinessProfile:
    listing = conversation.listing
    fields = fields_from_effective_fields(
        effective_buyer_fields or {},
        fallback_budget_aed=conversation.detected_budget,
    )
    return compute_readiness(
        fields,
        conversation_ctx=_readiness_conversation_context(score, conversation),
        listing_ctx=(
            {
                "listing_id": listing.listing_id,
                "property_type": listing.property_type,
            }
            if listing
            else {"listing_id": conversation.listing_id}
        ),
    )


def build_hot_list_readiness_shadow(
    *,
    effective_buyer_fields: dict,
    conversation: DBConversation,
    score: HotListScoreLike,
) -> dict:
    readiness = readiness_profile_for_hot_list(
        effective_buyer_fields=effective_buyer_fields,
        conversation=conversation,
        score=score,
    )
    ranking = readiness_ranking_input(readiness)
    score_delta = getattr(score, "readiness_ranking_delta", None)
    ranking_delta = ranking.delta if score_delta is None else score_delta
    base_score = getattr(score, "base_urgency_score", None)
    if base_score is None:
        base_score = score.urgency_score
    ranked_score = max(0, min(100, base_score + ranking_delta))
    ranking_reason = ranking.reason if ranking_delta else None
    return {
        "mode": "ranking_input",
        "used_for_ranking": ranking_delta > 0,
        "ranking_delta": ranking_delta,
        "ranking_reason": ranking_reason,
        "base_urgency_score": base_score,
        "ranked_urgency_score": ranked_score,
        "used_for_thresholds": False,
        "used_for_tasks": False,
        "deal_readiness": serialize_readiness(readiness),
    }


def _readiness_conversation_context(score: HotListScoreLike, conversation: DBConversation) -> dict:
    messages = conversation.messages or []
    latest_message = messages[-1] if messages else None
    latest_text = str(latest_message.content if latest_message else "").lower()
    offer_reason = str(conversation.escalation_reason or "")
    return {
        "viewing_intent": bool(
            score.next_action == "book_viewing"
            or score.signal == "ready_to_view"
            or (latest_message and latest_message.intent == "viewing_request")
        ),
        "offer_intent": bool(
            score.next_action == "review_offer"
            or score.signal == "firm_offer"
            or offer_reason.startswith("offer:")
        ),
        "responsive": bool(latest_message and latest_message.role == "user"),
        "urgent": bool(
            (score.urgency_score or 0) >= 70
            or any(term in latest_text for term in ("urgent", "asap", "serious"))
        ),
    }
