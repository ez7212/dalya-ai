# Security Researcher Checklist

Use this checklist before production deploy.

## Supabase and Postgres

- [ ] RLS enabled on all tenant/user data tables.
- [ ] Policies tested for cross-user and cross-brokerage access.
- [ ] Every tenant-owned row has `brokerage_id`, `tenant_id`, or equivalent.
- [ ] Child tables cannot join across tenants.
- [ ] `service_role` key is never exposed to frontend.
- [ ] Anon key access is limited through RLS.
- [ ] Storage buckets have tenant/user-scoped policies.
- [ ] RPC functions use safe permissions.
- [ ] Security-definer functions are reviewed carefully.
- [ ] Constraints prevent orphaned or cross-tenant records.
- [ ] Indexes support RLS predicates where needed.

## Auth and authorization

- [ ] Every sensitive action authenticates the user.
- [ ] Every sensitive action authorizes access to the specific resource.
- [ ] API does not trust `user_id`, `agent_id`, or `brokerage_id` from the request body.
- [ ] Roles are checked server-side.
- [ ] Invitation/team membership flows cannot be abused.
- [ ] Account deletion/deactivation removes or restricts access properly.

## API routes

- [ ] Input validation exists.
- [ ] Rate limits exist for public/expensive routes.
- [ ] Errors do not leak secrets or internals.
- [ ] Responses return minimum necessary data.
- [ ] Mutation endpoints are idempotent when needed.
- [ ] CSRF/CORS assumptions are clear for browser-exposed routes.

## Webhooks and integrations

- [ ] Signature verification implemented.
- [ ] Replay protection considered.
- [ ] Idempotency implemented.
- [ ] Unknown event types handled safely.
- [ ] Payloads are not trusted for tenant identity without verification.
- [ ] Integration tokens are encrypted or otherwise protected.
- [ ] External API failures do not corrupt internal state.

## AI security

- [ ] AI context retrieval is tenant-scoped.
- [ ] User messages cannot override system instructions.
- [ ] AI tools re-check authorization server-side.
- [ ] Sensitive data minimized in prompts.
- [ ] AI cannot send outbound messages without required guardrails.
- [ ] AI-generated claims about properties, fees, ROI, availability, or legal process are constrained.
- [ ] Prompt/model versions are tracked.
- [ ] Conversation transcripts are protected as PII/sensitive business data.

## Deployment and secrets

- [ ] Production environment variables audited.
- [ ] No debug logs in production.
- [ ] CORS restricted.
- [ ] Error tracking scrubbers configured.
- [ ] Dependency vulnerabilities reviewed.
- [ ] Build artifacts do not contain secrets.
- [ ] Preview deployments do not expose production data.

## Logging and privacy

- [ ] Sensitive message bodies are not logged unnecessarily.
- [ ] Access tokens are never logged.
- [ ] PII in analytics is minimized.
- [ ] Admin/sensitive actions have audit logs.
- [ ] Data retention strategy exists.
- [ ] User/brokerage export and deletion paths are considered.
