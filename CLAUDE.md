# Dalya AI — Project Context for Claude

## Project
**Dalya is software — B2B AI infrastructure for Dubai real estate brokerages.** It gives individual agents tools to handle buyer conversations, run viewings, acquire listings, and close deals more efficiently. It gives brokerage owners visibility into team performance, pipeline health, and listing acquisition. FastAPI backend, Next.js + Tailwind v4 frontend, Anthropic Claude for the buyer-facing Property Advisor, document parsing, and the workflow intelligence layer.

**Dalya is not RERA-licensed — software can't be.** Every transaction on the platform sits under the RERA licence of the brokerage that owns the listing. Mahoroba Realty is one such brokerage on the platform — brokerage #1 in the seed data, and Eric's existing operation — but it is one tenant among many, not the regulatory umbrella for Dalya itself. New brokerages (Irwin Real Estate, Luqman's brokerage, and others added by the platform admin) each onboard their own agents under their own RERA office.

Customer one (current design partner): **Luqman's brokerage**. 60–90 day design partnership with agent stickiness as the success criterion. Pricing is deferred until stickiness is proven.

## Product positioning — empowerment, not replacement
Dalya does the work agents shouldn't be doing (initial buyer qualification, repetitive questions, midnight WhatsApp replies, viewing coordination overhead) so agents can do the work they should be doing (closing deals, managing relationships, navigating negotiations). The metric the brokerage owner is steered toward is **revenue per agent**, not number of agents on payroll. The product must visibly augment agents, not visibly replace them.

## Design Context

### Users
**Individual agents (primary users)** — entry-level agents and team leads working at the brokerages we sell to. Mobile-first, WhatsApp-adjacent workflow. Daily-use surface for hours at a stretch. Trust trigger: the tool actually closes more deals for them and makes their day easier; never replaces them. Calm enough to live in for four hours straight.

**Brokerage owners (secondary users, the buyer of the product)** — Luqman-shaped: owners of small-to-medium Dubai brokerages who care about team performance, listing acquisition, and revenue per agent. Primarily desktop, 2–4 hours daily of sustained data work. Dense, analytical, dashboard-grade. Trust trigger: real telemetry on agents and listings; RERA+PDPL compliance audit trail; clear demonstration of revenue lift per agent.

**Buyers (consumed via the bot, not customers)** — UAE-based qualified buyers who message via WhatsApp or portal-embedded chat. The bot answers them on the agent's behalf, governed by `BOT_RULES.md`. Multilingual (EN/AR/RU/HI/Mandarin). Not the buyer of the product. Their experience matters because it reflects on the agent and the brokerage.

**Brokerage operational staff (tertiary)** — office managers, support staff, paperwork-only workers who handle post-offer flow (NOC, MOU, trustees, Trakheesi). Same surface as agents, lower priority on Phase 3 build.

### Brand attributes (priority order)
**Trustworthy. Calm. Sharp.** Defined operationally in `brand/01-foundations.md`. Replaces the previous "Precise. Inviting. Modern." consumer-marketing triplet.

### Aesthetic direction
**Light-default with parallel dark mode** (per `brand/PHASE-2-LOCK.md`). Slate-blue accent, neutral-scale workhorse, semantic colors only when status is actually meaningful. Closest references: **Attio** for product surface, **Notion** for white-space discipline, **Linear** for color discipline. Quiet-by-omission posture — no decorative ornament, no Dubai-themed exoticization, no luxury PropTech residue.

**Anti-references:** Property Finder / Bayut crowded UI, generic SaaS pastel, tech-bro brutalism, the previous consumer-marketing dark-luxury Dalya.

### Token Reference
The complete locked token system is in `brand/applications/_tokens.css`. Top-level summary:
```
Primary brand:   --color-brand-500   #3D5A80   (slate blue — wordmark, focus rings, links, selected, secondary primary)
Top-tier CTA:    --color-brand-600   #324B6B   (deeper slate — reserved for 3–5 brand-critical CTAs only)
Success:         --color-success-500 #4A7C6F   (sage — NOC eligible, verified, live status)
Warning:         --color-warning-500 #B7793A   (copper — NOC pending, countered offer)
Error:           --color-error-500   #B84838   (bank-grade brick red — destructive, blocked)
Surface (light): --color-surface-0   #FAFAF9   (page) / --color-surface-1 #F4F4F2 (card) / --color-surface-2 #E8E8E5 (recessed)
Text (light):    --color-text-1      #3D3D39   (body) / --color-text-2 #5C5C57 (secondary) / --color-text-3 #7B7B76 (muted)

Fonts: Inter Variable (UI), IBM Plex Mono (code / RERA IDs only), IBM Plex Sans Arabic (Arabic content), Noto Sans Devanagari (Hindi)
RTL: required; use logical CSS properties (margin-inline, padding-inline-start, etc.) — Tailwind v4 ms-/me-/ps-/pe-
```

**Retired tokens (do not use):** `#C9A96E` gold (fully retired — product, marketing, wordmark), Plus Jakarta Sans, JetBrains Mono on AED figures.

### CTA Standards (do not deviate)
- Top-tier CTAs (3–5 across product): `bg-brand-600`. Examples: "Upload SPA," "Accept offer," "Send to managing agent," "Confirm destructive."
- Secondary primary CTAs: `bg-brand-500`.
- AI naming: **Dalya** or **Property Advisor** when speaking inside any product surface. **"Dalya's Property Advisor"** is acceptable in buyer-facing copy on portal listing pages and WhatsApp opener templates (the bot speaks *to* a buyer about *itself*). Never "chatbot," "bot," "AI assistant."
- Agent and brokerage-owner CTAs are operational verbs first (Send · Forward · Accept · Counter · Approve), not marketing copy.

### Required Brand Elements (every public page)
- Marketing trust framing: **Dalya is AI infrastructure for Dubai brokerages — every listing on the platform is operated by a RERA-licensed brokerage.** Do not put a "RERA Licensed · Mahoroba Realty" trust bar across the marketing site (Dalya isn't the licensee). Where regulatory attribution is needed on a specific listing surface, attribute it to that listing's brokerage.
- AED amounts always use Inter tabular-nums with the slashed-zero stylistic set (`font-feature-settings: "tnum", "ss01"`)
- The wordmark "dalya" renders in slate-blue `#3D5A80`, at 80% opacity in dense product chrome and 100% on signed-out / marketing surfaces
- Empty states say what's not here and what next; never "Coming soon" or "Oops!"

## Data integrity note
The "15-25% resale premium" figure is sourced from `knowledge_base/emaar_oasis.json` for branded Emaar Oasis villas only and must not be introduced via the prompt for other listings.

**Off-plan vs ready properties:** the product scope has expanded beyond off-plan resale to include ready-property resale. Document layer now needs to handle title deed, Ejari, service charge statements, NOC, valuation reports, snagging reports, and mortgage paperwork in addition to SPA. The bot's persona must distinguish off-plan and ready-stock questions correctly — off-plan questions stay payment-plan/NOC-anchored; ready questions become noise/neighbor/AC/view/parking-anchored.

**First-turn identity rule**: Introduce as Dalya unless the buyer's opening message is a transactional demand without greeting (typical spam-offer pattern). In those cases, anchor against the offer first; identity can be introduced later. The bot identifies *itself* as Dalya the Property Advisor; the *listing's brokerage* (resolved per-listing from `DBListing.brokerage_id`) is named on regulatory/legal surfaces and on first-mention of the listing's managing agent per `BOT_RULES.md`.

## Where to find the rest
The complete brand system is in `brand/`:
- `BRAND.md` — start here; canonical reference
- `STRATEGIC-PIVOT-2026-05-15.md` — why we pivoted; permanent record
- `01-foundations.md` through `08-voice-tone.md` — Phase 1 + 2 detail
- `applications/` — six locked HTML mockups + the production-ready token CSS

Bot voice (buyer-facing) is in `BOT_RULES.md` at the repo root. Product voice (agent-facing) is in `brand/08-voice-tone.md`. They share posture, diverge in register.

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
  --provider claude \
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

When Eric asks for any of these reviewers, use the relevant files as reviewer instructions and stay in review-only mode unless explicitly asked to implement fixes:

- Chatbot Master: `dalya-reviewers/chatbot-master/`
- Real Estate Guru: `dalya-reviewers/real-estate-guru/`
- UX Designer: `dalya-reviewers/ux-designer/`
- Security Researcher: `dalya-reviewers/security-researcher/`

Always read first:

- `dalya-reviewers/shared-context.md`
- `dalya-reviewers/review-session-rules.md`
- `dalya-reviewers/file-routing.md`
- `dalya-reviewers/templates/review-output-template.md`

Claude Code project subagents are installed in `.claude/agents/`:

- `dalya-chatbot-master`
- `dalya-real-estate-guru`
- `dalya-ux-designer`
- `dalya-security-researcher`

Reusable command prompts live in `dalya-reviewers/commands/`.

Default behavior: do not modify code during review. Return prioritized findings and Linear-ready tasks.

<!-- DALYA_REVIEWERS_END -->
