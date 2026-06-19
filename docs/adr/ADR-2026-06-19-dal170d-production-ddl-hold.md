# ADR — Hold DAL-170D production DDL until onboarding gate

**Date:** 2026-06-19
**Status:** Accepted
**Linear:** DAL-170

## Context

DAL-170D fresh Neon rehearsal passed, and the staging rollout passed with the
approved DAL-170D1/D2 scope:

- 7 parent composite identity indexes
- 15 supporting child indexes
- 5 first-pass NOT VALID tenant FKs
- 4 listing-linked NOT VALID tenant FKs
- all 9 FKs still `convalidated=false`

No production DDL has been run. No RLS, NOT NULL constraints, FK validation,
data backfills, suspicious-activity work, `listing_inquiries` /
`offer_records` FKs, lead/relay FKs, DAL-171, DAL-172, or chatbot behavior
changes have been run in production.

Dalya is still in the build/tinkering phase. Luqman's agency has not been
officially onboarded, no real brokerage data has been imported into production,
and live WhatsApp buyer traffic is not connected to production.

## Decision

Hold DAL-170D production DDL during the current build phase.

Production DDL remains blocked by default and is not needed until production is
about to contain real brokerage tenants, real buyer PII, or live agency traffic.

The DAL-170D production rollout must be revisited before any of these gates:

- official Luqman agency onboarding
- importing real brokerage data into production
- connecting live WhatsApp buyer traffic to production

## Consequences

- Rehearsal and staging evidence stay available for production planning.
- Production stays unchanged during the build phase.
- The production rollout plan remains valid but requires fresh production DB
  fingerprint approval, direct Neon production URL confirmation, maintenance
  window approval, artifact generation, monitoring, and rollback readiness
  before execution.
- DAL-170D production DDL should not be treated as complete until the onboarding
  gate is reached and the production rollout is explicitly approved and run.

## Follow-up

Before the onboarding gate, rerun the production rollout checklist from
`docs/runbooks/dal170d-production-ddl.md` and attach current evidence to Linear.
