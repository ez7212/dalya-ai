"""
Chatbot test report generator.

Reads a chatbot test report directory and writes index.html
with a chat-bubble UI for browsing test results.

CLI usage:
    python scripts/generate_test_report.py reports/chatbot_test_multitenant
    python scripts/generate_test_report.py          # auto-selects latest

Importable:
    from scripts.generate_test_report import generate_report
    html_path = generate_report(Path("reports/chatbot_test_multitenant"))
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_directory(directory: Path) -> dict:
    """Load all data from a test-run directory. Returns a shape-normalised dict."""
    aggregate_path = directory / "_aggregate.json"
    progress_path = directory / "_progress.log"

    aggregate = _load_json(aggregate_path) if aggregate_path.exists() else None
    progress_text = progress_path.read_text(encoding="utf-8") if progress_path.exists() else None

    persona_files = sorted(directory.glob("persona_*.json"))
    personas = []
    for pf in persona_files:
        data = _load_json(pf)
        if data:
            data["_filename"] = pf.name
            personas.append(data)

    # Compute total duration from progress log
    total_duration = None
    if progress_text:
        m = re.search(r"=== DONE in ([\d.]+)s", progress_text)
        if m:
            total_duration = float(m.group(1))

    return {
        "aggregate": aggregate,
        "personas": personas,
        "progress_text": progress_text,
        "total_duration": total_duration,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LISTING_NAMES: dict[str, str] = {
    "7eb2b37b95468b1856d907113ad4c09c36be": "Ostra",
    "test-ostra-2805-fixture": "Ostra",
    "bd7a40facc785814f81c7110e03bf89427ed": "Seahaven",
}

METRIC_DISPLAY = {
    "em_dashes_per_response": "Em-dashes/resp",
    "the_team_mentions_per_conversation": '"the team" refs',
    "closing_question_rate": "Closing Q rate",
    "markdown_bold_count": "Markdown bold",
    "emoji_count": "Emoji count",
}


def _listing_name(listing_id: str | None) -> str:
    if not listing_id:
        return "—"
    return _LISTING_NAMES.get(listing_id, listing_id[:8] + "…")


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return "—"
    digits = re.sub(r"[^\d]", "", phone)
    if len(digits) >= 4:
        return "+97150…" + digits[-4:]
    return phone


def _h(text: str | None) -> str:
    """HTML-escape a string."""
    if text is None:
        return ""
    return html_lib.escape(str(text))


def _fmt_num(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


def _fmt_pct(value) -> str:
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.1f}%".replace(".0%", "%")


def _fmt_rate(value) -> str:
    try:
        return f"{float(value) * 100:.1f}%".replace(".0%", "%")
    except (TypeError, ValueError):
        return "—"


def _render_distribution(distribution: dict | None) -> str:
    if not distribution:
        return "—"
    return ", ".join(f"{_h(key)}: {_h(value)}" for key, value in sorted(distribution.items()))


def _render_escalation_thread_metrics(metrics: dict | None, *, compact: bool = False) -> str:
    if not metrics:
        return '<div class="thread-metrics na-note">Escalation thread metrics not available for this run.</div>'
    fields = [
        ("Threads", _fmt_num(metrics.get("thread_count"))),
        ("Questions", _fmt_num(metrics.get("question_count"))),
        ("Avg Q/thread", metrics.get("avg_questions_per_thread", "—")),
        ("Append rate", _fmt_rate(metrics.get("append_rate"))),
        ("Bundle rate", _fmt_rate(metrics.get("debounce_bundle_rate"))),
        ("Bypass rate", _fmt_rate(metrics.get("bypass_rate"))),
        ("Timeout rate", _fmt_rate(metrics.get("timeout_rate"))),
        ("False +", _fmt_num(metrics.get("false_positive_threads"))),
        ("False -", _fmt_num(metrics.get("false_negative_threads"))),
    ]
    cells = "".join(
        f'<div class="thread-metric-cell"><span>{_h(label)}</span><strong>{_h(value)}</strong></div>'
        for label, value in fields
    )
    distribution = _render_distribution(metrics.get("category_distribution"))
    cls = "thread-metrics compact" if compact else "thread-metrics"
    return (
        f'<div class="{cls}">'
        f'<div class="thread-metric-grid">{cells}</div>'
        f'<div class="thread-distribution"><span>Categories</span><strong>{distribution}</strong></div>'
        "</div>"
    )


def _render_listing_facts(facts: dict | None) -> str:
    if not facts:
        return ""
    fields = [
        ("Property", facts.get("property_name")),
        ("Beds", facts.get("beds")),
        ("Baths", facts.get("baths")),
        ("Sqft", _fmt_num(facts.get("sqft"))),
        ("Plot", _fmt_num(facts.get("plot_sqft"))),
        ("Price", f"AED {_fmt_num(facts.get('price_aed'))}" if facts.get("price_aed") else "—"),
        ("Status", facts.get("status") or facts.get("property_type")),
    ]
    if facts.get("property_type") == "off_plan":
        fields.extend([
            ("Paid", _fmt_pct(facts.get("paid_to_developer_pct"))),
            ("NOC threshold", _fmt_pct(facts.get("noc_threshold_pct"))),
            ("Offer floor", (
                f"AED {_fmt_num(facts.get('offer_threshold_aed'))}"
                + (f" / {_fmt_pct(facts.get('offer_threshold_pct'))}" if facts.get("offer_threshold_pct") is not None else "")
                if facts.get("offer_threshold_aed") else "—"
            )),
        ])
    cells = "".join(
        f'<div class="facts-cell"><span>{_h(label)}</span><strong>{_h(value)}</strong></div>'
        for label, value in fields
    )
    return f'<div class="listing-facts">{cells}</div>'


def _highlight_aed(text: str) -> str:
    """Wrap AED figures in a mono span."""
    if not text:
        return ""
    escaped = _h(text)
    return re.sub(
        r"(AED\s[\d,]+(?:\.\d+)?(?:\s*M(?:illion)?)?)",
        r'<span class="aed">\1</span>',
        escaped,
    )


def _metric_pass(metrics: dict | None) -> tuple[bool | None, str]:
    """Return (all_pass, badge_html) for a metrics dict."""
    if not metrics:
        return None, '<span class="badge badge-na">metrics N/A</span>'
    badges = []
    for key, display in METRIC_DISPLAY.items():
        m = metrics.get(key)
        if m is None:
            badges.append(f'<span class="badge badge-na" title="{_h(key)}">{_h(display)}: N/A</span>')
            continue
        val = m.get("value", "?")
        target = m.get("target", "?")
        comparator = m.get("comparator", "")
        passed = m.get("pass", False)
        cls = "badge-pass" if passed else "badge-fail"
        val_str = f"{val:.3f}" if isinstance(val, float) else str(val)
        title = f"target {comparator} {target}"
        badges.append(
            f'<span class="badge {cls}" title="{_h(title)}">'
            f'{_h(display)}: {_h(val_str)}</span>'
        )
    return None, " ".join(badges)


def _distinct_listings(personas: list[dict]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    for p in personas:
        lid = p.get("listing_id") or ""
        if lid and lid not in seen:
            seen[lid] = _listing_name(lid)
    return list(seen.items())


# ---------------------------------------------------------------------------
# HTML rendering pieces
# ---------------------------------------------------------------------------

def _render_turn(turn: dict, turn_idx: int) -> str:
    tnum = turn.get("turn", turn_idx + 1)
    buyer_msg = turn.get("buyer", "")
    bot_msg = turn.get("bot", "")
    esc = turn.get("escalation_triggered", False)
    escalation = turn.get("escalation") or {}
    error = turn.get("error")
    dur = turn.get("duration_s")
    dur_str = f"{dur:.1f}s" if isinstance(dur, (int, float)) else "—"
    card_id = f"esc_t{tnum}_{turn_idx}"

    parts = []
    # Buyer bubble
    parts.append(f'''
        <div class="turn-row buyer-row">
          <div class="bubble buyer-bubble">
            <div class="bubble-meta">T{tnum} · {_h(dur_str)}</div>
            <div class="bubble-text">{_highlight_aed(buyer_msg)}</div>
          </div>
        </div>''')

    # Error strip
    if error:
        parts.append(f'<div class="error-strip">ERROR: {_h(str(error))}</div>')

    # Bot bubble
    esc_badge = (
        f'<button class="esc-badge" onclick="toggleBlock(\'{card_id}\')" type="button">ESC</button>'
        if esc else ""
    )
    parts.append(f'''
        <div class="turn-row bot-row">
          <div class="bubble bot-bubble">
            <div class="bubble-meta">{esc_badge} Dalya · T{tnum}</div>
            <div class="bubble-text">{_highlight_aed(bot_msg)}</div>
          </div>
        </div>''')

    # Escalation detail card
    if esc and escalation:
        esc_type = escalation.get("escalation_type", "")
        offer = escalation.get("offer_amount_aed")
        listing_price = escalation.get("listing_price_aed")
        threshold = escalation.get("negotiation_threshold_aed")
        priority = escalation.get("priority", "")
        trigger = escalation.get("trigger", "")
        subtype = escalation.get("escalation_subtype")
        seller_intent = escalation.get("seller_intent")
        payload = escalation.get("payload") or {}

        detail_rows = []
        if esc_type:
            detail_rows.append(f"<tr><td>Type</td><td>{_h(esc_type)}</td></tr>")
        if trigger:
            detail_rows.append(f"<tr><td>Trigger</td><td>{_h(trigger)}</td></tr>")
        if subtype:
            detail_rows.append(f"<tr><td>Subtype</td><td>{_h(subtype)}</td></tr>")
        if seller_intent:
            detail_rows.append(f"<tr><td>Seller intent</td><td>{_h(seller_intent)}</td></tr>")
        if offer is not None:
            detail_rows.append(f"<tr><td>Offer</td><td><span class='aed'>AED {offer:,.0f}</span></td></tr>")
            if listing_price:
                detail_rows.append(f"<tr><td>Offer %</td><td>{_fmt_pct(float(offer) / float(listing_price) * 100)}</td></tr>")
        if listing_price is not None:
            detail_rows.append(f"<tr><td>Asking</td><td><span class='aed'>AED {listing_price:,.0f}</span></td></tr>")
        if threshold is not None:
            detail_rows.append(f"<tr><td>Threshold</td><td><span class='aed'>AED {threshold:,.0f}</span></td></tr>")
            if offer is not None:
                detail_rows.append(f"<tr><td>Vs threshold</td><td><span class='aed'>AED {float(offer) - float(threshold):,.0f}</span></td></tr>")
        if priority:
            detail_rows.append(f"<tr><td>Priority</td><td>{_h(priority)}</td></tr>")
        for key, value in payload.items():
            if value is None or value == "" or value == []:
                continue
            if isinstance(value, (dict, list)):
                value_text = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (int, float)) and "aed" in key.lower():
                value_text = f"AED {value:,.0f}"
            else:
                value_text = str(value)
            detail_rows.append(f"<tr><td>Payload: {_h(key)}</td><td>{_h(value_text)}</td></tr>")

        if detail_rows:
            parts.append(f'''
        <div class="esc-detail-card">
          <button class="esc-toggle" onclick="toggleBlock('{card_id}')">Escalation detail +</button>
          <div id="{card_id}" class="esc-detail-body hidden">
            <table class="esc-table">{''.join(detail_rows)}</table>
          </div>
        </div>''')

    return "".join(parts)


def _render_persona_detail(persona: dict, idx: int) -> str:
    name = persona.get("persona", f"Persona {idx + 1}")
    phone = _mask_phone(persona.get("phone"))
    listing_id = persona.get("listing_id", "")
    listing_display = _listing_name(listing_id)
    summary = persona.get("summary_auto", "")
    listing_facts = persona.get("listing_facts")
    turns = persona.get("turns", [])
    checks = persona.get("checks", [])
    quality_metrics = persona.get("quality_metrics")
    thread_metrics = persona.get("escalation_thread_metrics")
    issues = persona.get("issues_found", [])

    # Build conversation
    convo_parts = [_render_turn(t, i) for i, t in enumerate(turns)]
    convo_html = "\n".join(convo_parts)

    # Checks panel
    check_rows = []
    for c in checks:
        chk = c.get("check", "")
        passed = c.get("pass", False)
        evidence = c.get("evidence", "")
        cls = "check-pass" if passed else "check-fail"
        icon = "&#10003;" if passed else "&#10007;"
        evi_id = f"evi_{idx}_{_h(chk)}"
        evi_short = evidence[:80] + ("…" if len(evidence) > 80 else "")
        check_rows.append(f'''
          <tr class="{cls}">
            <td class="check-icon">{icon}</td>
            <td class="check-name">{_h(chk)}</td>
            <td class="check-evi">
              <button class="evi-toggle" onclick="toggleBlock('{evi_id}')">{_h(evi_short)}</button>
              <div id="{evi_id}" class="evi-full hidden">{_h(evidence)}</div>
            </td>
          </tr>''')
    checks_html = f'''
        <div class="checks-panel">
          <h4 class="panel-title">Checks ({len([c for c in checks if c.get("pass")])}/{len(checks)} pass)</h4>
          <table class="checks-table">{''.join(check_rows)}</table>
        </div>''' if checks else '<div class="checks-panel na-note">No checks data for this run.</div>'

    # Quality metrics panel
    if quality_metrics:
        _, metrics_html = _metric_pass(quality_metrics)
        qm_html = f'<div class="qm-panel"><h4 class="panel-title">Quality metrics</h4><div class="badges-row">{metrics_html}</div></div>'
    else:
        qm_html = '<div class="qm-panel na-note">quality metrics not available for this run</div>'

    thread_metrics_html = (
        f'<div class="qm-panel"><h4 class="panel-title">Escalation thread metrics</h4>'
        f'{_render_escalation_thread_metrics(thread_metrics, compact=True)}</div>'
    )

    issues_html = ""
    if issues:
        issues_list = " ".join(f'<span class="issue-pill">{_h(i)}</span>' for i in issues)
        issues_html = f'<div class="issues-row"><strong>Issues:</strong> {issues_list}</div>'

    persona_id = f"persona_detail_{idx}"

    return f'''
    <tr class="persona-expand-row" id="{persona_id}_row">
      <td colspan="7" class="expand-cell">
        <div class="persona-detail">
          <div class="detail-header">
            <div class="detail-meta">
              <span class="detail-name">{_h(name)}</span>
              <span class="detail-phone">{_h(phone)}</span>
              <span class="detail-listing">{_h(listing_display)}</span>
              {('<span class="detail-listing-id">' + _h(listing_id[:12]) + '…</span>') if listing_id else ''}
            </div>
            {_render_listing_facts(listing_facts)}
            {f'<div class="detail-summary">{_h(summary)}</div>' if summary else ''}
            {issues_html}
          </div>
          <div class="detail-body">
            <div class="convo-pane">
              <h4 class="panel-title">Conversation ({len(turns)} turns)</h4>
              <div class="chat-thread">{convo_html}</div>
            </div>
            <div class="side-pane">
              {checks_html}
              {qm_html}
              {thread_metrics_html}
            </div>
          </div>
        </div>
      </td>
    </tr>'''


def _render_persona_row(persona: dict, idx: int) -> tuple[str, str]:
    """Return (table row HTML, detail row HTML)."""
    name = persona.get("persona", f"Persona {idx + 1}")
    listing_id = persona.get("listing_id", "")
    listing_display = _listing_name(listing_id)
    turns = persona.get("turns", [])
    esc_turns = persona.get("escalation_turns", [])
    issues = persona.get("issues_found", [])

    # Derive category for filtering
    name_lower = name.lower()
    if "seller" in name_lower or "owner" in name_lower:
        category = "seller"
    elif any(kw in name_lower for kw in ["broker", "lawyer", "advisor", "advisor", "raj"]):
        category = "professional"
    else:
        category = "buyer"

    has_issues = len(issues) > 0
    status_cls = "status-issues" if has_issues else "status-clean"
    status_label = f"{len(issues)} issue{'s' if len(issues) != 1 else ''}" if has_issues else "CLEAN"
    status_badge = f'<span class="status-pill {status_cls}">{status_label}</span>'

    filter_tags = f"all {category} {'issues' if has_issues else 'clean'}"
    row_id = f"persona_row_{idx}"
    detail_id = f"persona_detail_{idx}_row"

    row_html = f'''
      <tr class="persona-row" data-tags="{filter_tags}" id="{row_id}"
          onclick="togglePersona({idx})" role="button" tabindex="0"
          onkeydown="if(event.key==='Enter')togglePersona({idx})">
        <td class="col-idx">{idx + 1}</td>
        <td class="col-name">{_h(name)}</td>
        <td class="col-listing">{_h(listing_display)}</td>
        <td class="col-turns">{len(turns)}</td>
        <td class="col-esc">{len(esc_turns)}</td>
        <td class="col-issues">{len(issues)}</td>
        <td class="col-status">{status_badge}</td>
      </tr>'''

    detail_html = _render_persona_detail(persona, idx)
    return row_html, detail_html


# ---------------------------------------------------------------------------
# Main HTML assembly
# ---------------------------------------------------------------------------

INLINE_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --gold:   #C9A96E;
  --ink:    #1A2B3C;
  --slate:  #2E4057;
  --deep:   #0F1923;
  --sage:   #4A7C6F;
  --sage-lt:#6BA898;
  --sand:   #F5EFE6;
  --n500:   #8A8078;
  --copper: #9B5D2E;
  --fail:   #C0392B;
  --pass:   #4A7C6F;
  --font-ui: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

html { font-size: 15px; }
body {
  background: var(--deep);
  color: var(--sand);
  font-family: var(--font-ui);
  line-height: 1.55;
  min-height: 100vh;
  padding: 0 0 80px;
}

/* ---- Layout ---- */
.page-wrap { max-width: 1200px; margin: 0 auto; padding: 0 20px; }

/* ---- Header ---- */
.report-header {
  padding: 40px 0 28px;
  border-bottom: 1px solid rgba(201,169,110,.18);
  margin-bottom: 32px;
}
.run-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--gold);
  letter-spacing: -.01em;
}
.run-meta {
  font-size: .82rem;
  color: var(--n500);
  margin-top: 4px;
}
.stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin: 20px 0 0;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--sand);
  font-family: var(--font-mono);
  line-height: 1.1;
}
.stat-label {
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--n500);
}

/* ---- Badges ---- */
.badges-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.badge {
  font-size: .75rem;
  font-family: var(--font-mono);
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
}
.badge-pass { background: rgba(74,124,111,.25); color: var(--sage-lt); border: 1px solid rgba(74,124,111,.4); }
.badge-fail { background: rgba(155,93,46,.25); color: #E8905A; border: 1px solid rgba(155,93,46,.5); }
.badge-na   { background: rgba(138,128,120,.15); color: var(--n500); border: 1px solid rgba(138,128,120,.3); }

/* ---- Listing pills ---- */
.listings-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.listing-pill {
  font-size: .72rem;
  padding: 3px 10px;
  border-radius: 20px;
  background: var(--slate);
  color: var(--sand);
  border: 1px solid rgba(201,169,110,.2);
  font-family: var(--font-mono);
}

/* ---- Filter chips ---- */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
}
.filter-label {
  font-size: .75rem;
  color: var(--n500);
  text-transform: uppercase;
  letter-spacing: .07em;
  margin-right: 4px;
}
.chip {
  font-size: .78rem;
  padding: 5px 14px;
  border-radius: 20px;
  border: 1px solid var(--slate);
  background: transparent;
  color: var(--n500);
  cursor: pointer;
  transition: all .15s;
  font-family: var(--font-ui);
}
.chip:hover { border-color: var(--gold); color: var(--sand); }
.chip.active { background: var(--gold); color: var(--deep); border-color: var(--gold); font-weight: 600; }

/* ---- Persona table ---- */
.table-wrap { overflow-x: auto; }
.persona-table {
  width: 100%;
  border-collapse: collapse;
  font-size: .85rem;
}
.persona-table thead th {
  padding: 10px 12px;
  text-align: left;
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--n500);
  background: var(--ink);
  border-bottom: 1px solid var(--slate);
  white-space: nowrap;
  user-select: none;
}
.persona-table thead th.sortable { cursor: pointer; }
.persona-table thead th.sortable:hover { color: var(--gold); }
.persona-table thead th .sort-arrow { margin-left: 4px; opacity: .5; }
.persona-row td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(46,64,87,.6);
  vertical-align: middle;
}
.persona-row { cursor: pointer; transition: background .12s; }
.persona-row:hover { background: var(--ink); }
.persona-row.active-row { background: var(--ink); border-left: 2px solid var(--gold); }
.col-idx { color: var(--n500); width: 36px; }
.col-name { font-weight: 500; min-width: 180px; }
.col-listing { color: var(--n500); font-size: .8rem; }
.col-turns, .col-esc, .col-issues { font-family: var(--font-mono); text-align: center; width: 64px; }

/* ---- Status pills ---- */
.status-pill {
  font-size: .7rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
  letter-spacing: .03em;
}
.status-clean  { background: rgba(74,124,111,.2); color: var(--sage-lt); border: 1px solid rgba(74,124,111,.4); }
.status-issues { background: rgba(155,93,46,.25); color: #E8905A; border: 1px solid rgba(155,93,46,.5); }

/* ---- Expand row ---- */
.persona-expand-row { display: none; }
.persona-expand-row.visible { display: table-row; }
.expand-cell { padding: 0; }

/* ---- Persona detail ---- */
.persona-detail {
  background: var(--ink);
  border-top: 2px solid var(--gold);
  padding: 24px;
}
.detail-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--slate);
}
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: baseline;
  margin-bottom: 8px;
}
.detail-name   { font-size: 1rem; font-weight: 700; color: var(--sand); }
.detail-phone  { font-size: .8rem; font-family: var(--font-mono); color: var(--n500); }
.detail-listing { font-size: .8rem; background: var(--slate); padding: 2px 8px; border-radius: 4px; color: var(--gold); }
.detail-listing-id { font-size: .72rem; font-family: var(--font-mono); color: var(--n500); }
.detail-summary { font-size: .85rem; color: var(--n500); font-style: italic; }
.listing-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin: 12px 0;
}
.facts-cell {
  background: rgba(46,64,87,.45);
  border: 1px solid rgba(201,169,110,.14);
  border-radius: 4px;
  padding: 8px 10px;
  min-width: 0;
}
.facts-cell span {
  display: block;
  color: var(--n500);
  font-size: .66rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-bottom: 2px;
}
.facts-cell strong {
  display: block;
  color: var(--sand);
  font-size: .78rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.issues-row { margin-top: 8px; font-size: .8rem; }
.issue-pill {
  display: inline-block;
  margin-left: 6px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(155,93,46,.2);
  color: #E8905A;
  font-family: var(--font-mono);
  font-size: .72rem;
  border: 1px solid rgba(155,93,46,.4);
}
.detail-body {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  align-items: start;
}
@media (max-width: 700px) {
  .detail-body { grid-template-columns: 1fr; }
  .listing-facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat-row { gap: 16px; }
  .report-header { padding: 24px 0 18px; }
}

/* ---- Chat thread ---- */
.chat-thread { display: flex; flex-direction: column; gap: 12px; padding: 4px 0; }
.turn-row { display: flex; }
.buyer-row { justify-content: flex-end; }
.bot-row   { justify-content: flex-start; }

.bubble {
  max-width: 78%;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: .85rem;
  line-height: 1.5;
}
.buyer-bubble {
  background: var(--slate);
  border-bottom-right-radius: 3px;
}
.bot-bubble {
  background: rgba(26,43,60,.9);
  border: 1px solid rgba(201,169,110,.22);
  border-bottom-left-radius: 3px;
}
.bubble-meta {
  font-size: .68rem;
  color: var(--n500);
  margin-bottom: 5px;
  font-family: var(--font-mono);
}
.bubble-text { word-break: break-word; white-space: pre-wrap; }

/* ---- Escalation ---- */
.esc-badge {
  display: inline-block;
  font-size: .65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  border: none;
  background: var(--sage);
  color: #fff;
  letter-spacing: .05em;
  margin-right: 4px;
  vertical-align: middle;
  cursor: pointer;
  font-family: var(--font-mono);
}
.esc-detail-card {
  margin: -4px 0 8px 12px;
  max-width: 480px;
}
.esc-toggle {
  font-size: .72rem;
  background: none;
  border: none;
  color: var(--sage-lt);
  cursor: pointer;
  padding: 0;
  font-family: var(--font-ui);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.esc-toggle:hover { color: var(--gold); }
.esc-detail-body { margin-top: 6px; }
.esc-table { font-size: .78rem; border-collapse: collapse; width: 100%; }
.esc-table td {
  padding: 3px 8px;
  border-bottom: 1px solid rgba(46,64,87,.5);
  vertical-align: top;
}
.esc-table tr:first-child td:first-child { color: var(--n500); width: 80px; }

/* ---- Error strip ---- */
.error-strip {
  background: rgba(192,57,43,.2);
  border: 1px solid rgba(192,57,43,.4);
  border-radius: 6px;
  color: #E87676;
  font-size: .8rem;
  padding: 6px 12px;
  margin: 4px 0;
  font-family: var(--font-mono);
}

/* ---- Checks panel ---- */
.panel-title {
  font-size: .78rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--n500);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--slate);
}
.checks-panel, .qm-panel { margin-bottom: 16px; }
.checks-table { font-size: .78rem; border-collapse: collapse; width: 100%; }
.checks-table td { padding: 5px 6px; border-bottom: 1px solid rgba(46,64,87,.4); vertical-align: top; }
.check-icon { width: 18px; font-weight: 700; }
.check-pass .check-icon { color: var(--sage-lt); }
.check-fail .check-icon { color: #E87676; }
.check-name { width: 160px; font-family: var(--font-mono); font-size: .72rem; word-break: break-all; }
.check-evi { color: var(--n500); }
.evi-toggle {
  font-size: .72rem;
  background: none;
  border: none;
  color: var(--n500);
  cursor: pointer;
  font-family: var(--font-ui);
  text-align: left;
  padding: 0;
  line-height: 1.4;
}
.evi-toggle:hover { color: var(--sand); }
.evi-full {
  font-size: .72rem;
  font-family: var(--font-mono);
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--sand);
  background: var(--slate);
  padding: 6px 8px;
  border-radius: 4px;
  margin-top: 4px;
}

/* ---- QM panel ---- */
.qm-panel .badges-row { gap: 6px; margin-top: 0; }
.qm-panel .badge { font-size: .68rem; padding: 3px 8px; }

/* ---- Escalation thread metrics ---- */
.thread-metrics {
  background: rgba(26,43,60,.68);
  border: 1px solid rgba(201,169,110,.16);
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
}
.thread-metrics.compact { padding: 10px; margin-top: 0; }
.thread-metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}
.thread-metric-cell {
  background: rgba(46,64,87,.45);
  border-radius: 6px;
  padding: 8px;
  min-width: 0;
}
.thread-metric-cell span,
.thread-distribution span {
  display: block;
  color: var(--n500);
  font-size: .66rem;
  text-transform: uppercase;
  letter-spacing: .05em;
}
.thread-metric-cell strong {
  display: block;
  margin-top: 3px;
  color: var(--sand);
  font-family: var(--font-mono);
  font-size: .82rem;
  overflow-wrap: anywhere;
}
.thread-distribution {
  margin-top: 8px;
  background: rgba(46,64,87,.35);
  border-radius: 6px;
  padding: 8px;
}
.thread-distribution strong {
  display: block;
  margin-top: 3px;
  color: var(--gold);
  font-size: .75rem;
  font-family: var(--font-mono);
  overflow-wrap: anywhere;
}

/* ---- N/A note ---- */
.na-note { font-size: .8rem; color: var(--n500); font-style: italic; padding: 8px 0; }

/* ---- AED figures ---- */
.aed { font-family: var(--font-mono); color: var(--gold); }

/* ---- Utility ---- */
.hidden { display: none !important; }
.section-title {
  font-size: .85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--n500);
  margin: 28px 0 14px;
}
"""

