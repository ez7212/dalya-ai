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
from pathlib import Path, PurePosixPath


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
HELPER_SCRIPT_PREFIXES = ("audit_", "migrate_")


@dataclass(frozen=True, slots=True)
class GuardResult:
    label: str
    passed: bool
    evidence: list[str]


def run_git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout


def changed_paths(base: str) -> list[str]:
    return [line for line in run_git(["diff", "--name-only", f"{base}..HEAD"]).splitlines() if line]


def changed_paths_from_fixture(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def diff_text(base: str) -> str:
    return run_git(["diff", f"{base}..HEAD"])


def diff_text_from_fixture(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def is_helper_script(path: str) -> bool:
    parsed_path = PurePosixPath(path)
    return (
        parsed_path.parent == PurePosixPath("scripts")
        and parsed_path.suffix == ".py"
        and parsed_path.name.startswith(HELPER_SCRIPT_PREFIXES)
    )


def helper_script_paths(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if is_helper_script(path))


def load_helper_script_allowlist(path: Path | None) -> tuple[set[str], list[str]]:
    if path is None:
        return set(), []
    try:
        raw_allowlist = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return set(), [f"{path}: invalid JSON ({exc.msg})"]
    if not isinstance(raw_allowlist, dict):
        return set(), [f"{path}: expected a JSON object"]
    raw_entries = raw_allowlist.get("allowed_helper_script_edits")
    if not isinstance(raw_entries, list):
        return set(), [f"{path}: missing allowed_helper_script_edits list"]

    allowed_paths: set[str] = set()
    errors: list[str] = []
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            errors.append(f"{path}: entry {index} is not an object")
            continue
        raw_path = raw_entry.get("path")
        raw_rationale = raw_entry.get("rationale")
        if not isinstance(raw_path, str) or not is_helper_script(raw_path):
            errors.append(f"{path}: entry {index} has invalid helper path")
            continue
        if not isinstance(raw_rationale, str) or not raw_rationale.strip():
            errors.append(f"{path}: entry {index} has empty rationale")
            continue
        allowed_paths.add(raw_path)
    return allowed_paths, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--changed-paths-fixture", type=Path)
    parser.add_argument("--diff-fixture", type=Path)
    parser.add_argument("--helper-script-allowlist", type=Path)
    args = parser.parse_args()

    paths = changed_paths_from_fixture(args.changed_paths_fixture) if args.changed_paths_fixture else changed_paths(args.base)
    diff = diff_text_from_fixture(args.diff_fixture) if args.diff_fixture else diff_text(args.base)
    text = added_diff_text(diff)
    prefix_hits = path_prefix_hits(paths)
    locks = lockfile_hits(paths)
    markers = marker_hits(text)
    owner_dashboard_hits = [path for path in paths if "owner" in path.lower() and "dashboard" in path.lower()]
    provider_replacement_hits = [path for path in paths if "dialog360" in path.lower() or "360dialog" in path.lower()]
    allowed_helpers, allowlist_errors = load_helper_script_allowlist(args.helper_script_allowlist)
    helper_paths = helper_script_paths(paths)
    unapproved_helper_paths = [path for path in helper_paths if path not in allowed_helpers]
    approved_helper_paths = [path for path in helper_paths if path in allowed_helpers]

    results = (
        GuardResult("no env or migration path edits", not prefix_hits, prefix_hits),
        GuardResult("no dependency lockfile edits", not locks, locks),
        GuardResult("no DDL/RLS/role/readiness-forbidden diff markers", not markers, markers),
        GuardResult("no owner-dashboard expansion", not owner_dashboard_hits, owner_dashboard_hits),
        GuardResult("no Telegram replacement provider implementation", not provider_replacement_hits, provider_replacement_hits),
        GuardResult("helper-script allowlist is well formed", not allowlist_errors, allowlist_errors),
        GuardResult(
            "approved audit/migrate helper-script edits only",
            not unapproved_helper_paths,
            unapproved_helper_paths if unapproved_helper_paths else approved_helper_paths,
        ),
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
