# Dalya Internal Pilot Plan

Date: 2026-06-24  
Label: `codex-pilot`  
Mode: seeded internal pilot rehearsal  
Primary brokerage: Mahoroba Realty  
Primary agent: Eric Zhu  

## Purpose

Run Dalya's current MVP end to end as a realistic internal Mahoroba pilot, using synthetic data only. The goal is to determine whether Dalya can credibly function as an agent daily command center before any external brokerage or live-customer pilot.

This is not a production-readiness certification. Production RLS/app-role rollout, live WhatsApp provider readiness, real customer data, and external brokerage traffic remain outside this pilot unless separately approved.

## Pilot Verdict To Produce

The final run must answer:

- Can Eric open `/agent` and understand what to do next within 30 seconds?
- Does Today Queue prioritize real work: escalations, overdue tasks, needs-reply, viewings, drafts, hot buyers, follow-ups?
- Does the buyer-facing Property Advisor answer safe listing questions, ask one qualification question at a time, and fail closed on unsupported Dubai process/fee/legal claims?
- Do escalations, drafts, offers, viewings, buyer cards, and DealReadiness work together as one coherent workflow?
- Does the product feel like it helps an agent close deals faster without leaking private/seller/internal data?

## Non-Negotiable Constraints

- Do not use real customer data.
- Do not send real WhatsApp messages unless Eric explicitly confirms a safe simulated/sandbox transport.
- Prefer `MESSAGING_TRANSPORT=simulated`.
- Do not enable production/live external data flows.
- Do not run production/staging DDL.
- Do not run migrations unless a pilot-only local/test DB setup explicitly requires them and Eric approves.
- Do not enable production RLS/app-role rollout.
- Do not read production/staging env file contents.
- Do not mutate non-pilot data.
- All seed/reset scripts must be idempotent and restricted to clearly labeled pilot/demo data.
- Any destructive reset must require an explicit pilot identifier.
- If DB-backed flow is unavailable, record the blocker and run the closest local/API/UI simulation.

## Success Definition

Internal pilot demo readiness is Green only if:

- Seeded Mahoroba workspace loads in `/agent`.
- Today Queue contains realistic prioritized work with working links.
- At least one golden-path ready-property buyer can move from inquiry to readiness/viewing/escalation/draft/agent action.
- At least one off-plan stress buyer proves Verified Facts guardrails and agent-confirmation behavior.
- Buyer cards show qualification provenance and DealReadiness.
- Escalations can be listed, replied to or resolved, and route correctly.
- Drafts can be edited, sent, rejected, and snoozed in a safe simulated path.
- Offers can be created/confirmed/discarded/transitioned and reflected in buyer/conversation surfaces.
- Ready-property viewing flow can be proposed/confirmed and inspected in `/agent/viewings`.
- Lead ingest can be simulated or explicitly marked blocked with reason.
- No fake operational sample data appears as live workspace data.
- No unsupported production/live-data readiness claims are made in the report.

## Agent Workstreams

Use multiple coding agents, but keep write scopes separate.

### Agent A - Repo Discovery And Data Model

Scope:

- Inspect current seed scripts, fixtures, test conventions, auth/dev login, messaging transport, API routes, and frontend routes.
- Produce a route and table/model map for pilot-critical flows.
- Identify the safest local DB path for a seeded run.

Allowed output:

- Notes under `codex-pilot/evidence/discovery.md`
- No code changes unless needed for discovery scripts, and only after Agent Lead approval.

### Agent B - Pilot Seed And Reset

Scope:

- Build or reuse a pilot seed script.
- Build or reuse a pilot reset script.
- Seed Mahoroba brokerage, agents, listings, buyers, conversations, drafts, escalations, offers, viewings, and lead ingest examples.

Expected files if missing:

- `scripts/seed_internal_pilot.py`
- `scripts/reset_internal_pilot.py`
- `codex-pilot/seed-data/internal-pilot-seed.json` or equivalent fixture

Requirements:

- Idempotent.
- Pilot-only labels everywhere.
- No non-pilot deletes.
- Fake/test phones and emails only.
- Seed data must be realistic enough for frontend and chatbot flows.

