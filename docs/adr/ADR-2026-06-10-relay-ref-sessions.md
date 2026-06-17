# ADR — Relay ref sessions and misdirection mitigations (DAL-161)

**Date:** 2026-06-10
**Status:** Accepted
**Linear:** DAL-161

## Context

The WhatsApp agent relay previously required a quote-reply of a `[Ref: TOKEN]`
message for every send. WhatsApp permits one quoted message per send, so an
agent forwarding five brochure PDFs would have to quote five times — hostile
UX for the agent's most common action. Worse, agents predominantly **forward**
media from other chats, and WhatsApp forwards can carry neither a quote nor an
edited caption, leaving them unroutable under the quote-only model.

## Decision

Four routing tiers, ordered explicit → implicit, with friction proportional to
misroute risk:

1. **Caption token** (`#TOKEN`) — explicit, sends immediately. The
   interleaving primitive: an agent juggling three buyers tags each file.
   Token typos fall through; they are **never fuzzy-matched**.
2. **Quote-reply** — explicit, sends immediately and opens/refreshes a **ref
   session** (`agent_relay_sessions`) for that buyer. A quote to a different
   ref closes the old session. One active session per agent number.
3. **Active session** — implicit. An unquoted, untagged message within 10
   minutes of session activity routes to the session conversation, **held 30
   seconds** (`relay_outbox`, status `held`) with a recipient-naming ack:
   *"→ Ahmed (Marina Gate 2BR) — sending in 30s. Reply UNDO to cancel."*
4. **Single open `media_requested` escalation** — implicit, held 30s with a
   basis-stating ack. Qualifying threads must be open/updated, flagged
   `media_requested` **at classification time** (keyword+intent rubric in
   `escalation_threads.is_media_request`), and alerted within 48 hours.
   Routing reads stored state; it never re-interprets content. Zero or 2+
   qualifying threads → no auto-route.

No tier matches → media is **parked** (not rejected): 60-second burst windows
group multi-file forwards into one batch with one routing prompt (numbered
options when several media-request escalations qualify). A numeric reply,
quote-reply, or `#REF` routes the whole batch and sends immediately. Parked
media expires after 30 minutes with a discard notice. Non-media messages
bounce asking for a quote or `#REF` — text is cheap to re-send, media is not.

### Caption hygiene on forwards

A forwarded file carries its original caption — potentially another buyer's
name or internal developer pricing (PDPL exposure). When the inbound webhook
flags `Forwarded` (Twilio) / `context.forwarded` (Cloud API), the caption is
**stripped by default**. Directly-sent media keeps its caption minus any
routed `#TOKEN`. If the forwarded flag proves unavailable on the Twilio dev
path, dev accepts caption passthrough; the production rule targets 360dialog.

### Misdirection mitigations

- **Implicit-tier hold + UNDO** absorbs the inference-error class that Dalya
  introduced: the 30s hold with a recipient-naming ack gives the agent a
  visible window to cancel before anything reaches a buyer.
- **Closing a session never re-routes its in-flight items** — held items keep
  the conversation they were routed to.
- Misrouted **explicit** sends (agent quotes the wrong ref) are unrecoverable
  (the Cloud API cannot unsend); the recipient-naming ack makes the error
  visible within seconds so the agent can send a correction. Accepted floor.
- The 24-hour session-window check runs **per conversation, per item** at
  release time; a closed window bounces back with the reason and a dashboard
  deep link.
- Every send records its routing method on the timeline/compliance event
  (`caption_token | quote_reply | session | escalation_match |
  parking_prompt`) so misroutes can be audited and tier-4 eligibility tuned
  from real data.

## Alternatives considered

- **Quote-per-attachment (status quo):** safe but hostile; agents would fall
  back to personal WhatsApp, defeating the platform.
- **Fuzzy content matching of files to escalations:** rejected outright — the
  routing layer must read state, not interpret content; a wrong guess sends a
  buyer another buyer's paperwork.
- **No hold on implicit tiers:** faster, but leaves no recovery window for
  the error class our inference introduced.

## Consequences

- New state: `agent_relay_sessions`, `relay_outbox` (held/parked lifecycle on
  the debounce worker's poll interval).
- Command keywords (`TAKEOVER`, `RESUME`, `SEND`, `UNDO`) are consumed, never
  forwarded, and do not extend sessions.
- The hold window (30s) and tier-4 eligibility (48h) are tuning knobs —
  revisit after live feel tests with Luqman's agents (spec open question #4).
