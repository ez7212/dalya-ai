# Dalya MVP Re-Review Evidence Pack - 2026-06-22

## Decision

| Readiness target | Status | Decision basis |
| --- | --- | --- |
| Internal demo | Green | The original P0 blockers are closed or locally verified, the agent workspace build passes, and the demo can use controlled fixtures/internal data. |
| Friendly pilot | Yellow, conditional | Allowed only for synthetic/internal data, Twilio-only transport, manual review, and the Task 11 operator runbook. Real-customer/external-brokerage data remains blocked until the approval-gated DB role/RLS work is complete. |
| External brokerage pilot | Red, blocked | Requires explicit data-class approval, provider/live-environment signoff, and the separate Task 10b approval gate before real-customer data is used. |
| Production/live data | Red, blocked | Task 10b was not executed under this plan and still requires separate Eric approval with target DB fingerprint, rollback artifact, and maintenance window. |

## Executive Summary

The remediation wave moves Dalya from the original "internal demo Green / friendly pilot Yellow / external and production Red" review toward a stronger controlled-pilot posture. The three original P0 blockers are addressed:

- Legacy listing surfaces are gated/removed under PR #43.
- Buyer-facing off-plan finance/process claims now fail closed through Verified Facts policy under PR #44.
- Authenticated agent workspaces no longer receive normal-path sample operational data under PR #45.

The remaining production-class risk is explicit rather than hidden: Task 10a recorded a non-production RLS/app-role posture, but Task 10b was deliberately not run. This evidence pack therefore does not promote external or live-data readiness.

## Merged Remediation Evidence

| Task | PR | Merge commit | Evidence summary |
| --- | --- | --- | --- |
| Task 3 - Gate legacy listing routes | #43 | `2608f80232ece39228f84ced0bf5bdf5d744ab7a` | Focused route-gating tests and security review evidence are local under `.omo/evidence/task-3-*`; public metadata stayed generic. |
| Task 4 - Gate off-plan finance claims | #44 | `e8828c25d27939091089449e5fa3d9e29e02494a` | Focused no-DB runtime QA passed after approved temp-venv repair: 7 tests passed plus direct engine/prompt seams. |
| Task 5 - Remove sample dashboard fallback | #45 | `bef5a4ebf23efc0596a55ea56df585adf2940cb3` | Direct authenticated empty-dashboard seam passed; response asserts `sample_data: false`, empty collections, zero metrics, and no sample IDs/copy. |
| Task 6 - Make staging live-class | #46 | `ca3584db3268a18c85abb0278625e02974f11b93` | Focused live-class runtime tests passed with 40 no-conftest tests. |
| Task 7 - Lock WhatsApp pilot transport plan | #47 | `0e7b6344d939966b5aef726ef112754fb2c80048` | Pilot transport is Twilio-only; unsupported provider path remains future work. |
| Task 8 - Show readiness reasons | #48 | `daf80c655a7f65276a5d659f7ecbeb289d56ff9e` | Presenter and visual QA show readiness stage/action/reason/missing fields in agent surfaces without ranking changes. |
| Task 9 - Prioritize Today Queue | #49 | `d036c093669a604ae7c4d172812a583013429c57` | Static and visual QA show one ranked Today Queue, mobile/desktop screenshots, and pilot-focused nav gating. |
| Task 10a - Record RLS/app-role risk posture | #50 | `0141cd2e39080e1544e9ab3725675a20a4216871` | Non-production guard rehearsal/risk record only; no production/staging DDL, RLS enablement, role mutation, or live write. |
| Task 11 - Add pilot readiness runbook | #51 | `a455416f0a62087651f6d54f89c0096114d9aa95` | Runbook defines allowed data/users, Twilio-only limits, manual review, pause/rollback, and 10b as the live-data gate. |

## Four-Dimension Re-Review

### Security

Verdict: Yellow for controlled internal/synthetic pilot; Red for real-customer external or live data.

Evidence:
- PR #43 closed the original unauthenticated legacy listing-surface blocker with focused route-gating coverage kept in local evidence.
- PR #46 treats staging, preview, and live-class environments as fail-closed for debug routes, webhook requirements, provider checks, and simulated/unsupported transports.
- PR #50 records that RLS/app-role enforcement is rehearsed/risk-recorded only. Real-customer external pilot and production/live data are still blocked until Task 10b.

Fresh Task 12 checks:
- `PYTHONPATH=venv/lib/python3.13/site-packages:. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest --noconftest tests/test_runtime_config_live_env.py tests/test_live_class_security_env.py -q` -> `40 passed in 0.25s`.
- `python3 -c '<ast parse key Python files>'` -> `ast_parse_ok 12`.
- `git diff --check` -> pass.
- Conflict-marker scan over app/frontend/docs/reports/tests/scripts -> no matches.

