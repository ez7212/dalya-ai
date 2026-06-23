#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# ///
# --- How to run ---
# python3 scripts/verify_next_mvp_scope_guard.py \
#   --base 3482a7fb863c542836fa2aabef707ad8fd503b71 \
#   --output .omo/evidence/final-next-mvp-scope-guard.json

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKFILE_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb", "uv.lock"}
FORBIDDEN_PATH_PREFIXES = ("supabase/migrations/", "migrations/")
FORBIDDEN_ENV_PATHS = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    "frontend/.env",
    "frontend/.env.local",
    "frontend/.env.production",
    "frontend/.env.staging",
}
FORBIDDEN_DIFF_MARKERS = (
    "ENABLE ROW " + "LEVEL SECURITY",
    "ALTER " + "TABLE",
    "ALTER " + "ROLE",
    "CREATE " + "ROLE",
    "CREATE " + "POLICY",
    "DROP " + "POLICY",
    "Task 10b " + "complete",
    "production " + "ready",
    "live data " + "ready",
    "external brokerage pilot " + "ready",
    "360dialog " + "ready",
    "BSP " + "ready",
    "Telegram " + "enabled",
)


@dataclass(frozen=True, slots=True)
class GuardResult:
    label: str
    passed: bool
    evidence: list[str]


def run_git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout


def changed_paths(base: str) -> list[str]:
    return [line for line in run_git(["diff", "--name-only", f"{base}..HEAD"]).splitlines() if line]


def diff_text(base: str) -> str:
    return run_git(["diff", f"{base}..HEAD"])


def added_diff_text(text: str) -> str:
    return "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def path_prefix_hits(paths: list[str]) -> list[str]:
    return [path for path in paths if path in FORBIDDEN_ENV_PATHS or path.startswith(FORBIDDEN_PATH_PREFIXES)]


def lockfile_hits(paths: list[str]) -> list[str]:
    return [path for path in paths if Path(path).name in LOCKFILE_NAMES]


def marker_hits(text: str) -> list[str]:
    lower_text = text.lower()
    return [marker for marker in FORBIDDEN_DIFF_MARKERS if marker.lower() in lower_text]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = changed_paths(args.base)
    text = added_diff_text(diff_text(args.base))
    prefix_hits = path_prefix_hits(paths)
    locks = lockfile_hits(paths)
    markers = marker_hits(text)
    owner_dashboard_hits = [path for path in paths if "owner" in path.lower() and "dashboard" in path.lower()]
    provider_replacement_hits = [path for path in paths if "dialog360" in path.lower() or "360dialog" in path.lower()]

    results = (
        GuardResult("no env or migration path edits", not prefix_hits, prefix_hits),
        GuardResult("no dependency lockfile edits", not locks, locks),
        GuardResult("no DDL/RLS/role/readiness-forbidden diff markers", not markers, markers),
        GuardResult("no owner-dashboard expansion", not owner_dashboard_hits, owner_dashboard_hits),
        GuardResult("no Telegram replacement provider implementation", not provider_replacement_hits, provider_replacement_hits),
    )
    payload = {
        "scenario": "F4 next MVP scope fidelity guard",
        "base": args.base,
        "changed_path_count": len(paths),
        "passed": all(result.passed for result in results),
        "results": [asdict(result) for result in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
