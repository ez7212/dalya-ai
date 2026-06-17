# Dalya

**B2B AI infrastructure for Dubai real estate brokerages.** The product gives individual agents tools to handle buyer conversations, run viewings, acquire listings, and close deals more efficiently. It gives brokerage owners visibility into team performance, pipeline health, and listing acquisition.

Built on Mahoroba Realty's RERA licence; Mahoroba itself is now in maintenance mode. Customer one (design partner) is Luqman's brokerage.

> **Read first:** [`brand/BRAND.md`](./brand/BRAND.md) — the canonical brand reference.
>
> **Then:** [`brand/STRATEGIC-PIVOT-2026-05-15.md`](./brand/STRATEGIC-PIVOT-2026-05-15.md) — the permanent record of the consumer-direct → B2B shift.

---

## Where to look for things

| If you want to know… | Read this |
|---|---|
| Who Dalya is, who we serve, what the brand stands for | [`brand/BRAND.md`](./brand/BRAND.md) |
| Why we pivoted from consumer-direct to B2B | [`brand/STRATEGIC-PIVOT-2026-05-15.md`](./brand/STRATEGIC-PIVOT-2026-05-15.md) |
| Project context for Claude Code / agents | [`CLAUDE.md`](./CLAUDE.md) |
| Five-minute project overview | [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md) |
| What's currently built and shipped | [`FEATURES.md`](./FEATURES.md) |
| What's queued and what we're building next | [`BACKLOG.md`](./BACKLOG.md) |
| How the buyer-facing chatbot speaks | [`BOT_RULES.md`](./BOT_RULES.md) |
| Visual system, components, motion, voice | [`brand/`](./brand/) (Phase 1–3 docs + locked HTML mockups in `brand/applications/`) |
| Latest test verification | [`reports/chatbot_test_2026-05-08_phase9/VERIFICATION.md`](./reports/chatbot_test_2026-05-08_phase9/VERIFICATION.md) |
| Pre-pivot brand and marketing artifacts | [`archive/pre-pivot-brand/`](./archive/pre-pivot-brand/) (read-only historical reference) |

---

## Architecture

```
Buyer message via WhatsApp
        ↓
Twilio webhook → FastAPI debounce queue
        ↓
Chatbot engine (app/core/chatbot_engine.py)
  ├── Multilingual intent classifier (Claude Haiku)
  ├── Per-listing prompt builder
  ├── Response validator (em-dash / deferral / closer / bold / emoji stripping)
  ├── Escalation graph (offer / marginal / soft-offer / Form A / BRN / regulatory / etc.)
  └── OfferRecord + SuspiciousActivity persistence
        ↓
Response back to buyer · Telegram alert to broker (when escalation fires)
```

Backend: **FastAPI + SQLAlchemy + Neon Postgres + Supabase Auth + Anthropic Claude**
Frontend: **Next.js (Tailwind v4) + Supabase client**
Document parsing: **Claude vision** for SPA (off-plan). Title-deed, Ejari, service-charge, NOC, valuation, snagging, mortgage parsers are in the backlog.

---

## Local development

```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY, DATABASE_URL, SUPABASE_*
PYTHONPATH=$(pwd) venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # localhost:3001 (3000 reserved for another local project)

# Tests
pytest tests/ -v -m "not integration"        # unit only, free
pytest tests/ -v -m integration              # hits Claude, costs tokens
PYTHONPATH=$(pwd) venv/bin/python scripts/chatbot_full_test.py  # 24-persona QA run
# Successful full runs publish to reports/chatbot_test_multitenant/index.html
```

Health check: `curl http://localhost:8000/health` returns DB, Twilio, Telegram, listing-count status.
Interactive API docs: `http://localhost:8000/docs`.

---

## Repo layout

```
dalya-ai/
├── app/                    # FastAPI backend
│   ├── api/                # HTTP routes (whatsapp, telegram, seller, research, spa_parser)
│   ├── core/               # Engine: chatbot_engine, prompt_builder, intent_classifier, response_validator
│   ├── db/                 # SQLAlchemy session + crud
│   ├── models/             # DB models
│   └── schemas/            # Pydantic
├── frontend/               # Next.js dashboard + marketing
├── brand/                  # ⮕ Brand system. Start at BRAND.md
│   ├── BRAND.md            # Canonical
│   ├── STRATEGIC-PIVOT-2026-05-15.md
│   ├── 01-foundations.md … 08-voice-tone.md
│   ├── PHASE-1-LOCK.md / PHASE-2-LOCK.md
│   └── applications/       # Six HTML mockups + _tokens.css (production-ready)
├── knowledge_base/         # Per-community + per-developer KB (emaar_oasis.json, sobha_seahaven.json)
├── reports/                # Test verifications + evergreen research
│   └── _archive/           # Pre-Phase-8 test runs, pre-pivot research
├── archive/                # Pre-pivot brand artifacts (read-only historical)
├── scripts/                # Test orchestrator, seed scripts, report generator
├── tests/                  # pytest
├── CLAUDE.md               # Project context for Claude Code
├── AGENTS.md               # Agent operating instructions
├── PROJECT_BRIEF.md        # Five-minute human-readable overview
├── BOT_RULES.md            # Canonical bot voice + escalation reference
├── FEATURES.md             # Shipped + planned features (B2B at top, Mahoroba legacy below)
└── BACKLOG.md              # Top-5 for Luqman + B2B platform backlog (Mahoroba legacy below)
```

---

## Quick-start API examples

```bash
# Parse an SPA
curl -X POST http://localhost:8000/api/v1/parse-spa -F "file=@your_spa.pdf"

# Sample response
# {
#   "success": true,
#   "listing_id": "uuid-here",
#   "data": {
#     "project": "Palace Villas Ostra",
#     "developer": "Emaar Properties",
#     "purchase_price_aed": 15173230,
#     "noc_eligible": false,
#     "parse_confidence": 0.97,
#     "payment_schedule": [...]
#   }
# }
```
