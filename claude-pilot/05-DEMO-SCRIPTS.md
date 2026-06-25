# 05 — Demo Scripts (golden path + stress path)

Two runnable scripts Eric can follow live from `/agent`. Buyer messages are sent via the **simulated
transport** (Agent B's `run_scenarios.py`), so each buyer turn lands in the real pipeline and the
dashboard updates for real. After each step: the **expected dashboard change** is stated — Agent F
confirms actual.

Setup before either demo: backend :8000, frontend :3001, `MESSAGING_TRANSPORT=simulated`, seed loaded,
Eric signed in at `/agent`.

---

## A. GOLDEN PATH (10–15 min) — "Dalya working well"

Listing **L1 (Dubai Hills ready villa)**, buyer **Adam Miller (hot ready)**, plus a viewing/offer
follow-up. The clean story: a hot buyer arrives, qualifies himself through the bot, asks to view, Eric
acts from the queue, and a follow-up draft is one click away.

1. **Open `/agent`.** → Dashboard loads with pilot data, no fallback banner. Note current Today Queue.
2. **Send Adam turn 1** (simulated): *"Hi, I'm looking for a 4-bed villa in Dubai Hills around 6.5M,
   ready to move. Can you tell me about this one?"*
   → Bot answers listing-aware (asking price, community), asks **one** qualifying question. New
   conversation appears; readiness starts climbing.
3. **Adam turn 2:** *"I'm in Dubai, cash buyer, want to see it this week. My wife decides with me."*
   → Bot captures budget/financing/timeline/decision-maker; readiness → **viewing-ready/hot**; Adam
   surfaces in **Hot buyers** and Today Queue.
4. **Adam turn 3:** *"Can we view Thursday evening?"*
   → `viewing_request` escalation / actionable viewing appears in Today Queue.
5. **In `/agent/conversations/[Adam]`:** read the **brief + next action** (not the raw transcript).
   → Next action: propose viewing slots. Listing snapshot + readiness panel visible.
6. **Propose slots** from the conversation (availability blocks already seeded for L1) → **confirm
   viewing** → **draft + send tenant notice** (L1 is tenant-occupied; Lina is coordinator).
   → Viewing moves to confirmed; tenant/buyer/calendar confirmation states show.
7. **Open `/agent/drafts`:** the **price/viewing follow-up draft** for Adam is ready with verified-fact
   metadata + suggested next question. **Edit one line, Send.**
   → Draft leaves the queue; message + action + compliance event written; conversation timeline updates.
8. **Back on `/agent`:** Today Queue reflects the completed viewing setup + sent follow-up; Adam shows
   as viewing-scheduled. → **Story:** Dalya qualified the buyer, teed up the viewing, and handed Eric a
   ready-to-send follow-up — minutes, not an afternoon.

(Optional offer beat if time: send Adam *"We'd offer 6.4M"* → offer record + escalation to Eric →
Eric reviews from the queue.)

---

## B. STRESS PATH (20–30 min) — "Dalya stays safe under pressure"

Exercises unsafe facts, low-context buyers, a below-threshold offer, human takeover, opt-out, and the
incomplete listing. The story: messy real-world inputs, and Dalya never says something it shouldn't.

1. **Priya (off-plan analytical), L3/L4 Emaar/Sobha off-plan.** Send, one per turn:
   - *"What's the payment schedule and how much is left to pay?"* → answers from SPA-like verified data.
   - *"What are the DLD fees and NOC process? Can I get 80% LTV?"* → **verified facts only**; legal/fee
     uncertainty **escalates** with agent-confirmation language; no invented numbers.
   - *"Can I view the unit this weekend?"* → **no physical-viewing push** (off-plan); offers
     brochure/floor-plan/renders + agent follow-up.
   → Escalation thread for Priya; Verified Facts gate visibly holds.
2. **Low-context buyer, L1.** Send: *"price?"* then *"last price?"* then *"send pics"*.
   → Bot gives price, asks **one** useful qualifying question, does **not** over-qualify; readiness
   stays low/partial; media handled per private-media posture.
3. **Hassan (offer), L1.** Send *"I'll pay 6.1M, firm, today."* → below 6.4M threshold → **offer record
   + firm-offer detection + escalation to Eric**. Then *"ok, 6.35M then."* → offer history shows
   revise-up. In `/agent`, **review offer, add seller counter 6.55M, transition with a note.**
   → Buyer card + conversation reflect full offer history.
4. **Mei (human takeover), L5 luxury.** Send *"can I talk to a real agent? 我想看房"* (mixed language).
   → Escalation + **AI pause**. In conversation detail, confirm **AI paused**, Eric replies via the
   `[Ref: TOKEN]` relay; later **resume AI** (confirmation dialog).
5. **Tom (weak listing L2).** Send *"What's the service charge and is the NOC clear? When can I view?"*
   → Facts are missing/unverified → **"the agent needs to confirm"** language + **escalation**, no
   guessing. Demonstrates safe failure.
6. **Opt-out.** Send *"stop"* from any buyer → **suppression recorded**; that buyer shows opt-out state
   on the card and is suppressed from sends.
7. **Escalation inbox sweep `/agent/escalations`:** threads are **bundled** (no duplicate spam), Eric
   replies to one, relays resolve/update correctly, and one is **manually resolved**.
   → **Story:** under offers, legal questions, language switches, and missing data, Dalya escalated
   correctly and never leaked seller info or stated an unverified fact.

---

## Per-step expected-change ledger (Agent F)
For each numbered step above, F records: dashboard/queue delta, DB rows written (conversation, message,
offer, escalation, viewing, draft, suppression, compliance event), and pass/fail. Mismatches become
findings in `06-DELIVERABLES.md §4`.
