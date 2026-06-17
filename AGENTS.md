# Dalya AI — Project Context for Codex

## Project
**Dalya is B2B AI infrastructure for Dubai real estate brokerages.** It gives existing brokerages and their agents software for buyer conversations, lead qualification, smart escalation, follow-up drafts, viewing logistics, ready-property knowledge, offer context, and agent performance visibility.

Dalya is software, not the licensed brokerage. Every transaction sits under the RERA licence of the brokerage that owns the listing. Mahoroba Realty is one tenant and seed brokerage, not Dalya's regulatory umbrella. New brokerages onboard their own listings, agents, and compliance context.

Customer one is **Luqman's brokerage**. The first success criterion is agent stickiness during a 60-90 day design partnership; pricing comes after proof that agents use it daily.

Primary stack: FastAPI backend, Next.js + Tailwind v4 frontend, Postgres/Supabase-style data layer, Anthropic/LLM-powered buyer-facing Property Advisor, document parsing, and workflow intelligence.

## Product Direction

Build from the agent's daily workflow outward. Do not drift back into the pre-pivot consumer-direct Mahoroba marketplace unless Eric explicitly asks for legacy or archived surfaces.

Active MVP surfaces:

1. **24/7 Inquiry Concierge** — multilingual buyer WhatsApp/portal inquiry handling, buyer qualification, voice-note transcription, document-grounded property answers, and safe handoff.
2. **Smart Escalation to Agents** — Brokerage AI escalates serious or unanswerable buyer questions to Agents AI; agents reply through WhatsApp `[Ref: TOKEN]` relay or the dashboard composer.
3. **Morning Hot List + Follow-Up Engine** — ranked active buyers, deduped tasks, review-only follow-up drafts, and notification preferences.
4. **Viewing Logistics Automation + Pre-Viewing Report** — ready-property logistics, slot proposal, tenant/buyer coordination, Google Calendar, reminders, post-viewing feedback, and follow-up drafts.
5. **Agent Workspace** — `/agent` is the active product entry: conversations, escalations, drafts, buyers, offers, viewings, calendar, notifications, and personal performance.

Deferred or maintenance surfaces:

- Brokerage owner dashboards, owner rollups, broad CRM, owner outreach/campaigns, AI buyer matching as a launch surface, Mandarin production support, and advanced route optimization are deferred.
- Legacy consumer-direct seller/buyer marketplace surfaces remain only for maintenance, demos, or reference unless explicitly requested.

## Users

**Individual agents (primary daily users):** Dubai real estate agents at customer brokerages. Mobile-first, WhatsApp-adjacent, time-poor, deal-focused. Trust trigger: Dalya helps them respond faster, miss fewer serious buyers, coordinate viewings, and close cleaner deals without threatening their role.

**Brokerage owners/team leads (customers and later admin users):** Small-to-medium Dubai brokerage leaders who care about revenue per agent, pipeline health, listing quality, compliance, and team visibility. Owner dashboards are later than the MVP agent workflow.

**Buyers (consumed via the bot, not customers):** UAE-based buyer leads arriving through WhatsApp, portal forms, or listing channels. The Property Advisor speaks on behalf of the listing's brokerage/agent and must stay factual, brief, and specific.

**Operational staff (secondary):** Admins or coordinators supporting viewings, paperwork, NOC/MOU/trustee workflows, and compliance.

## Product Positioning

Dalya augments agents. It handles the work agents should not be doing manually: repetitive buyer questions, midnight first replies, qualification, follow-up nudges, viewing coordination overhead, and summary/admin work. It should never frame itself as replacing agents or reducing headcount. The product language should make agents feel sharper, better briefed, and faster.

## Brand And Design Context

Brand attributes, in priority order: **Trustworthy. Calm. Sharp.**

Design posture: quiet operational software, not luxury brokerage marketing. Product surfaces should feel closer to Attio/Linear/Notion discipline than Property Finder/Bayut clutter or Dubai real-estate brochure design. Use dense but readable information hierarchy, restrained color, clear task states, and mobile-practical workflows.

Locked visual direction:

```
Primary brand:   #3D5A80   slate blue
Top-tier CTA:    #324B6B   deeper slate
Success:         #4A7C6F   sage
Warning:         #B7793A   copper
Error:           #B84838   brick red
Surface light:   #FAFAF9 / #F4F4F2 / #E8E8E5
Text light:      #3D3D39 / #5C5C57 / #7B7B76

Fonts: Inter Variable, IBM Plex Mono for code/RERA IDs only, IBM Plex Sans Arabic, Noto Sans Devanagari
RTL: required; use logical CSS properties (`margin-inline`, `padding-inline-start`, Tailwind `ms-`/`me-`/`ps-`/`pe-`)
```

Retired pre-pivot style: navy/gold dark-luxury marketplace, `#C9A96E` gold, Plus Jakarta Sans, JetBrains Mono on AED figures, "Property intelligence. No pressure.", Mahoroba-as-platform trust bars.

CTA and naming standards:

- Product CTAs are operational verbs: Send, Forward, Approve, Reject, Snooze, Resolve, Confirm, Counter, Accept.
- Top-tier CTAs are rare and use the locked slate system, not gold.
- AI naming: **Dalya** or **Property Advisor**. "Dalya's Property Advisor" is acceptable in buyer-facing copy. Do not call it a chatbot/bot/AI assistant in product copy.
- Public trust framing: Dalya is AI infrastructure for Dubai brokerages. Regulatory attribution belongs to the listing's brokerage, not to Dalya globally.

## Data Integrity Notes

The "15-25% resale premium" figure is sourced from `knowledge_base/emaar_oasis.json` for branded Emaar Oasis villas only and must not be introduced via the prompt for other listings.

The product now covers off-plan and ready-property resale. Ready-property document workflows include title deed, Ejari, service charge statements, NOC, valuation reports, snagging reports, and mortgage paperwork in addition to SPA. The bot must distinguish off-plan payment/NOC questions from ready-property tenancy/noise/view/parking/AC questions.

**First-turn identity rule:** introduce as Dalya unless the buyer's opening message is a transactional demand without greeting. For spam-offer-style openers, anchor against the offer first; identity can come later. The bot identifies itself as Dalya/Property Advisor; the listing brokerage is resolved per listing and named on regulatory/legal surfaces and managing-agent handoff where appropriate.

## Where To Find The Rest

- Current project truth: `PROJECT_BRIEF.md`
- Active backlog and shipped work: `BACKLOG.md`
- Bot voice: `BOT_RULES.md`
- Product voice and brand system: `brand/`
- MVP roadmap: `MVP_ROADMAP_0609.md`, `GOAL_SPEC_0610.md`
- Product decisions: `docs/adr/`

## App Navigation Architecture

Multi-step product flows must be route-backed. Each meaningful screen or decision point gets its own path so the app/browser Back button returns the user to the previous page they were on.

- Do not rely on in-component step state for primary navigation between screens.
- Do not add duplicate inline "back", "change path", or "previous step" controls when the global app Back button can handle the flow.
- Use links or router navigation that creates normal history entries for choices and branch points.
- Keep temporary in-component state only for fields within a single screen, not for replacing page-level route changes.

## Delivery Tracking

Every meaningful feature, bug fix, behavior change, schema change, harness change, or product decision must have corresponding Linear ticket(s) before implementation work starts, and the delivered status must be reflected in `BACKLOG.md`. Keep ticket descriptions actionable: purpose, implementation actions, and confirmation criteria. If a change is too small for a standalone ticket, attach it to the nearest active Linear issue and name that issue in the backlog/update notes.

<!-- BEGIN:command-center-activity-logging -->
## Command Center Activity Logging

This project reports meaningful work to the Command Center dashboard.

- Project: Dalya
- Dashboard project slug: `dalya`
- Command Center path: `/Users/eric/command-center`

After completing any meaningful feature, fix, bug investigation, review, strategy change, research, marketing/distribution/ads/ops task, or other key event, add a structured activity record before the final response:

```bash
COMMAND_CENTER_WORKING_DIR="$PWD" npm --prefix /Users/eric/command-center run activity-log -- \
  --project dalya \
  --title "Short outcome title" \
  --work-type coding \
  --labels feature,bugfix \
  --purpose "Why this work mattered" \
  --process "What was done or investigated" \
  --outcome "What changed and what the result was"
```

Use `--sync` only when Supabase env vars are configured and the event should be imported immediately.

If an event pattern is repetitive or continuously contributes to the agentic workflow, design an automatic capture path instead of relying on manual logging. Prefer scripts, hooks, watchers, or scheduled sync jobs.

For live telemetry events, use `agent-log` from this project directory:

```bash
COMMAND_CENTER_WORKING_DIR="$PWD" npm --prefix /Users/eric/command-center run agent-log -- \
  --provider codex \
  --type code_changed \
  --work-type coding \
  --labels feature \
  --title "Short event title" \
  --body "Concise event detail"
```
<!-- END:command-center-activity-logging -->

<!-- BEGIN:command-center-project-brief -->
## Project Brief Maintenance

Keep `PROJECT_BRIEF.md` as the living 5-minute overview of this project for a smart outside reader. Update it whenever meaningful work changes or clarifies the mission, current product, features built, ongoing work, backlog, users/customers, positioning, marketing/distribution plan, key decisions, important artifacts, or open questions.

Do not put the full product brief in `AGENTS.md` or `CLAUDE.md`. These files are for agent operating instructions; `PROJECT_BRIEF.md` is for human-readable product context.
<!-- END:command-center-project-brief -->


<!-- DALYA_REVIEWERS_START -->

## Dalya Reviewer Agents

Dalya reviewer instructions live in `dalya-reviewers/`.

When Eric asks for any of these reviewers, treat the relevant files as reviewer instructions and stay in review-only mode unless explicitly asked to implement fixes:

- Chatbot Master: `dalya-reviewers/chatbot-master/`
- Real Estate Guru: `dalya-reviewers/real-estate-guru/`
- UX Designer: `dalya-reviewers/ux-designer/`
- Security Researcher: `dalya-reviewers/security-researcher/`

Always read first:

- `dalya-reviewers/shared-context.md`
- `dalya-reviewers/review-session-rules.md`
- `dalya-reviewers/file-routing.md`
- `dalya-reviewers/templates/review-output-template.md`

Reusable commands live in `dalya-reviewers/commands/`.

Codex project-scoped custom agents are installed in `.codex/agents/`:

- `dalya_chatbot_master`
- `dalya_real_estate_guru`
- `dalya_ux_designer`
- `dalya_security_researcher`

Default behavior: do not modify code during review. Return prioritized findings and Linear-ready tasks.

<!-- DALYA_REVIEWERS_END -->
