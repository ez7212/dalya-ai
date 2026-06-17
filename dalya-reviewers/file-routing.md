# Dalya Reviewer File Routing

Use this file to decide what to inspect before issuing findings. It is a routing map, not a substitute for reading the code.

## Source of Truth

- Product context: `PROJECT_BRIEF.md`, then `BACKLOG.md`.
- Operating instructions: root `AGENTS.md` / `CLAUDE.md`.
- Brand and voice: `brand/`, `BOT_RULES.md`, and frontend route/component copy.
- If these conflict, call out the conflict explicitly in the review and prefer `PROJECT_BRIEF.md` / `BACKLOG.md` for current product direction.

## Shared Review Targets

- Backend entry points: `app/main.py`, `app/api/`.
- Domain logic: `app/core/`.
- Data model: `app/models/db_models.py`, `app/schemas/`, `app/db/`.
- Frontend routes: `frontend/src/app/`.
- Frontend components: `frontend/src/components/`.
- Shared frontend API/types: `frontend/src/lib/`, `frontend/src/types/`.
- Regression tests and harnesses: `tests/`, `scripts/`, `reports/`.
- Product decisions: `docs/adr/`, `GOAL_SPEC_0610.md`, `MVP_ROADMAP_0609.md`.

## Chatbot Master

Start with:

- `app/core/chatbot_engine.py`
- `app/core/prompt_builder.py`
- `app/core/intent_classifier.py`
- `app/core/intent_rules.py`
- `app/core/response_validator.py`
- `app/core/refusal_variation.py`
- `app/core/conversation_takeover.py`
- `app/core/escalation_threads.py`
- `app/core/agent_relay.py`
- `app/core/summary_worker.py`
- `app/api/whatsapp.py`
- `app/api/agent.py`
- `app/schemas/conversation.py`
- `BOT_RULES.md`
- `tests/test_*chatbot*.py`, `tests/test_*conversation*.py`, `tests/test_*escalation*.py`, `tests/test_voice_note_flows.py`
- `scripts/chatbot_full_test.py`
- Latest relevant `reports/chatbot_*` artifact

Frontend surfaces to inspect when conversation review includes the agent workspace:

- `frontend/src/components/conversations/ConversationDetail.tsx`
- `frontend/src/components/shared-ui/ConversationView.tsx`
- `frontend/src/components/escalations/EscalationInbox.tsx`
- `frontend/src/components/drafts/DraftQueue.tsx`
- `frontend/src/app/(app)/agent/conversations/[id]/page.tsx`
- `frontend/src/app/(app)/agent/escalations/page.tsx`
- `frontend/src/app/(app)/agent/drafts/page.tsx`

## Real Estate Guru

Start with:

- `app/core/payment_compute.py`
- `app/core/unit_profile.py`
- `app/core/ready_property_knowledge.py`
- `app/core/listing_enrichment.py`
- `app/core/listing_stages.py`
- `app/core/offers.py`
- `app/core/viewing_logistics.py`
- `app/core/tenant_viewings.py`
- `app/core/post_viewing_capture.py`
- `app/core/post_viewing_followup.py`
- `app/core/buyer_profiles.py`
- `app/core/buyer_preferences.py`
- `app/api/listings.py`
- `app/api/seller.py`
- `app/api/spa_parser.py`
- `app/api/viewings.py`
- `knowledge_base/`
- `tests/test_ready_property_knowledge.py`
- `tests/test_viewing_logistics.py`
- `tests/test_buyer_card_offers.py`
- `tests/test_post_viewing_followup.py`

Frontend surfaces:

- `frontend/src/components/cards/ListingCard.tsx`
- `frontend/src/components/listings/`
- `frontend/src/components/buyers/`
- `frontend/src/components/viewings/`
- `frontend/src/components/shared-ui/UnitProfileView.tsx`
- `frontend/src/components/shared-ui/InterestedBuyersPanel.tsx`
- `frontend/src/app/(app)/dashboard/listings/`
- `frontend/src/app/(app)/agent/buyers/`
- `frontend/src/app/(app)/agent/viewings/`

## UX Designer

Start with:

- `frontend/src/app/(app)/agent/page.tsx`
- `frontend/src/components/agent-dashboard/AgentDashboard.tsx`
- `frontend/src/components/app/AppSidebar.tsx`
- `frontend/src/components/conversations/ConversationDetail.tsx`
- `frontend/src/components/drafts/DraftQueue.tsx`
- `frontend/src/components/escalations/EscalationInbox.tsx`
- `frontend/src/components/buyers/BuyerList.tsx`
- `frontend/src/components/buyers/BuyerCard.tsx`
- `frontend/src/components/viewings/ViewingCalendar.tsx`
- `frontend/src/components/viewings/ViewingDetail.tsx`
- `frontend/src/components/settings/NotificationPreferences.tsx`
- `frontend/src/components/shared-ui/`
- `frontend/src/app/(app)/onboarding/agent/page.tsx`
- `frontend/src/app/(app)/component-showcase/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/lib/shared-ui-tokens.ts`

Review public or legacy surfaces only when requested:

- `frontend/src/app/(marketing)/`
- `frontend/src/components/marketing/`
- `frontend/src/components/sections/`
- `frontend/src/app/(app)/seller-dashboard-archive/page.tsx`

Verification aids:

- `frontend/scripts/verify-component-showcase.mjs`
- `frontend/test-results/`
- `brand/`

## Security Researcher

Start with:

- `app/core/auth.py`
- `app/core/brokerage_access.py`
- `app/core/brokerage_config.py`
- `app/core/brokerage_resolver.py`
- `app/core/multitenant_context.py`
- `app/core/messaging/`
- `app/core/media_assets.py`
- `app/core/lead_ingest.py`
- `app/core/relay_media.py`
- `app/api/`
- `app/db/session.py`
- `app/models/db_models.py`
- `scripts/migrate_*.py`
- `scripts/create_brokerage_signup.py`
- `scripts/approve_agent_profile.py`
- `scripts/activate_dld_matched_agents.py`
- `tests/test_*auth*.py`, `tests/test_*tenant*.py`, `tests/test_*brokerage*.py`, `tests/test_*security*.py`
- `.env.example`, `env.example`, `frontend/.env.local` only for variable names and accidental secret exposure checks.

Frontend/auth surfaces:

- `frontend/src/components/providers/AuthProvider.tsx`
- `frontend/src/lib/supabase/`
- `frontend/src/proxy.ts`
- `frontend/src/app/(app)/auth/callback/route.ts`

Security reviews should inspect for cross-tenant data access, service-role misuse, webhook forgery, insecure media/file paths, prompt-injection data leakage, unsafe logging, and production/test database confusion.
