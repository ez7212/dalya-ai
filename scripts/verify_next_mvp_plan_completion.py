#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# --- How to run ---
# python3 scripts/verify_next_mvp_plan_completion.py \
#   --plan .omo/plans/dalya-next-mvp-readiness-plan.md \
#   --evidence-dir .omo/evidence \
#   --output .omo/evidence/final-next-mvp-plan-compliance.json

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class TaskExpectation:
    task_id: str
    title: str
    pr_number: int
    branch: str
    merge_commit: str
    evidence_globs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TaskResult:
    task_id: str
    title: str
    pr_number: int
    merge_commit: str
    plan_checked: bool
    merge_present: bool
    evidence_paths: list[str]
    local_branch_absent: bool
    passed: bool


TASKS: tuple[TaskExpectation, ...] = (
    TaskExpectation("1", "Today Queue escalation routing", 54, "codex/fix-today-queue-escalation-route", "7167d9e", ("task-1-dalya-next-mvp-readiness-plan.md", "task-1-escalation-route.png")),
    TaskExpectation("2", "Live dashboard fallback", 55, "codex/remove-live-dashboard-fallback", "d68185a", ("task-2-dalya-next-mvp-readiness-plan.md", "task-2-dashboard-fallback.png")),
    TaskExpectation("3", "Legacy Telegram removal", 56, "codex/remove-legacy-telegram", "bf04efe", ("task-3-dalya-next-mvp-readiness-plan.md", "task-3-telegram-routes.json")),
    TaskExpectation("4", "CORS by environment", 57, "codex/restrict-cors-by-env", "fc5a79e", ("task-4-dalya-next-mvp-readiness-plan.md", "task-4-cors.json")),
    TaskExpectation("5", "Seller lead PII", 58, "codex/anonymize-seller-leads", "44748c9", ("task-5-dalya-next-mvp-readiness-plan.md",)),
    TaskExpectation("6", "Verified Facts output gate", 59, "codex/verified-facts-output-gate", "fc07406", ("task-6-dalya-next-mvp-readiness-plan.md", "task-6-verified-facts-output.json")),
    TaskExpectation("7", "Verified Facts seed expansion", 60, "codex/expand-verified-facts-seed", "e40ef21", ("task-7-dalya-next-mvp-readiness-plan.md",)),
    TaskExpectation("8", "Chatbot regression", 61, "codex/chatbot-regression-current-state", "303ce63", ("task-8-chatbot-regression.json",)),
    TaskExpectation("9A", "DealReadiness calibration", 62, "codex/calibrate-deal-readiness-ranking", "3511d97", ("task-9a-deal-readiness-calibration.md",)),
    TaskExpectation("9B", "Bounded DealReadiness ranking", 63, "codex/bound-deal-readiness-ranking", "9895268", ("task-9b-dalya-next-mvp-readiness-plan.md",)),
    TaskExpectation("10", "needs_reply priority", 64, "codex/prioritize-needs-reply-intent", "1b0c9d3", ("task-10-dalya-next-mvp-readiness-plan.md",)),
    TaskExpectation("11", "Handoff action cards", 65, "codex/upgrade-handoff-action-cards", "bb45281", ("task-11-dalya-next-mvp-readiness-plan.md", "task-11-handoff-cards.png")),
    TaskExpectation("12", "First-run activation", 66, "codex/agent-first-run-activation", "24ca573", ("task-12-dalya-next-mvp-readiness-plan.md", "task-12-first-run-desktop.png", "task-12-first-run-mobile.png")),
)


def run_git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout


def plan_has_checked_task(plan_text: str, task_id: str) -> bool:
    variants = (task_id, task_id.lower())
    return any(f"- [x] {variant}." in plan_text for variant in variants)


def non_empty_matches(evidence_dir: Path, globs: tuple[str, ...]) -> list[str]:
    paths: list[str] = []
    for pattern in globs:
        for path in sorted(evidence_dir.glob(pattern)):
            if path.is_dir() or path.stat().st_size > 0:
                paths.append(str(path.relative_to(ROOT)))
    return paths


def build_result(task: TaskExpectation, plan_text: str, log_text: str, branches_text: str, evidence_dir: Path) -> TaskResult:
    evidence_paths = non_empty_matches(evidence_dir, task.evidence_globs)
    plan_checked = plan_has_checked_task(plan_text, task.task_id)
    merge_present = task.merge_commit in log_text and f"#{task.pr_number}" in log_text
    local_branch_absent = task.branch not in branches_text
    passed = plan_checked and merge_present and bool(evidence_paths) and local_branch_absent
    return TaskResult(
        task_id=task.task_id,
        title=task.title,
        pr_number=task.pr_number,
        merge_commit=task.merge_commit,
        plan_checked=plan_checked,
        merge_present=merge_present,
        evidence_paths=evidence_paths,
        local_branch_absent=local_branch_absent,
        passed=passed,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    plan_text = args.plan.read_text(encoding="utf-8")
    log_text = run_git(["log", "--oneline", "--first-parent", "-40"])
    branches_text = run_git(["branch", "--list"])
    results = [build_result(task, plan_text, log_text, branches_text, args.evidence_dir.resolve()) for task in TASKS]
    task13_ready = all((ROOT / path).exists() for path in (
        "scripts/verify_next_mvp_plan_completion.py",
        "scripts/review_next_mvp_final_diff.py",
        "scripts/verify_next_mvp_scope_guard.py",
        "frontend/scripts/verify-next-mvp-final-surface.mjs",
    )) and any((ROOT / "reports").glob("dalya-next-mvp-readiness-closeout-*.md"))

    payload = {
        "scenario": "F1 plan compliance audit for Tasks 1-12 plus 9A/9B and Task 13 closeout assets",
        "passed": all(result.passed for result in results) and task13_ready,
        "task13_closeout_assets_present": task13_ready,
        "results": [asdict(result) for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
