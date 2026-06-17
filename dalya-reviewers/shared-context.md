# Dalya Shared Context

## Product

Dalya is a B2B AI SaaS product for real estate agents and brokerages in Dubai.

The first MVP is **agent-facing**. Brokerage owner/admin views come later.

## Stack

- React frontend.
- Supabase backend.
- Postgres database.
- Supabase Auth and Row Level Security are expected to protect multi-tenant data.
- Integrations may include WhatsApp, CRM systems, Property Finder, Bayut, and AI APIs.

## MVP reality

- Chatbot logic is the most battle-tested part.
- Dashboard/workflow features are less examined.
- Agents already live in WhatsApp; Dalya must either improve that workflow or clearly beat it.
- Reviewers should challenge whether the MVP creates daily value, not just whether the code works.

## Primary user

A Dubai real estate agent working inbound buyer leads, owner outreach, viewing coordination, follow-ups, and property marketing.

## Later user

A brokerage owner or manager who wants team visibility, lead conversion visibility, and standardization.

## Core jobs Dalya should help with

1. Respond to inbound buyer leads quickly.
2. Qualify buyers naturally without killing conversion.
3. Summarize conversations so the agent knows what to do next.
4. Identify hot leads and urgent follow-ups.
5. Help agents prepare better outbound messages.
6. Reduce manual CRM/WhatsApp admin.
7. Help agents book viewings and close deals.
8. Create useful daily habit loops.

## Known risks

- Chatbot sounds too AI-generated.
- Chatbot is too hard-coded and brittle.
- Chatbot asks too many questions before offering value.
- Chatbot does not know when to hand off to a human agent.
- Dashboard is a passive database rather than an action system.
- Agents keep using WhatsApp and ignore Dalya.
- Supabase RLS or API authorization leaks tenant/user data.
- AI context retrieval crosses tenant boundaries.
- Webhooks are trusted without verification.
- Logs expose sensitive buyer, seller, or brokerage data.
- AI-generated property/outreach text overpromises, hallucinates, or creates compliance risk.

## Review principles

- Be direct.
- Avoid vague praise.
- Prefer launch-blocking issues over polish.
- Separate product risk from implementation risk.
- Cite exact files, routes, prompts, screens, tables, or flows when possible.
- Use P0/P1/P2 priorities for product and UX.
- Use Critical/High/Medium/Low severities for security.
- End with concrete Linear-ready tasks.