INLINE_SCRIPT = """
// ----- Persona expand/collapse -----
function togglePersona(idx) {
  var detailRow = document.getElementById('persona_detail_' + idx + '_row');
  var tableRow  = document.getElementById('persona_row_' + idx);
  if (!detailRow) return;
  var isOpen = !detailRow.classList.contains('visible');
  // Close all others
  document.querySelectorAll('.persona-expand-row.visible').forEach(function(r) {
    r.classList.remove('visible');
  });
  document.querySelectorAll('.persona-row.active-row').forEach(function(r) {
    r.classList.remove('active-row');
  });
  if (isOpen) {
    detailRow.classList.add('visible');
    tableRow.classList.add('active-row');
    // Scroll so row top is near viewport top
    setTimeout(function() {
      tableRow.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
  }
}

// ----- Generic block toggle (esc details, evidence) -----
function toggleBlock(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle('hidden');
}

// ----- Filter chips -----
document.addEventListener('DOMContentLoaded', function() {
  var chips = document.querySelectorAll('.chip');
  chips.forEach(function(chip) {
    chip.addEventListener('click', function() {
      chips.forEach(function(c) { c.classList.remove('active'); });
      chip.classList.add('active');
      var tag = chip.dataset.filter;
      document.querySelectorAll('.persona-row').forEach(function(row) {
        var tags = (row.dataset.tags || '').split(' ');
        row.style.display = (tag === 'all' || tags.includes(tag)) ? '' : 'none';
        // Also hide the associated detail row when filtering hides the parent row
        var idx = row.id.replace('persona_row_', '');
        var det = document.getElementById('persona_detail_' + idx + '_row');
        if (det && row.style.display === 'none') det.classList.remove('visible');
      });
    });
  });

  // ----- Column sort -----
  var table = document.querySelector('.persona-table');
  if (!table) return;
  var headers = table.querySelectorAll('th.sortable');
  headers.forEach(function(th) {
    var arrow = th.querySelector('.sort-arrow');
    var asc = true;
    th.addEventListener('click', function() {
      var col = parseInt(th.dataset.col);
      var numeric = th.dataset.type === 'num';
      var rows = Array.from(table.querySelectorAll('tbody .persona-row'));
      rows.sort(function(a, b) {
        var av = a.cells[col] ? a.cells[col].textContent.trim() : '';
        var bv = b.cells[col] ? b.cells[col].textContent.trim() : '';
        if (numeric) {
          av = parseFloat(av) || 0;
          bv = parseFloat(bv) || 0;
          return asc ? av - bv : bv - av;
        }
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      headers.forEach(function(h) {
        var a = h.querySelector('.sort-arrow');
        if (a) a.textContent = '';
      });
      if (arrow) arrow.textContent = asc ? ' \\u2191' : ' \\u2193';
      asc = !asc;
      var tbody = table.querySelector('tbody');
      rows.forEach(function(r) {
        var idx = r.id.replace('persona_row_', '');
        var det = document.getElementById('persona_detail_' + idx + '_row');
        tbody.appendChild(r);
        if (det) tbody.appendChild(det);
      });
    });
  });
});
"""


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s"


