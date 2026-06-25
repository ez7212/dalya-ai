#!/usr/bin/env python3
"""
Report + matrix generator for the internal Mahoroba OMO pilot.

Reads the pilot evidence directory and renders a self-describing report that
makes MISSING evidence explicitly BLOCKED (never silently PASS). The verdict is
computed only from the execution modes that actually produced evidence.

Execution modes:
- Smoke mode  : safety gate + API smoke evidence (service/test context OK).
- Chatbot mode: scenario runner evidence (requires ANTHROPIC_API_KEY at run time).
- Browser mode: /agent browser walkthrough evidence (requires Eric auth).

Usage:
    python scripts/pilot/generate_report.py \
        --input .omo/evidence/lazycodex-omo-pilot \
        --output reports/internal_pilot/mahoroba_first_run [--final]

Exit code is always 0 — a partial run still produces a useful BLOCKED-annotated
report. The verdict (Green/Yellow/Red) is the signal, not the exit code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

# Evidence artifacts the pilot is expected to produce, keyed by logical area.
# Each entry: (relative path under --input, human label, mode it feeds).
EVIDENCE_MAP: list[tuple[str, str, str]] = [
    ("task-2-safety.json", "Phase 0 safety gate", "smoke"),
    ("listing-creation/listing-ids.json", "Dashboard listing creation (4 URLs)", "browser"),
    ("seed-summary.json", "Dependent seed summary", "smoke"),
    ("scenarios", "Buyer scenario runner", "chatbot"),
    ("task-6-api-smoke.json", "Pilot-critical API smoke", "smoke"),
    ("browser", "/agent browser walkthrough", "browser"),
    ("demo", "Golden + stress rehearsal", "chatbot"),
    ("minimal-safety.json", "Minimal safety sanity", "smoke"),
]

BLOCKED = "BLOCKED"
PRESENT = "PRESENT"


def _exists(base: Path, rel: str) -> bool:
    target = base / rel
    if target.is_dir():
        return any(target.iterdir())
    return target.is_file()


def _read_json(base: Path, rel: str) -> Optional[Any]:
    target = base / rel
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _safety_result(base: Path) -> str:
    payload = _read_json(base, "task-2-safety.json")
    if isinstance(payload, dict) and payload.get("result") in {"PASS", "FAIL"}:
        return str(payload["result"])
    return BLOCKED


def collect(base: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    modes = {"smoke": False, "chatbot": False, "browser": False}
    for rel, label, mode in EVIDENCE_MAP:
        present = _exists(base, rel)
        if present:
            modes[mode] = True
        rows.append({"label": label, "mode": mode, "status": PRESENT if present else BLOCKED, "path": rel})
    return {"rows": rows, "modes": modes, "safety": _safety_result(base)}


def verdict(collected: dict[str, Any]) -> tuple[str, str]:
    modes = collected["modes"]
    safety = collected["safety"]
    if safety == "FAIL":
        return "Red", "Phase 0 safety gate FAILED; no pilot run is valid until the environment is safe."
    browser_ready = modes["browser"]
    chatbot_ready = modes["chatbot"]
    smoke_ready = modes["smoke"]
    if browser_ready and chatbot_ready and smoke_ready:
        return "Green", "Browser, chatbot, and smoke evidence all present for review."
    if smoke_ready and (browser_ready or chatbot_ready):
        return "Yellow", "Partial run: some modes have evidence, others are blocked (see matrix)."
    return "Red", "Insufficient evidence: required modes are blocked. Supply auth/keys/seed and re-run."


def render(base: Path, collected: dict[str, Any], final: bool) -> str:
    modes = collected["modes"]
    decision, reason = verdict(collected)
    lines: list[str] = []
    lines.append("# Dalya Mahoroba First-Run Pilot Report")
    lines.append("")
    lines.append(f"_Generated from evidence at `{base}`{' (final)' if final else ' (interim)'}._")
    lines.append("")
    lines.append("## Executive Verdict")
    lines.append("")
    lines.append(f"- Verdict: **{decision}**")
    lines.append(f"- Reason: {reason}")
    lines.append("- Brokerage: `mahoroba-realty`")
    lines.append(f"- Phase 0 safety gate: {collected['safety']}")
    lines.append(f"- Smoke mode ran: {'yes' if modes['smoke'] else 'no'}")
    lines.append(f"- Chatbot mode ran: {'yes' if modes['chatbot'] else 'no'}")
    lines.append(f"- Browser mode ran: {'yes' if modes['browser'] else 'no'}")
    lines.append("")
    lines.append("## Evidence Matrix")
    lines.append("")
    lines.append("| Area | Mode | Status | Evidence path |")
    lines.append("| --- | --- | --- | --- |")
    for row in collected["rows"]:
        lines.append(f"| {row['label']} | {row['mode']} | {row['status']} | `{row['path']}` |")
    lines.append("")
    blocked = [row for row in collected["rows"] if row["status"] == BLOCKED]
    if blocked:
        lines.append("## Blocked Artifacts (must resolve before Green)")
        lines.append("")
        for row in blocked:
            lines.append(f"- {row['label']} — supply `{row['path']}` (mode: {row['mode']}).")
        lines.append("")
    lines.append("## Standing Blockers (always separate from first run)")
    lines.append("")
    lines.append("- Production RLS / app-role rollout remains separate.")
    lines.append("- Live WhatsApp provider readiness remains separate.")
    lines.append("- 360dialog / BSP pilot is out of first-run scope.")
    lines.append("- Real customer data is out of first-run scope.")
    lines.append("")
    lines.append("## Verdict Thresholds")
    lines.append("")
    lines.append("- Green: browser + chatbot + smoke evidence present; stress path has no unsafe claims.")
    lines.append("- Yellow: golden path demo-able, but some stress/API/browser items blocked or rough.")
    lines.append("- Red: `/agent` cannot load real pilot data, fallback rows appear, unsafe claims leak, "
                 "or the safety gate failed.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render the internal Mahoroba pilot report from evidence.")
    parser.add_argument("--input", required=True, help="Evidence directory root.")
    parser.add_argument("--output", required=True, help="Report output directory.")
    parser.add_argument("--final", action="store_true", help="Mark the report as final rather than interim.")
    args = parser.parse_args(argv)

    base = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    collected = collect(base) if base.exists() else {
        "rows": [{"label": label, "mode": mode, "status": BLOCKED, "path": rel} for rel, label, mode in EVIDENCE_MAP],
        "modes": {"smoke": False, "chatbot": False, "browser": False},
        "safety": BLOCKED,
    }
    report = render(base, collected, args.final)
    report_path = out_dir / "PILOT-REPORT.md"
    report_path.write_text(report + "\n", encoding="utf-8")

    decision, _ = verdict(collected)
    summary = {
        "verdict": decision,
        "modes": collected["modes"],
        "safety": collected["safety"],
        "rows": collected["rows"],
    }
    (out_dir / "scenario-results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Report written: {report_path}")
    print(f"Verdict: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
