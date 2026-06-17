# Dalya MVP Roadmap — 2026-06-09

Source: `GOAL_SPEC_0609`.

This file is the current launch roadmap for the Dalya agent-platform MVP. It supersedes older notes that treated the MVP as four broad blocks only. The four blocks remain the product frame, but the execution order is now the ten production-readiness priorities below.

## Launch Definition

The MVP is complete when a real brokerage agent can:

1. Receive buyer inquiries through Brokerage AI WhatsApp.
2. Let Dalya answer routine listing questions.
3. Have serious or unanswerable questions escalated to Agents AI.
4. Reply either through Agents AI WhatsApp or the Dalya dashboard.
5. Review and approve AI follow-up drafts.
6. Start each morning with an automatically refreshed hot list.
7. Upload ready-property documents and have Dalya answer practical buyer questions from them.
8. Configure viewing logistics.
9. Propose and confirm viewings.
10. Notify tenant and receive confirm/reschedule response.
11. Create Google Calendar events.
12. Receive post-viewing buyer feedback.
13. Rate buyer seriousness after viewing.
14. See basic personal performance metrics.
15. Operate without relying on sample data.

## Explicit MVP Deferrals

These are deliberately outside the MVP unless required by a launch-critical flow above:

- Mandarin production support.
- Owner outreach engine, owner CSV upload, campaign builder, listing-acquisition automation, and AI property one-pager generation.
- AI buyer matching launch surface. Existing matching experiments remain non-launch scaffolding until buyer database depth supports the value.
- Brokerage owner dashboard, owner rollups, agent leaderboard, and owner login.
- Advanced Google Maps route optimization beyond basic travel-time support.

## Current Foundation Already Built

- Brokerage-scoped auth, memberships, listings, conversations, opt-outs, and prompt config.
- Buyer-facing WhatsApp webhook, debounce queue, intent classifier, response validator, offer logic, and multi-tenant prompt context.
- Agents AI escalation routing with `[Ref: TOKEN]` WhatsApp relay.
- Persistent escalation threads, ordered questions, update/debounce semantics, manual resolve, and route-backed `/agent/escalations`.
- Agent dashboard live conversation inbox, deterministic hot-list scoring, open tasks, follow-up draft rows, and sample-data fallback when no real rows exist.
- Viewing logistics foundation: listing logistics, building prefill, tenant PII redaction, tenant consent audit, availability blocks, calendar settings shell, slot proposals, viewing confirmation, notification drafts, and pre-viewing brief.
- Agent onboarding through DLD/RERA card lookup against registered brokerages.
- Agent inspection notes/unit profile, buyer preference profiles, and buyer-listing match scaffolding.

## Final MVP Completion Order

| Priority | Linear | Feature | Current status | Completion target |
|---|---|---|---|---|
| 1 | DAL-149 | Dashboard reply composer | Built and verified | Agents reply from `/agent/escalations` or `/agent/conversations/[id]`, buyer receives via Brokerage AI, timeline/compliance/thread resolution all persist, consumed token routes are blocked, `[Ref:]` relay remains valid |
| 2 | DAL-150 | Draft approval queue | Built and verified | `/agent/drafts` lets agents edit/send/reject/snooze AI follow-ups, open the underlying conversation, and send only after explicit approval |
| 3 | DAL-151 | Scheduled hot-list refresh | Built and verified | Daily scheduled refresh entry point creates assignments/tasks/drafts, stores run status in `hotlist_refresh_runs`, and manual refresh remains on `/agent` |
| 4 | DAL-152 | Ready property intelligence layer | Built and verified | Agents upload ready-property documents, extracted facts are reviewable/verifiable, buyer prompt uses buyer-safe facts, verified facts are preferred, and tenant private data is redacted |
| 5 | DAL-153 | Google Calendar integration | Built and verified | Agent connects Google Calendar via token-ref/OAuth helpers, slot engine avoids busy time, confirmed/rescheduled/cancelled viewings sync to calendar |
| 6 | DAL-154 | Tenant WhatsApp confirmation flow | Built and verified | Approved tenant notices send, confirm/reschedule/decline/free-text replies update viewing state and notify agent while preserving PII boundaries |
| 7 | DAL-155 | Viewing logistics completion | Built and verified | Proposed slot to confirmed/completed lifecycle works with buyer confirm, tenant confirm/reschedule, reminders, calendar event, and post-viewing trigger |
| 8 | DAL-156 | Post-viewing capture | Built and verified | Buyer and agent feedback prompts run after viewing, responses parse into structured feedback, hot-list/CRM state updates |
| 9 | DAL-157 | Agent performance dashboard | Built and verified | `/agent` shows real current-agent metrics for today/7d/30d without owner rollups |
| 10 | DAL-143 | WhatsApp/BSP production verification | Report complete; Twilio path verified, 360dialog BSP blocked | `reports/whatsapp_production_readiness_20260610.md` proves buyer, agent, dashboard reply, tenant flow, opt-out, duplicate protection; lists 360dialog implementation/WABA blockers |

