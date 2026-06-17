# ADR: Smart Escalation Threading

Date: 2026-06-05

Status: Accepted for MVP backend foundation

Linear: DAL-132, DAL-133, DAL-134, DAL-135, DAL-137, DAL-138, DAL-139, DAL-141

## Context

The first Agents AI relay implementation treated every escalation alert as a point-in-time WhatsApp message. That worked for a single unanswered buyer question, but follow-up buyer questions either created separate alerts or were suppressed by recent-escalation logic. Agents need one open work item per buyer/listing/category, with follow-up questions appended until the agent replies or the thread times out.

## Decisions Q1-Q18

Q1. Category taxonomy:

- `fees_and_charges`
- `payment_plan`
- `regulatory_documents`
- `tenancy_status`
- `physical_property`
- `building_amenities`
- `community_amenities`
- `financing`
- `market_analysis`
- `developer_handover`
- `offer`
- `viewing_logistics`
- `legal_general`
- `seller_action`
- `other`

Q2. Category resolution:

Static map in `app/core/escalation_threads.py`. This is deterministic, testable, and easier to review than an LLM classifier. A DB-managed map is deferred until category behavior stabilizes.

Current mapping:

- `offer` escalation type -> `offer`
- `viewing_schedule`, `viewing_request` -> `viewing_logistics`
- `regulatory_request`, `brn_request`, `legitimate_conveyancing` -> `regulatory_documents`
- `seller_action` -> `seller_action`
- legal/lawyer/conveyancing text -> `legal_general`
- service charge / maintenance charge / fee / commission / DLD / transfer -> `fees_and_charges`
- payment plan / instalment / post-handover / remaining balance -> `payment_plan`
- NOC / title deed / Ejari / SPA / SOA / Form A / Trakheesi / BRN / documents -> `regulatory_documents`
- rental yield / ROI / capital appreciation / comparables / recent transactions -> `market_analysis`
- tenant / lease / vacant / eviction / rent -> `tenancy_status`
- mortgage / finance / LTV / bank / loan -> `financing`
- handover / completion / snagging / defects liability -> `developer_handover`
- school / metro / community / retail / drive-time anchors -> `community_amenities`
- gym / pool / security / amenities / parking pass / concierge / lobby -> `building_amenities`
- parking / storage / view / layout / sqft / BUA / plot / bed / bath / AC / balcony / maid -> `physical_property`
- `materials_request` defaults to `regulatory_documents`
- `info_gap` and `unanswerable_question` use the current missing-fact topic first, then fall back to keyword matching across the full digest, then default to `physical_property`
- unmatched -> `other`

Q3. Open window:

An escalation stays open for 24 hours since `last_buyer_message_at`, unless resolved by agent reply or closed by opt-out.

Q4. Agent reply resolution:

The first successful agent relay resolves the whole thread for MVP. Multi-reply unresolved sub-question handling is deferred to the webapp inbox.

Q5. Initial debounce:

90 seconds. Stored on `escalation_threads.debounce_until`.

Q6. Initial debounce reset:

Same-category buyer follow-ups during `debouncing` extend `debounce_until` by 90 seconds, capped by `max_debounce_until`.

Q7. Update debounce:

30 seconds. Once an alerted thread receives follow-up questions, it moves to `updated` and the WhatsApp update is sent when due.

Q8. Cross-category during debounce:

Independent. Different category creates a separate thread.

Q9. Per-brokerage configurability:

Deferred. Constants are currently code-level defaults in `app/core/escalation_threads.py`; expose in brokerage runtime config after Luqman feedback.

Q10. Bypass categories:

Immediate send for `offer`, `legal_general`, `regulatory_request`, and `legitimate_conveyancing`. `brn_request` maps to `regulatory_documents` but does not bypass debounce; if BRN requests become frequent, the chatbot should answer them from configured brokerage data rather than pinging the managing agent immediately.

Q11. Offer threading:

Offers are standalone. `find_open_thread` never matches category `offer`, so every material offer can create a distinct thread.

Q12. Returning-buyer carve-out:

Not special-cased in threading. The existing returning-buyer escalation path remains immediate outside normal non-offer suppression.

Q13. Single reply resolves all:

Yes for MVP. The agent-facing update message shows the open questions; the agent is expected to answer all of them.

Q14. Compliance event for multi-question resolution:

Yes. `agent_reply_relayed` and `escalation_thread_resolved` include `question_count`.

Q15. Update message format:

```
[Update on Ref: TOKEN]

Buyer also asked:
"Question text"

Open questions on this escalation:
1. Original question (original, 12 min ago)
2. Follow-up question (added, 3 min ago)
```

The update message intentionally omits buyer phone/name and listing ID. It caps visible questions at 10 and adds `...and X more - see dashboard.`

Q16. State machine:

- `debouncing` -> same-category buyer message -> `debouncing`
- `debouncing` -> due processing -> `open`
- `debouncing` -> opt-out -> `opt_out_closed`
- `debouncing` -> 24h stale -> `timed_out`
- `open` -> same-category buyer message -> `updated`
- `open` -> agent reply -> `resolved`
- `open` -> opt-out -> `opt_out_closed`
- `open` -> 24h stale -> `timed_out`
- `updated` -> same-category buyer message -> `updated`
- `updated` -> due processing -> `updated` with `last_update_sent_at`
- `updated` -> agent reply -> `resolved`
- `updated` -> opt-out -> `opt_out_closed`
- `updated` -> 24h stale -> `timed_out`
- `resolved`, `timed_out`, `opt_out_closed` -> later matching buyer message creates a new thread

Q17. Debounce implementation:

Database-backed timestamps plus poller. The existing FastAPI debounce worker now also calls `process_due_escalation_threads`. No in-process timers.

Q18. Polling frequency:

Uses existing `DEBOUNCE_POLL_INTERVAL_SECONDS`, default 5 seconds. Worst-case latency is debounce window plus poll interval.

## Consequences

- The webapp can now render one escalation inbox item per `escalation_thread`.
- WhatsApp remains append-only; no reliance on unsupported message editing.
- Agent reply routing still depends on `[Ref:]` token preservation until dashboard reply controls ship.
- Race-condition protection uses `uq_open_escalation_thread_scope`, a PostgreSQL partial unique index in `scripts/migrate_escalation_threads.py`, plus an `IntegrityError` retry in `send_initial_or_update`: rollback, refetch the just-created open thread, append the buyer question, and continue the debounce/update path.

## Deferred

- Per-brokerage debounce configuration.
- Full persona CSV metrics for thread count / append rate / debounce bundle rate / timeout rate.
- Webapp escalation inbox and dashboard reply controls.
- Advanced partial-answer handling where an agent resolves only some questions.
