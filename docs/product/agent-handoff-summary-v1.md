# Agent Handoff Summary v1

**Status:** Spec. No runtime code changed. Does not touch DAL-172 files, auth, tenant context, or API client behavior.

## Purpose

Define exactly what an agent sees when Dalya hands a buyer over — built so the agent can decide *who to call and what to say* in **under 15 seconds**. This consumes the [DealReadinessProfile](./deal-readiness-v1.md) and the conversation summary; it is what the agent reads before a call or before approving a draft.

## Design rule: scannable first, detail on demand

The handoff is a **glanceable card**, not a transcript. Top of the card answers three questions instantly: *who, why now, what do I do.* Everything else is below the fold.

---

## Sections (in display order)

1. **Buyer identity** — name (or "Unknown"), masked phone (last 4), preferred language, contact preference.
2. **Property / listing context** — the listing the conversation is about (project, unit, price), off-plan vs ready.
3. **Why now** — one sentence: the trigger that caused the handoff (offer, viewing request, hot signal, stuck). *This is the most important line.*
4. **Recommended next action** — one `NextBestAction` (e.g. "Approve viewing reply or call now").
5. **Confirmed buyer facts** — only `agent_confirmed` or high-confidence inferred fields, as short chips.
6. **Inferred buyer facts** — lower-confidence inferences, visually distinct (so the agent knows these are guesses).
7. **Missing important fields** — the 1–3 fields whose absence is blocking the next stage.
8. **Suggested draft reply** — the held draft (if any), editable.
9. **Risk flags** — privacy/compliance/financing-unverified/second-decision-maker/abuse flags.
10. **Questions agent should ask** — the 1–3 things only a human can resolve (proof of funds, decision-maker, real timeline).
11. **Last buyer message** — verbatim, with timestamp.
12. **Conversation summary in 3 bullets** — from `ai_summary` (topics / key question / next step).

### Provenance must be visible
Confirmed vs inferred must be **visually obvious** (matches the `effective_fields()` model). An agent should never mistake an AI guess for a verified fact — especially budget and financing.

### PDPL / privacy
The card shows only what's needed to act. Phone is masked except last 4. Seller PII never appears. Buyer personal data is brokerage-scoped (isolation owned by DAL-170/DAL-172, not this doc).

---

## Concise format (the 15-second card)

```
Buyer:
Sara M. · WhatsApp …1234 · prefers EN · WhatsApp only

Looking for:
3BR Dubai Marina · AED 4.5M max · cash · end-use

Why now:
Asked for a viewing and has confirmed budget + financing.

Next action:
Approve viewing reply  ·  or call now

Confirmed:
• Budget AED 4.5M   • Financing: cash   • Timeline: this month   • Purpose: end-use

Inferred (unverified):
• Bedrooms: 3 (from chat)

Missing:
• Decision-maker status   • Viewing availability

Risk flags:
— none —

Ask on the call:
• Are you the sole decision-maker?   • When can you view this week?

Last message (2h ago):
"Can I see the 3-bed this week?"

Summary:
• High interest, focused on Marina 3-beds within 4.5M
• Confirmed cash buyer, wants to move this month
• Next step: book a viewing
```

### Example — a NOT-hot handoff (so the agent doesn't over-invest)
```
Buyer:
Unknown · WhatsApp …8890 · lang: RU

Why now:
Asked one price question, no budget or intent yet.

Next action:
Send options  ·  bot will keep qualifying

Confirmed:
• (none)

Inferred (unverified):
• Interest area: Downtown (from chat)

Missing:
• Budget   • Purpose   • Financing   • Timeline

Risk flags:
— none —

Last message (10m ago):
"how much is the 1 bed"

Summary:
• Early enquiry, single price question
• No qualification yet
• Bot continuing to qualify; no agent action needed now
```

---

## Current repo alignment

- **Likely current matching concepts:**
  - `app/core/summary_worker.py` — `ai_summary` (`topics`, `interest_level`, `sentiment`, `key_question`, `next_step_hint`) ≈ sections 3 & 12.
  - `app/core/buyer_profiles.py` `effective_fields()` — confirmed/inferred/suggestion ≈ sections 5/6.
  - `app/core/hot_list.py` — `next_action` + `next_action_reason` ≈ sections 3/4.
  - `DBLeadAssignment`, `DBDraftReply` — where next-action and draft (section 8) live.
  - `app/core/post_viewing_capture.py` / `post_viewing_followup.py` — post-viewing next-action computation.
  - `app/core/agent_notifications.py` — morning digest already assembles a per-agent rollup; the handoff card is the per-buyer equivalent.
- **Likely gaps vs this spec:**
  - No single assembled "handoff card" object; pieces are spread across summary, profile, assignment, draft.
  - "Risk flags" and "questions agent should ask" are not computed/surfaced as first-class fields.
  - Provenance is modeled in data but the 15-second card layout is not specified for the dashboard.
- **Files likely affected later (do NOT change now):** a new `handoff_summary.py` assembler reading existing models; `app/schemas/conversation.py` for the card schema; dashboard rendering (defer to UX phase, overlaps DAL-172). No isolation/auth changes.
- **Implementation ticket suggestion:** "Assemble agent handoff/buyer card from DealReadinessProfile" (see final output).
