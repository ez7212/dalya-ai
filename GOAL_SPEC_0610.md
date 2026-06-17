# Dalya MVP Gap-Closure Spec — Agent-Critical Features

**Date:** 2026-06-10
**Status:** Draft for review
**Scope:** Eight workstreams closing the gaps identified in the June 10 MVP review, ordered by agent-visible impact. Logistics building-level inheritance is explicitly **out of scope** (single-listing config retained for now).

**Suggested ticket numbering (assign in Linear):**

| Ticket | Title | Phase |
|---|---|---|
| DAL-158 | Live conversation takeover (pause/resume AI) | P1 |
| DAL-159 | Voice note handling in buyer + agent flows | P1 |
| DAL-160 | Outbound media via dashboard composer | P1 |
| DAL-161 | Outbound media via WhatsApp agent relay (batching window) | P1 |
| DAL-162 | Agent notification framework | P2 |
| DAL-163 | Portal lead ingestion + AI first-touch | P2 |
| DAL-164 | Buyer card & buyer list view | P3 |
| DAL-165 | Offer log | P3 |
| DAL-166 | Post-viewing follow-up draft CTA | P3 (flagged optional) |

Phasing rationale: P1 items are the failures an agent sees **on day one of real traffic** (AI mishandles a voice note, can't send a brochure, can't be shut off). P2 items fill the funnel and keep the agent informed without polling. P3 items are the structured-data layer that compounds (buyer card + offer log are co-dependent and should land together). Per the one-change-set-per-run discipline, each ticket below is sized as an independent change-set with its own verification checklist.

---

## 1. DAL-158 — Live Conversation Takeover

### Problem
The escalation model covers "AI knows it should hand off." Takeover covers "AI doesn't know it's wrong." Without a kill switch, agents will not trust the AI with their buyers. This is the trust prerequisite for everything else.

### Behavior
A conversation gains an AI mode with two states:

```
AI_ACTIVE  ──(takeover)──▶  AGENT_CONTROLLED
AI_ACTIVE  ◀──(resume)───  AGENT_CONTROLLED
```

While `AGENT_CONTROLLED`:
- Inbound buyer messages are **never** answered by the concierge. They are forwarded raw to the agent via Agents AI (with `[Ref: TOKEN]`) and appear in the dashboard inbox as unanswered.
- Escalation classification still runs (for analytics/compliance tagging) but produces no buyer-facing output.
- Draft generation for this conversation is suppressed (hot-list refresh skips draft creation; existing pending drafts for the conversation are auto-snoozed with reason `takeover`).
- Agent replies (dashboard or WhatsApp relay) flow exactly as today.

### Triggers
1. **Dashboard:** one-tap toggle on `/agent/conversations/[id]` and on each inbox row. Confirmation-free to pause (the dangerous direction is resuming, not pausing); resuming shows a one-line confirm.
2. **WhatsApp:** agent quote-replies any `[Ref: TOKEN]` message with the single keyword `TAKEOVER` (case-insensitive, trimmed). Agents AI confirms: *"AI paused for [buyer name / listing]. All messages will be forwarded to you. Reply RESUME to this thread to re-enable."* Keyword `RESUME` re-enables. These keywords are consumed as commands and never forwarded to the buyer.

### Data model
On `conversations`: `ai_mode` enum (`active` | `agent_controlled`, default `active`), `ai_mode_changed_at`, `ai_mode_changed_by` (agent_id), `ai_mode_change_source` (`dashboard` | `whatsapp`). Every transition writes a timeline event and a compliance event.

### Edge cases
- Buyer messages arriving in the debounce window when takeover fires: flush the debounce buffer as raw forwards, do not bundle into an AI escalation summary.
- `TAKEOVER` sent without a quote-reply (no ref resolvable): Agents AI replies asking the agent to quote the relevant message. Never guess the conversation.
- Tenant confirmation conversations are exempt — takeover applies to buyer conversations only in this change-set.
- No auto-resume. Optional later: a daily digest line listing conversations still in `agent_controlled` > 48h.

### Verification checklist
1. Pause via dashboard → buyer message arrives → no AI reply, raw forward received on Agents AI, inbox shows unanswered.
2. Pause via `TAKEOVER` quote-reply → confirmation received → state persisted with source `whatsapp`.
3. Pending drafts for the conversation auto-snoozed with reason recorded.
4. `RESUME` restores normal concierge behavior on the next buyer message.
5. Keyword messages never reach the buyer (assert on outbound transport mock).
6. Compliance events written for both transitions.
7. Cross-tenant: takeover state on brokerage A conversation invisible to brokerage B (isolation test extended).
8. Persona harness regression: append/bundle/bypass rates unchanged on the 30-persona baseline (takeover off by default, so baseline must be untouched).

