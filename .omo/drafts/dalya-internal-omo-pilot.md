---
slug: dalya-internal-omo-pilot
status: plan-written
intent: clear
pending-action: update .omo/plans/dalya-internal-omo-pilot.md
approach: Claude plan as repo-grounded spine, Codex verdict framing, LazyCodex evidence/lanes discipline, trimmed to a smaller first-run Mahoroba rehearsal.
---

# Draft: dalya-internal-omo-pilot

## Components (topology ledger)
| id | outcome (one line) | status | evidence path |
| --- | --- | --- | --- |
| C1 Safety and blockers | `.env.pilot`, disposable local DB or Neon `pilot` branch, Eric auth path, seed permission, Anthropic key, four listing URLs, and simulated-only transport are explicit before execution. | active | .omo/pilots/lazycodex-omo-pilot/manual-inputs.md |
| C2 Canonical Mahoroba seed | First run uses existing `mahoroba-realty`, four dashboard-created listings, pilot-marked dependent rows, seven buyers, surgical reset, and collision protection for non-pilot Mahoroba data. | active | .omo/evidence/lazycodex-omo-pilot/seed-summary.json |
| C3 Simulated buyer rehearsal | Seven buyer scenarios exercise golden and stress paths through safe simulated transport. | active | .omo/evidence/lazycodex-omo-pilot/scenarios/ |
| C4 Agent workspace proof | Eric's `/agent` browser session proves seeded live data and core route-backed workflows, or auth is explicitly BLOCKED. | active | .omo/evidence/lazycodex-omo-pilot/browser/ |
| C5 Final verdict report | One report answers whether Eric can demo Dalya as Mahoroba's command center and lists blockers/tickets. | active | reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md |

## Open assumptions (announced defaults)
| assumption | adopted default | rationale | reversible? |
| --- | --- | --- | --- |
| Final spine | Use Claude's plan as the operational base. | It is most repo-accurate about Mahoroba, auth, transport, endpoints, and fallback-data risk. | yes |
| Product framing | Keep Codex verdict questions and golden/stress split. | These best express what the pilot should decide. | yes |
| Execution discipline | Keep LazyCodex lanes, evidence, report template, and final verification. | These prevent self-report-only success. | yes |
| Brokerage identity | Use `mahoroba-realty`, not `mahoroba-internal-pilot`. | Existing repo conventions and Claude findings point to canonical Mahoroba. | yes, only if Eric explicitly wants isolated tenant |
| First-run scope | Four listings, seven buyers, core `/agent` surfaces. | This can finish and still answer the command-center question. | yes |
| Deferred checks | Lead ingest, media/voice, Google live write, full tenant/security sweep, and live transport are deferred. | They are valuable but can turn the first rehearsal into a hardening epic. | yes |
| Tracking | One umbrella Linear issue if available; if blocked, use one `BACKLOG.md` fallback item and continue. | Satisfies project discipline without letting external SaaS writes hard-block useful work. | yes |

## Findings (cited)
- `claude-pilot/00-EXECUTION-PLAN.md` provides the strongest phase order: safety gate -> seed -> auth -> buyer sim/API/safety -> browser -> report.
- `claude-pilot/01-REPO-FINDINGS.md` identifies canonical `mahoroba-realty`, Supabase JWT requirements, `SimulatedTransport`, existing seed patterns, route tree, and fallback-data risk.
- `claude-pilot/02-SEED-DATASET.md` gives exact Mahoroba/Eric seed shape; first run trims it to 4 listings and 7 buyers.
- `codex-pilot/dalya-internal-pilot-plan.md` gives the strongest product verdict questions and non-production-readiness framing.
- `.omo/plans/dalya-internal-omo-pilot.md` already had strong evidence/QA discipline but used `mahoroba-internal-pilot` and too-broad first-run scope.

## Decisions (with rationale)
- Update the plan in place rather than creating a fourth plan.
- Canonical first-run tenant is `mahoroba-realty`; all rows must be pilot-marked.
- Manual inputs live in `.omo/pilots/lazycodex-omo-pilot/.env.pilot`.
- Four listing archetypes should be created through `/listings/new/portal` as Eric, using Eric-provided Property Finder/Bayut URLs. `POST /api/v1/listings/draft-from-url` remains the dashboard's scraper mechanism and diagnostic surface, not a substitute for the full listing pass.
- Seed/reset may add pilot-marked child rows under `mahoroba-realty` but must never delete or overwrite existing non-pilot Mahoroba records.
- First-run output is `reports/internal_pilot/mahoroba_first_run/PILOT-REPORT.md`.
- Implementation scripts, if needed during execution, live under `scripts/pilot/` and tests under `tests/pilot/`.
- The first run has explicit modes: smoke mode, chatbot mode, browser mode, and deferred live/sandbox transport mode.
- API checks without Eric JWT are `SMOKE PASS`, not full PASS, and cannot satisfy browser/auth readiness.
- Missing test DB, Eric auth, or Anthropic key should create BLOCKED rows, not fake PASS rows.

## Scope IN
- Safety gate.
- Canonical Mahoroba seed/reset.
- Four first-run listings.
- Seven first-run buyers.
- Simulated buyer scenario runner.
- Pilot-critical API smoke.
- `/agent` browser walkthrough as Eric.
- Minimal safety sanity.
- Final report and suggested tickets.

## Scope OUT (Must NOT have)
- Real customer data.
- Live WhatsApp.
- 360dialog/BSP.
- Production DDL or shared-staging schema creation/DDL.
- Production RLS/app-role rollout.
- Lead ingest as a required first-run pass.
- Media/voice as a required first-run pass.
- Google Calendar live write.
- Full tenant/security sweep.
- Owner/admin/campaign/legacy marketplace polish.

## Open questions
- Required before DB-backed run: fill `.env.pilot` with disposable local DB or dedicated Neon `pilot` branch `DATABASE_URL`, `PROD_DB_HOST`, four listing URLs, and seed/reset permission. Shared staging only if Eric explicitly confirms isolation and pilot safety.
- Required before browser run: Eric Supabase auth user uuid/JWT/session path.
- Required before chatbot mode: `ANTHROPIC_API_KEY`.
- Optional: Eric can override generated listing/buyer details.

## Approval gate
status: plan-written
Note: Eric approved the new hybrid direction in the previous message and explicitly asked to update the plan. Execution still requires a separate explicit start command.
