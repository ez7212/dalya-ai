# Dalya Mahoroba First-Run Pilot Report Template

Output path: `reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md`

## Executive Verdict

- Verdict: Green / Yellow / Red
- One-sentence reason:
- Biggest blocker or confidence driver:
- Environment:
- Data class:
- Transport:
- Smoke mode ran: yes/no
- Chatbot mode ran: yes/no
- Browser mode ran: yes/no
- Full first-run verdict basis:
- Main agent:
- Brokerage: `mahoroba-realty`

## Manual Inputs Used

- Test/dev DB:
- `PROD_DB_HOST`:
- Eric Supabase auth path:
- Anthropic key available: yes/no
- Seed/reset approval:
- Listing creation mode: agent-dashboard
- Listing import mode: api/snapshot/manual
- Listing URLs provided:
- Generated buyer data approved:

## Verdict Thresholds

- Green: Browser mode + chatbot mode + API smoke all pass for the golden path,
  and stress path has no unsafe claims.
- Yellow: Golden path is demo-able, but some stress/API/browser items are
  blocked or rough.
- Red: `/agent` cannot load real pilot data, fallback rows appear, unsafe
  claims leak, or agent actions cannot be completed.

API checks run without Eric JWT must be marked `SMOKE PASS`, not full `PASS`,
and cannot satisfy browser/auth readiness.

## Commands Run

```bash
# Exact commands, copied from command logs.
```

## First-Run Matrix

| Area | Scenario | Expected | Actual | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| Safety | Phase 0 gate | test/dev DB, simulated transport, reset-safe | | | |
| Listing creation | Agent dashboard | four PF/Bayut URLs pasted through `/listings/new/portal`, reviewed, published, listing ids captured | | | |
| Seed | Canonical Mahoroba | `mahoroba-realty`, 4 listings, 7 buyers | | | |
| Dashboard | `/agent` healthy load | seeded data, no fallback rows | | | |
| Today Queue | Route-backed work | useful title/reason/status/href | | | |
| API | Service-context smoke | endpoint assertions labeled `SMOKE PASS`, not full auth readiness | | | |
| API | Eric auth pass | Eric JWT + `X-Brokerage-Id: mahoroba-realty` where available | | | |
| Chatbot | Adam hot ready | one-question qualification, viewing-ready | | | |
| Chatbot | Priya Verified Facts | direct only when verified; defer/escalate unsafe | | | |
| Chatbot | Low-context | one useful question, low readiness | | | |
| Offers | Hassan | offer record/escalation/history | | | |
| Handoff | Mei | escalation + AI pause/resume visible or blocked | | | |
| Weak facts | Tom | no invented service/NOC/access facts | | | |
| Opt-out | Stop | suppression + blocked sends | | | |
| Drafts | Review actions | edit/send/reject/snooze or blocked | | | |
| Viewings | Ready listing | propose/confirm/inspect or blocked | | | |
| Safety | Minimal sanity | wrong-context denial/no live sends/no leaks | | | |

## Golden Path Demo

1. Open `/agent`.
2. Review Today Queue.
3. Run Adam ready-buyer scenario.
4. Open Adam conversation.
5. Inspect readiness and next action.
6. Propose/confirm or inspect viewing.
7. Edit/send or inspect follow-up draft.
8. Return to `/agent` and confirm queue state changed.

## Stress Path Demo

1. Priya asks off-plan payment/DLD/NOC/LTV/legal questions.
2. Low-context buyer asks `price?`, `last price?`, `send pics`.
3. Hassan makes below-threshold offer and revises upward.
4. Mei asks for a human agent.
5. Tom asks missing service charge/NOC/access questions.
6. Opt-out buyer sends `stop`.

## Findings

| Severity | Category | Finding | Evidence | Suggested ticket |
| --- | --- | --- | --- | --- |

Categories:

- Bug
- UX gap
- Data/seed gap
- Environment blocker
- Safety blocker

## Blockers Before External/Friendly Pilot

Always state:

- Production RLS/app-role rollout remains separate.
- Live WhatsApp provider readiness remains separate.
- 360dialog is out of first-run scope.
- Real customer data is out of first-run scope.

Add any run-specific blockers here.

## Suggested Next PRs/Tickets

Format:

```markdown
[area] title
Why now:
Files likely touched:
Acceptance:
Out of scope:
```

## Final Recommendation

- Ready for repeat internal demo:
- Ready for approved synthetic/internal friendly pilot:
- Not ready for:
