# LazyCodex / OMO Pilot - Dalya Mahoroba First Run

This folder is the control folder for Dalya's first internal MVP pilot
rehearsal. It is planning and coordination material only. Product code execution
starts only after Eric explicitly says to start work.

## Final Direction

Use the hybrid direction Eric approved:

- **Claude plan as spine:** canonical `mahoroba-realty`, real Supabase/JWT
  constraints, `SimulatedTransport`, `scripts/pilot/`, actual `/agent` route
  tree, and repo-grounded endpoint/test references.
- **Codex product framing:** answer whether Eric can demo Dalya as a daily
  command center, with golden path and stress path verdicts.
- **LazyCodex execution discipline:** wave-based ownership, evidence-first
  acceptance, final verification, no commits unless authorized.

## What The First Run Proves

The first run answers:

- Can Eric open `/agent` and know what to do next within about 30 seconds?
- Does Today Queue surface realistic work from pilot data, not fallback rows?
- Can a hot ready buyer move from inquiry to readiness/viewing/draft/action?
- Does Dalya fail closed on off-plan/legal/process/fact gaps?
- Do conversations, buyer cards, drafts, escalations, offers, and viewings feel
  like one coherent agent workflow?

## First-Run Scope

- Brokerage: existing canonical `mahoroba-realty`.
- Listings: 4, created through the normal agent dashboard flow at
  `/listings/new/portal`.
  - Dubai Hills ready villa from `PILOT_LISTING_GOLDEN_READY_URL`.
  - Dubai Hills incomplete ready listing from
    `PILOT_LISTING_INCOMPLETE_READY_URL`.
  - Emaar/Oasis off-plan listing from `PILOT_LISTING_OFFPLAN_URL`.
  - Luxury/high-ticket ready listing from `PILOT_LISTING_LUXURY_READY_URL`.
- Buyers: 7.
  - Adam Miller.
  - Priya Shah.
  - Low-context buyer.
  - Hassan Ali.
  - Mei Chen.
  - Tom Becker / weak-listing buyer.
  - Opt-out buyer.
- Core surfaces:
  - `/agent`
  - Today Queue
  - conversations
  - buyer list/card
  - drafts
  - escalations
  - offers in conversation/buyer context
  - viewings

## Deferred From First Run

- Lead ingest.
- Media/voice.
- Google Calendar live write.
- Full tenant/security sweep.
- Live WhatsApp/Twilio production sends.
- 360dialog/BSP.
- Production RLS/app-role rollout.
- Owner/admin/campaign/legacy marketplace polish.

## Key Artifacts

- Local pilot env: `.omo/pilots/lazycodex-omo-pilot/.env.pilot`
- Formal OMO plan: `.omo/plans/dalya-internal-omo-pilot.md`
- Planner draft: `.omo/drafts/dalya-internal-omo-pilot.md`
- Manual inputs: `.omo/pilots/lazycodex-omo-pilot/manual-inputs.md`
- Agent lanes: `.omo/pilots/lazycodex-omo-pilot/agent-lanes.md`
- Scenario matrix: `.omo/pilots/lazycodex-omo-pilot/scenario-matrix.md`
- Report template: `.omo/pilots/lazycodex-omo-pilot/report-template.md`

## Execution Modes

- **Smoke mode:** seed/API checks, and browser checks only when auth exists,
  without chatbot scenarios if no Anthropic key is available. API checks run
  without Eric JWT using service/test context must be marked `SMOKE PASS`, not
  full `PASS`.
- **Chatbot mode:** Property Advisor scenario runner; requires
  `ANTHROPIC_API_KEY`.
- **Browser mode:** `/agent` as Eric; requires Supabase auth/JWT/session path.
- **Live/sandbox transport mode:** not part of first run; separate approval.

The final report must show Smoke mode yes/no, Chatbot mode yes/no, Browser mode
yes/no, and the full first-run verdict based only on the modes actually run.

## Verdict Thresholds

- Green: Browser mode + chatbot mode + API smoke all pass for the golden path,
  and stress path has no unsafe claims.
- Yellow: Golden path is demo-able, but some stress/API/browser items are
  blocked or rough.
- Red: `/agent` cannot load real pilot data, fallback rows appear, unsafe
  claims leak, or agent actions cannot be completed.

## Default Execution Shape

1. Create or attach one umbrella Linear issue if available; if blocked, record
   one umbrella tracking item in `BACKLOG.md` and continue.
2. Run Phase 0 safety gate.
3. Create the four listings as Eric through `/listings/new/portal`: paste each
   `.env.pilot` Property Finder/Bayut URL, review the scraper-prefilled draft,
   publish, and capture the listing ids.
4. Seed dependent Mahoroba pilot buyers/conversations/drafts/offers/viewings
   against the dashboard-created listing ids with surgical reset.
5. Run simulated buyer scenarios.
6. Run pilot-critical API smoke.
7. Run `/agent` browser walkthrough as Eric.
8. Run golden and stress rehearsal.
9. Run minimal safety sanity.
10. Produce one report with verdict, matrix, evidence, blockers, and next tickets.
