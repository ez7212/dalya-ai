# Dalya — Mahoroba First-Run Internal Pilot Report

_Brokerage: `mahoroba-realty` · pilot DB: Neon fork `ep-odd-pine` · transport: simulated (no live sends)_
_Evidence root: `.omo/evidence/lazycodex-omo-pilot/`_

## Executive Verdict — **YELLOW** (demo-able golden + stress path; browser mode blocked on auth)

The chatbot, API-smoke, and minimal-safety surfaces all pass against real seeded pilot data
over simulated transport. The golden path (hot ready buyer) and the full stress path (Verified
Facts, low-context, firm offer, human takeover, weak-listing fact gap, opt-out) **pass 7/7**.
The single thing standing between Yellow and Green is **browser mode (T7/T8)**, which needs Eric's
Supabase login to drive `/agent` as a real authenticated agent — I cannot authenticate as Eric.

**Biggest verdict driver:** browser walkthrough is unrun (auth-gated). Everything I can run without
Eric's session is green.

### Execution modes
| Mode | Ran? | Notes |
| --- | --- | --- |
| Smoke (service/API) | ✅ yes | 7 pilot-critical endpoints wired + auth-protected |
| Chatbot (LLM, simulated transport) | ✅ yes | 7/7 buyer scenarios pass |
| Browser (`/agent` as Eric) | ❌ no | Blocked: needs Eric Supabase auth |

## Task status
| Task | Status | Evidence |
| --- | --- | --- |
| T1 tracking | ✅ done | `BACKLOG.md` umbrella entry |
| T2 safety gate + reset policy | ✅ done | `scripts/pilot/check_safety_gate.py` |
| T3 dashboard listings + dependent seed/reset | ✅ done | `seed-summary.json`; `seed_mahoroba_pilot.py`, `reset_mahoroba_pilot.py` |
| T4 buyer scenario runner | ✅ done — **7/7 PASS** | `scenarios/scenario-results.json` |
| T5 report generator | ✅ done | `scripts/pilot/generate_report.py` |
| T6 pilot-critical API smoke | ✅ done — 7 SMOKE PASS | `task-6-api-smoke.json` |
| T7 `/agent` browser walkthrough | 🔒 BLOCKED | needs Eric Supabase auth |
| T8 golden + stress rehearsal (browser half) | 🟡 partial | chatbot half done (T4); browser replay blocked |
| T9 minimal safety sanity | ✅ done — PASS | `task-9-safety.json` |
| T10 final report | ✅ this document | — |

## Top findings

1. **🐛 Found + fixed: firm-offer escalation crashed the buyer reply.** The offer path recorded the
   offer in `offer_records` but then raised a Pydantic validation error building `EscalationAlert`
   (`escalation_type=EscalationType.offer` — the enum — where the schema wants the string literal
   `"offer"`). Net effect in production: a buyer making a firm offer would get **no reply** while the
   offer silently logged. A second latent instance (`legitimate_conveyancing`) had the same defect.
   Both fixed (`.value`) in `app/core/chatbot_engine.py`; the offer scenario now passes end-to-end.
2. **🐛 Found + fixed: pilot reset confirm-guard was defeated by the env file.** `.env.pilot` defines
   `DALYA_PILOT_CONFIRM`, and the reset loaded it with `override=True`, auto-satisfying the
   "are-you-sure" guard (a test deleted the seed). Fixed to read the confirm token from the operator's
   shell only. Apply-without-confirm and wrong-confirm now both refuse (exit 2).
3. **Chatbot behavior is genuinely strong.** Verified-Facts deferral on off-plan LTV/NOC, agent-
   confirmation language on missing service-charge/NOC facts, human-takeover routing to Eric, and
   opt-out suppression all behaved correctly with no seller-private leakage.

## Scenario matrix — chatbot (7/7 PASS)
| Scenario | Buyer → listing | Proved |
| --- | --- | --- |
| `hot_ready_buyer` | Adam → Golf Grove (ready) | Engages, identifies as Dalya/Mahoroba, names listing; no seller-private leak |
| `offplan_verified_facts` | Priya → The Oasis (off-plan) | Defers LTV/NOC to agent/advisor; no invented ratio |
| `low_context_price_buyer` | low-context → Golf Grove | Answers price, does not over-qualify (≤2 questions) |
| `firm_offer_escalation` | Hassan → The Nest (luxury) | Offer handled safely + recorded; no leak (post-fix) |
| `human_takeover` | Mei → The Nest | Routes to Eric; escalation raised; AI hands off |
| `weak_listing_fact_gap` | Tom → Park Ridge | Does not invent service charge/NOC; "asking Eric to confirm" |
| `opt_out` | opt-out → Golf Grove | Suppression honored; no marketing push |

## Seed dataset as run (idempotent, pilot-marked)
4 dashboard-created listings (Golf Grove ready 7.5M, Park Ridge ready 4.2M, The Oasis off-plan 15.2M,
The Nest luxury 85.5M) · 3 supporting agents (Sara/Omar/Lina) · 7 buyer personas · 7 conversations +
14 messages · 1 below-threshold offer · 1 viewing · 2 drafts · 3 escalation threads. All rows carry
`dalya_pilot=mahoroba-first-run` / `pilot_` ids; reset is surgical and confirm-gated.

## API smoke (T6) — 7 SMOKE PASS, full-auth BLOCKED
hot-list, buyers, drafts, escalations, offers, viewings, conversation-detail — each rejects both
unauthenticated and wrong-brokerage requests (403). This proves routing + the tenant auth guard.
**It is not a full PASS:** the real authenticated data path needs Eric's Supabase JWT.

## Minimal safety (T9) — PASS
No live sends (simulated transport) · unauthenticated denied · wrong-brokerage denied · opt-out
suppressed · no seller-private leakage · Verified Facts defers on uncertainty.
**Deferred (not run, by design):** full tenant isolation audit, media URL signing depth, live/sandbox
provider readiness, production RLS/app-role rollout.

## Blockers before a real customer pilot
1. **Browser mode (T7/T8)** — drive `/agent` as Eric (Supabase login) to prove the UI loads real
   seeded data with no fallback rows and that Today-Queue links work.
2. **Full-auth API verification** — re-run T6 with Eric's JWT for true 200 data PASS.
3. Live WhatsApp provider readiness, production RLS/app-role — standing, out of first-run scope.

## Suggested next tickets
- `fix(chatbot)`: regression test asserting firm-offer + conveyancing escalations build a valid
  `EscalationAlert` (guard against enum-vs-literal recurrence).
- `test(pilot)`: browser walkthrough harness (Playwright + stored Eric `storageState`) for T7/T8.
- `chore(pilot)`: thread `ERIC_PILOT_JWT` into `verify_api_smoke.py` for full-auth PASS.

## Commands run
```
scripts/pilot/seed_mahoroba_pilot.py   --apply --summary seed-summary.json
scripts/pilot/reset_mahoroba_pilot.py  --dry-run   (+ refuse-without-confirm verified)
scripts/pilot/run_scenarios.py         --suite first-run --evidence-dir scenarios
scripts/pilot/verify_api_smoke.py      --base-url http://localhost:8000
scripts/pilot/verify_minimal_safety.py --env-file .env.pilot
scripts/pilot/generate_report.py       --input <evidence> --output <report>
```
