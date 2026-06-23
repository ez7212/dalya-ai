# /// script
# requires-python = ">=3.11"
# ///
# ─── How to run ───
# PYTHONPATH=. python3 scripts/compare_deal_readiness_ranking.py --output .omo/evidence/task-9a-deal-readiness-calibration.md
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping, Sequence

from app.core.deal_readiness import DealReadinessProfile, NextBestAction, ReadinessStage, compute_readiness

FieldValue = str | int | float | bool | tuple[str, ...]
FieldMap = Mapping[str, FieldValue]

MIN_PROPOSED_DELTA: Final = -5
MAX_PROPOSED_DELTA: Final = 15

_STAGE_DELTAS: Final[Mapping[ReadinessStage, int]] = {
    ReadinessStage.NEW: 0,
    ReadinessStage.PARTIALLY_QUALIFIED: 0,
    ReadinessStage.QUALIFIED: 4,
    ReadinessStage.HOT: 8,
    ReadinessStage.VIEWING_READY: 10,
    ReadinessStage.OFFER_READY: 12,
    ReadinessStage.AGENT_TAKEOVER_REQUIRED: 0,
}
_ACTION_DELTAS: Final[Mapping[NextBestAction, int]] = {
    NextBestAction.PREPARE_VIEWING_BRIEF: 3, NextBestAction.PREPARE_OFFER_CONTEXT: 3, NextBestAction.AGENT_CALL_NOW: 2
}


@dataclass(frozen=True, slots=True)
class CalibrationScenario:
    name: str
    description: str
    current_urgency: int
    current_signal: str
    current_next_action: str
    fields: FieldMap
    conversation_ctx: Mapping[str, bool]
    listing_ctx: Mapping[str, str]
    future_expectation: str
    failure_case: str


@dataclass(frozen=True, slots=True)
class ComparisonRow:
    name: str
    description: str
    current_urgency: int
    current_signal: str
    current_next_action: str
    readiness_stage: str
    readiness_score: int
    readiness_action: str
    proposed_delta: int
    proposed_score: int
    future_expectation: str
    failure_case: str


def calibration_scenarios() -> tuple[CalibrationScenario, ...]:
    base_qualified: FieldMap = {
        "budget_max_aed": 3_000_000,
        "financing": "cash",
        "purpose": "end_user",
        "timeline": "this month",
        "target_areas": ("Dubai Hills",),
        "property_type": "villa",
        "other_agent_status": "not_working_with_agent",
    }
    return (
        CalibrationScenario(
            name="recent_light_follow_up",
            description="Recent buyer reply with only budget captured.",
            current_urgency=88,
            current_signal="budget_matched",
            current_next_action="follow_up",
            fields={"budget_max_aed": 2_200_000},
            conversation_ctx={"responsive": True},
            listing_ctx={"listing_id": "listing-1"},
            future_expectation="should_not_dominate",
            failure_case="recency_only_false_positive",
        ),
        CalibrationScenario(
            name="stale_high_engagement_follow_up",
            description="Qualified buyer is engaged but has no concrete viewing or offer intent.",
            current_urgency=82,
            current_signal="stale_follow_up",
            current_next_action="follow_up",
            fields=base_qualified,
            conversation_ctx={"responsive": False},
            listing_ctx={"listing_id": "listing-1"},
            future_expectation="should_not_dominate",
            failure_case="complete_but_low_intent_profile",
        ),
        CalibrationScenario(
            name="viewing_ready_lower_urgency",
            description="Buyer has budget, funding, viewing availability, and a concrete viewing ask.",
            current_urgency=76,
            current_signal="ready_to_view",
            current_next_action="book_viewing",
            fields={**base_qualified, "viewing_availability": "tomorrow afternoon", "in_dubai_now": "yes"},
            conversation_ctx={"responsive": True, "viewing_intent": True},
            listing_ctx={"listing_id": "listing-1"},
            future_expectation="should_move_up",
            failure_case="viewing_ready_under_ranked",
        ),
        CalibrationScenario(
            name="offer_ready_agent_review",
            description="Buyer is offer-ready and needs agent review, not autonomous negotiation.",
            current_urgency=74,
            current_signal="firm_offer",
            current_next_action="review_offer",
            fields={
                **base_qualified,
                "decision_makers": "sole buyer",
                "viewing_availability": "flexible today",
            },
            conversation_ctx={"responsive": True, "offer_intent": True},
            listing_ctx={"listing_id": "listing-1"},
            future_expectation="should_move_up",
            failure_case="offer_ready_under_ranked",
        ),
        CalibrationScenario(
            name="legal_question_agent_takeover",
            description="Legal/process question needs agent or verified-facts handling before ranking boost.",
            current_urgency=71,
            current_signal="needs_agent",
            current_next_action="escalate",
            fields={**base_qualified, "viewing_availability": "today"},
            conversation_ctx={"responsive": True, "legal_question": True},
            listing_ctx={"listing_id": "listing-1"},
            future_expectation="should_not_move",
            failure_case="agent_takeover_no_autonomous_boost",
        ),
        CalibrationScenario(
            name="missing_readiness_fallback",
            description="No resolved readiness fields; future ranking should fall back to current urgency.",
            current_urgency=68,
            current_signal="cold",
            current_next_action="follow_up",
            fields={},
            conversation_ctx={},
            listing_ctx={"listing_id": "listing-1"},
            future_expectation="fallback_only",
            failure_case="missing_readiness_fallback",
        ),
    )


