# First-Run Scenario Matrix

Every scenario must produce machine-readable evidence. Browser-facing steps also
need screenshots and action transcript.

## Golden Path - Dalya Working Well

| Scenario | Buyer/listing | Surfaces | Expected result |
| --- | --- | --- | --- |
| G1 Hot ready buyer | Adam Miller, Dubai Hills ready villa | Chatbot mode, DealReadiness, `/agent`, Today Queue, conversation detail, buyer card | Adam becomes hot/viewing-ready; queue item has working href; readiness fields explain why. |
| G2 Viewing request | Adam Miller, ready listing logistics | Conversation detail, viewing APIs, `/agent/viewings`, viewing detail | Slots are proposed/seeded; viewing can be confirmed or limitation is BLOCKED with exact reason. |
| G3 Agent action | Adam escalation or needs-reply | `/agent/escalations?thread=<id>`, conversation detail, draft queue | Eric can reply/resolve or send a draft through simulated path; timeline/action/compliance evidence is captured where implemented. |
| G4 Queue closes cleanly | Adam after action | `/agent`, buyer card, drafts/viewings | Today Queue reflects action; Adam shows scheduled/followed-up state; no fallback rows. |

## Stress Path - Dalya Stays Safe

| Scenario | Buyer/listing | Surfaces | Expected result |
| --- | --- | --- | --- |
| S1 Verified Facts off-plan | Priya Shah, Emaar/Oasis off-plan | Chatbot mode, Verified Facts, escalation/draft assist | Direct answers only for verified safe facts; legal/process/mortgage/NOC uncertainty defers or escalates. |
| S2 Low-context buyer | Unknown buyer, ready listing | Chatbot mode, buyer card | Dalya asks one useful question, does not over-qualify, readiness remains low/partial. |
| S3 Offer buyer | Hassan Ali, ready listing | Chatbot mode, offers API, conversation detail, buyer card | Below-threshold firm offer records/escalates; revised offer updates history; no seller-private leakage. |
| S4 Human takeover | Mei Chen, luxury listing | Chatbot mode, escalation, conversation AI mode | Speak-to-human request escalates; AI pause/resume is visible or BLOCKED with exact reason. |
| S5 Weak listing fact gap | Tom Becker, incomplete ready listing | Verified Facts, escalation, conversation/draft assist | Missing service charge/NOC/access facts are not invented; agent-confirmation language appears. |
| S6 Opt-out | Opt-out buyer | Chatbot/API, suppression state, dashboard/buyer card | Suppression recorded; outbound sends blocked; opt-out state visible or API-proven. |

## Deferred Coverage

These remain valuable but are not required for first-run PASS:

- Lead ingest from Property Finder/Bayut. Listings may still be created from
  Eric-provided Property Finder/Bayut URLs through the agent dashboard's
  `/listings/new/portal` flow before dependent seeding.
- Media/voice.
- Google Calendar live write.
- Full tenant/security sweep.
- Live/sandbox WhatsApp.
- 360dialog/BSP.

## Required Evidence Per Scenario

- Scenario input messages or browser actions.
- Expected state transition.
- Actual response/API/DB summary.
- Browser screenshot for route-backed steps.
- PASS / FAIL / BLOCKED.
- Follow-up ticket recommendation for every failure or blocker.
