# Linear Plan — GOAL_SPEC_0609

Date: 2026-06-09

Source spec: [`GOAL_SPEC_0609`](../../GOAL_SPEC_0609)

Canonical roadmap: [`MVP_ROADMAP_0609.md`](../../MVP_ROADMAP_0609.md)

## Status Legend

- **Done:** already completed and verified in current repo/artifacts.
- **In Progress / Partial:** usable foundation exists, but acceptance criteria are not complete.
- **Todo:** not yet implemented.
- **Deferred:** explicitly outside MVP per `GOAL_SPEC_0609`.

## Issues To Create Or Update In Linear

### 1. Dashboard reply composer

Linear: DAL-149

Status: Done

Priority: Urgent

Labels: `mvp`, `agent-workspace`, `escalations`, `whatsapp`

Purpose:
Agents need to answer escalations directly from Dalya dashboard, not only by preserving a WhatsApp `[Ref: TOKEN]` envelope.

Implementation actions:

- Add `POST /api/v1/agent/escalations/{thread_id}/reply`.
- Validate brokerage membership and conversation visibility.
- Validate escalation is open.
- Validate buyer is not opted out.
- Send reply through Brokerage AI WhatsApp number.
- Store timeline message as `agent_relay`.
- Add `DBLeadAction` and `DBComplianceEvent`.
- Resolve escalation thread and unresolved questions.
- Consume or expire latest WhatsApp token route if applicable.
- Add composer UI to `/agent/escalations` and conversation detail.
- Preserve existing `[Ref: TOKEN]` relay behavior.

Confirmation criteria:

- Agent can send dashboard reply from `/agent/escalations` and `/agent/conversations/[id]`.
- Buyer receives the message through Brokerage AI.
- Timeline shows the agent reply as `agent_relay`.
- Escalation resolves and open questions are marked resolved.
- Compliance event and lead action are persisted.
- Consumed token routes are blocked from duplicate relay.
- Existing WhatsApp token relay tests still pass.

Verification:

- `venv/bin/python -m pytest tests/test_escalation_inbox_api.py tests/test_smart_escalation_relay.py`
- `npm run build` in `frontend/`

### 2. Draft approval queue

Linear: DAL-150

Status: Done

Priority: Urgent

Labels: `mvp`, `agent-workspace`, `drafts`, `follow-up`

Purpose:
Agents need a review-only queue for AI-suggested follow-ups that can be approved, edited, rejected, or snoozed.

Implementation actions:

- Add `/agent/drafts`.
- Normalize draft categories: urgent, today, stale buyer, viewing follow-up, offer follow-up, financing follow-up, general nurture.
- Reconcile existing `DBDraftReply` with required fields or add migration for missing fields.
- Add send/edit-send/reject/snooze endpoints.
- Sending uses Brokerage AI WhatsApp and never auto-sends.
- Store outbound message in conversation timeline.
- Mark draft status and create lead action.
- Update hot-list state after send/reject/snooze.

Confirmation criteria:

- Stale buyer follow-up drafts appear.
- Agent can edit and send.
- Agent can reject.
- Agent can snooze.
- Sent drafts are stored in timeline.
- No draft sends without explicit approval.

Verification:

- `venv/bin/python -m pytest tests/test_draft_queue_api.py`
- `npm run build` in `frontend/`

### 3. Scheduled morning hot-list refresh

Linear: DAL-151

Status: Done

Priority: Urgent

Labels: `mvp`, `hot-list`, `scheduler`, `agent-workspace`

Purpose:
Hot lists should refresh automatically every morning per brokerage/agent, not only when dashboard loads.

Implementation actions:

- Add `hotlist_refresh_runs` persistence.
- Add `daily_hotlist_refresh` job.
- Default schedule: 8:00 AM brokerage timezone.
- Iterate active brokerages and active agents.
- Score visible conversations.
- Generate assignments, tasks, and follow-up drafts.
- Deduplicate existing open tasks/drafts.
- Store run metrics and errors.
- Add `/agent` last-refreshed status and manual refresh button.

Confirmation criteria:

- Refresh runs without dashboard load.
- Duplicate tasks are not created.
- Duplicate drafts are not created.
- Agent sees fresh morning queue.
- Manual refresh still works.
- Run status is visible.

Verification:

- `venv/bin/python -m pytest tests/test_morning_hot_list.py`
- `npm run build` in `frontend/`

### 4. Ready property intelligence layer

Linear: DAL-152

Status: Done

Priority: High

Labels: `mvp`, `ready-property`, `documents`, `advisor`

Purpose:
Dalya must answer practical ready-property buyer questions using structured knowledge from uploaded documents and agent/unit notes.

Implementation actions:

- Added `listing_documents`.
- Added `listing_facts`.
- Added `listing_knowledge_summaries`.
- Added document upload/list/reprocess APIs.
- Added knowledge GET/regenerate APIs.
- Added fact verification PATCH API.
- Added MVP deterministic extraction for title deed, Oqood, Ejari, tenancy contract, service charge statement, NOC, valuation report, mortgage liability letter, floor plan, snagging report, DEWA/utility info, building/community rules, agent inspection notes, and seller disclosure notes.
- Extracts minimum required facts from `GOAL_SPEC_0609`.
- Added Ready Property Knowledge tab on listing detail.
- Updated ready-property prompt branch to prefer verified facts and unit profile.
- Feeds available buyer-safe ready-property facts into info-gap detection.
- Prevents tenant/seller private data exposure through pre-extraction redaction and buyer-safe summary generation.
- Preserved existing off-plan behavior.

Confirmation criteria:

- Agent can upload ready-property documents. Confirmed by `tests/test_ready_property_knowledge.py`.
- System extracts structured facts. Confirmed by `tests/test_ready_property_knowledge.py`.
- Agent can review and verify facts. Confirmed by `tests/test_ready_property_knowledge.py`.
- Buyer advisor answers ready-property questions from knowledge layer. Confirmed by prompt payload and info-gap coverage tests.
- Unknown/risky answers remain visible through missing-information and risk-flag summary fields.
- Tenant/seller private data is not exposed. Confirmed by redaction assertions.
- Frontend route builds successfully. Confirmed by `npm run build` in `frontend/`.

### 5. Google Calendar integration

Linear: DAL-153

Status: Done

Priority: High

Labels: `mvp`, `viewings`, `calendar`, `integrations`

Purpose:
Agents should connect Google Calendar so Dalya can check availability and create/update viewing events.

Implementation actions:

- Added Google Calendar OAuth URL/callback flow for agents.
- Store external token references (`token_ref`) rather than raw OAuth tokens in Dalya.
- Read free/busy through the Google Calendar provider.
- Use free/busy in slot proposal engine.
- Create calendar event after viewing confirmation.
- Update event when viewing is rescheduled.
- Cancel/remove event when viewing is cancelled.
- Added `/agent/calendar` for connect/status/disconnect/default calendar token-ref settings.

Confirmation criteria:

- Agent can connect Google Calendar via token-ref settings and OAuth URL/callback endpoints.
- Slot engine avoids busy calendar times. Confirmed by `tests/test_viewing_logistics.py`.
- Confirmed viewing creates event. Confirmed by `tests/test_viewing_logistics.py`.
- Rescheduled viewing updates event. Confirmed by `tests/test_viewing_logistics.py`.
- Cancelled viewing cancels/removes event. Confirmed by `tests/test_viewing_logistics.py`.
- Frontend route builds successfully. Confirmed by `npm run build` in `frontend/`.

### 6. Tenant WhatsApp confirmation flow

Linear: DAL-154

Status: Done

Priority: High

Labels: `mvp`, `viewings`, `tenant`, `whatsapp`, `pdpl`

Purpose:
Tenants need to receive viewing notices and confirm or request reschedule, with the result visible to agents and tenant PII protected.

Implementation actions:

- Added `tenant_viewing_confirmations`.
- Send approved tenant WhatsApp notice after viewing scheduling.
- Support confirm replies.
- Support ask-to-reschedule/decline replies.
- Support free-text tenant replies.
- Summarize free-text replies and relay to agent through Agents AI.
- Update viewing state and confirmation status.
- Notify agent of confirmation/reschedule/free-text replies.
- Added viewing detail controls: send/resend notice, mark manually confirmed, request new time.
- Enforced tenant PII visibility rules through existing logistics redaction and tenant-specific webhook interception.

Confirmation criteria:

- Tenant notice can be generated and sent after approval. Confirmed by `tests/test_viewing_logistics.py`.
- Tenant confirm reply updates viewing state. Confirmed by `tests/test_viewing_logistics.py`.
- Tenant reschedule/decline reply classification is implemented in `app/core/tenant_viewings.py`.
- Free-text reply is summarized/relayed to agent. Confirmed by `tests/test_viewing_logistics.py`.
- Tenant PII remains scoped.
- Buyer never sees tenant contact details.
- Frontend route builds successfully. Confirmed by `npm run build` in `frontend/`.

### 7. Viewing logistics completion

Linear: DAL-155

Status: Done

Priority: High

Labels: `mvp`, `viewings`, `whatsapp`, `calendar`

Purpose:
Complete the viewing journey from proposed slot to confirmed calendar event, notifications, completion, and feedback trigger.

Implementation actions:

- Implemented viewing lifecycle coverage from proposal/confirmation through cancellation/completion, with post-viewing trigger handoff.
- Sent approved WhatsApp notifications for buyer confirmation, buyer reminder, tenant notice, running-late, and reschedule drafts.
- Preserved buyer/tenant confirmation state on viewing detail and webhook replies.
- Wrote Google Calendar invites on confirmation, updated them on reschedule, and removed them on cancellation.
- Added manual viewing completion and scheduled `scripts/complete_due_viewings.py` completion for due confirmed viewings.
- Triggered post-viewing capture by creating the post-viewing feedback task and buyer draft when a viewing completes.

