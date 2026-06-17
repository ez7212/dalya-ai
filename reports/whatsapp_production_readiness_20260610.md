# WhatsApp Production Readiness Verification

Date: 2026-06-10
Linear: DAL-143

## Executive Status

Status: **conditionally ready on Twilio; not ready on 360dialog BSP**.

Dalya's WhatsApp business logic is verified through the transport abstraction for Brokerage AI, Agents AI, dashboard replies, tenant viewing confirmations, opt-out suppression, and duplicate webhook protection. The default live transport remains Twilio.

The 360dialog/BSP production path is **not production-ready** because `app/core/messaging/dialog360_transport.py` is intentionally a stub pending WABA approval and raises `NotImplementedError` for send and inbound parse operations. Do not set `MESSAGING_TRANSPORT=dialog360` in production until that transport is implemented and tested against an approved WABA number.

## Verification Run

Command:

```bash
venv/bin/python -m pytest \
  tests/test_multitenant.py::test_dialog360_transport_is_stub \
  tests/test_smart_escalation_relay.py \
  tests/test_escalation_inbox_api.py::test_agent_can_reply_to_escalation_from_dashboard_and_consume_route \
  tests/test_foundation_hardening.py::test_opt_out_is_brokerage_scoped \
  tests/test_foundation_hardening.py::test_suppressed_buyer_does_not_trigger_outbound_send \
  tests/test_viewing_logistics.py::test_viewing_list_detail_notification_drafts_status_and_tenant_reply
```

Result: **10 passed**.

## Flow Coverage

| Area | Status | Evidence |
|---|---:|---|
| Brokerage AI outbound buyer sends | Pass on Twilio | `TwilioTransport.send_to_buyer`; covered through dashboard reply, tenant/viewing, and post-viewing tests using the transport interface. |
| Agents AI outbound agent envelopes | Pass on Twilio | `TwilioTransport.send_to_agents_ai` stamps `[Ref: TOKEN]`; `tests/test_smart_escalation_relay.py` verifies route persistence, relay, wrong-agent blocking, expiry, and webhook branch behavior. |
| Dashboard reply to buyer | Pass | `tests/test_escalation_inbox_api.py::test_agent_can_reply_to_escalation_from_dashboard_and_consume_route` verifies dashboard reply sends to buyer, persists timeline/action/compliance, consumes the route, and resolves the thread. |
| Tenant WhatsApp viewing flow | Pass | `tests/test_viewing_logistics.py::test_viewing_list_detail_notification_drafts_status_and_tenant_reply` verifies approved tenant notice send, tenant reply handling, status updates, and Agents AI notification. |
| Opt-out suppression | Pass | `tests/test_foundation_hardening.py` verifies brokerage-scoped opt-out and suppressed outbound sends. |
| Duplicate webhook protection | Pass | `tests/test_smart_escalation_relay.py::test_buyer_webhook_dedupes_twilio_message_sid` verifies repeated buyer webhook `MessageSid` queues only once. |
| 360dialog BSP transport | Blocked | `tests/test_multitenant.py::test_dialog360_transport_is_stub` confirms the 360dialog transport is not implemented and fails closed. |

## Production Configuration Notes

- Production messaging should use `MESSAGING_TRANSPORT=twilio` until the 360dialog WABA path is implemented.
- Required Twilio env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, plus brokerage-level `brokerage_ai_number` and `agents_ai_number`.
- `PUBLIC_URL` must match the deployed webhook URL when Twilio signature validation is enabled.
- The inbound webhook is `/api/v1/whatsapp/webhook`.
- Duplicate webhook protection is keyed by Twilio `MessageSid` in `message_queue`.

## Remaining BSP Work

Before switching to 360dialog:

- Implement `Dialog360Transport.send_to_buyer`.
- Implement `Dialog360Transport.send_to_agents_ai`.
- Implement `Dialog360Transport.parse_inbound`.
- Add 360dialog webhook signature verification using `D360_WEBHOOK_SECRET` or the approved provider mechanism.
- Add template/button payload support if 360dialog approved templates/buttons are required for tenant confirmations.
- Run the same verification set against a 360dialog sandbox or approved WABA number.

## Decision

Twilio production path: **ready for controlled production verification**.

360dialog BSP path: **not ready; external WABA approval and transport implementation required**.
