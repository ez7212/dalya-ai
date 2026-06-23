from __future__ import annotations

from scripts.compare_deal_readiness_ranking import (
    MAX_PROPOSED_DELTA,
    MIN_PROPOSED_DELTA,
    build_comparison_rows,
    calibration_scenarios,
    render_markdown_report,
)


def test_current_urgency_order_remains_separate_from_readiness_proposal():
    rows = build_comparison_rows(calibration_scenarios())

    current_order = [row.name for row in sorted(rows, key=lambda row: row.current_urgency, reverse=True)]
    proposed_order = [row.name for row in sorted(rows, key=lambda row: row.proposed_score, reverse=True)]

    assert current_order[:3] == [
        "recent_light_follow_up",
        "stale_high_engagement_follow_up",
        "viewing_ready_lower_urgency",
    ]
    assert proposed_order[:3] == [
        "viewing_ready_lower_urgency",
        "offer_ready_agent_review",
        "recent_light_follow_up",
    ]


def test_proposed_readiness_deltas_are_bounded_and_do_not_replace_urgency():
    rows = build_comparison_rows(calibration_scenarios())

    assert all(MIN_PROPOSED_DELTA <= row.proposed_delta <= MAX_PROPOSED_DELTA for row in rows)
    assert rows[0].proposed_score == rows[0].current_urgency + rows[0].proposed_delta
    assert max(row.proposed_delta for row in rows) <= 15
    assert min(row.proposed_delta for row in rows) >= -5


def test_examples_document_future_moves_and_non_moves():
    rows = {row.name: row for row in build_comparison_rows(calibration_scenarios())}

    assert rows["viewing_ready_lower_urgency"].future_expectation == "should_move_up"
    assert rows["offer_ready_agent_review"].future_expectation == "should_move_up"
    assert rows["recent_light_follow_up"].future_expectation == "should_not_dominate"
    assert rows["missing_readiness_fallback"].proposed_delta == 0
    assert rows["legal_question_agent_takeover"].proposed_delta == 0


def test_named_failure_cases_cover_task_9a_guardrails():
    rows = build_comparison_rows(calibration_scenarios())
    failure_cases = {row.failure_case for row in rows}

    assert "recency_only_false_positive" in failure_cases
    assert "missing_readiness_fallback" in failure_cases
    assert "agent_takeover_no_autonomous_boost" in failure_cases
    assert "complete_but_low_intent_profile" in failure_cases


def test_markdown_report_contains_required_calibration_sections():
    report = render_markdown_report(build_comparison_rows(calibration_scenarios()))

    assert "| Current urgency rank | Proposed readiness rank | Scenario |" in report
    assert "## Proposed Bounded Weights" in report
    assert "## Named Failure Cases" in report
    assert "No production ranking behavior changes in Task 9A." in report