### Agent C - Message Simulation And Chatbot Harness

Scope:

- Simulate buyer messages safely.
- Prefer existing `send-test`, direct chatbot engine, simulated transport, or test harness paths.
- Exercise buyer-facing chatbot, Verified Facts, DealReadiness next-question planning, offers, escalation triggers, opt-out, media/voice limitations.

Expected files if missing:

- `scripts/run_internal_pilot_messages.py`
- `codex-pilot/evidence/chatbot-transcripts/*.json`

Requirements:

- Do not use real WhatsApp transport.
- Log buyer message, assistant response, escalation state, draft state, readiness state, and safety notes.

### Agent D - API Smoke And Data Verification

Scope:

- Verify pilot-critical backend endpoints against seeded data.
- Check auth/tenant boundaries where safe.
- Verify DB records after actions.

Endpoints to cover:

- `GET /api/v1/agent/dashboard`
- `POST /api/v1/agent/hot-list/refresh`
- `GET /api/v1/agent/buyers`
- `GET /api/v1/agent/buyers/{profile_id}`
- `PATCH /api/v1/agent/buyers/{profile_id}/fields`
- `GET /api/v1/agent/leads/{conversation_id}`
- `POST /api/v1/agent/leads/{conversation_id}/ai-mode`
- `GET /api/v1/agent/escalations`
- `POST /api/v1/agent/escalations/{thread_id}/reply`
- `POST /api/v1/agent/escalations/{thread_id}/resolve`
- `GET /api/v1/agent/drafts`
- `PATCH /api/v1/agent/drafts/{draft_id}`
- `POST /api/v1/agent/drafts/{draft_id}/send`
- `POST /api/v1/agent/drafts/{draft_id}/reject`
- `POST /api/v1/agent/drafts/{draft_id}/snooze`
- `GET /api/v1/agent/offers`
- `POST /api/v1/agent/offers`
- `POST /api/v1/agent/offers/{offer_id}/confirm`
- `POST /api/v1/agent/offers/{offer_id}/discard`
- `POST /api/v1/agent/offers/{offer_id}/transition`
- `GET /api/v1/agent/viewings`
- `POST /api/v1/agent/leads/{conversation_id}/viewings/propose`
- `POST /api/v1/agent/viewings/{viewing_id}/confirm`
- `POST /api/v1/agent/viewings/{viewing_id}/notification-drafts`
- `POST /api/v1/agent/viewings/{viewing_id}/complete`
- `POST /api/v1/leads/ingest/email`

Expected files if missing:

- `scripts/verify_internal_pilot_api.py`
- `codex-pilot/evidence/api-smoke.json`

### Agent E - Frontend And Browser Rehearsal

Scope:

- Start local frontend safely if available.
- Open `/agent` and pilot-critical child routes.
- Verify visible states, navigation, links, empty/error states, and workflows.

Routes to cover:

- `/agent`
- `/agent/escalations?thread=<thread_id>`
- `/agent/conversations/<conversation_id>`
- `/agent/buyers`
- `/agent/buyers/<profile_id>`
- `/agent/drafts`
- `/agent/viewings`
- `/agent/viewings/<viewing_id>`
- `/agent/calendar`
- listing creation/knowledge route if pilot includes listing setup UI

Expected files if missing:

- `frontend/scripts/verify-internal-pilot-surface.mjs`
- `codex-pilot/evidence/frontend-screenshots/`
- `codex-pilot/evidence/frontend-surface.json`

### Agent F - Report Writer

Scope:

- Aggregate all evidence.
- Produce final internal pilot report.
- Convert blockers into suggested small PRs/tickets.

Expected final artifact:

- `codex-pilot/reports/dalya-internal-pilot-report-YYYY-MM-DD.md`

## Seed Dataset

All records must include clear pilot markers:

- `metadata_json.pilot = "codex-pilot"`
- names include `Internal Pilot` where appropriate
- fake phone numbers use a reserved/test pattern
- fake emails use `example.com`

### Brokerage

Name: Mahoroba Realty  
Slug: `mahoroba-realty-internal-pilot`  
Brokerage AI number: fake UAE/sandbox number  
Agents AI number: fake UAE/sandbox number  
Settings:

