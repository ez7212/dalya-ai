# Dalya Mahoroba First-Run Pilot Report

_Generated from evidence at `.omo/evidence/lazycodex-omo-pilot` (interim)._

## Executive Verdict

- Verdict: **Red**
- Reason: Insufficient evidence: required modes are blocked. Supply auth/keys/seed and re-run.
- Brokerage: `mahoroba-realty`
- Phase 0 safety gate: BLOCKED
- Smoke mode ran: no
- Chatbot mode ran: no
- Browser mode ran: no

## Evidence Matrix

| Area | Mode | Status | Evidence path |
| --- | --- | --- | --- |
| Phase 0 safety gate | smoke | BLOCKED | `task-2-safety.json` |
| Dashboard listing creation (4 URLs) | browser | BLOCKED | `listing-creation/listing-ids.json` |
| Dependent seed summary | smoke | BLOCKED | `seed-summary.json` |
| Buyer scenario runner | chatbot | BLOCKED | `scenarios` |
| Pilot-critical API smoke | smoke | BLOCKED | `task-6-api-smoke.json` |
| /agent browser walkthrough | browser | BLOCKED | `browser` |
| Golden + stress rehearsal | chatbot | BLOCKED | `demo` |
| Minimal safety sanity | smoke | BLOCKED | `minimal-safety.json` |

## Blocked Artifacts (must resolve before Green)

- Phase 0 safety gate — supply `task-2-safety.json` (mode: smoke).
- Dashboard listing creation (4 URLs) — supply `listing-creation/listing-ids.json` (mode: browser).
- Dependent seed summary — supply `seed-summary.json` (mode: smoke).
- Buyer scenario runner — supply `scenarios` (mode: chatbot).
- Pilot-critical API smoke — supply `task-6-api-smoke.json` (mode: smoke).
- /agent browser walkthrough — supply `browser` (mode: browser).
- Golden + stress rehearsal — supply `demo` (mode: chatbot).
- Minimal safety sanity — supply `minimal-safety.json` (mode: smoke).

## Standing Blockers (always separate from first run)

- Production RLS / app-role rollout remains separate.
- Live WhatsApp provider readiness remains separate.
- 360dialog / BSP pilot is out of first-run scope.
- Real customer data is out of first-run scope.

## Verdict Thresholds

- Green: browser + chatbot + smoke evidence present; stress path has no unsafe claims.
- Yellow: golden path demo-able, but some stress/API/browser items blocked or rough.
- Red: `/agent` cannot load real pilot data, fallback rows appear, unsafe claims leak, or the safety gate failed.

