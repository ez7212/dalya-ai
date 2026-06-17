# Security Researcher Review Rubric

## 1. Multi-tenant isolation

Severity focus: Critical/High.

Look for:

- Missing `brokerage_id`/`tenant_id` checks.
- Client-side-only authorization.
- APIs accepting arbitrary IDs.
- Weak or missing Supabase RLS.
- Storage buckets without tenant isolation.
- Queries that can return another agent's/brokerage's data.
- AI context retrieval that is not tenant-scoped.

## 2. Supabase RLS and Postgres

Look for:

- Tables without RLS enabled.
- Overly broad policies.
- Policies using `auth.uid()` incorrectly.
- `service_role` misuse.
- Insecure RPC/security-definer functions.
- Missing constraints and indexes supporting isolation.
- Migrations that create data before policies are safe.

## 3. API routes

Look for:

- Missing auth checks.
- Missing role/resource checks.
- Trusting request body IDs.
- No schema validation.
- No rate limiting.
- Excessive data returned.
- Unsafe error messages.
- Missing idempotency for repeated requests.

## 4. Webhooks and integrations

Look for:

- Missing signature verification.
- Replay attack risk.
- No idempotency.
- Event source not validated.
- Payload trusted too much.
- Missing audit logs.
- Integration tokens stored insecurely.

## 5. AI security

Look for:

- Prompt injection.
- Cross-tenant context leakage.
- AI seeing more data than necessary.
- Tool calls without server-side authorization.
- User-provided text overriding system rules.
- AI-generated outbound messages making unsupported claims.
- Unclear human review for sensitive messages.

## 6. Secrets and deployment

Look for:

- Secrets in client bundle.
- Service-role key in frontend.
- Weak env separation.
- Missing production env validation.
- Overly permissive CORS.
- Debug logging in production.
- Preview deploys connected to production secrets/data.

## 7. Logging and privacy

Look for:

- Sensitive message bodies logged unnecessarily.
- Access tokens in logs.
- PII in analytics events.
- No audit trail for sensitive actions.
- No data retention strategy.

## Required output additions

For every finding, include:

- Severity: Critical / High / Medium / Low.
- Attack scenario.
- Evidence from code or architecture.
- Recommended fix.
- Regression test or verification step.

Do not provide offensive exploitation beyond what is needed to validate and fix.