- `legacy_telegram_alerts = false`
- Twilio/simulated transport only
- owner surfaces optional
- pilot metadata enabled

### Agents

1. Eric Zhu
   - Role: brokerage admin and primary agent unless Eric chooses otherwise
   - Email: `eric+dalya-pilot@example.com`
   - Phone: fake/test UAE number
   - Specialty: main pilot operator

2. Sara Khan
   - Role: senior agent
   - Email: `sara+dalya-pilot@example.com`
   - Specialty: Dubai Hills / ready villas

3. Omar Haddad
   - Role: off-plan specialist
   - Email: `omar+dalya-pilot@example.com`
   - Specialty: Emaar / waterfront projects

4. Lina Petrova
   - Role: viewing coordinator
   - Email: `lina+dalya-pilot@example.com`
   - Specialty: tenant coordination and viewing logistics

### Listings

#### Listing 1 - Dubai Hills Ready Villa

Purpose:

- Golden-path ready-property listing.
- Tests high-intent family buyer, viewing logistics, tenant/vacant access, offer handling.

Suggested fields:

- Title: `Internal Pilot - Dubai Hills 4BR Ready Villa`
- Community: Dubai Hills Estate
- Type: ready villa/townhouse
- Bedrooms: 4
- Asking price: AED 6,800,000
- Negotiation threshold: AED 6,500,000
- Assigned agent: Eric Zhu
- Seller notes: serious seller, prefers clean cash/pre-approved buyer, needs 24h access notice
- Occupancy: tenant occupied or access controlled
- Viewing logistics: key location, tenant notice, available windows, parking/access notes
- Buyer-safe facts: title deed exists if approved for seed, service charge estimate if supported, basic layout notes
- Agent-only notes: seller flexibility and private negotiation context
- Media: placeholder render/image URLs or local test assets

#### Listing 2 - Dubai Hills Ready Incomplete Facts

Purpose:

- Tests missing knowledge, safe failure, escalation, agent-confirmation language.

Suggested fields:

- Title: `Internal Pilot - Dubai Hills Incomplete Townhouse`
- Community: Dubai Hills Estate
- Type: ready townhouse
- Bedrooms: 3
- Asking price: AED 4,900,000
- Negotiation threshold: AED 4,650,000
- Assigned agent: Sara Khan
- Missing/uncertain: service charges, title deed/NOC details, viewing access, seller motivation
- Expected behavior: bot must not invent missing facts; should route to agent confirmation.

#### Listing 3 - Emaar Off-Plan Waterfront

Purpose:

- Tests payment schedule, SPA-like facts, remaining payment, handover, DLD/NOC/mortgage guardrails.

Suggested fields:

- Title: `Internal Pilot - Emaar Creek Harbour Off-Plan 2BR`
- Developer: Emaar
- Community: Dubai Creek Harbour or Rashid Yachts-style test community
- Type: off-plan apartment
- Bedrooms: 2
- Asking/resale price: AED 3,600,000
- Original price/internal paid-to-date if safe as internal data
- Payment schedule: realistic staged installments
- Amount paid / remaining amount
- Expected handover
- Assigned agent: Omar Haddad
- Media: brochure, floor plan, renders placeholders
- Expected behavior: no physical-viewing push; use brochure/floor plan/renders and verified facts.

#### Listing 4 - Investment Off-Plan

Purpose:

- Tests investor questions, projections, rental assumptions, ROI safety.

Suggested fields:

- Title: `Internal Pilot - Investment Off-Plan 1BR`
- Developer: test-safe developer
- Community: Dubai Creek Harbour / Oasis-style
- Asking price: AED 2,200,000
- Handover: future date
- Payment plan: staged
- Assigned agent: Omar Haddad
- Known safe facts only
- Agent-only notes may include investor context; buyer-facing copy must not promise ROI.

#### Listing 5 - Luxury High-Ticket Ready Listing

Purpose:

- Tests serious buyer qualification, negotiation threshold, handoff, premium buyer experience.

Suggested fields:

