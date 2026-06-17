#!/usr/bin/env python3
"""Generate a compact HTML report from a pytest JUnit XML file."""

from __future__ import annotations

import argparse
import html
import os
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def _as_int(value: str | None) -> int:
    try:
        return int(float(value or "0"))
    except ValueError:
        return 0


def _as_float(value: str | None) -> float:
    try:
        return float(value or "0")
    except ValueError:
        return 0.0


def _test_suites(root: ET.Element) -> list[ET.Element]:
    if root.tag == "testsuite":
        return [root]
    return [child for child in root if child.tag == "testsuite"]


def _case_status(case: ET.Element) -> str:
    if case.find("failure") is not None:
        return "failed"
    if case.find("error") is not None:
        return "error"
    if case.find("skipped") is not None:
        return "skipped"
    return "passed"


def _read_junit(path: Path) -> dict:
    root = ET.parse(path).getroot()
    suites = _test_suites(root)
    cases = [case for suite in suites for case in suite.iter("testcase")]

    totals = {
        "tests": sum(_as_int(suite.get("tests")) for suite in suites) or len(cases),
        "failures": sum(_as_int(suite.get("failures")) for suite in suites),
        "errors": sum(_as_int(suite.get("errors")) for suite in suites),
        "skipped": sum(_as_int(suite.get("skipped")) for suite in suites),
        "time": sum(_as_float(suite.get("time")) for suite in suites),
    }
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]

    by_file: dict[str, Counter] = defaultdict(Counter)
    failures = []
    escalation_cases = []
    for case in cases:
        classname = case.get("classname", "")
        file_name = classname.replace(".", "/") + ".py"
        status = _case_status(case)
        by_file[file_name][status] += 1

        name = case.get("name", "")
        if "escalation_threading_harness" in classname:
            escalation_cases.append(
                {
                    "name": name,
                    "status": status,
                    "time": _as_float(case.get("time")),
                }
            )

        if status in {"failed", "error"}:
            node = case.find(status)
            failures.append(
                {
                    "file": file_name,
                    "name": name,
                    "status": status,
                    "message": node.get("message", "") if node is not None else "",
                    "text": node.text or "" if node is not None else "",
                }
            )

    return {
        "totals": totals,
        "by_file": dict(sorted(by_file.items())),
        "failures": failures,
        "escalation_cases": escalation_cases,
    }


def _status_badge(status: str) -> str:
    cls = {
        "passed": "pass",
        "failed": "fail",
        "error": "error",
        "skipped": "skip",
    }.get(status, "skip")
    return f'<span class="badge {cls}">{html.escape(status)}</span>'