## Priority Requirements

### 1. Dashboard Reply Composer

Linear: DAL-149

API:

- `POST /api/v1/agent/escalations/:id/reply`
- Payload: `{ "body": "string", "send_to_buyer": true }`

Acceptance criteria:

- Agent can reply from dashboard.
- Buyer receives message via Brokerage AI number.
- Timeline stores the reply as `agent_relay`.
- Compliance event is written.
- Escalation resolves.
- Existing `[Ref: TOKEN]` WhatsApp relay still works.

### 2. Draft Approval Queue

Linear: DAL-150

Page:

- `/agent/drafts`

Draft categories:

- Urgent
- Today
- Stale Buyer
- Viewing Follow-Up
- Offer Follow-Up
- Financing Follow-Up
- General Nurture

Acceptance criteria:

- Stale buyer follow-up drafts appear.
- Agent can edit, send, reject, and snooze.
- Sent drafts are stored in the conversation timeline.
- No draft sends automatically without approval.

### 3. Scheduled Morning Hot List Refresh

Linear: DAL-151

Job:

- `daily_hotlist_refresh`
- Default: every day at 8:00 AM brokerage timezone.

Acceptance criteria:

- Hot list refreshes without dashboard load.
- Duplicate tasks/drafts are not created.
- Agent sees fresh morning queue.
- `/agent` shows last refresh time, status, and manual refresh.

### 4. Ready Property Intelligence Layer

Linear: DAL-152

Documents:

- Title deed
- Oqood
- Ejari / tenancy contract
- Service charge statement
- NOC
- Valuation report
- Mortgage liability letter
- Floor plan
- Snagging report
- DEWA / utility info
- Building/community rules
- Agent inspection notes
- Seller disclosure notes

Core data model:

- `listing_documents`
- `listing_facts`
- `listing_knowledge_summaries`

Required fact groups:

- Ownership/title/transfer readiness.
- Tenancy/vacancy/vacant-on-transfer/notice status.
- Service charge amount/frequency/paid-until.
- Parking count and spaces.
- Mortgage/NOC status.
- Building age, floor, view, floor plan, size.
- Snagging, upgrades, AC/chiller, noise, view obstruction, access notes.
- Buyer-safe limitations.

Prompt rules:

- Prefer verified structured facts over raw document text.
- Prefer agent-authored unit profile over uncertain extraction.
- If unknown, say it is not confirmed and offer to check with the agent.
- Never expose tenant private information.
- Never expose seller purchase price or private motivation unless explicitly buyer-safe.
- Legal/financial transfer questions get general guidance plus agent confirmation.
- Low-confidence facts escalate to agent.

Frontend:

- Built `Ready Property Knowledge` tab at `/dashboard/listings/[id]/knowledge`.
- Sections: Uploaded Documents, Extracted Facts, Missing Information, Buyer-Safe Summary, Risk Flags, document processing form, and fact verification/buyer-safe/risk controls.

Verification:

- `tests/test_ready_property_knowledge.py`
- `npm run build` in `frontend/`
- `scripts/migrate_ready_property_knowledge.py` applied to the configured database

API:

- `POST /api/v1/listings/:id/documents`
- `GET /api/v1/listings/:id/documents`
- `POST /api/v1/listings/:id/documents/:document_id/reprocess`
- `GET /api/v1/listings/:id/knowledge`
- `PATCH /api/v1/listings/:id/facts/:fact_id`
- `POST /api/v1/listings/:id/knowledge/regenerate`

Acceptance criteria:

- Agent can upload ready-property documents.
- System extracts structured facts.
- Agent can review/verify facts.
- Buyer bot answers ready-property questions from the knowledge layer.
- Unknown or risky answers escalate.
- Tenant/seller private data is not exposed.
- Existing off-plan behavior is not broken.

### 5. Google Calendar Integration

Linear: DAL-153

Acceptance criteria:

- Agent can connect Google Calendar through `/agent/calendar`, token-ref settings, and OAuth URL/callback endpoints.
- Slot engine avoids busy calendar times using free/busy when a connected calendar is available.
- Confirmed viewing creates calendar event.
- Rescheduled viewing updates calendar.
- Cancelled viewing cancels/removes event.

Verification:

- `tests/test_viewing_logistics.py`
- `npm run build` in `frontend/`

### 6. Tenant WhatsApp Confirmation Flow

Linear: DAL-154

Acceptance criteria:

- Tenant notice can be generated and sent after approval.
- Tenant confirm/reschedule/decline/free-text response updates viewing state.
- Agent is notified of confirmation/reschedule/free-text tenant replies.
- Tenant PII is visible only to assigned agent/brokerage roles.
- Buyer is not exposed to tenant contact details.

Verification:

- `tests/test_viewing_logistics.py`
- `npm run build` in `frontend/`
- `scripts/migrate_tenant_viewing_confirmations.py` applied to the configured database

### 7. Viewing Logistics Completion

Linear: DAL-155

Lifecycle:

- `draft`
- `proposed`
- `buyer_confirmed`
- `tenant_pending`
- `tenant_confirmed`
- `confirmed`
- `reschedule_requested`
- `cancelled`
- `completed`
- `feedback_requested`
- `feedback_completed`

Acceptance criteria:

- Agent can propose slots.
- Buyer can confirm.
- Tenant can confirm/reschedule if tenanted.
- Calendar event is created.
- Buyer reminder is generated/sent.
- Viewing moves to completed after end time.
- Post-viewing capture starts.

Implemented:

- Approved notification draft sending now covers buyer confirmation, buyer reminder, running-late, and reschedule messages.
- Viewing detail lets agents send drafts and mark a viewing completed.
- `scripts/complete_due_viewings.py` completes confirmed viewings after the end buffer.
- Completion records lead action/compliance events and creates a post-viewing feedback task plus draft.

Verification:

- `tests/test_viewing_logistics.py`
- `npm run build` in `frontend/`

### 8. Post-Viewing Capture

Linear: DAL-156

Acceptance criteria:

- Buyer receives feedback request 4 hours after viewing.
- Buyer response is parsed and stored.
- Agent receives buyer-rating prompt.
- Agent response is parsed and stored.
- Hot-list score updates based on feedback.
- Dashboard viewing detail shows feedback.

Implemented:

- `viewing_feedback` persists buyer and agent post-viewing feedback with scores, sentiment, temperature, financing, next action, raw text, and structured metadata.
- `scripts/request_post_viewing_feedback.py` and `/agent/viewings/post-viewing/request-due` request feedback once viewing end + 4 hours has passed.
- Buyer WhatsApp replies are intercepted before normal chat processing and parsed into structured feedback.
- Agents receive an Agents AI prompt and can save structured feedback from `/agent/viewings/[id]`.
- Feedback updates viewing status, closes the post-viewing task when complete, creates a next-action task, and feeds hot-list assignment metadata.

Verification:

- `tests/test_viewing_logistics.py`
- `npm run build` in `frontend/`
- `scripts/migrate_viewing_feedback.py` applied to the configured database

### 9. Agent Performance Dashboard

Linear: DAL-157

Metrics for current agent only:

- New buyer conversations.
- Escalations handled.
- Average response time.
- Follow-ups sent.
- Viewings proposed.
- Viewings confirmed.
- Viewings completed.
- Offers detected.
- Hot leads active.
- Tasks overdue.

Time ranges:

- Today.
- 7 days.
- 30 days.

Acceptance criteria:

- Agent can see their own performance.
- No brokerage owner rollups.
- Metrics use real workspace data, not sample data.

Implemented:

- `/api/v1/agent/dashboard` returns a `performance` block scoped to `ctx.user_id`.
- `/agent` renders today, 7-day, and 30-day current-agent metrics.
- Metrics cover new buyer conversations, escalations handled, average response time, follow-ups sent, viewings proposed/confirmed/completed, offers detected, hot leads active, and overdue tasks.
- Regression coverage asserts other-agent activity is excluded.

Verification:

- `tests/test_morning_hot_list.py`
- `npm run build` in `frontend/`

### 10. WhatsApp/BSP Production Verification

Linear: DAL-143

Acceptance criteria:

- Create `reports/whatsapp_production_readiness_YYYYMMDD.md`.
- Include tested numbers, tested flows, screenshots/log references, failures, and blockers.
- Verify live buyer inbound/outbound, Agents AI escalation, `[Ref:]` relay, dashboard reply relay, tenant template send, tenant button reply, opt-out handling, and duplicate webhook protection.

Report:

- `reports/whatsapp_production_readiness_20260610.md`

Verification:

- `tests/test_multitenant.py::test_dialog360_transport_is_stub`
- `tests/test_smart_escalation_relay.py`
- `tests/test_escalation_inbox_api.py::test_agent_can_reply_to_escalation_from_dashboard_and_consume_route`
- `tests/test_foundation_hardening.py::test_opt_out_is_brokerage_scoped`
- `tests/test_foundation_hardening.py::test_suppressed_buyer_does_not_trigger_outbound_send`
- `tests/test_viewing_logistics.py::test_viewing_list_detail_notification_drafts_status_and_tenant_reply`

Result: 10 passed. Twilio path verified; 360dialog BSP remains blocked by the explicit stub until WABA approval and transport implementation.