---

## 2. DAL-159 — Voice Note Handling

### Current state to verify first (pre-coding questions)
- Confirm the Speechmatics (primary) / AssemblyAI (fallback) pipeline exists as a callable service and what its interface is (sync vs async, language hint support).
- Confirm Twilio webhook media payload handling: does the inbound webhook currently drop non-text media or persist it?

### Scope — three paths

**Path A: Buyer → Brokerage AI (inbound buyer voice note).** Webhook receives audio media → download and persist media (storage ref on timeline) → transcribe with language auto-detect (expect Arabic/English mix; Hindi/Urdu likely — log detected language, do not block on unsupported) → transcription stored on the message record (`transcription_text`, `transcription_language`, `transcription_confidence`, `transcription_provider`) → concierge processes the transcription exactly as if it were inbound text, including escalation classification and debounce participation.

**Path B: Agent → Agents AI (agent replies by voice note).** Agent quote-replies a `[Ref: TOKEN]` with a voice note. Two design options — **decision needed:**
- *Option B1 (recommended for MVP):* transcribe, send the **transcription as text** to the buyer via Brokerage AI, and echo the transcription back to the agent for the record ("Sent as text: …"). Keeps the human-in-the-loop property — the agent spoke the words; we are not generating content.
- *Option B2:* forward the audio file itself to the buyer. Simpler, but buyer receives an agent voice from the brokerage's AI number — brand-confusing, and loses searchable text on the timeline.
- B1 has a risk: transcription errors get sent verbatim. Mitigation: if `transcription_confidence` below threshold, do **not** auto-send; reply to agent with the transcription and ask for a confirm keyword (`SEND`) — this is the only flow where confidence gates sending.

**Path C: Voice note in escalation context.** When an escalation thread includes a transcribed voice note, the forwarded summary to Agents AI labels it: `🎙 (voice, transcribed): "…"` so the agent knows provenance.

### Failure mode (must be designed, not incidental)
Transcription fails or audio format unsupported → buyer receives a single polite fallback in conversation language: *"I couldn't process your voice message — could you type it instead, or your agent will follow up shortly."* → conversation is escalated with reason `media_unprocessable` so the failure is never silent. (Silent suppression here is exactly the failure class the threading rework existed to kill.)

### Out of scope
Outbound AI-generated voice (never), video notes (forward-to-agent only with `media_unprocessable` handling), voice dictation mode for post-viewing notes (separate existing backlog item).

### Verification checklist
1. Inbound buyer voice note (English) → transcribed → concierge answers grounded on transcription.
2. Inbound Arabic voice note → language detected, transcription stored, RTL rendering of transcription in dashboard timeline checked.
3. Transcription failure → fallback message sent once, escalation created with `media_unprocessable`, no AI answer attempted.
4. Agent voice reply (high confidence) → text delivered to buyer, echo to agent.
5. Agent voice reply (low confidence) → held, agent receives transcript + `SEND` prompt, send occurs only after confirm.
6. Voice note inside a debounce window bundles correctly with surrounding text messages.
7. Duplicate webhook MessageSid on a media message handled idempotently (no double transcription billing).
8. Provider failover: Speechmatics forced failure → AssemblyAI used, provider recorded.

---

## 3. DAL-160 / DAL-161 — Outbound Media (Dashboard + WhatsApp Relay)

### Problem
The agent's most common action is pushing a brochure PDF, photos, or a location pin into a buyer conversation. Text-only replies make the AI channel worse than the agent's personal WhatsApp.

### DAL-160 — Dashboard composer media

- Composer on `/agent/conversations/[id]` and `/agent/escalations` gains attachments: PDF, JPEG/PNG, with caption text. Multiple attachments per send (cap 10 per message group).
- Media uploaded to storage, persisted with `media_assets` records (`brokerage_id`, `agent_id`, `conversation_id`, `mime_type`, `size`, `storage_ref`, `sha256`), then sent via the transport's media API. Twilio sandbox supports media; verify size limits (WhatsApp: 100 MB media, 5 MB images via some BSPs — encode the per-transport limit in the transport layer, not the UI).
- **Listing asset shortcut:** composer offers "attach from listing" — the listing's brochure/photos already in the system — so the agent doesn't re-upload per buyer. This is the 80% case.
- 24-hour session window rule: media sends are session messages. If the buyer's last inbound is > 24h old, the composer must surface this and block free-form media (template-first reopen flow is existing behavior — reuse it; do not build a media template path in this change-set).
- Timeline renders thumbnails/file chips; compliance event per media send.

