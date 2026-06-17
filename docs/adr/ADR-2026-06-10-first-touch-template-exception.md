# ADR — First-touch template auto-send as the bounded exception to draft-and-approve (DAL-163)

**Date:** 2026-06-10
**Status:** Accepted
**Linear:** DAL-163

## Context

Dalya's standing principle is draft-and-approve: no AI-generated content
reaches a buyer without an agent approving it. Portal leads break the
economics of that principle: 85–95% of buyer inquiries arrive as Property
Finder/Bayut emails, and speed-to-lead is the single strongest conversion
lever — a lead answered in minutes converts at a multiple of one answered in
hours. Waiting for an agent to approve a first message defeats the purpose of
ingesting the lead at all.

Separately, the buyer has not messaged our WhatsApp number, so the first
contact is **business-initiated** and requires an **approved template
message** regardless of BSP.

## Decision

First-touch is the **one** exception to draft-and-approve, and it is bounded
by construction:

- The content is **template-locked** with variable slots only
  (`lead_first_touch_utility:v1`):

  > Hi {{1}}, thanks for your enquiry about {{2}} on {{3}}. I'm the AI
  > assistant for {{4}} — happy to answer questions or arrange a viewing.
  > Reply STOP to opt out.

  Variables: 1 = buyer first name, 2 = listing/project, 3 = portal,
  4 = brokerage name. **No free-form AI content is ever auto-sent** — the
  template lock is what keeps this consistent with the human-in-the-loop
  principle.
- It is auto-sent on ingestion (speed-to-lead), with the agent notified
  simultaneously (DAL-162 catalog event #2 — the highest-urgency event in the
  system).
- A buyer reply opens the normal 24h session and the standard concierge flow
  (and its draft-and-approve rules) takes over.
- No reply in 48h → one **review-only** nudge draft enters the agent's normal
  draft queue. Never auto-sent.

### Consent basis (PDPL)

The buyer submitted their number on a portal lead form expecting contact —
the standard consent basis the industry operates on. It is made auditable:

- recorded on the compliance trail (`lead_first_touch_sent` event,
  `consent_basis: portal_lead_form_submission`), with the originating lead
  email retained as evidence (`lead_ingests.raw_payload`);
- paired with an opt-out instruction in the first message; STOP propagates
  through the existing cross-agent opt-out machinery, and suppressed buyers
  never receive a first-touch or a nudge.

### Template approvals (open question #2 — submit with the WABA application)

- **Utility-category submission (primary):** the template above — it is
  transactional, referencing the buyer's own enquiry.
- **Marketing-category fallback (submit in parallel):**

  > Hi {{1}}, you enquired about {{2}} on {{3}}. {{4}} can share details,
  > availability and viewing slots here on WhatsApp. Reply STOP to opt out.

  If Meta classifies the utility variant as marketing, the fallback ships
  with marketing-category pricing/limits and identical slot discipline.

## Consequences

- The whole ingestion path (parser → resolution → first-touch) is
  template-version-stamped; changing copy requires a new template version and
  a new BSP approval cycle — this is the longest external dependency in the
  gap-closure spec and is on the WABA critical path.
- Unparseable lead emails dead-letter with an AI-failure notification;
  unresolved listings never block ingestion (the lead routes to a human
  without a first-touch, because there is no listing context to speak to).