def generate_report(directory: Path) -> Path:
    """Generate index.html in `directory`. Returns path to the HTML file."""
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    data = _load_directory(directory)
    aggregate = data["aggregate"] or {}
    personas = data["personas"]
    total_duration = data["total_duration"]

    run_at_raw = aggregate.get("run_at", "")
    try:
        run_at_dt = datetime.fromisoformat(run_at_raw)
        run_at_str = run_at_dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        run_at_str = run_at_raw or "unknown"

    total_personas = aggregate.get("total_personas") or len(personas)
    completed = aggregate.get("completed") or len(personas)
    issues_count = sum(1 for p in personas if p.get("issues_found"))
    clean_count = completed - issues_count

    # Fleet quality metrics
    fleet_metrics = aggregate.get("fleet_quality_metrics")
    _, fleet_badges_html = _metric_pass(fleet_metrics)
    escalation_thread_metrics = aggregate.get("escalation_thread_metrics")
    escalation_thread_metrics_html = _render_escalation_thread_metrics(escalation_thread_metrics)

    # Listings
    distinct_listings = _distinct_listings(personas)
    listing_pills = "".join(
        f'<span class="listing-pill">{_h(lid[:10])}… · {_h(name)}</span>'
        for lid, name in distinct_listings
    )

    # Stats
    dur_display = _format_duration(total_duration) if total_duration else "—"
    stat_row = f"""
      <div class="stat-row">
        <div class="stat"><span class="stat-value">{total_personas}</span><span class="stat-label">Personas</span></div>
        <div class="stat"><span class="stat-value">{completed}</span><span class="stat-label">Completed</span></div>
        <div class="stat"><span class="stat-value" style="color:var(--sage-lt)">{clean_count}</span><span class="stat-label">Clean</span></div>
        <div class="stat"><span class="stat-value" style="color:{'#E8905A' if issues_count else 'var(--sage-lt)'}">{issues_count}</span><span class="stat-label">With issues</span></div>
        <div class="stat"><span class="stat-value" style="font-size:1.2rem">{dur_display}</span><span class="stat-label">Duration</span></div>
      </div>"""

    # Build persona table rows
    all_row_html = []
    all_detail_html = []
    for i, persona in enumerate(personas):
        row_html, detail_html = _render_persona_row(persona, i)
        all_row_html.append(row_html)
        all_detail_html.append(detail_html)

    # Interleave rows + detail rows in tbody
    tbody_parts = []
    for row_html, detail_html in zip(all_row_html, all_detail_html):
        tbody_parts.append(row_html)
        tbody_parts.append(detail_html)
    tbody = "\n".join(tbody_parts)

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Test Report — {_h(directory.name)}</title>
  <style>
{INLINE_STYLE}
  </style>