### DAL-161 — WhatsApp relay media + the 5-PDF problem

Current relay constraint: agent must quote-reply the `[Ref: TOKEN]` message. WhatsApp permits one quoted message per send, and quoting on every attachment is hostile UX. Design:

**Routing precedence (three explicit-to-implicit tiers):**

1. **Caption token (explicit, immediate).** Every ref token is unique per conversation. An agent can put the token (`#REF123`) in the caption of any media message; it routes to that conversation regardless of quotes or sessions. The token is stripped from the caption before the buyer send. Typo/no-match → falls through to tier 2/3, never fuzzy-matched. This is the interleaving primitive: an agent juggling three buyers tags each file explicitly.
2. **Quote-reply (explicit, immediate).** Quote-replying a ref routes to that conversation and opens/refreshes a **ref session** for that buyer. A quote to a **different** ref closes the old session and opens a new one.
3. **Active session (implicit, held).** An unquoted, untagged message within **10 minutes** of session activity routes to the session conversation — but because the routing is inferred, it is **held 30 seconds before sending**, with a per-item ack naming the recipient: *"→ Ahmed (Marina Gate 2BR) — sending in 30s. Reply UNDO to cancel."* `UNDO` cancels all held, unsent items in the session. Explicit sends (tiers 1–2) skip the hold — friction is proportional to misroute risk.
4. **Single open media-request escalation (implicit, held).** No session active, but the agent has **exactly one** open escalation flagged `media_requested` (see below) → media auto-routes to that conversation, held 30s with an ack stating the basis: *"→ Ahmed (Marina Gate 2BR) — matched your open escalation asking for the floor plan. Sending in 30s. Reply UNDO to cancel."* Zero or two-plus qualifying escalations → no auto-route; fall through to parking.

No tier matches → media is parked with a routing prompt (see forwarded-media section); non-media messages bounce asking for a quote or `#REF` caption. Never guess beyond tier 4's exactly-one rule.