- Title: `Internal Pilot - Luxury Palm / Dubai Hills Mansion`
- Asking price: AED 18,000,000
- Threshold: AED 17,250,000
- Assigned agent: Eric or Sara
- Seller notes: strict qualification, proof of funds/preapproval required before viewing
- Viewing constraints: limited windows
- Media: high-quality placeholders

### Buyers

1. Adam Miller - hot ready buyer
   - Budget: AED 6.5M
   - Target: 4BR villa/townhouse in Dubai Hills
   - In Dubai: yes
   - Financing: cash or pre-approved mortgage
   - Timeline: this week
   - Decision-maker: available
   - Wants viewing
   - Expected: hot/viewing-ready

2. Priya Shah - off-plan analytical buyer
   - Budget: AED 3M-4M
   - Target: off-plan investment
   - Asks DLD, NOC, mortgage/LTV, payment schedule, service charges, handover risk
   - Expected: Verified Facts direct answers only where safe; otherwise agent confirmation/escalation.

3. Unknown low-context buyer
   - Messages: `price?`, `last price?`, `send pics`
   - Expected: low/partial readiness; one useful qualification question; no aggressive form behavior.

4. Hassan Ali - offer buyer
   - Ready listing buyer
   - Below-threshold firm offer, then upward revision
   - Expected: offer records, escalation, offer history, agent review.

5. Mei Chen - human takeover buyer
   - Mixed language/vague request
   - Asks for agent
   - Expected: escalation / takeover; AI pause/resume from conversation detail.

6. Voice/media buyer
   - Asks for media or sends simulated voice note
   - Expected: private media/safe media fallback; documented limitation if not runnable.

7. Opt-out buyer
   - Sends STOP
   - Expected: suppression, dashboard opt-out state, sends blocked.

8. Stale follow-up buyer
   - Older interested buyer with no recent reply
   - Expected: follow-up task/draft.

9. Financing buyer
   - Ready property buyer asking about mortgage/preapproval
   - Expected: readiness captures financing; unsafe policy claims deferred.

10. Tenant-access buyer
   - Ready property buyer requiring viewing coordination
   - Expected: tenant notice / viewing logistics path.

## Scenario Scripts

### Golden Path - 10 to 15 Minutes

Goal: show Dalya working well as Eric's daily command center.

1. Seed/reset pilot data.
2. Start backend/frontend in safe local/test mode.
3. Open `/agent` as Eric.
4. Confirm Today Queue shows:
   - Adam Miller viewing-ready item
   - critical escalation or needs-reply
   - a draft ready for approval
   - a viewing task
5. Open Adam Miller conversation.
6. Show listing snapshot, timeline, brief, readiness, and next action.
7. Propose or inspect viewing slots for Dubai Hills ready listing.
8. Open `/agent/viewings/<id>` and confirm status/logistics.
9. Open Adam's buyer card.
10. Confirm qualification fields and DealReadiness.
11. Edit/confirm one field.
12. Return to `/agent`; Today Queue reflects the action.
13. Open draft queue, edit and send/simulate-send a follow-up draft.
14. Show compliance/action/message record if available.

Expected demo message sequence:

- Adam: `Hi, I am looking for a 4 bedroom villa in Dubai Hills around 6.5M. I am in Dubai this week and can view tomorrow evening.`
- Adam: `Cash buyer. My wife will join the viewing. Can we see it after 6?`
- Eric action: inspect Today Queue, open conversation, propose viewing, send/approve follow-up.

### Stress Path - 20 to 30 Minutes

Goal: prove unsafe/edge cases do not break trust.

1. Priya asks off-plan facts:
   - `What are the DLD fees and NOC cost?`
   - `Can I get a mortgage at 50 percent LTV?`
   - `How much is left to pay and can I pay the developer directly?`
   - `What legal risk is there if handover is delayed?`
2. Verify Verified Facts:
   - safe direct facts are cited/grounded where supported
   - unsupported facts are rewritten to agent-confirmation language
   - legal-sensitive parts escalate
3. Low-context buyer sends:
   - `price?`
   - `last price?`
   - `send pics`
   - Verify one question at a time and no overqualification.
