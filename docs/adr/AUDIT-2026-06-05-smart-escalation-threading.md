# Audit: Current Smart Escalation Behavior Before/After Threading

Date: 2026-06-05

Scope: Q19-Q25 from the threading plan.

## Q19. Does current suppression depend on whether the agent replied?

Previously, no. Suppression looked at `conv.escalation_triggered`, `conv.escalation_reason`, and `last_escalated_at` within 24 hours. It did not inspect route consumption. The new code keeps that guard for non-threaded escalation types, but info-gap and unanswerable-question alerts now defer consolidation to `escalation_threads`: same-category questions append and different-category questions create separate open threads.

Relevant code:

- `ChatbotEngine._should_suppress_non_offer_escalation`
- `has_open_thread_for_alert`

## Q20. Does suppression count `consumed_at` routes as still open?

Previously, `consumed_at` was not checked by suppression. It also was not checked by `relay_agent_reply`, so a token could technically be reused until expiry. Threading now treats `agent_reply_relayed` as product resolution by setting `escalation_threads.state = resolved`; route `consumed_at` remains a transport/audit field.

## Q21. Does suppression check across all agents or assigned one?

Suppression is conversation-level, not agent-level. Thread matching is scoped by:

- `brokerage_id`
- `buyer_phone`
- `listing_id`
- `category`
- open state

The assigned agent is stored on the thread and route, but not part of the matching key. This means if the assigned agent changes mid-thread, the existing thread remains the work item until resolved/timed out. Reassignment behavior is deferred to the webapp inbox.

## Q22. What if assigned agent changes between two messages?

Current behavior: append to the existing open thread. The original `agent_user_id` and `agent_phone` remain on the thread and route. This avoids silently moving an already-sent WhatsApp token to a different agent. Future dashboard reassignment should explicitly close/reassign the thread with audit.

## Q23. Is `pending_forwarded_questions` replaceable?

Not fully removed yet. The old fields still exist on `conversations` and are still used in deterministic info-gap prompt paths to format the buyer-facing "I've asked the agent" response and avoid repeated identical prompts.

Current interaction after `DAL-141`:

- New threaded alerts return from `notify_managing_agent` during debounce, so the legacy Telegram alert path does not also send the same info-gap alert.
- Successful threaded initial/update sends move `pending_forwarded_questions` into `alerted_questions` and clear pending, matching the old post-send behavior.
- Successful Agents AI initial sends return before legacy Telegram fallback. If threaded delivery fails with `skipped`, legacy Telegram can still act as fallback where configured.

Threading is now the product-level escalation record; decommissioning `pending_forwarded_questions` / `alerted_questions` remains deferred until persona harness metrics prove no legacy response path depends on them.

## Q24. Actual subtype/type taxonomy found in code

Escalation types observed in `EscalationAlert` and `chatbot_engine.py`:

- `offer`
- `soft_offer`
- `viewing_request`
- `contact_sharing`
- `speak_to_human`
- `bypass_attempt`
- `regulatory_request`
- `seller_action`
- `general_lead_capture`
- `legitimate_conveyancing`
- `unanswerable_question`
- `info_gap`
- `materials_request`
- `viewing_schedule`
- `returning_buyer_followup`
- `brn_request`

Observed subtypes include:

- `listing_fact_gap`
- `physical_viewing`
- `off_plan_materials`
- `qualified_handoff`
- `new_listing_inquiry`
- `brn_request`
- `co_broker_compliance`
- `promise_kept`
- `matched_offer`
- `unverified_lawyer_mou`
- `materials_request`

## Q25. Existing data migration/backfill

The migration is additive and idempotent. It creates:

- `escalation_threads`
- `escalation_thread_questions`
- `agent_message_routes.thread_id`
- indexes for matching and route linkage
- partial unique index `uq_open_escalation_thread_scope`

Backfill status:

- No historical backfill is performed yet. Existing `agent_message_routes` remain valid and continue to relay replies without a `thread_id`.
- `relay_agent_reply` treats `thread_id = NULL` as a legacy route: it relays the reply, persists the timeline/action/compliance records, and simply skips thread-state resolution. This is covered by `test_legacy_null_thread_route_relay_still_succeeds`.
- This is acceptable for the current pre-production/test usage, but production rollout should add a backfill if there are active route rows that need to appear in the webapp escalation inbox.

## Test Coverage Added

- Same-category pre-alert debounce bundling.
- Update debounce and token reuse.
- Different-category thread split.
- Agent reply resolution.
- 24h timeout.
- Offer debounce bypass.
- BRN requests do not bypass debounce.
- Buyer opt-out closure.
- Multi-thread isolation on agent reply.
- 10-question update cap.
- Compliance events for create, append, update, resolve, timeout, and opt-out.
- Concurrent open-thread insert retry after `uq_open_escalation_thread_scope` conflicts.
- Legacy `thread_id = NULL` route relay compatibility.
- Legacy pending-question cleanup after threaded initial/update sends.

## Remaining Gaps

- Full persona CSV metrics are not implemented yet.
- Per-brokerage debounce configuration is deferred.
- Webapp inbox is not implemented in this slice.
