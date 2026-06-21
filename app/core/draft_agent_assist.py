"""DAL-173C4 draft/agent-assist planning metadata.

Pure helpers for agent-visible draft context. They do not send messages, change
send policy, rank hot lists, ingest leads, or write to the database.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from app.core.deal_readiness import (
    compute_readiness,
    fields_from_effective_fields,
)
from app.core.verified_facts import (
    VerifiedFact,
    VerifiedFactRegistry,
    fact_source_label,
    verified_facts_grounding_for_message,
)


def _fact_summary(fact: VerifiedFact) -> dict[str, Any]:
    return {
        "key": fact.key,
        "category": fact.category,
        "text": fact.text,
        "source_label": fact_source_label(fact),
        "runtime_policy": fact.runtime_policy.value,
    }


def build_draft_agent_assist(
    *,
    latest_buyer_message: Optional[str],
    effective_buyer_fields: Optional[Mapping[str, Any]] = None,
    fallback_budget_aed: Optional[Any] = None,
    conversation_ctx: Optional[Mapping[str, Any]] = None,
    listing_ctx: Optional[Mapping[str, Any]] = None,
    brokerage_id: Optional[str] = None,
    verified_fact_registry: Optional[VerifiedFactRegistry] = None,
) -> dict[str, Any]:
    """Build JSON-safe, agent-visible assist metadata for review-only drafts.

    `effective_buyer_fields` should be the output of buyer_profiles.effective_fields().
    That preserves confirmed-over-inferred precedence before DealReadiness sees
    the data, so confirmed profile values are not re-asked.
    """
    grounding = verified_facts_grounding_for_message(
        latest_buyer_message,
        registry=verified_fact_registry,
        brokerage_id=brokerage_id,
    )
    direct_facts = list(getattr(grounding, "direct_facts", ()) or ())
    blocked_facts = list(getattr(grounding, "blocked_facts", ()) or ())
    missing_topics = list(getattr(grounding, "missing_topics", ()) or ())

    fields = fields_from_effective_fields(
        effective_buyer_fields or {},
        fallback_budget_aed=fallback_budget_aed,
    )
    readiness = compute_readiness(
        fields,
        conversation_ctx=conversation_ctx,
        listing_ctx=listing_ctx,
    )
    readiness_question = readiness.next_best_question
    missing_readiness_field = (
        readiness.missing_fields[0]
        if readiness_question and readiness.missing_fields
        else None
    )

    return {
        "kind": "draft_agent_assist",
        "agent_visible": True,
        "verified_facts": {
            "applies": bool(grounding),
            "verified_fact_used": bool(direct_facts),
            "facts": [_fact_summary(fact) for fact in direct_facts],
            "needs_agent_confirmation": [
                {
                    "key": fact.key,
                    "source_label": fact_source_label(fact),
                    "runtime_policy": fact.runtime_policy.value,
                    "reason": "Verified Fact exists but is not direct-answer safe for buyer-facing claims.",
                }
                for fact in blocked_facts
            ] + [
                {
                    "topic": topic,
                    "reason": "No active direct Verified Fact is available; agent confirmation is required before making a confident claim.",
                }
                for topic in missing_topics
            ],
        },
        "deal_readiness": {
            "stage": readiness.stage.value,
            "score": readiness.score,
            "priority_band": readiness.priority_band.value,
            "next_best_action": readiness.next_best_action.value,
            "missing_readiness_field": missing_readiness_field,
            "suggested_follow_up_question": readiness_question,
        },
    }