### Chatbot And Real-Estate Claims

Verdict: Yellow for controlled pilot; Red for unrestricted live buyers.

Evidence:
- PR #44 removes seller-equity numeric disclosure and avoids deterministic payment-process overclaiming unless direct active Verified Facts support it.
- Approved Task 4 runtime QA installed only `requirements.txt` in an isolated temp venv, then ran `pytest ... --noconftest`: `7 passed, 1 warning in 9.05s`.
- Direct engine/prompt seams verified remaining developer balance handling, ready-property no-developer-plan behavior, and fail-closed missing Verified Facts topics.

Residual risk:
- Wider conversational breadth, Arabic/Hinglish evaluation, and full chatbot regression still belong to future hardening. Controlled pilot use must keep manual review on buyer-facing drafts and avoid unverified finance/process claims.

### UX And Agent Workflow

Verdict: Yellow/Green for internal demo and controlled synthetic/internal pilot.

Evidence:
- PR #45 removed fake sample operational data from authenticated normal-path dashboard payloads.
- Task 8 / PR #48 adds readiness reasons to agent surfaces.
- Task 9 / PR #49 converts `/agent` toward a ranked Today Queue and pilot-focused navigation.

Fresh Task 12 checks:
- `npm run build` in `frontend/` -> passed.
- `node scripts/verify-task8-readiness-display.mjs` -> 14 presenter checks passed.
- `node scripts/verify-task8-readiness-visual.mjs` -> passed after escalated local Chromium launch; screenshot: `reports/dalya-mvp-rereview-evidence-2026-06-22/task8-readiness-reasons-visual.png`.
- `node scripts/verify-task9-today-queue.mjs` -> 16 queue/nav checks passed.
- `node scripts/verify-task9-today-queue-visual.mjs` -> 6 visual checks passed after escalated local Chromium launch; screenshots: `reports/dalya-mvp-rereview-evidence-2026-06-22/task9-today-queue-desktop.png` and `reports/dalya-mvp-rereview-evidence-2026-06-22/task9-today-queue-mobile.png`.

### Pilot Workflow

Verdict: Yellow, conditional.

Evidence:
- PR #47 locks the pilot transport path to Twilio-only.
- PR #51 gives the operator an executable no-deploy pause/rollback path and manual fallback.
- The runbook allows only synthetic/internal pilot data unless the RLS/app-role approval gate is cleared.

Residual risk:
- Existing WhatsApp provider strategy beyond Twilio-only is not part of this plan.
- External brokerage and live-data operation require a separate target/fingerprint/rollback/maintenance-window approval.

## P0 Checklist

| P0 item from original re-review | Current status | Evidence |
| --- | --- | --- |
| Legacy listing surface exposure/mutation risk | Closed for this plan | PR #43; local security evidence under `.omo/evidence/task-3-*`; no public reproduction details included here. |
| Buyer-facing off-plan finance/process overclaims | Closed for controlled pilot | PR #44; focused runtime QA passed and direct seams verified fail-closed behavior. |
| Authenticated sample dashboard fallback | Closed | PR #45; direct handler seam confirms `sample_data: false` and no sample operational data. |

## Remaining P1/P2 Risks

| Risk | Owner | Tracking/status |
| --- | --- | --- |
| Production/live RLS/app-role rollout | Eric/operator approval gate | Task 10b excluded from this plan; requires target DB fingerprint, rollback artifact, and maintenance window. |
| External brokerage pilot with real-customer data | Eric/operator | Blocked until the Task 10b gate and live-data approval are satisfied. |
| Full chatbot multilingual/edge-case breadth | Product/engineering | Future hardening; not a blocker for controlled internal/synthetic pilot. |
| Non-Twilio WhatsApp provider path | Product/engineering | Future separate provider implementation; not included in this pilot posture. |

## Runtime And HTTP Evidence Notes

- Full FastAPI live-server HTTP replay was not rerun in Task 12 because the local repo venv points at a missing Python runtime and full app import can trigger unsafe DB configuration paths. This pack relies on the focused route/TestClient and direct-route evidence captured during Tasks 3 and 6, plus fresh no-DB Task 6 runtime tests.
- No DB-backed tests were run against unverified external Neon or any production/staging database.
- No production/staging env file contents were read.
- No production/staging DDL, migrations, RLS enablement, role/grant mutation, external DB test, live write, dependency/lockfile edit, or Linear write occurred.

## Final Recommendation

Proceed with an internal demo and, if Eric accepts the documented constraints, a synthetic/internal friendly pilot using the Task 11 runbook. Do not use this state for real-customer external brokerage pilot data or production/live data.
