# Dalya Next MVP Readiness Closeout - 2026-06-23

## Verdict

| Readiness target | Status | Decision basis |
| --- | --- | --- |
| Internal demo | Green | Route, fallback, security, and chatbot gates from Tasks 1-12 plus 9A/9B are merged on first-parent history and have focused evidence. Use controlled fixtures/internal data and the agent workspace only. |
| Friendly pilot | Yellow, conditional | Allowed only for synthetic/internal pilot data with Twilio-only transport, manual review, explicit fallback to manual WhatsApp handling, CORS allowlist configuration, and the RLS/Task 10b boundary accepted. |
| External brokerage with real customer data | Red, blocked | Task 10b was not approved or executed in this plan. External brokerage/live-data use still requires target DB fingerprint, rollback artifact, maintenance window, app-role/RLS smoke evidence, and Eric approval. |
| Production/live data | Red, blocked | No production/staging DDL, RLS enablement, role/grant mutation, live writes, external DB tests, or production/staging env-file reads were performed. |

## Merged PR Summary

| Task | PR | Merge commit | Scope | Evidence |
| --- | --- | --- | --- | --- |
| 1 | #54 | `7167d9e7c71178691abd62dd906be183fabd3f45` | Today Queue escalation links route to `/agent/escalations?thread=<id>` and focus the inbox row. | `.omo/evidence/task-1-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-1-escalation-route.png` |
| 2 | #55 | `d68185a7fe8d8ecb7a7fd55aab465fb5a377cdbd` | Authenticated dashboard API failure renders an error/retry shell instead of sample rows. | `.omo/evidence/task-2-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-2-dashboard-fallback.png` |
| 3 | #56 | `bf04efe674d6cf2178cfbefa8770aaabb25c52cd` | Legacy Telegram Bot API runtime removed; historical DB artifacts remain only for schema/RLS history. | `.omo/evidence/task-3-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-3-telegram-routes.json` |
| 4 | #57 | `fc5a79ebfec114662113e6ef5cefe22e3f2bef19` | CORS now fails closed for live-class environments unless explicit origins are configured. | `.omo/evidence/task-4-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-4-cors.json` |
| 5 | #58 | `44748c93f9827829bc87bab43dfc9f356064fbb6` | Seller lead payloads anonymize buyer identity and preserve agent-facing PII permissions. | `.omo/evidence/task-5-dalya-next-mvp-readiness-plan.md` |
| 6 | #59 | `fc0740694bfd5bdc779af614bc7b4c3f9ce38e9d` | Buyer-facing output gate rewrites unsupported finance/process/legal claims to agent-confirmation language. | `.omo/evidence/task-6-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-6-verified-facts-output.json` |
| 7 | #60 | `e40ef214f6356d1d1574a127907048f73ffcd7c8` | Confirmed Dubai closing-cost facts seeded without expanding draft-only or listing-specific claims. | `.omo/evidence/task-7-dalya-next-mvp-readiness-plan.md` |
| 8 | #61 | `303ce634ed966881cd2ce74a67d60f3cea2c588c` | Current MVP chatbot regression profile covers simulated buyer-facing claim safety and no Telegram alert expectation. | `.omo/evidence/task-8-chatbot-regression.json` |
| 9A | #62 | `3511d978c35eca51c9d82d78fddfbfa4460e187b` | DealReadiness ranking calibration captured expected examples before behavior change. | `.omo/evidence/task-9a-deal-readiness-calibration.md` |
| 9B | #63 | `9895268509ec935789dcb0c3677edb81932ebe3d` | DealReadiness is a bounded ranking input for strongly actionable buyers, not a replacement ranking system. | `.omo/evidence/task-9b-dalya-next-mvp-readiness-plan.md` |
| 10 | #64 | `1b0c9d3a4c8ab8926a45006d5801aefb89ce3e9c` | `needs_reply` now distinguishes low-intent acknowledgements from actionable viewing/offer/process questions. | `.omo/evidence/task-10-dalya-next-mvp-readiness-plan.md` |
| 11 | #65 | `bb45281e8b473ebbf451468ce73354928fc0d20b` | Today Queue and escalation rows show structured 15-second handoff cards and exact actions. | `.omo/evidence/task-11-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-11-handoff-cards.png` |
| 12 | #66 | `24ca573b8fa609c2b66941dc9fea535afcdb96cf` | First-run and error states guide safe synthetic/internal activation without fake operational data. | `.omo/evidence/task-12-dalya-next-mvp-readiness-plan.md`, `.omo/evidence/task-12-first-run-desktop.png`, `.omo/evidence/task-12-first-run-mobile.png` |

## Final QA Wave

Task 13 adds and runs these final helpers:

- `scripts/verify_next_mvp_plan_completion.py`
- `scripts/review_next_mvp_final_diff.py`
- `scripts/verify_next_mvp_scope_guard.py`
- `frontend/scripts/verify-next-mvp-final-surface.mjs`

Required captured artifacts:

- `.omo/evidence/task-13-first-parent-log.txt`
- `.omo/evidence/task-13-git-status.txt`
- `.omo/evidence/final-next-mvp-plan-compliance.json`
- `.omo/evidence/final-next-mvp-code-review.md`
- `.omo/evidence/final-next-mvp-scope-guard.json`
- `.omo/evidence/final-next-mvp-surface/` (`BLOCKED.md` is acceptable only when the local surface cannot be safely launched)
- `.omo/evidence/task-13-next-mvp-readiness-closeout.md`

## Residual Risk

- Friendly pilot remains constrained to synthetic/internal data unless Eric separately approves the data class and the Task 10b gate.
- 360dialog/BSP is not an allowed current pilot path; the current posture is Twilio-only.
- Manual fallback remains required: if WhatsApp behavior, claim safety, or tenant/data concerns appear, disable/revoke the pilot Twilio webhook/credential and let agents handle WhatsApp manually.
- CORS must use explicit configured HTTP/HTTPS origins in live-class environments.
- The RLS/app-role rollout remains unexecuted for this plan. Task 10b is the separate approval boundary for production/live data and external brokerage real-customer use.

## Safety Confirmations

- Task 10b was not executed.
- No production/staging DDL, migrations, RLS enablement, role/grant mutation, live writes, external DB tests, dependency/lockfile edits, or production/staging env-file content reads are part of this closeout.
- Telegram is removed as an active runtime integration and was not replaced in this plan.
- This report does not claim external brokerage readiness or production/live-data readiness.