**`media_requested` flag — structural, not inferred at send time.** The flag is set on the escalation thread **at classification time** by the existing escalation classifier when the buyer's message requests media artifacts (brochure, floor plan, photos, payment plan PDF, video, location pin — maintain as a keyword+intent rubric in the classifier, same pattern as category mapping). It is a stored boolean on the thread, never re-derived by fuzzy-matching the forwarded file against escalation text at routing time — routing reads state, it doesn't interpret content. Qualifying threads must be in `OPEN_ALERTED`/`OPEN_UPDATED` and alerted within the last **48 hours** (a stale media request must not capture today's forward). Resolution/closure of the thread removes it from tier-4 eligibility immediately.

**Multi-buyer workflows this yields:**
- *Sequential batches (common case):* quote buyer A's ref with the first file → remaining A files unquoted (session) → quote buyer B's ref (A's session closes) → B's files → quote C. Three quotes total for three batches.
- *Interleaved:* caption-token every file. No session ambiguity possible.
- *Same brochure to 3 buyers:* forward the same PDF three times, each with a different `#REF` caption — or use the dashboard composer's attach-from-listing, which is faster for this case and is what onboarding material should recommend.

Rules:
- Command keywords (`TAKEOVER`, `RESUME`, `SEND`, `UNDO`) are consumed, never forwarded, and do not extend sessions.
- Session state: `agent_relay_sessions` (`agent_id`, `conversation_id`, `opened_at`, `last_activity_at`, `expires_at`, `closed_reason`). One active session per agent number; concurrent threads use caption tokens.
- Held items: `relay_outbox` rows (`status`: `held` | `sent` | `cancelled`, `release_at`) processed by a short-interval job; UNDO flips unsent rows to `cancelled` with an ack confirming what was cancelled.
- All relay media follows the 24h-window check per conversation; closed window → bounce-back with reason and dashboard deep link (checked per item, since interleaved buyers can have different window states).

**Residual risk:** misrouted *explicit* sends (agent quotes the wrong ref) are unrecoverable — the Cloud API cannot unsend. The recipient-naming ack makes the error visible within seconds so the agent can send a correction; that is the accepted floor. The implicit-tier hold + UNDO covers the inference-error class, which is the one Dalya introduced and therefore must absorb.

### Forwarded media (the dominant real-world flow)

Agents typically don't store files on their phone — they **forward** media from another WhatsApp conversation (developer chat, another buyer, a broker group). WhatsApp's forwarding mechanics constrain routing:

- A forwarded message **cannot carry a quote-reply** → tier 2 unavailable for forwards.
- A forwarded message's caption **cannot be edited at forward time** — the original caption travels with it → tier 1 unavailable; the agent cannot type a `#REF` token into a forward.

So every forward arrives quote-less and token-less, leaving only tier 3 (active session) or the bounce path. Two consequences are designed in:

**1. Parked media (replaces the bounce for media).** Media arriving with no active session and no tier-4 match is not rejected — it is **parked**: persisted, held in `relay_outbox` with status `parked`, scoped to the agent. Multiple unrouted media arriving within a 60-second burst window group into one parking batch (multi-file forwards arrive as separate webhook messages). Agents AI sends one routing prompt per batch. When multiple open `media_requested` escalations exist (the tier-4 ambiguous case), the prompt lists them as numbered options: *"Got 3 files — who are these for? 1 = Ahmed (Marina Gate 2BR), 2 = Fatima (Creek Harbour 1BR), or quote a ref / reply #REF."* A numeric reply, quote-reply, or `#REF` routes the whole batch, which then sends immediately (routing became explicit). Otherwise the prompt is the plain form: *"Got 3 files — where should these go? Quote a buyer's ref, or reply with the #REF token."* Parked media expires after **30 minutes** with a discard notice. This also fixes the natural ordering problem — agents will forward first and think about routing second; the system must accommodate that order, not fight it.

Every media send records its routing method on the timeline/compliance event: `caption_token | quote_reply | session | escalation_match | parking_prompt` — needed to audit misroutes and to tune tier-4 eligibility later from real data.

**2. Caption hygiene on forwards.** A forwarded file carries its *original* caption — potentially another buyer's name, internal developer pricing notes, or group-chat context. Forwarding that caption to a new buyer is a leakage and PDPL exposure. Rule: when the inbound webhook flags the message as forwarded (`context.forwarded` on Cloud API; Twilio's `Forwarded` parameter — **verify availability in sandbox**, see open questions), the caption is **stripped by default** before the buyer send. Directly-sent media (agent typed the caption intentionally) keeps its caption, minus any routed `#REF` token. If the forwarded flag proves unavailable on the Twilio dev path, dev accepts caption passthrough with a documented production rule on 360dialog rather than stripping all tier-3 captions indiscriminately.

Architecture note: forwards require no special media handling — they arrive as ordinary inbound media on the Agents AI webhook, and the existing download → persist → re-send-via-API pipeline (shared with DAL-159/160) means Dalya never depends on the agent possessing the file locally. Routing and caption hygiene are the only forward-specific logic.

Recommended agent workflow for onboarding material: *quote the buyer's ref with any short text ("brochure coming") to open the session, then forward the files* — they route tier-3 with the named ack — or simply forward first and answer the routing prompt. Both orders work.

Edge notes: view-once media cannot be forwarded (no handling needed); `frequently_forwarded` flag logged but not behavior-changing; forwarded *text* messages follow the standard tiers (no parking — text is cheap to re-send, media is not).

### Verification checklist (combined)
1. Dashboard: 3 PDFs + caption → buyer receives all, timeline shows chips, compliance events written.
2. "Attach from listing" pulls existing listing assets without re-upload.
3. Media send blocked when 24h window closed; reopen flow surfaced.
4. Relay sequential: quote-reply + 4 unquoted follow-up PDFs within window → all 4 reach the correct buyer with recipient-naming acks; held items released after 30s.
5. Relay interleaved: files captioned `#REF_A`, `#REF_B`, `#REF_A` in succession → each routes to the correct buyer immediately, captions stripped of tokens before buyer delivery, no session created or consumed.
6. Caption-token typo → falls through to active session (held) or bounce-back if none; never fuzzy-matched to a different buyer.
7. UNDO during hold → all held items cancelled with confirmation ack; nothing reaches the buyer; `relay_outbox` rows marked `cancelled`.
8. Session expiry: unquoted message at minute 11 → bounce-back asking for a quote or `#REF` caption, nothing forwarded.
9. New quote to different ref mid-session → old session closed, file routes to new buyer; any still-held items from the old session are released to the **old** buyer (closing a session must not re-route its in-flight items).
10. Three-buyer fan-out with mixed window states: buyer A in-window, buyer B's 24h window closed → A's files send, B's bounce per item with reason, C unaffected.
11. Oversize file → agent-facing error naming the limit, nothing partially sent.
12. Cross-tenant: media asset storage refs scoped by `brokerage_id`; a `#REF` token from brokerage A presented by an agent of brokerage B resolves to nothing (token-forgery isolation test).
13. Forwarded PDF with no active session → parked, routing prompt received; agent quote-reply releases it to the correct buyer immediately.
14. Burst forward of 3 files → one parking batch, one routing prompt, one routing answer releases all 3 in order.
15. Forwarded media with original caption ("Here you go Fatima…") → caption stripped before buyer delivery; directly-sent media keeps its caption minus `#REF` token.
16. Parked media untouched for 30 min → discarded with notice to agent; `relay_outbox` row marked `expired`, media asset retained per retention policy but never sent.
17. Forward arriving while a session is active → routes tier-3 (held 30s, named ack), caption stripped; session takes precedence over an open media-request escalation.
18. Exactly one open `media_requested` escalation, no session → forwarded PDF auto-routes to it, held 30s with basis-stating ack; UNDO cancels.
19. Two open `media_requested` escalations → no auto-route; parked with numbered-options prompt; numeric reply releases the batch to the chosen buyer.
20. One `media_requested` escalation alerted 49h ago → stale, not tier-4 eligible; media parks with plain prompt.
21. Escalation resolved between forward and hold release → boundary rule: tier-4 eligibility is evaluated at routing time and the hold proceeds (the request existed when routed); but a thread resolved **before** the forward arrives never matches.
22. `media_requested` flag set by classifier on a "can you send the floor plan?" persona message; not set on "what's the service charge?"; flag is read as stored state at routing time (assert no content re-interpretation in the routing path).
23. Routing method recorded correctly on compliance events for all five methods.

---

## 4. DAL-162 — Agent Notification Framework

### Problem
Anything that requires opening `/agent` to discover will be discovered hours late. Every time-sensitive event needs a WhatsApp push via Agents AI with a deep link.

### Event catalog

| # | Event | Default timing | Notes |
|---|---|---|---|
| 1 | Escalation created/updated | Immediate | Existing behavior — becomes catalog entry #1, unchanged |
| 2 | New portal lead ingested + first-touch sent | Immediate | DAL-163 dependency; highest-urgency event in the system |
| 3 | Buyer reply on a hot-list conversation (score ≥ threshold) | Immediate | "Your hot buyer just replied" — only above threshold to avoid spam |
| 4 | Buyer viewing confirmation / decline / reschedule request | Immediate | |
| 5 | Tenant confirmation received / declined | Immediate | Declines are urgent (viewing at risk) |
| 6 | Upcoming viewing reminder | T−60 min (incorporating travel buffer) | One per viewing |
| 7 | Post-viewing feedback received from buyer | Immediate | Links to feedback + (DAL-166) draft CTA |
| 8 | New AI drafts pending approval | **Digest** — morning batch with hot-list push | Never immediate; drafts are review work, not interrupts |
| 9 | Buyer opt-out | Immediate | Compliance-relevant; agent must know to stop all channels |
| 10 | AI failure events (`media_unprocessable`, transcription fail, send failure) | Immediate | Silent failures forbidden |
| 11 | Calendar sync error / token expiry | Immediate, once per error state | Re-auth deep link |
| 12 | Conversation in takeover > 48h | Daily digest line | From DAL-158 |
| 13 | Morning hot list ready | Scheduled (existing refresh time) | The anchor digest; events 8 and 12 ride along |

### Mechanics
- Single `agent_notifications` table: `event_type`, `agent_id`, `conversation_id`/`viewing_id` refs, `urgency` (`immediate` | `digest`), `sent_at`, `whatsapp_message_sid`, `dedupe_key`. Dedupe key prevents double-push on retried webhooks/jobs.
- All immediate pushes include a deep link to the exact `/agent/...` surface.
- **Quiet hours:** per-agent config (default 22:00–07:00 GST). During quiet hours, events 3, 6, 7, 8 queue for morning digest; events 1, 2, 4, 5, 9, 10 still send (configurable later, conservative default now: a lead at 11pm is exactly the speed-to-lead case).
- **Per-agent preferences:** v1 is a simple per-event-type on/off + quiet hours window on `/agent/settings`. No granular channels.
- Rate guard: hard cap of N immediate pushes per agent per hour (suggest 20) with overflow collapsing into a single "you have X more updates" message — protects against pathological loops.

### Verification checklist
1. Each catalog event fires exactly once for its trigger (dedupe key honored on webhook retry).
2. Quiet hours: hot-buyer reply at 23:30 → queued; appears in morning digest; tenant decline at 23:30 → sent immediately.
3. Deep links resolve to the correct conversation/viewing for the correct agent.
4. Preference toggle off → event suppressed and recorded as suppressed (not silently dropped — audit row exists).
5. Rate guard collapses a forced flood into the overflow message.
6. Cross-tenant: notification rows scoped; agent A never receives agent B's events even within the same brokerage (assignment-scoped, not just brokerage-scoped).

---

## 5. DAL-163 — Portal Lead Ingestion + AI First-Touch

### Problem
85–95% of buyer inquiries arrive as Property Finder/Bayut leads delivered to the agent by email and/or CRM. Without ingestion, Dalya scores an empty pipeline.

### Ingestion paths (build in this order)

**Path 1 — Email parsing (universal, MVP).** Every PF/Bayut lead generates a notification email with buyer name, phone, message, and listing reference. Per brokerage (later per agent), provision a dedicated ingest address (`leads+{brokerage_slug}@dalya...`) and have the agent set up auto-forwarding from their lead inbox. Parser extracts: buyer name, phone (normalize to E.164), buyer message, portal listing ref/URL, lead source. Parsers are per-portal-template with versioning — **portal email formats change; treat each template as data with a `parser_version`, and route unparseable emails to a dead-letter queue with an event-10 notification, never silently dropped.**

**Path 2 — CRM webhook (per-design-partner).** Adapter interface (`LeadIngestAdapter`) with the email parser as the first implementation. Luqman's brokerage's actual CRM (or absence of one) determines the second. **Open question #1: what does Luqman's team actually use today — email only, PF Expert/Bayut Pro inboxes, or a CRM?** This decides whether Path 2 is MVP at all.

### Lead resolution pipeline
1. Normalize phone → check for existing conversation (any listing) for this brokerage. If exists: attach lead as a timeline event on the existing conversation, notify agent, **do not** create a duplicate first-touch.
2. Resolve portal listing ref → internal listing (match by portal URL captured at listing creation; fall back to permit/Trakheesi number if present in the email; else fuzzy match flagged for agent confirmation). Unresolved listing → still ingest the lead, route to agent with "couldn't match listing" — never block a lead on listing resolution.
3. Create conversation in state `lead_ingested`, assign to the listing agent, create hot-list entry with a strong recency score.

### First-touch — the compliance-critical part
The buyer has not messaged our WhatsApp number, so first contact is **business-initiated → approved template message required**, regardless of BSP. Implications:

- A first-touch **utility-category template** must be drafted and submitted for approval **now** — this sits on the same critical path as WABA approval and takes its own review cycle. Suggested shape: *"Hi {{1}}, thanks for your enquiry about {{2}} on {{3}}. I'm the AI assistant for {{4}} — happy to answer questions or arrange a viewing. Reply STOP to opt out."* (Category risk: Meta may classify chatty variants as marketing; keep it transactional-referencing-their-enquiry to argue utility. Have a marketing-category fallback drafted.)
- **Consent basis:** the buyer submitted their number on a portal lead form expecting contact — this is the standard consent basis the whole industry operates on, but it must be (a) documented in the PDPL records as the lawful basis with the lead email retained as evidence, and (b) paired with opt-out in the first message. Opt-out propagates through existing cross-agent opt-out machinery.
- First-touch is the **one exception to draft-and-approve**: it is template-locked content with variable slots only, auto-sent on ingestion (speed-to-lead is the whole point), with the agent notified simultaneously (event #2). No free-form AI content is ever auto-sent — the template lock is what makes this consistent with the human-in-the-loop principle. State this explicitly in the ADR.
- Buyer replies to first-touch → opens the 24h session → normal concierge flow takes over.
- No reply in 48h → one review-only draft nudge enters the agent's draft queue (normal approval flow, not auto-sent).

### Verification checklist
1. PF-format and Bayut-format fixture emails parse to correct fields; `parser_version` recorded.
2. Malformed email → dead-letter queue + agent notification; nothing silent.
3. Duplicate lead (same phone, same listing, < 7 days) → no second first-touch; timeline event only.
4. Existing conversation match → lead attached, no new conversation.
5. Unresolved listing → lead still ingested and routed with flag.
6. First-touch send recorded with template name/version + consent-basis compliance event.
7. STOP reply → opt-out enforced and propagated; no nudge draft created.
8. Hot-list refresh ranks a fresh lead above stale conversations.
9. Cross-tenant: ingest address for brokerage A cannot create conversations in brokerage B (forged-forward test).

---

## 6. DAL-164 — Buyer Card & Buyer List View

### Problem
Buyer context lives in conversation summaries. Agents need the qualification snapshot at a glance and the ability to correct AI inferences.

### Surfaces
- `/agent/buyers` — list view: buyer name, top conversation/listing, qualification snapshot chips (budget band, financing, timeline), hot-list score, last activity, open offers count, next viewing. Sort by score (default) / last activity / name. Filter: has open offer, viewing scheduled, stale.
- `/agent/buyers/[id]` — the card.

### Card structure
**Identity:** name, phone (masked per PDPL display rules), language, source (portal lead / organic WhatsApp), consent status + opt-out flag.

**Qualification (the structured core):** budget min/max (AED), financing (`cash` | `mortgage_preapproved` | `mortgage_unknown` | `unknown`), pre-approval amount/bank if disclosed, timeline, target areas[], property type/beds, must-haves[], deal-breakers[]. Every field carries **provenance**: `ai_inferred` (with confidence + source message link) vs `agent_confirmed`. Agent edit promotes to `agent_confirmed`; subsequent AI inference **never overwrites** an `agent_confirmed` value (structural enforcement — schema-level guard, not prompt instruction). New conflicting AI inference on a confirmed field surfaces as a suggestion chip ("buyer mentioned 1.8M — update confirmed budget of 2M?"), agent-actioned only.

**Synced histories (read views, no new write paths):** viewing history with feedback outcomes, offer history (from DAL-165), conversation summary (existing summarizer output) with link into the inbox, escalation count.

### Data model
`buyer_profiles` keyed by (`brokerage_id`, normalized phone). One profile can span multiple conversations/listings within a brokerage. **Never cross-brokerage** — the same buyer phone at two brokerages is two independent profiles (this is the tenant boundary; the cross-brokerage intelligence graph is a Phase 2 strategic question, not an MVP data model).

`buyer_profile_fields` as field-level rows (`field`, `value`, `provenance`, `confidence`, `source_message_id`, `confirmed_by`, `updated_at`) rather than columns — keeps the provenance/no-overwrite rule enforceable per field and audit-friendly.

### AI extraction
Qualification extraction runs on the existing message-processing path (Haiku-tier), writing `ai_inferred` rows. Backfill job over existing conversations at migration time. Hot-list scoring reads confirmed-over-inferred values when both exist.

### Verification checklist
1. List view renders for an agent with seeded buyers; scoping is assignment-level (agent sees own buyers only, no owner rollup).
2. AI infers budget from a persona transcript → appears as `ai_inferred` with source link.
3. Agent edits budget → `agent_confirmed`; forced conflicting AI inference creates suggestion chip, does not overwrite (DB-level assertion).
4. Same phone, two listings → one profile, two linked conversations.
5. Same phone, two brokerages in seed → two profiles, isolation test extended with profile-field forbidden-list check.
6. Opt-out buyer renders with opt-out banner; all send CTAs disabled on the card.
7. Viewing + feedback + offers render from their source tables (no duplicated state).

---

## 7. DAL-165 — Offer Log

### Problem
Escalation flags offer-related messages but nothing tracks the offer itself. Agents juggle multiple offers in their heads.

### Model
`offers`: `brokerage_id`, `agent_id`, `conversation_id`, `listing_id`, `buyer_profile_id`, `amount` (AED), `direction` (`buyer_offer` | `seller_counter`), `status`, `conditions` (free text + structured flags: `financing_contingent`, `subject_to_viewing`), `source` (`ai_detected` | `agent_logged`), `source_message_id`, timestamps.

State machine per offer thread (a thread = sequence of offer/counter on one conversation+listing):

```
DRAFT_PENDING_CONFIRM ─▶ SUBMITTED ─▶ COUNTERED ─▶ (SUBMITTED…)
SUBMITTED/COUNTERED ─▶ ACCEPTED | REJECTED | WITHDRAWN | EXPIRED
```

### Flows
- **AI-detected:** when escalation classification fires offer-related, an extraction pass (Sonnet-tier, structured) attempts amount/conditions → creates `DRAFT_PENDING_CONFIRM` attached to the escalation. Agent confirms/edits/discards from the escalation view or via a confirm prompt on Agents AI. **An offer never enters `SUBMITTED` without agent confirmation** — AI proposes, agent disposes, same as drafts.
- **Agent-logged:** manual "log offer" on conversation view and buyer card.
- Status changes write timeline + compliance events (offer history is exactly the audit trail a brokerage owner asks about — and a quiet seed for the Negotiation Co-Pilot data layer later).
- Surfaces: conversation view (offer strip), buyer card (history), and a new hot-list scoring input: open `SUBMITTED`/`COUNTERED` offer = strong score boost (verify against existing offer-signal scoring to avoid double counting — the current scorer reads offer *signals* from messages; once offers are first-class, the scorer should prefer the structured record).

### Verification checklist
1. Persona offer message → escalation + `DRAFT_PENDING_CONFIRM` with extracted amount.
2. Agent confirm → `SUBMITTED`; reject → discarded with audit row.
3. Counter flow advances the thread; full history renders in order on buyer card.
4. Extraction failure (vague "would they take less?") → escalation only, no draft offer, no hallucinated amount (banned-output check: amount must have a source-message anchor).
5. Hot-list: open offer boosts score; structured record preferred over message-signal double count.
6. Cross-tenant + cross-agent scoping verified.

---

## 8. DAL-166 — Post-Viewing Follow-Up Draft CTA *(flagged optional)*

Smallest possible loop-closer; ship behind a flag, cut if P1/P2 slip.

- On feedback received (event #7), the feedback view gains one CTA: **"Draft follow-up"** → generates a review-only draft into the existing draft queue, grounded on: feedback content, buyer card qualification, and — if any exist — up to 3 alternative listings from the **same brokerage's** inventory matching confirmed qualification fields (simple filter match, not the deferred AI matching system; if no matches, the draft is a plain follow-up with no alternatives, never padded with weak matches).
- Reuses the entire existing draft approve/edit/send machinery. No new send paths.

**Verification:** draft appears in queue with feedback grounding; alternatives only from same brokerage (isolation); zero-match case produces no fabricated listings; flag off = CTA absent, no behavior change.

---

## Cross-Cutting

### ADR & audit docs required
- ADR: first-touch template auto-send as the bounded exception to draft-and-approve (DAL-163).
- ADR: ref session model and its misdirection mitigations (DAL-161).
- ADR: buyer profile field-level provenance and the no-overwrite guard (DAL-164).

### Regression discipline
30-persona harness baseline (32.7% append / 34.3% bundle / 42.9% bypass) re-run after each P1 change-set lands. Voice notes (DAL-159) is the only P1 item that touches the message-processing path directly — expect baseline movement there and re-baseline deliberately, not accidentally.

### Open questions (answer before P2 starts)
1. **Luqman's lead delivery today:** email only, portal pro inboxes, or CRM? Determines DAL-163 Path 2 scope.
2. **First-touch template:** draft both utility and marketing-category variants this week and submit with the WABA application — this is the longest external dependency in the entire spec.
3. **Voice reply mode:** confirm B1 (transcribe-to-text) vs B2 (forward audio) — recommend B1.
4. **Hold window for implicit-tier relay sends:** 30s is the proposed default — long enough to catch a misroute from the ack, short enough not to feel broken. Tune after live feel test; consider per-agent config later, not now.
5. **Hot-list score threshold for event #3** (hot-buyer reply push) — propose reusing the existing "hot" band cutoff.
6. **Transcription confidence threshold** for the agent voice-reply gate — needs empirical setting against Speechmatics confidence distribution on Gulf-accented English/Arabic.
7. **Forwarded-flag availability:** Cloud API (360dialog) exposes `context.forwarded` on inbound messages; verify whether Twilio's `Forwarded` webhook parameter is delivered in the sandbox. Caption-stripping behavior in dev depends on this; production rule targets 360dialog regardless.

### Dependency graph
```
DAL-158 (takeover) ──────────────── independent, ship first
DAL-159 (voice) ─────────────────── depends on transcription service verification
DAL-160 (dash media) ────┐
DAL-161 (relay media) ───┴───────── DAL-161 depends on DAL-160 storage layer
DAL-162 (notifications) ─────────── consumes events from 158/159/163; framework can ship with existing events first
DAL-163 (lead ingestion) ────────── external dep: template approval (start NOW); emits event #2 into DAL-162
DAL-164 (buyer card) ─────┐
DAL-165 (offer log) ──────┴──────── land together; 165 feeds 164's history panel
DAL-166 (feedback CTA) ──────────── depends on 164 (qualification grounding); flagged
```