4. Hassan makes offer:
   - `I offer 6.1m cash`
   - `Ok I can revise to 6.55m, valid today`
   - Verify offer records, escalation, and offer history.
5. Mei asks:
   - `Can I speak to someone? English/中文 ok?`
   - Verify agent handoff and AI pause/resume.
6. Opt-out buyer sends:
   - `STOP`
   - Verify suppression and blocked sends.
7. Incomplete listing buyer asks missing service charge/NOC/title details.
   - Verify agent confirmation path, not invented answer.

## Test Matrix Template

The final report must include this table populated with actual results.

| Surface | Scenario | Expected result | Actual result | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `/agent` dashboard | Seeded Eric workspace loads | Live workspace, no fake sample fallback rows | TBD | TBD | TBD |
| Today Queue | Escalation href | `/agent/escalations?thread=<id>` focuses row | TBD | TBD | TBD |
| Chatbot | Adam ready buyer | One useful qualification question, viewing-ready readiness | TBD | TBD | TBD |
| Chatbot | Priya off-plan verified facts | Direct only for verified facts; unsupported claims defer/escalate | TBD | TBD | TBD |
| Chatbot | Low-context buyer | Does not overqualify; asks one useful question | TBD | TBD | TBD |
| DealReadiness | Adam | hot/viewing-ready with expected missing fields | TBD | TBD | TBD |
| Escalations | Offer/legal/human request | Thread created/bundled, visible in inbox | TBD | TBD | TBD |
| Agent relay | Dashboard reply | Simulated send, thread resolved/updated | TBD | TBD | TBD |
| Drafts | Edit/send/reject/snooze | State changes, DB/action/compliance records | TBD | TBD | TBD |
| Conversation detail | Each buyer | Timeline, listing, AI mode, brief, offers, assets visible | TBD | TBD | TBD |
| Buyer list/card | Filters/sort/edit fields | Works and preserves confirmed-over-inferred precedence | TBD | TBD | TBD |
| Offers | Below then revised offer | Records/transition/history correct | TBD | TBD | TBD |
| Viewings | Ready listing | slots, confirm, notice/drafts, feedback flow | TBD | TBD | TBD |
| Viewings | Off-plan listing | no physical-viewing push; media/agent follow-up | TBD | TBD | TBD |
| Lead ingest | PF/Bayut examples | Mahoroba resolution, dedupe, first-touch template | TBD | TBD | TBD |
| Security | wrong/unauth access | denied where testable | TBD | TBD | TBD |
| Media | signed/private asset | private/signed or blocked with reason | TBD | TBD | TBD |

## Commands To Prefer

Agents should inspect actual repo conventions first. Likely safe command families:

```bash
git status --short --branch
rg -n "seed|pilot|demo|fixture|MESSAGING_TRANSPORT|send-test|agent/dashboard|lead_ingest" scripts tests app frontend
PYTHONPATH=. python3 -m py_compile <changed-python-files>
PYTHONPATH=. python3 scripts/seed_internal_pilot.py --dry-run
PYTHONPATH=. MESSAGING_TRANSPORT=simulated python3 scripts/seed_internal_pilot.py --apply
PYTHONPATH=. MESSAGING_TRANSPORT=simulated python3 scripts/run_internal_pilot_messages.py --scenario all --output codex-pilot/evidence/messages.json
PYTHONPATH=. python3 scripts/verify_internal_pilot_api.py --output codex-pilot/evidence/api-smoke.json
cd frontend && npx --no-install tsc --noEmit
cd frontend && node scripts/verify-internal-pilot-surface.mjs --output-dir ../codex-pilot/evidence/frontend-screenshots
```

Blocked commands must be recorded with:

- command
- exact failure
- whether failure is environment, dependency, auth, DB, or product behavior
- closest fallback run

## Deliverables

### 1. Pilot Execution Report

Path:

`codex-pilot/reports/dalya-internal-pilot-report-YYYY-MM-DD.md`

Required sections:

1. Executive verdict
2. Demo script
3. Test matrix
4. Top product findings
5. Recommended pilot seed dataset actually used
6. Golden path demo
7. Stress path demo
8. Blockers before real customer pilot
9. Commands run
10. Suggested next PRs/tickets