def _render_report(data: dict, *, command: str, output: Path, source_xml: Path) -> str:
    totals = data["totals"]
    is_green = totals["failures"] == 0 and totals["errors"] == 0
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_rel = os.path.relpath(source_xml, output.parent)

    file_rows = []
    for file_name, counts in data["by_file"].items():
        total = sum(counts.values())
        file_rows.append(
            "<tr>"
            f"<td>{html.escape(file_name)}</td>"
            f"<td>{total}</td>"
            f"<td>{counts.get('passed', 0)}</td>"
            f"<td>{counts.get('skipped', 0)}</td>"
            f"<td>{counts.get('failed', 0)}</td>"
            f"<td>{counts.get('error', 0)}</td>"
            "</tr>"
        )

    escalation_rows = []
    for case in data["escalation_cases"]:
        escalation_rows.append(
            "<tr>"
            f"<td>{html.escape(case['name'])}</td>"
            f"<td>{_status_badge(case['status'])}</td>"
            f"<td>{case['time']:.2f}s</td>"
            "</tr>"
        )

    failure_html = "<p>No failures or errors.</p>"
    if data["failures"]:
        items = []
        for failure in data["failures"]:
            text = (failure["message"] or failure["text"]).strip()
            items.append(
                "<section class=\"failure\">"
                f"<h3>{html.escape(failure['file'])}::{html.escape(failure['name'])}</h3>"
                f"<p>{_status_badge(failure['status'])}</p>"
                f"<pre>{html.escape(text[:5000])}</pre>"
                "</section>"
            )
        failure_html = "\n".join(items)

    decision_items = [
        "DB-backed initial debounce: 90s, max 5 min bundle window.",
        "Update debounce: 30s before sending appended open questions to the same agent token.",
        "Bypass: offer, legal_general, regulatory_request, and legitimate_conveyancing alert immediately.",
        "BRN requests map to regulatory_documents but use normal debounce; they should be answerable from brokerage config over time.",
        "Resolution: one valid agent reply resolves all open questions on that thread.",
        "Timeout: open/debouncing/updated threads close after 24h since last buyer message.",
        "Opt-out: buyer opt-out closes open threads for that buyer inside the brokerage.",
        "Isolation: matching includes brokerage, buyer, listing, category, and open state.",
    ]
    decision_html = "".join(f"<li>{html.escape(item)}</li>" for item in decision_items)

    links = [
        ("ADR", "../../docs/adr/ADR-2026-06-05-smart-escalation-threading.md"),
        ("Audit", "../../docs/adr/AUDIT-2026-06-05-smart-escalation-threading.md"),
        ("JUnit XML", source_rel),
        ("Threading Harness", "../../tests/test_escalation_threading_harness.py"),
    ]
    link_html = "".join(
        f'<li><a href="{html.escape(url)}">{html.escape(label)}</a></li>' for label, url in links
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dalya Smart Escalation Threading Verification</title>
  <style>
    :root {{
      --deep: #0f1923;
      --ink: #1a2b3c;
      --slate: #2e4057;
      --gold: #c9a96e;
      --sand: #f5efe6;
      --muted: #a79d92;
      --sage: #4a7c6f;
      --danger: #bd5d55;
      --skip: #9b8a58;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--deep);
      color: var(--sand);
      font: 15px/1.55 "Plus Jakarta Sans", Inter, system-ui, sans-serif;
    }}
    main {{ width: min(1180px, calc(100vw - 40px)); margin: 0 auto; padding: 40px 0 56px; }}
    h1, h2, h3 {{ letter-spacing: 0; line-height: 1.2; margin: 0; }}
    h1 {{ font-size: 32px; max-width: 820px; }}
    h2 {{ font-size: 20px; margin-top: 34px; }}
    h3 {{ font-size: 16px; }}
    p {{ color: var(--muted); margin: 10px 0 0; }}
    a {{ color: var(--gold); text-decoration: none; }}
    code, pre, .mono {{ font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .hero {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }}
    .status {{ border: 1px solid rgba(245,239,230,.14); background: rgba(26,43,60,.72); border-radius: 8px; padding: 16px 18px; min-width: 260px; }}
    .ok {{ color: var(--sage); }}
    .bad {{ color: var(--danger); }}
    .grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-top: 22px; }}
    .metric {{ background: var(--ink); border: 1px solid rgba(245,239,230,.1); border-radius: 8px; padding: 16px; }}
    .metric strong {{ display: block; color: var(--gold); font: 700 24px/1 "JetBrains Mono", monospace; }}
    .metric span {{ display: block; color: var(--muted); margin-top: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; background: rgba(26,43,60,.55); border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid rgba(245,239,230,.08); text-align: left; vertical-align: top; }}
    th {{ color: var(--gold); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; background: rgba(46,64,87,.7); }}
    tr:last-child td {{ border-bottom: 0; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 3px 8px; color: var(--deep); font-size: 12px; font-weight: 700; }}
    .pass {{ background: var(--sage); }}
    .fail, .error {{ background: var(--danger); }}
    .skip {{ background: var(--skip); }}
    .panel {{ margin-top: 14px; background: rgba(26,43,60,.55); border: 1px solid rgba(245,239,230,.1); border-radius: 8px; padding: 16px 18px; }}
    ul {{ margin: 10px 0 0 20px; padding: 0; }}
    pre {{ white-space: pre-wrap; background: #081017; color: #f6d8d4; padding: 12px; border-radius: 8px; overflow-x: auto; }}
    @media (max-width: 820px) {{
      .hero {{ display: block; }}
      .status {{ margin-top: 20px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>Dalya Smart Escalation Threading Verification</h1>
        <p>Generated {html.escape(generated_at)} from pytest JUnit output.</p>
        <p class="mono">{html.escape(command)}</p>
      </div>
      <div class="status">
        <h2 class="{("ok" if is_green else "bad")}">{("Test run green" if is_green else "Test run has failures")}</h2>
        <p>{totals["tests"]} tests, {totals["failures"]} failures, {totals["errors"]} errors, {totals["skipped"]} skipped.</p>
      </div>
    </section>

    <section class="grid" aria-label="Test summary">
      <div class="metric"><strong>{totals["tests"]}</strong><span>Total tests</span></div>
      <div class="metric"><strong>{totals["passed"]}</strong><span>Passed</span></div>
      <div class="metric"><strong>{totals["skipped"]}</strong><span>Skipped</span></div>
      <div class="metric"><strong>{totals["failures"]}</strong><span>Failures</span></div>
      <div class="metric"><strong>{totals["time"]:.2f}s</strong><span>Runtime</span></div>
    </section>

    <section>
      <h2>Escalation Threading Coverage</h2>
      <p>The focused harness exercises debounce bundling, token reuse, category splitting, resolution, stale-window new threads, bypass categories, opt-out closure, thread isolation, update formatting, and question-cap truncation.</p>
      <table>
        <thead><tr><th>Test</th><th>Status</th><th>Time</th></tr></thead>
        <tbody>{''.join(escalation_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Locked Decisions</h2>
      <div class="panel"><ul>{decision_html}</ul></div>
    </section>

    <section>
      <h2>Failures</h2>
      <div class="panel">{failure_html}</div>
    </section>

    <section>
      <h2>Results By File</h2>
      <table>
        <thead><tr><th>File</th><th>Total</th><th>Passed</th><th>Skipped</th><th>Failed</th><th>Errors</th></tr></thead>
        <tbody>{''.join(file_rows)}</tbody>
      </table>
    </section>

    <section>
      <h2>Artifacts</h2>
      <div class="panel"><ul>{link_html}</ul></div>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--command", required=True)
    args = parser.parse_args()

    data = _read_junit(args.junit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        _render_report(data, command=args.command, output=args.output, source_xml=args.junit),
        encoding="utf-8",
    )
    totals = data["totals"]
    print(
        f"Wrote {args.output} ({totals['tests']} tests, "
        f"{totals['failures']} failures, {totals['errors']} errors, {totals['skipped']} skipped)"
    )


if __name__ == "__main__":
    main()
