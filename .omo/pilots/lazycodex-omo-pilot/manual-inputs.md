# Manual Inputs Required From Eric

The first run has a small set of hard blockers. Everything else can use safe,
generated pilot data.

## Input File

Fill local values in `.omo/pilots/lazycodex-omo-pilot/.env.pilot`.

This file is gitignored. Agents may load it to run pilot commands, but must not
print, copy, summarize, or inspect secret values.

## Hard Blockers

1. **Pilot database target**
   - Preferred: provide a disposable local database or a dedicated Neon test
     branch named `pilot`.
   - Staging is allowed only if you explicitly confirm it is isolated and safe
     for pilot writes.
   - Shared staging must not receive schema creation or DDL.
   - Agents may load an approved test/dev env file to run commands, but must
     not print, copy, summarize, or inspect secrets. Production env files are
     out of scope.
   - Required values:
     - `DALYA_ENV=test|development|pilot`, or explicitly approved isolated
       `staging`
     - `DATABASE_URL=<non-production database>`
     - `PROD_DB_HOST=<production hostname denylist>`
   - Without this, DB-backed seed/API/browser evidence is BLOCKED.

2. **Eric Supabase auth path for browser mode**
   - Provide a Supabase auth user uuid for Eric, plus a way to sign in or obtain
     a JWT/session.
   - Default email if creating one: `eric+dalya-pilot@example.com`.
   - Without this, service/test-context API smoke may still run and must be
     labeled `SMOKE PASS`, but `/agent` browser mode and real Eric auth
     readiness are BLOCKED.

3. **Permission to seed/reset pilot-marked rows**
   - Approve writing clearly marked pilot rows into the test/dev database.
   - Approve a reset script that deletes only rows with the first-run pilot
     marker or `pilot_` ids.
   - Reset must refuse without `DALYA_PILOT_CONFIRM=mahoroba-realty`.
   - Seed/reset may add pilot-marked child rows under canonical
     `mahoroba-realty`, but must not delete or overwrite existing non-pilot
     Mahoroba records, settings, agents, listings, conversations, or
     memberships.

4. **Anthropic key for chatbot mode**
   - Provide `ANTHROPIC_API_KEY` if the first run should exercise the live
     Property Advisor path.
   - Without this, chatbot scenarios are BLOCKED and the run falls back to smoke
     mode where possible.

5. **Listing source links**
   - Provide one Property Finder or Bayut URL in each env variable:
     - `PILOT_LISTING_GOLDEN_READY_URL`
     - `PILOT_LISTING_INCOMPLETE_READY_URL`
     - `PILOT_LISTING_OFFPLAN_URL`
     - `PILOT_LISTING_LUXURY_READY_URL`
   - Full pilot listing pass uses the normal agent dashboard flow:
     `/listings/new` -> `Paste from Property Finder / Bayut` ->
     `/listings/new/portal` -> review draft -> publish.
   - The dashboard uses the existing authenticated scraper API
     `POST /api/v1/listings/draft-from-url` to prefill the form, then
     `POST /api/v1/listings` to publish.
   - Direct API/script listing creation is diagnostic or smoke evidence only;
     it cannot satisfy the full listing-creation pass.
   - Set `PILOT_LISTING_IMPORT_MODE=api` for live dashboard scraper import,
     `snapshot` for frozen harness-style scrape snapshots if live scraping is
     blocked, or `manual` if the links cannot be scraped and listing facts must
     be entered by hand in the dashboard.
   - If a Bayut live import needs RapidAPI fallback, fill `BAYUT_RAPIDAPI_KEY`.

## Approved Defaults Unless You Override

1. **Brokerage**
   - Use existing canonical brokerage id `mahoroba-realty`.
   - Display name: `Mahoroba Realty`.
   - DLD office number: use existing repo value/placeholder unless you override.

2. **Tracking**
   - Use one umbrella Linear issue before execution if Linear is available.
   - If external SaaS writes are blocked, record one umbrella tracking item in
     `BACKLOG.md` and continue.
   - Do not create per-subtask ticket sprawl before the first rehearsal.

3. **Messaging**
   - First run uses `MESSAGING_TRANSPORT=simulated`.
   - No live WhatsApp.
   - No Twilio production send.
   - No 360dialog/BSP.

4. **Agents**
   - Eric: main agent and admin-capable pilot user.
   - Sara Khan: senior agent, Dubai Hills / ready villas.
   - Omar Haddad: off-plan specialist, Emaar / waterfront projects.
   - Lina Petrova: viewing coordinator, tenant coordination.
   - Supporting agents may be data-only if only Eric logs into `/agent`.

5. **Listings**
   - Prefer the four Property Finder/Bayut links from `.env.pilot`.
   - Create listings through `/listings/new/portal` for:
     - Dubai Hills ready villa.
     - Dubai Hills incomplete ready listing.
     - Emaar/Oasis off-plan listing.
     - Luxury/high-ticket ready listing.
   - If scraper import is blocked, use `snapshot` mode where available, then
     `manual` mode as dashboard fallback. Do not invent portal-only facts that
     were not scraped, shown in the draft, or explicitly provided.
   - You may still override title, community, price, threshold, seller notes,
     buyer-safe facts, agent-only notes, media, logistics, or payment schedule
     inside the env-backed pilot seed notes.

6. **Buyers**
   - Generate safe first-run pilot buyers:
     - Adam Miller.
     - Priya Shah.
     - Low-context buyer.
     - Hassan Ali.
     - Mei Chen.
     - Tom Becker / weak-listing buyer.
     - Opt-out buyer.
   - Fake UAE-style phone numbers are OK unless you specify otherwise.

7. **Demo length**
   - Golden path: 10-15 minutes.
   - Stress path: 20-30 minutes.

## Explicitly Not Needed For First Run

- Real customer data.
- Real live WhatsApp numbers.
- 360dialog access.
- Google Calendar OAuth account for live writes.
- Media/voice sample audio.
- Lead ingest provider credentials.
- Production RLS/app-role approval.

## Fastest Approval Reply

Provide:

1. Fill `.omo/pilots/lazycodex-omo-pilot/.env.pilot`.
2. Disposable local DB or dedicated Neon `pilot` branch `DATABASE_URL`.
3. `PROD_DB_HOST`.
4. Four Property Finder/Bayut listing URLs.
5. Eric Supabase uuid/JWT or login path.
6. `ANTHROPIC_API_KEY` if chatbot mode should run.
7. "Approve generated buyer data and pilot-marked seed/reset."