Confirmation criteria:

- [x] Agent can propose slots.
- [x] Buyer can confirm.
- [x] Tenant can confirm/reschedule if tenanted.
- [x] Calendar event is created.
- [x] Buyer reminder is generated/sent.
- [x] Viewing moves to completed after end time.
- [x] Post-viewing capture starts.

Verification:

- `tests/test_viewing_logistics.py`
- `npm run build` in `frontend/`

### 8. Post-viewing capture

Linear: DAL-156

Status: Done

Priority: Medium

Labels: `mvp`, `viewings`, `feedback`, `hot-list`

Purpose:
Four hours after a confirmed viewing, Dalya should collect buyer feedback and agent buyer-rating feedback, then feed hot-list and CRM state.

Implementation actions:

- Added `viewing_feedback`.
- Added `scripts/request_post_viewing_feedback.py` plus `/agent/viewings/post-viewing/request-due`.
- Detects completed viewings where end time + 4 hours has passed and no request was sent.
- Sends buyer feedback prompt through Brokerage AI.
- Parses buyer score, likes, concerns, and offer/similar-options interest from WhatsApp replies.
- Sends managing-agent rating prompt through Agents AI.
- Parses agent score, temperature, financing, and next action from the viewing-detail feedback form.
- Added dashboard feedback form and summaries on viewing detail.
- Feeds hot-list assignment metadata, creates next-action tasks, and closes the post-viewing feedback task when both responses are captured.

Confirmation criteria:

- [x] Buyer receives feedback request 4 hours after viewing.
- [x] Buyer response is parsed and stored.
- [x] Agent receives buyer-rating prompt.
- [x] Agent response is parsed and stored.
- [x] Hot-list score updates based on feedback.
- [x] Viewing detail shows feedback.

Verification:

- `tests/test_viewing_logistics.py`
- `npm run build` in `frontend/`
- `scripts/migrate_viewing_feedback.py` applied to the configured database

### 9. Agent performance dashboard

Linear: DAL-157

Status: Done

Priority: Medium

Labels: `mvp`, `agent-workspace`, `metrics`

Purpose:
Agents need basic personal performance stats without building brokerage owner dashboards or leaderboards.

Implementation actions:

- Added performance section on `/agent`.
- Added current-agent metrics for today, 7 days, and 30 days.
- Metrics: new buyer conversations, escalations handled, average response time, follow-ups sent, viewings proposed, viewings confirmed, viewings completed, offers detected, hot leads active, tasks overdue.
- Uses real workspace rows only.
- Excludes other-agent and owner-rollup activity.

Confirmation criteria:

- [x] Agent sees own performance.
- [x] No brokerage owner rollups.
- [x] Metrics use real data, not sample data.

Verification:

- `tests/test_morning_hot_list.py`
- `npm run build` in `frontend/`

### 10. WhatsApp/BSP production verification

Linear: DAL-143

Status: Done

Priority: High

Labels: `mvp`, `whatsapp`, `production-readiness`, `360dialog`

Purpose:
Confirm production WhatsApp topology works before live shipment.

Implementation actions:

- Created `reports/whatsapp_production_readiness_20260610.md`.
- Verified Twilio transport path for Brokerage AI and Agents AI messaging through the transport abstraction.
- Verified incoming buyer webhook queueing and duplicate `MessageSid` protection.
- Verified outgoing buyer reply paths.
- Verified escalation to Agents AI and `[Ref: TOKEN]` relay.
- Verified dashboard reply relay.
- Verified tenant viewing notice/reply flow.
- Verified opt-out handling and suppressed outbound sends.
- Listed 360dialog BSP as blocked because `Dialog360Transport` is intentionally stubbed pending WABA approval/implementation.

Confirmation criteria:

- [x] Report includes tested flows, log/test references, failures, and blockers.
- [x] All required flows are either passing or explicitly listed as blockers.

Verification:

- `tests/test_multitenant.py::test_dialog360_transport_is_stub`
- `tests/test_smart_escalation_relay.py`
- `tests/test_escalation_inbox_api.py::test_agent_can_reply_to_escalation_from_dashboard_and_consume_route`
- `tests/test_foundation_hardening.py::test_opt_out_is_brokerage_scoped`
- `tests/test_foundation_hardening.py::test_suppressed_buyer_does_not_trigger_outbound_send`
- `tests/test_viewing_logistics.py::test_viewing_list_detail_notification_drafts_status_and_tenant_reply`

Result: 10 passed.

## Deferred Linear Items

These should not be pulled into the MVP unless they become necessary for the launch flows:

- Mandarin production support.
- Owner outreach engine.
- Owner CSV upload.
- Campaign builder.
- Listing acquisition automation.
- AI property one-pager generation.
- AI buyer matching launch surface.
- Brokerage owner dashboard.
- Owner rollups.
- Agent leaderboard.
- Advanced Google Maps route optimization beyond basic travel-time support.
