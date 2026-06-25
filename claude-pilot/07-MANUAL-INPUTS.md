# 07 — Manual Inputs (what Eric must provide / approve)

Every item has a **safe default** the agents will use if you don't answer — so you can approve the
whole list in one pass and only override what you care about. Items marked **⛔ BLOCKER** have no safe
default and genuinely gate a DB-backed / browser run.

---

## ⛔ Hard blockers (no safe default — needed to actually run)

1. **Test/staging database** — a Neon **test branch** connection string (`DATABASE_URL`) plus the
   production hostname (`PROD_DB_HOST`) for the denylist guard. Without an isolated DB, the pilot drops
   to API/UI-only simulation and can't verify real DB writes. *(If you can't provide one, say so and the
   agents will run the closest local simulation and document the gap.)*

2. **Eric's Supabase login** — to log into `/agent` in the browser as Eric, the agents need a **real
   Supabase auth user** in this project's Supabase: its **user uuid** + a way to get a JWT (you sign in
   at `/login`, or hand over a short-lived token). Email default `eric+dalya-pilot@example.com`. The
   seed will attach Eric's Mahoroba membership/profile to that uuid and set `ADMIN_USER_ID` to it.
   *(No Supabase access → API/CLI phases still run, but the live browser demo is blocked.)*

3. **`ANTHROPIC_API_KEY`** — real key; the chatbot, DealReadiness, and Verified Facts all make live LLM
   calls. *(No key → chatbot/readiness/facts scenarios can't run.)*

---

## Approve-or-override (safe defaults exist)

4. **Brokerage details**
   - Name **Mahoroba Realty**, id `mahoroba-realty` (fixed — canonical). ✔ default
   - DLD office number: default `1858` (placeholder). Override if you want the real one.
   - Brokerage-AI / Agents-AI fake numbers: `+971500000001` / `+971500000099`. ✔ generate-fake OK?

5. **Agent profiles** (3 fakes + Eric)
   - Eric: brokerage **admin + primary agent** (default). OK?
   - Sara Khan / Omar Haddad / Lina Petrova — fake emails `+dalya-pilot@example.com`, fake phones
     `+97150000001[1-3]`. ✔ permission to generate these?

6. **Listings (5)** — the agents will generate realistic pilot values (see `02-SEED-DATASET.md §3`):
   L1 Dubai Hills ready villa (golden), L2 incomplete-facts townhouse, L3 Emaar Oasis off-plan,
   L4 Sobha SeaHaven investment off-plan, L5 luxury villa. **Approve generated, or** hand over real-ish
   values for any of them (title, price, threshold, seller notes, buyer-safe facts, agent-only notes,
   media URLs, viewing logistics, payment schedule). One question that matters:
   - **Use a real listing of yours?** Your memory notes a "first test listing" — if you want the pilot's
     golden-path L1 to mirror a specific real Dubai Hills unit, give me its non-sensitive details;
     otherwise agents use the fabricated default.

7. **Buyer personas (8)** — names/budgets/intent are pre-specified (Adam, Priya, Hassan, Mei, +4) in
   `02-SEED-DATASET.md §4`. **Approve generated** or rename. Phone format default `+9715510000xx`.

8. **Messaging mode** — confirm **simulated transport only** (default; required). Which safe paths to
   exercise?
   - [x] direct chatbot engine / scenario runner (default, always)
   - [ ] local Twilio webhook POST (`/whatsapp/webhook`) — optional, still simulated send
   - [ ] API-level `/whatsapp/send-test` (debug routes)
   Default = all three local/simulated paths; **no** live provider.

9. **Demo expectations**
   - Golden path **10–15 min**, stress path **20–30 min** (defaults). OK?
   - Final artifact: **all three** — markdown pilot report + seed script + scenario runner (default).
     Want just the report, or all?

10. **Seed write permission** — OK for agents to write **clearly-marked pilot rows** (`dalya_pilot` /
    `pilot_` prefix) into the **test** DB, and to add a reset script that deletes only those rows?
    (Required for a DB-backed run.) ✔ / ✘

---

## What you do NOT need to provide
- Mahoroba/Eric base identity, KB community data, verified-facts seed, simulated transport, auth
  verification logic, and the test harness — all already exist in the repo (`01-REPO-FINDINGS.md`).
- Any production credentials, live WhatsApp numbers, or 360dialog access — explicitly out of scope.

---

### Fastest path
Reply with: **(a)** the test `DATABASE_URL` + `PROD_DB_HOST`, **(b)** Eric's Supabase uuid (or "create
one"), **(c)** "approve all defaults" — and note any listing/buyer you want changed. The agents take it
from there.