def proposed_readiness_delta(profile: DealReadinessProfile) -> int:
    if profile.stage is ReadinessStage.AGENT_TAKEOVER_REQUIRED:
        return 0
    if profile.stage is ReadinessStage.NEW:
        return 0

    delta = _STAGE_DELTAS[profile.stage] + _ACTION_DELTAS.get(profile.next_best_action, 0)
    if profile.score >= 70 and profile.stage in {ReadinessStage.HOT, ReadinessStage.VIEWING_READY, ReadinessStage.OFFER_READY}:
        delta += 2
    if profile.stage in {ReadinessStage.VIEWING_READY, ReadinessStage.OFFER_READY} and (
        "budget" in profile.missing_fields or "financing" in profile.missing_fields
    ):
        delta -= 5
    return max(MIN_PROPOSED_DELTA, min(MAX_PROPOSED_DELTA, delta))


def build_comparison_rows(scenarios: Sequence[CalibrationScenario]) -> tuple[ComparisonRow, ...]:
    rows: list[ComparisonRow] = []
    for scenario in scenarios:
        profile = compute_readiness(
            scenario.fields,
            conversation_ctx=scenario.conversation_ctx,
            listing_ctx=scenario.listing_ctx,
        )
        proposed_delta = proposed_readiness_delta(profile)
        rows.append(
            ComparisonRow(
                name=scenario.name,
                description=scenario.description,
                current_urgency=scenario.current_urgency,
                current_signal=scenario.current_signal,
                current_next_action=scenario.current_next_action,
                readiness_stage=profile.stage.value,
                readiness_score=profile.score,
                readiness_action=profile.next_best_action.value,
                proposed_delta=proposed_delta,
                proposed_score=scenario.current_urgency + proposed_delta,
                future_expectation=scenario.future_expectation,
                failure_case=scenario.failure_case,
            )
        )
    return tuple(rows)


def render_markdown_report(rows: Sequence[ComparisonRow]) -> str:
    current_rank = {
        row.name: index
        for index, row in enumerate(sorted(rows, key=lambda row: row.current_urgency, reverse=True), start=1)
    }
    proposed_rank = {
        row.name: index
        for index, row in enumerate(sorted(rows, key=lambda row: row.proposed_score, reverse=True), start=1)
    }
    lines = [
        "# Task 9A DealReadiness Ranking Calibration",
        "",
        "No production ranking behavior changes in Task 9A.",
        "",
        "## Comparison Table",
        "",
        "| Current urgency rank | Proposed readiness rank | Scenario | Current urgency | Readiness | Proposed delta | Proposed score | Future expectation | Failure case |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- |",
    ]
    for row in sorted(rows, key=lambda row: current_rank[row.name]):
        lines.append(
            "| "
            f"{current_rank[row.name]} | "
            f"{proposed_rank[row.name]} | "
            f"{row.name} | "
            f"{row.current_urgency} ({row.current_signal}/{row.current_next_action}) | "
            f"{row.readiness_stage} {row.readiness_score}/100 ({row.readiness_action}) | "
            f"{row.proposed_delta:+d} | "
            f"{row.proposed_score} | "
            f"{row.future_expectation} | "
            f"{row.failure_case} |"
        )

    lines.extend(
        [
            "",
            "## Proposed Bounded Weights",
            "",
            f"- Total readiness adjustment is clamped from {MIN_PROPOSED_DELTA} to +{MAX_PROPOSED_DELTA}.",
            "- Stage proposal: qualified +4, hot +8, viewing_ready +10, offer_ready +12.",
            "- Action proposal: prepare_viewing_brief +3, prepare_offer_context +3, agent_call_now +2.",
            "- High-readiness bonus: +2 only for hot/viewing_ready/offer_ready profiles at score >= 70.",
            "- Agent-takeover and missing-readiness cases receive +0 and remain fallback/current-urgency led.",
            "- Viewing/offer profiles missing budget or financing receive a blocker penalty before clamping.",
            "",
            "## Named Failure Cases",
            "",
        ]
    )
    for row in sorted(rows, key=lambda row: row.failure_case):
        lines.append(f"- `{row.failure_case}`: {row.description}")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Comparator reads only deterministic DealReadiness signals.",
            "- Hot-list urgency remains the authoritative current ordering for this task.",
            "- No task creation, queue ordering, send behavior, UI priority semantics, migrations, RLS, or live writes changed.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(output: Path) -> None:
    rows = build_comparison_rows(calibration_scenarios())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown_report(rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_report(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
