## Context

The chatbot currently exists as a single-tenant internal tool for Mahoroba Realty. It has hardcoded fee rules (the 0.2% commission), references to Eric as the escalation contact, and only surfaces listings that have been SPA-parsed for Mahoroba. All tenancy is implicit — everything is "Mahoroba's."

We are pivoting to B2B AI infrastructure for Dubai brokerages and their agents. Each brokerage has its own listing database, its own agents, its own fee structures, and (eventually) its own pair of WhatsApp numbers. This goal migrates the system from single-tenant internal tool to multi-tenant platform, and builds the agent-facing portal that lets agents register and list properties.

## In scope for this goal

(a) Multi-tenancy refactor — scope all listing data and chatbot logic by brokerage and by agent.
(b) Agent portal — registration (gated on an approved brokerage, RERA-number-driven), dashboard, and a Create Listing page supporting both off-plan and finished properties.

Build the full two-chatbot-per-brokerage architecture (Brokerage AI buyer-facing + Agents AI agent-facing) in the data model and routing logic so it is fully simulatable now, with live WhatsApp transport stubbed behind a clean interface.

## Explicitly deferred (do NOT build live in this goal)

- Live WhatsApp Business API integration (360dialog transport). We are waiting on WABA approval. Build everything as if it were live, against a messaging-transport interface, with a simulated implementation for testing.
- Public/private fee toggle (fees are public for now; see below).
- Brokerage-admin role (agent role only for now; note the admin role as a future addition, do not build it).
- Public self-serve registration (registration is gated on a pre-approved brokerage).

## Data model changes (multi-tenancy)

Shared backend, row-level multi-tenancy. Specifically:

