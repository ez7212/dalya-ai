from pathlib import Path

import pytest

from scripts import chatbot_full_test as suite


pytestmark = pytest.mark.no_db


def _write_publishable_report(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "_aggregate.json").write_text("{}", encoding="utf-8")
    (directory / "index.html").write_text("<html>full report</html>", encoding="utf-8")
    (directory / "_progress.log").write_text("transient", encoding="utf-8")


def test_publish_successful_run_replaces_single_stable_report_dir(tmp_path):
    work_dir = tmp_path / "work"
    final_dir = tmp_path / "chatbot_test_multitenant"
    _write_publishable_report(work_dir)
    final_dir.mkdir()
    (final_dir / "index.html").write_text("<html>old report</html>", encoding="utf-8")
    (final_dir / "stale.txt").write_text("old", encoding="utf-8")

    html_path = suite.publish_successful_run(
        work_dir,
        final_dir,
        completed=24,
        total=24,
    )

    assert html_path == (final_dir / "index.html").resolve()
    assert not work_dir.exists()
    assert (final_dir / "index.html").read_text(encoding="utf-8") == "<html>full report</html>"
    assert not (final_dir / "_progress.log").exists()
    assert not (final_dir / "stale.txt").exists()


def test_publish_successful_run_requires_index_html(tmp_path):
    work_dir = tmp_path / "work"
    final_dir = tmp_path / "chatbot_test_multitenant"
    work_dir.mkdir()
    (work_dir / "_aggregate.json").write_text("{}", encoding="utf-8")
    final_dir.mkdir()
    (final_dir / "index.html").write_text("<html>old report</html>", encoding="utf-8")

    with pytest.raises(RuntimeError, match="index.html"):
        suite.publish_successful_run(work_dir, final_dir, completed=24, total=24)

    assert work_dir.exists()
    assert (final_dir / "index.html").read_text(encoding="utf-8") == "<html>old report</html>"


def test_publish_successful_run_rejects_incomplete_persona_run(tmp_path):
    work_dir = tmp_path / "work"
    final_dir = tmp_path / "chatbot_test_multitenant"
    _write_publishable_report(work_dir)

    with pytest.raises(RuntimeError, match="incomplete"):
        suite.publish_successful_run(work_dir, final_dir, completed=23, total=24)

    assert work_dir.exists()
    assert not final_dir.exists()


def test_prepare_run_output_dir_refuses_final_output_dir(tmp_path):
    final_dir = tmp_path / "chatbot_test_multitenant"

    with pytest.raises(RuntimeError, match="must not equal"):
        suite.prepare_run_output_dir(final_dir, final_dir)


def test_parse_persona_selector_supports_ranges():
    assert suite.parse_persona_selector("2,14,19-21") == {2, 14, 19, 20, 21}


def test_expand_persona_dependencies_includes_prerequisites():
    selected = suite.expand_persona_dependencies(
        {20},
        [
            {"idx": 1},
            {"idx": 18, "depends_on": [1]},
            {"idx": 20, "depends_on": [1, 18]},
        ],
    )

    assert selected == {1, 18, 20}


def test_build_escalation_thread_metrics_counts_threads_categories_and_expectation_failures():
    results = [
        {
            "persona": "Buyer A",
            "phone": "+971501010001",
            "listing_id": "listing-a",
            "checks": [
                {"check": "offer_escalation_t3", "pass": False},
                {"check": "t4_no_escalation", "pass": False},
            ],
        },
        {
            "persona": "Buyer B",
            "phone": "+971501010002",
            "listing_id": "listing-b",
            "checks": [],
        },
    ]
    rows = [
        {
            "buyer_phone": "+971501010001",
            "listing_id": "listing-a",
            "category": "fees_and_charges",
            "state": "open",
            "escalation_type": "info_gap",
            "question_count": 3,
            "bypassed": False,
        },
        {
            "buyer_phone": "+971501010002",
            "listing_id": "listing-b",
            "category": "offer",
            "state": "open",
            "escalation_type": "offer",
            "question_count": 1,
            "bypassed": True,
        },
    ]

    metrics = suite.build_escalation_thread_metrics(rows, results)

    assert metrics["thread_count"] == 2
    assert metrics["question_count"] == 4
    assert metrics["avg_questions_per_thread"] == 2
    assert metrics["append_rate"] == 0.5
    assert metrics["debounce_bundle_rate"] == 0.5
    assert metrics["bypass_rate"] == 0.5
    assert metrics["category_distribution"] == {"fees_and_charges": 1, "offer": 1}
    assert metrics["false_negative_threads"] == 1
    assert metrics["false_positive_threads"] == 1
    buyer_a = next(item for item in metrics["personas"] if item["persona"] == "Buyer A")
    assert buyer_a["thread_count"] == 1
    assert buyer_a["append_rate"] == 0.6667


def test_generate_report_renders_escalation_thread_metrics(tmp_path):
    report_dir = tmp_path / "chatbot_test_multitenant_subset"
    report_dir.mkdir()
    aggregate = {
        "run_at": "2026-06-06T00:00:00",
        "total_personas": 1,
        "completed": 1,
        "fleet_quality_metrics": {},
        "escalation_thread_metrics": {
            "thread_count": 1,
            "question_count": 2,
            "avg_questions_per_thread": 2,
            "append_rate": 0.5,
            "debounce_bundle_rate": 1,
            "bypass_rate": 0,
            "timeout_rate": 0,
            "false_positive_threads": 0,
            "false_negative_threads": 0,
            "category_distribution": {"fees_and_charges": 1},
            "personas": [],
        },
    }
    persona = {
        "idx": 2,
        "slug": "buyer-a",
        "persona": "Buyer A",
        "phone": "+971501010001",
        "listing_id": "listing-a",
        "turns": [],
        "checks": [],
        "issues_found": [],
        "escalation_turns": [],
        "quality_metrics": {},
        "escalation_thread_metrics": {
            "thread_count": 1,
            "question_count": 2,
            "avg_questions_per_thread": 2,
            "append_rate": 0.5,
            "debounce_bundle_rate": 1,
            "bypass_rate": 0,
            "timeout_rate": 0,
            "false_positive_threads": 0,
            "false_negative_threads": 0,
            "category_distribution": {"fees_and_charges": 1},
        },
    }
    (report_dir / "_aggregate.json").write_text(__import__("json").dumps(aggregate), encoding="utf-8")
    (report_dir / "persona_02_buyer-a.json").write_text(__import__("json").dumps(persona), encoding="utf-8")

    from scripts.generate_test_report import generate_report

    html_path = generate_report(report_dir)
    html = html_path.read_text(encoding="utf-8")

    assert "Escalation Thread Metrics" in html
    assert "fees_and_charges" in html
    assert "Append rate" in html