</head>
<body>
  <div class="page-wrap">

    <!-- Header -->
    <header class="report-header">
      <div class="run-name">{_h(directory.name)}</div>
      <div class="run-meta">Run at: {_h(run_at_str)}</div>
      {stat_row}
      <div class="badges-row">
        {fleet_badges_html}
      </div>
      <div class="section-title">Escalation Thread Metrics</div>
      {escalation_thread_metrics_html}
      {f'<div class="listings-row">{listing_pills}</div>' if listing_pills else ''}
    </header>

    <!-- Persona table -->
    <div class="section-title">Personas</div>
    <div class="filter-bar">
      <span class="filter-label">Filter:</span>
      <button class="chip active" data-filter="all">All ({total_personas})</button>
      <button class="chip" data-filter="clean">Clean ({clean_count})</button>
      <button class="chip" data-filter="issues">With issues ({issues_count})</button>
      <button class="chip" data-filter="buyer">Buyers</button>
      <button class="chip" data-filter="seller">Sellers</button>
      <button class="chip" data-filter="professional">Professionals</button>
    </div>
    <div class="table-wrap">
      <table class="persona-table">
        <thead>
          <tr>
            <th class="sortable" data-col="0" data-type="num">#<span class="sort-arrow"></span></th>
            <th class="sortable" data-col="1" data-type="str">Persona<span class="sort-arrow"></span></th>
            <th class="sortable" data-col="2" data-type="str">Listing<span class="sort-arrow"></span></th>
            <th class="sortable" data-col="3" data-type="num">Turns<span class="sort-arrow"></span></th>
            <th class="sortable" data-col="4" data-type="num">Esc<span class="sort-arrow"></span></th>
            <th class="sortable" data-col="5" data-type="num">Issues<span class="sort-arrow"></span></th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {tbody}
        </tbody>
      </table>
    </div>

  </div>
  <script>
{INLINE_SCRIPT}
  </script>
</body>
</html>"""

    out_path = directory / "index.html"
    out_path.write_text(html_out, encoding="utf-8")
    return out_path.resolve()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _find_latest_report_dir() -> Path | None:
    root = Path(__file__).parent.parent / "reports"
    candidates = [d for d in root.iterdir() if d.is_dir() and d.name.startswith("chatbot_test_")]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML report for a chatbot test run.")
    parser.add_argument(
        "directory",
        nargs="?",
        help="Path to a chatbot test report directory (defaults to latest by mtime)",
    )
    args = parser.parse_args()

    if args.directory:
        directory = Path(args.directory)
    else:
        directory = _find_latest_report_dir()
        if directory is None:
            print("ERROR: No chatbot_test_* directories found under reports/", file=sys.stderr)
            sys.exit(1)
        print(f"Auto-selected: {directory}", file=sys.stderr)

    try:
        html_path = generate_report(directory)
        print(str(html_path))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
