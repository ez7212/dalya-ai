# Dalya Friendly Pilot Readiness Runbook

Date: 2026-06-22
Updated: 2026-06-23
Scope: Next MVP readiness closeout Task 13.

This runbook defines the only allowed friendly-pilot posture after Tasks 3-9 and
10a. It is an operator checklist, not a launch claim.

## Readiness Decision

| Target | Status | Reason |
| --- | --- | --- |
| Internal demo | Green | P0 blockers from Tasks 3, 4, and 5 are closed; agent workspace Tasks 8 and 9 are merged. |
| Friendly pilot with synthetic/internal data | Yellow/allowed by operator | Allowed only inside the constraints below, with Twilio-only transport, explicit CORS origins, manual review, manual fallback, and RLS/app-role risk accepted for synthetic/internal data only. |
| External brokerage pilot with real customer data | Blocked | Requires separate approval for the data class, verified provider posture, and production RLS/app-role gate 10b. |
| Production/live data | Blocked | Requires Task 10b approval and evidence: target DB fingerprint, rollback artifact, maintenance window, app-role smoke tests, and post-change tenant isolation proof. |

## Who Can Use Dalya

Allowed during this pilot:

- Eric/operator-approved internal users.
- Approved design-partnership brokerage admins and pilot agents.
- Buyers who message only the approved pilot Brokerage AI WhatsApp number for
  synthetic/internal pilot flows.

Forbidden until a later approval:

- Public demo users.
- Non-pilot brokerages.
- Owner/campaign surfaces as launch surfaces.
- External brokerage pilot traffic with real customer data.
- Production/live customer data.

## Allowed Data

Allowed:

- Synthetic/internal records created for the pilot.
- Verified internal fixtures used to exercise agent workflows.
- Real empty-state agent workspaces. Authenticated product surfaces must keep
  `sample_data: false` unless a future explicit demo mode is approved.

Forbidden:

- Real buyer/seller/customer PII from an external brokerage.
- Live WhatsApp traffic outside the approved pilot number set.
- Seller purchase price, numeric seller equity, or exact unverified finance,
  process, timing, NOC, mortgage, LTV, or payment claims.
- Any data class that would require production/live-data readiness.

## Transport Mode

Pilot transport is Twilio-only.

- Use only `MESSAGING_TRANSPORT=twilio` for approved pilot WhatsApp traffic.
- Allowed numbers are only the operator-approved brokerage-level
  `brokerage_ai_number` and `agents_ai_number` pairs for the pilot brokerage.
- If exact numbers are not listed in the operator handoff, treat the number
  scope as empty until Eric/operator approves the pair.
- The simulated transport is local/test only.
- 360dialog/BSP is not an allowed pilot path. Do not set
  `MESSAGING_TRANSPORT=dialog360` for this pilot.
- Telegram is removed as an active runtime integration. Do not configure or
  expect Telegram webhooks, Telegram alert sends, or Telegram reply handling.
  Historical Telegram database artifacts may remain only for schema history.

## CORS Posture

- Live-class environments must use explicit HTTP/HTTPS origins through
  `DALYA_CORS_ORIGINS`.
- Wildcard origins are not allowed with credentialed browser requests.
- If the approved pilot dashboard origin is not listed in the operator handoff,
  treat browser access as not approved until Eric/operator supplies the exact
  origin.

## Manual Review Requirements

- Agent-facing communications remain review-only drafts unless an existing spec
  explicitly allows autonomous send.
- Buyer-facing finance, process, timing, mortgage/LTV, NOC, and payment-plan
  answers must use Verified Facts. Missing, draft-only, ambiguous, or
  listing-mismatched facts must fail closed to agent-confirmation language.
- Viewing logistics, escalation, and follow-up drafts must be checked by an
  approved agent/operator during the pilot.
- Any unexpected WhatsApp behavior, claim-safety issue, or tenant/data concern
  triggers the pause procedure below.
- Manual fallback is part of the allowed pilot posture: if Dalya is paused or a
  provider/API path is uncertain, agents handle the buyer directly in WhatsApp
  until restoration is explicitly approved.

## RLS And App-Role Caveat

Task 10a recorded the current RLS/app-role posture:

- No production/staging DDL was run.
- No RLS enablement or role/grant mutation was performed.
- No approved DAL-170E5 rehearsal DB fingerprint is recorded.
- The RLS/app-role gate is risk-accepted only for synthetic/internal pilot data.

Task 10b remains the gate for production/live data and external brokerage real
customer data. It requires separate explicit Eric approval with target DB
fingerprint, rollback artifact, and maintenance window.

## No-Deploy Pause And Rollback

Pause owner: Eric/operator.

Use this path when Dalya must stop receiving pilot WhatsApp traffic without a
code deploy:

1. Disable or remove the Twilio webhook URL for the approved pilot number(s), or
   revoke the Twilio credential used by the pilot transport.
2. Notify approved agents that Dalya is paused and they must use WhatsApp
   manually until restoration is approved.
3. Send a controlled inbound WhatsApp message to each paused pilot number.
4. Verify the inbound message no longer reaches Dalya.
5. Keep the dashboard and database records as audit context only; do not resume
   outbound sends until the operator confirms the issue and restoration path.
6. If an existing app maintenance flag exists in the deployment environment, it
   may be used as an additional belt-and-braces control. This runbook does not
   require or introduce a new maintenance flag.

Rollback for product readiness is a process rollback, not a database migration:

- Keep the merged code in place unless the incident is caused by a specific
  product regression.
- Pause transport first.
- Fall back to manual WhatsApp handling by agents.
- Reopen the relevant task evidence before resuming the pilot.

## Evidence Checklist

Before calling the synthetic/internal friendly pilot allowed, confirm:

- Task 1: Today Queue escalation links route to the live escalation inbox.
- Task 2: authenticated dashboard fetch failure shows error/retry, not sample
  operational rows.
- Task 3: Telegram runtime is removed; Twilio/Agents AI paths remain.
- Task 4: CORS uses explicit origins in live-class environments.
- Task 5: seller-visible lead payloads anonymize buyer identity.
- Task 6: buyer-facing off-plan finance/process claims are gated through
  Verified Facts or fail-closed agent-confirmation language.
- Task 7: confirmed closing-cost facts are seeded without promoting draft-only
  or listing-specific claims to direct buyer answers.
- Task 8: current chatbot regression evidence exists and expects no Telegram
  alert path.
- Task 9A/9B: DealReadiness was calibrated first and then added only as a
  bounded ranking input.
- Task 10: `needs_reply` priority distinguishes acknowledgements from concrete
  buyer questions.
- Task 11: queue/escalation handoff cards show exact next actions.
- Task 12: first-run/error states guide safe synthetic/internal activation and
  manual fallback without fake live rows.
- Task 13: final evidence pack and readiness verdict are published.
- Task 10b: not executed under this plan. It remains required before
  production/live data or external brokerage real-customer readiness.

## Operator Signoff

Eric/operator must confirm all of the following before running the pilot:

- The pilot users and WhatsApp numbers are explicitly approved.
- The data class is synthetic/internal only.
- Agents know manual review and manual WhatsApp fallback expectations.
- The exact dashboard origin is included in `DALYA_CORS_ORIGINS`.
- The pause owner can disable the Twilio webhook URL or revoke the provider
  credential.
- The final Task 13 evidence pack does not contain an open P0 blocker.
