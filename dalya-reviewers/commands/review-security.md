# Review Security Command

Use before demos, deploys, and any backend/auth/RLS/API/integration changes.

## Read first

- `dalya-reviewers/shared-context.md`
- `dalya-reviewers/review-session-rules.md`
- `dalya-reviewers/file-routing.md`
- `dalya-reviewers/templates/review-output-template.md`
- `dalya-reviewers/security-researcher/persona.md`
- `dalya-reviewers/security-researcher/security-checklist.md`
- `dalya-reviewers/security-researcher/review-rubric.md`

## Scope

Review:

- Supabase schema and migrations.
- RLS policies.
- Auth flow.
- API routes/server actions.
- Webhook routes.
- Storage buckets.
- Environment variable handling.
- Deployment config.
- Logging/error tracking.
- AI context retrieval and tools.
- Integration tokens/secrets.

## Instructions

Do not change code.

Rank findings as Critical, High, Medium, or Low.

For each issue include:

- Attack scenario.
- Evidence.
- Recommended fix.
- Regression test or verification step.

Do not provide harmful exploitation instructions beyond what is needed to validate and fix.