### 2. Evidence Directory

Path:

`codex-pilot/evidence/`

Expected artifacts:

- discovery notes
- seed output
- reset output
- API smoke output
- chatbot transcripts
- frontend screenshots
- blocked command notes
- final status JSON if scripts support it

### 3. Optional Seed Fixture

Path:

`codex-pilot/seed-data/`

Expected:

- JSON fixture describing brokerage, agents, listings, buyers, conversations, offers, drafts, viewings, escalations

## Manual Inputs Needed From Eric

These should be provided or explicitly approved before agents write seed/demo code.

### Required Approval Inputs

1. **Messaging mode**
   - Confirm `simulated` transport only, or specify a safe sandbox/Twilio test path.
   - Confirm no real WhatsApp sends.

2. **Database target**
   - Which DB should receive pilot seed data?
   - Options: local dev DB, dedicated Neon branch, existing test DB, or no DB-backed run.
   - Confirm seed/reset permission for pilot-labeled records only.

3. **Auth/dev access**
   - How should agents log into `/agent` as Eric?
   - Provide test credentials or approve seed script creating/mapping auth/user/membership records.

4. **Pilot phone policy**
   - Approve generated fake UAE numbers, or provide desired fake/sandbox numbers for:
     - Eric
     - Brokerage AI
     - Agents AI
     - supporting agents
     - buyers

5. **Pilot email policy**
   - Approve `example.com` emails, or provide a preferred test domain.

6. **Listing seed approval**
   - Approve generated test-safe listing details, or provide listing details for the five recommended listings.

7. **Media asset policy**
   - Approve placeholder media URLs/local assets, or provide safe demo images/floor plans/brochures.

8. **Demo length**
   - Confirm target: 10-15 minute golden path, 20-30 minute stress path, or both.

### Optional Detail Inputs

1. Preferred brokerage display name if not exactly `Mahoroba Realty`.
2. Eric's preferred demo display name, title, phone, and role.
3. Whether Eric should be both `brokerage_admin` and assigned agent.
4. Whether Sara/Omar/Lina should appear in UI, or remain backend-only.
5. Exact listing prices/thresholds if the suggested values are not acceptable.
6. Exact seller notes and agent-only notes.
7. Whether off-plan examples should use Creek Harbour, Rashid Yachts, Oasis, or another test-safe project.
8. Whether the final report should be committed, local-only, or exported elsewhere.

## Default Safe Values If Eric Does Not Provide Inputs

If Eric does not provide details, agents may use:

- Emails: `eric+dalya-pilot@example.com`, `sara+dalya-pilot@example.com`, `omar+dalya-pilot@example.com`, `lina+dalya-pilot@example.com`
- Phones:
  - Eric: `+971500001001`
  - Brokerage AI: `+971500001010`
  - Agents AI: `+971500001011`
  - Sara: `+971500001002`
  - Omar: `+971500001003`
  - Lina: `+971500001004`
  - Buyers: `+971500002001` through `+971500002020`
- Brokerage slug: `mahoroba-realty-internal-pilot`
- Metadata marker: `codex-pilot`
- Transport: `simulated`

## Stop Conditions

Stop and report before continuing if:

- A command would write to production/staging.
- A command would enable RLS/app-role production rollout.
- A reset script cannot prove it only deletes pilot-labeled records.
- Messaging transport is not simulated/sandboxed.
- Auth requires real user credentials not explicitly provided.
- The seed path risks touching non-pilot data.
- The environment points to an unverified external DB.

## Suggested Follow-Up PR/Ticket Format

Each issue discovered should be converted into one small task:

```markdown
Title:
Scope:
Why now:
Files likely touched:
Acceptance criteria:
Tests:
Out of scope:
Risk:
```

Examples likely to emerge:

- Fix pilot seed auth/membership creation.
- Add safe internal pilot seed/reset scripts.
- Add internal pilot message simulation harness.
- Add seller-summary PII sanitizer if seller surfaces are included.
- Add conversation-level viewing proposal CTA if missing from UX.
- Add final surface QA script that can run with sanitized env.
- Expand Verified Facts seed for any blocked high-frequency pilot question.

