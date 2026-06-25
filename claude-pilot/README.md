# Dalya Internal Pilot — `claude-pilot/`

This folder is the **execution plan** for a full end-to-end internal pilot rehearsal of Dalya's
MVP, run by **multiple coding agents** in parallel. It is a plan, not a report — nothing here has
been executed yet. The agents produce the report (`reports/claude-pilot-<date>/`) when they run.

**Goal:** Stand up a realistic, controlled **Mahoroba Realty** workspace where Eric can act like a
real agent for one working day at `/agent` — review Today Queue, answer escalations, approve/edit
drafts, inspect buyer cards, manage offers, coordinate viewings, pause/resume AI — and decide
whether Dalya is demo-ready as an agent command center, plus what must be fixed before any external
pilot.

**Hard constraints (non-negotiable):** simulated messaging only · no real customer data · no live
WhatsApp sends · test/staging DB only · do not modify unrelated code · production RLS/app-role
rollout stays a separate approval gate. See `08-SAFETY-GUARDRAILS.md`.

## Read in this order

| File | Purpose |
|------|---------|
| `00-EXECUTION-PLAN.md` | Master plan: phases, sequencing, agent roster, how the pieces run |
| `01-REPO-FINDINGS.md` | What already exists in the repo (so agents reuse, not rebuild) |
| `02-SEED-DATASET.md` | Exact pilot seed spec: brokerage, agents, listings, buyers, convos, offers, viewings, escalations, drafts |
| `03-AGENT-WORKSTREAMS.md` | Per-agent task packets — the multi-agent decomposition with dependencies |
| `04-TEST-MATRIX.md` | The surface × scenario test matrix the agents fill in |
| `05-DEMO-SCRIPTS.md` | Golden-path (10–15 min) and stress-path (20–30 min) demo scripts |
| `06-DELIVERABLES.md` | Exact structure of the final pilot report |
| `07-MANUAL-INPUTS.md` | **What Eric must provide/approve before agents start** |
| `08-SAFETY-GUARDRAILS.md` | Env setup, the do-not list, simulated-only enforcement, scope guard |

## TL;DR for the human

1. Read `07-MANUAL-INPUTS.md` and answer/approve the inputs (most have safe defaults — you can
   approve in one pass).
2. Confirm a **test/staging database** is available (Neon test branch) — this is the one true
   blocker for a DB-backed run.
3. Hand `00-EXECUTION-PLAN.md` + `03-AGENT-WORKSTREAMS.md` to the coding agents.
4. Receive `reports/claude-pilot-<date>/PILOT-REPORT.md` with verdict, demo script, test matrix,
   findings, and the blocker list before external pilot.
