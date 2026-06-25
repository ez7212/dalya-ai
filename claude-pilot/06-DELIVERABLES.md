# 06 — Deliverables (final report structure)

Agent F writes `reports/claude-pilot-<date>/PILOT-REPORT.md` with exactly these sections. Supporting
artifacts go alongside it (`scenarios/`, `commands/`, `matrix.md`, screenshots/notes).

1. **Executive verdict** — Green / Yellow / Red for internal demo readiness + one-sentence reason.
   (Green = Eric can demo live today; Yellow = demo-able with caveats/scripted around gaps; Red = a
   surface breaks the story or leaks unsafe info.)

2. **Demo script** — the step-by-step Eric follows live from `/agent`, with exact buyer personas,
   messages to simulate, and the expected dashboard change after each step. (Productionized from
   `05-DEMO-SCRIPTS.md` with any reality corrections.)

3. **Test matrix** — `04-TEST-MATRIX.md` fully filled: surface, scenario, expected, actual,
   pass/fail/blocked, notes (file/endpoint refs).

4. **Top product findings** — prioritized by demo impact (confusing / unsafe / unimpressive first).
   Each finding: title, severity, surface, **file/endpoint ref**, and category — split into
   **Bugs** vs **UX gaps** vs **Data/seed gaps**.

5. **Recommended pilot seed dataset** — the final seed as run (brokerage, agents, listings, buyers,
   conversations, offers, viewings, escalations, drafts) with the exact ids/markers, so it's
   reproducible. Points at `scripts/pilot/seed_mahoroba_pilot.py`.

6. **Golden-path demo** — the cleanest 10–15 min flow, confirmed working.

7. **Stress-path demo** — the harder 20–30 min flow (unsafe facts, low-context, offer, escalation,
   takeover, opt-out, incomplete listing) and how Dalya held up.

8. **Blockers before real customer pilot** — explicitly: RLS/app-role production boundary (separate
   gate), live WhatsApp provider readiness, 360dialog limitations (`dialog360_transport.py` is a stub),
   and any dashboard/chatbot gaps found. Each with severity + what unblocks it.

9. **Commands run** — every test command, dev-server command, API call, browser check — including what
   failed and why. (Merge of `commands/<agent>.md`.)

10. **Suggested next PRs/tickets** — small, concrete, one branch/PR each. Format:
    `[area] title — what & why — files — acceptance`. Linear-ready (the repo uses the Linear MCP).

---

### Quality bar
- Every finding has a file/endpoint reference or it's marked "unverified — needs repro."
- No claim of "works" without an observed result (DB row, screenshot, or API response).
- Blocked items say exactly what blocked them and the closest simulation that was run instead.
- The verdict sentence names the single biggest reason, not a hedge.