- Every listing carries a `brokerage_id` and an `agent_id` (the managing agent). The managing agent is a required field and is the routing key for escalations.
- Agent profiles are stored under a brokerage and contain at minimum: RERA broker number (BRN), name, phone number, and any other fields returned by the RERA endpoint. The agent's phone number is the address escalations ultimately reach.
- Each brokerage record carries two number fields mirroring the target architecture: `brokerage_ai_number` (buyer-facing) and `agents_ai_number` (agent-facing). These may hold placeholder/simulated values for now, but the schema and routing must treat them as real.
- Community research is GLOBAL/shared across all brokerages (keep the existing data/<developer>/ structure, e.g. data/emaar/, data/sobha/). Listing data is tenant-scoped.
- Agents can append PRIVATE, agent-scoped remarks to a community (e.g. their own sales data they don't want shared). These remarks must be visible only to that agent and never leak to other agents or other brokerages. The chatbot may use them only when serving that agent's listings.
- Brokerage resolution at runtime: an inbound buyer message arrives on a brokerage's `brokerage_ai_number`; that number maps to the brokerage; all listing queries scope to that brokerage's listings.

## Agent portal

Auth already exists (login/signup screens are present). Reuse it.

Registration:
- There is an existing list of approved brokerages (currently Mahoroba Realty and Irwin Real Estate).
- An agent registers only if their brokerage is already approved. The agent enters their RERA number; call the existing live RERA endpoint to prefill their profile (name, BRN, etc.). The agent is then associated with their brokerage.

Create Listing page:
- Common fields (both paths): property type, community, building/project, unit number, bedrooms, size, asking price, notification threshold (see escalation logic), managing agent, commission rate, and an arbitrary list of additional fee line items (e.g. document processing, POA). The notification threshold is internal-only and must NEVER be disclosed to buyers.
- Off-plan path: SPA upload, which triggers the existing SPA parser flow. Keep this flow as-is.
- Finished path: the agent pastes a Property Finder or Bayut listing URL. Scrape the listing's data and images and PREFILL a draft Create Listing form with as much as possible. The agent reviews, corrects, and confirms before the listing goes live (scraping populates a draft; it is never published unreviewed). Scraping must fail gracefully — partial or failed scrapes fall back to a manual-entry form pre-filled with whatever was retrieved. Title deed is collected as a stored reference document (low structured value; may be removed later). Service charge statements and DEWA bills can also be uploaded as reference context the Property Advisor can draw on.
- When a listing is created in a community we have no research on, trigger the existing community research agent (keep this behavior). If no community research exists yet, the listing still goes live with listing-specific data; missing community data is simply absent and never blocks publishing.

Fees:
- Fees and commission are PUBLIC — the Property Advisor may disclose them to buyers when asked.
- Add a code note that a future feature will let agents toggle fee visibility public/private. Do not build the toggle.

## Chatbot / escalation logic

Preserve the existing conversational engine, tone, adversarial defense, and all agent/behavioral rules unchanged (see Preserve list). The only things that change are: who the brokerage and agents are, the per-listing fee structures, and how escalations route.

Escalation routing:
- A buyer chats with the brokerage's Brokerage AI (buyer-facing). When an escalation triggers, it routes to that brokerage's Agents AI (agent-facing), and from there to the SPECIFIC managing agent of the listing in question (resolved via the agent_id on the listing → that agent's registered phone number). The Agents AI number is shared per brokerage, so the escalation must be addressed/tagged to the correct individual agent. No fallback agent is needed.
- The managing agent responds via Agents AI, and the response relays back into the original buyer conversation on the Brokerage AI thread.

Offer-handling escalation logic (new). For a listing with asking price A and notification threshold T, where the near-threshold band is 5% of the threshold (0.05 × T):
- Offer below (T − 0.05×T): handle gracefully, acknowledge the offer, signal it's below where the seller is, DO NOT escalate. (Example: asking 5M, threshold 4.5M, offer 4M → handled, not escalated.)
- Offer within 5% below threshold, i.e. in [T − 0.05×T, T): handle gracefully and acknowledge to the buyer EXACTLY as in the band above (buyer experience is identical), but escalate to the managing agent with a "near threshold" tag. (Example: offer 4.3M → handled gracefully to buyer, escalated with near-threshold tag to agent.)
- Offer at or above threshold (≥ T): escalate directly to the managing agent, no special tag. (Example: offer 4.5M, 4.8M, 5M → escalated.)

The buyer experience across the bottom two bands is identical; the escalation behavior diverges silently behind the scenes. The buyer must never learn the threshold or whether their offer crossed the near-threshold line.

These offer triggers are ADDITIVE to the existing escalation triggers (low bot confidence, sensitive questions, explicit human requests, etc.), which all remain in place.

## Messaging-transport stub (the seam for deferred WhatsApp)

Draw the stub boundary at the messaging-TRANSPORT layer, not in business logic. Define a clean messaging-provider interface that the routing and escalation logic call. Provide:
- A real (360dialog) implementation, stubbed/unimplemented for now.
- A simulated implementation used by the test script.
All routing, escalation, and relay logic must run through the SAME interface in both cases, so the real WhatsApp provider can later be swapped in with zero changes to business logic.

## Preserve (do NOT change)

- All conversational guidelines and tone. No em-dashes. No reflexive closing questions, no affirmation openers, no repetitive name use, humanly-helpful-not-perfectly-helpful style.
- Adversarial defense and all existing safety/agent rules.
- The existing SPA parser flow for off-plan.
- The community research agent and its trigger behavior.
- The global community knowledge base structure.
- The existing model tier allocation (Haiku for the high-volume chatbot, Sonnet for SPA parsing, etc.).
- The existing auth/login/signup screens and the 20 test personas (persona questions will be modified later — not in this goal).

## Branding

- The app is now light-colored with a slate primary color. Apply this throughout.
- All USER-FACING copy refers to the system as "Property Advisor" — never "chatbot."

## Data migration

- Existing Mahoroba listing data migrates into the new multi-tenant structure as brokerage = Mahoroba Realty, agent = Eric.
- Remove the hardcoded 0.2% commission and all references to Mahoroba-as-the-only-tenant and Eric-as-the-universal-escalation-contact. Migrated Mahoroba listings get per-listing fee fields populated with sensible defaults (or flagged for Eric to complete).
- There must be NO remaining references anywhere to Mahoroba as the sole brokerage, the 0.2% fee, or Eric as the global escalation target. Mahoroba becomes simply brokerage #1 among many; Eric becomes simply the managing agent on the migrated listings.

## Simulation script (build, but do not run live)

After implementation, write a script that simulates the full flow against the simulated messaging provider:
- Stands up seed fixtures: at least two brokerages (Mahoroba Realty and Irwin Real Estate), several agents under each (with RERA-style profiles), and several listings each — a mix of off-plan (SPA flow) and finished (PF/Bayut-scrape flow).
- Simulates fake buyer WhatsApp numbers messaging a brokerage's Brokerage AI and asking questions about that brokerage's listings.
- Exercises the Property Advisor returning community research plus listing-specific data (asking price, fees).
- Exercises all three offer bands (below, near-threshold, at/above) and verifies the correct handle-vs-escalate behavior and the near-threshold tag.
- Exercises escalation: from the buyer query → Brokerage AI → Agents AI → the correct managing agent of that specific listing → agent response → relay back to the originating buyer number.

## Acceptance criteria

The goal is complete when:
1. The project compiles correctly and matches the new branding (light app, slate primary, "Property Advisor" in user-facing copy).
2. An agent whose brokerage is pre-approved can register by entering their RERA number (info prefilled via the live RERA endpoint), open the dashboard, and create BOTH an off-plan listing (SPA flow) and a finished listing (PF/Bayut URL scrape → draft → confirm).
3. A simulated buyer querying a listing receives the community research plus that listing's asking price and (public) fees.
4. An offer below the near-threshold band is handled-not-escalated; an offer within 5% below the threshold is handled gracefully to the buyer but escalated with a near-threshold tag; an offer at or above threshold is escalated directly.
5. An escalation routes to the correct managing agent of the queried listing via the brokerage's Agents AI, the agent can respond, and the response relays back to the original buyer.
6. All routing runs through the messaging-transport interface so live WhatsApp can be swapped in later with no business-logic changes.
7. No references remain to Mahoroba-as-sole-brokerage, the 0.2% fee, or Eric-as-universal-escalation. Existing Mahoroba data is present as brokerage = Mahoroba Realty, agent = Eric.
8. The simulation script exists and is ready to run (do not run it live as part of this goal).