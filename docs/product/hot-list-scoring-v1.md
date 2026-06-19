# Hot List Scoring v1

**Status:** Spec. No code written. Does not touch DAL-172 files, auth, tenant context, or API client behavior.

## Purpose

Define a v1 framework for ranking which buyers an agent should act on **now**. The hot list must reflect *deal readiness and intent*, not just how recently or how often a buyer messaged. A chatty tyre-kicker should not outrank a quiet cash buyer who just asked for a viewing.

This consumes the [DealReadinessProfile](./deal-readiness-v1.md). It refines — not replaces — the existing `score_conversation()` in `app/core/hot_list.py`.

## Principle: readiness × intent × urgency, minus blockers

A buyer is hot because they are **ready to transact, showing intent, and time-sensitive** — not because the thread is busy. Message volume and recency are *minor* inputs, not the spine.

> ⚠️ The component weights below are a v1 default for Eric's review. They are product tuning, not Dubai regulatory facts. Calibrate against Eric's real qualification bar (verified-facts §1).

---

## Score components

The total score is a sum of five positive components minus one penalty. (Illustrative ranges; tune later.)

### 1. Intent Score (0–40) — strongest signal
What the buyer is trying to do right now.
- Offer / offer intent: top of range.
- Viewing request: high.
- "Best price"/negotiation: medium-high.
- Asking specifics (service charge, availability, location) that imply real evaluation: medium.
- Generic browsing: low.

### 2. Readiness Score (0–25)
How transaction-ready they are (from confirmed fields).
- Budget confirmed: +.
- Financing confirmed (cash or pre-approved): + (cash/pre-approved > mortgage-unknown).
- Purpose + property/location fit confirmed: +.
- Decision-maker clarity: +.

### 3. Urgency Score (0–20)
Time pressure.
- Timeline within Eric's "urgent" window (verified-facts §1 `[Eric to fill]`): top.
- Near-term (this month): high.
- "Just browsing": ~0.

### 4. Fit Score (0–10)
How well the buyer matches the listing/available stock.
- Budget fits the area/property they want: +.
- Budget vs ask mismatch (needs coaching, not a fast close): lower.

### 5. Follow-Up Risk Score (0–15) — "decay/attention" component
Captures buyers about to slip, so high-value leads don't go cold silently.
- Stale but high-value (was hot, now quiet): + (this is a *reason to surface*, not to bury).
- Awaiting an agent action (draft pending approval, reply overdue): +.
- Fresh portal lead inside speed-to-lead window: + (matches the existing `new_portal_lead` urgency boost).

### Missing Info Penalty (−, capped)
Subtract when blockers prevent the next stage — but **never zero out a high-intent buyer**. A buyer who asked for a viewing but hasn't given budget is still hot; the missing budget is a *blocker to show*, not a reason to hide them.

**Final:** clamp to 0–100. Priority bands (reuse existing): `critical ≥ 90`, `high ≥ 70`, else `normal`.

---

## Every hot-list row must show

A score alone is useless to an agent. Each row shows:
- **Why hot** — one plain sentence (e.g. "Asked for viewing + budget confirmed + cash buyer").
- **Missing blocker** — the one thing in the way (e.g. "Decision-maker status").
- **Next action** — the `NextBestAction` (e.g. "Approve draft or call now").
- **Last buyer message timestamp** — recency at a glance.
- **Owner agent** — if assigned (else unassigned, claimable).

### Example row
```
Sara M. · 3BR Marina · AED 4.5M cash          [HIGH · 84]
Why hot:    Asked for a viewing + budget confirmed + cash buyer.
Missing:    Decision-maker status.
Next:       Approve viewing reply  ·  or call now.
Last msg:   2h ago        Owner: Alice
```

---

## What v1 deliberately avoids

- **Ranking by message count or recency alone** — these are capped minor inputs.
- **Hiding stale high-value buyers** — they surface under Follow-Up Risk with a "gone quiet" reason.
- **Zeroing a high-intent buyer for missing fields** — the missing field is shown as a blocker, not used to bury them.
- **Opaque scores** — every row explains itself.

---

## Current repo alignment

- **Likely current matching concepts:**
  - `app/core/hot_list.py` `score_conversation()` → `HotListScore` already has `signal`, `urgency_score` (0–100), `next_action`, `next_action_reason`, `status`, `stale`, and the `critical/high/normal` bands. **This is the v0 of this spec.**
  - Existing branch signals (`firm_offer +55`, `ready_to_view +42`, `needs_financing +32`, `budget_matched +28`) ≈ a blended Intent+Readiness already, plus recency/volume modifiers and a `+8` stale bump.
  - `app/core/lead_ingest.py` sets `new_portal_lead` with an urgency boost (speed-to-lead) ≈ Follow-Up Risk component.
  - `DBLeadAssignment` / `DBLeadTask` persist the score, next action, reason, due time, owner — the row already carries "why" + "next".
- **Likely gaps vs this spec:**
  - Scoring is **single-branch** (one signal wins) rather than a sum of components; a cash + viewing + urgent buyer isn't additively rewarded over a viewing-only buyer.
  - Recency/volume modifiers (`+12` last msg from buyer, `+3`/msg, age bumps) give message activity more weight than this spec wants.
  - No explicit Fit component (budget-vs-area), no Missing-Info penalty, no separation of Intent/Readiness/Urgency.
  - "Why hot" is a single templated `reason`; "missing blocker" isn't a distinct surfaced field.
  - Inputs lean on `detected_budget` / `ai_summary` keyword matching rather than the structured `DealReadinessProfile`.
- **Files likely affected later (do NOT change now):** `app/core/hot_list.py` (refactor `score_conversation` to component sum reading `DealReadinessProfile`; add `missing_blocker`), `DBLeadAssignment` (a `missing_blocker` field), dashboard rendering (defer to UX phase). No isolation/auth changes.
- **Implementation ticket suggestion:** "Make hot list deal-readiness driven (component scoring + missing-blocker)" (see final output).
