#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# --- How to run ---
# python3 scripts/review_next_mvp_final_diff.py \
#   --base 3482a7fb863c542836fa2aabef707ad8fd503b71 \
#   --output .omo/evidence/final-next-mvp-code-review.md

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKFILE_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "requirements.lock", "uv.lock"}
FORBIDDEN_DIFF_TERMS = (
    "ENABLE ROW " + "LEVEL SECURITY",
    "CREATE " + "POLICY",
    "ALTER " + "POLICY",
    "ALTER " + "ROLE",
    "TELEGRAM" + "_BOT_TOKEN",
    "Task 10b " + "complete",
    "external brokerage pilot " + "ready",
    "live data " + "ready",
)


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    label: str
    passed: bool
    detail: str


def run_git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout


def changed_paths(base: str) -> list[str]:
    output = run_git(["diff", "--name-only", f"{base}..HEAD"])
    return [line for line in output.splitlines() if line]


def diff_text(base: str) -> str:
    return run_git(["diff", "--unified=0", f"{base}..HEAD"])


def added_diff_text(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def has_lockfile(paths: list[str]) -> list[str]:
    return [path for path in paths if Path(path).name in LOCKFILE_NAMES]


def has_migration(paths: list[str]) -> list[str]:
    return [path for path in paths if path.startswith(("migrations/", "supabase/migrations/"))]


def term_hits(text: str) -> list[str]:
    upper_text = text.upper()
    hits: list[str] = []
    for term in FORBIDDEN_DIFF_TERMS:
        haystack = upper_text if term.isupper() else text
        if term in haystack:
            hits.append(term)
    return hits


def render(finding: ReviewFinding) -> str:
    status = "PASS" if finding.passed else "FAIL"
    return f"- {status}: {finding.label} — {finding.detail}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = changed_paths(args.base)
    text = added_diff_text(diff_text(args.base))
    lockfiles = has_lockfile(paths)
    migrations = has_migration(paths)
    forbidden_hits = term_hits(text)
    final_doc_paths = [path for path in paths if path.startswith(("PROJECT_BRIEF.md", "BACKLOG.md", "docs/runbooks/", "reports/"))]
    test_paths = [path for path in paths if path.startswith(("tests/", "frontend/scripts/", "scripts/"))]

    findings = (
        ReviewFinding("narrow closeout coverage", bool(final_doc_paths) and bool(test_paths), f"{len(paths)} paths changed since base; closeout docs and verifiers are present"),
        ReviewFinding("no dependency or lockfile edits", not lockfiles, ", ".join(lockfiles) if lockfiles else "none found"),
        ReviewFinding("no migration or DDL scope", not migrations, ", ".join(migrations) if migrations else "none found"),
        ReviewFinding("no forbidden readiness or Telegram runtime terms in diff", not forbidden_hits, ", ".join(forbidden_hits) if forbidden_hits else "none found"),
        ReviewFinding("Verified Facts gate has runtime/test files in diff", any("verified_facts" in path for path in paths), "verified facts output gate and seed changes are included in merged history"),
        ReviewFinding("DealReadiness ranking has bounded task evidence in diff", any("readiness" in path.lower() for path in paths), "readiness calibration and ranking changes are included in merged history"),
    )
    passed = all(finding.passed for finding in findings)
    body = "\n".join((
        "# Final Next MVP Diff Review",
        "",
        f"Base: `{args.base}`",
        f"Compared range: `{args.base}..HEAD`",
        f"Verdict: {'PASS' if passed else 'FAIL'}",
        "",
        "## Findings",
        *[render(finding) for finding in findings],
        "",
        "## Changed path count",
        str(len(paths)),
        "",
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body, encoding="utf-8")
    print(body)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
