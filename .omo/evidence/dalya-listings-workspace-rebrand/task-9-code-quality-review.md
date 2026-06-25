# T9 Code Quality And Slop Review

## Verdict

PASS with known, bounded risks.

This review covers the final T9 test-only remediation in:

- `tests/test_listing_inventory_api.py`
- `frontend/scripts/verify-listings-workspace.mjs`
- `.omo/evidence/dalya-listings-workspace-rebrand/task-9-tests.json`

No product UI or API implementation files were edited for this remediation.

Lowercase grep anchors: overfit, tautological, implementation-mirroring, extraction, scope drift, secret.

## Overfit

Backend assertions are value-based against observable API responses, not against implementation internals. The new `set_logistics` branch test seeds the missing branch directly: knowledge summary is `ready`, `missing_information` is empty, no logistics row exists, and the API response must return `primary_next_action == "set_logistics"`.

Frontend verifier risk is bounded by using fixture rows to exercise production inventory helper behavior plus action-link outputs. It is not a full browser test; that remains deferred to T12 visual/browser QA.

## Tautological Tests

The backend tests are not tautological because they call `/api/v1/listings/mine` through the FastAPI test client and assert response fields after real DB fixture setup. The tests would fail if the route stopped honoring brokerage context, removed lean fields, changed next-action precedence, stopped counting active viewings/open offers, or returned nested mega-payloads.

The frontend verifier avoids pure presence-only checks for behavior. Presence checks remain only as supplementary guards for parser fallbacks and canonical href wiring.

## Implementation-Mirroring

The previous verifier mirrored search/filter/sort logic locally, which was rejected. The current verifier extracts the inventory helper block from `frontend/src/components/listings/AgentListingsIndex.tsx`, exports `applyInventoryView` into a temporary module, and runs behavior cases against that extracted production helper. That removes the prior implementation-mirroring failure while avoiding product-code exports solely for tests.

## Extraction

The production extraction is intentionally narrow and temporary. It reads a stable helper block from `AgentListingsIndex.tsx`, transpiles it under `frontend/scripts/verify-listings-workspace.mjs`, runs behavior assertions, and deletes temp files in `finally` blocks.

This is acceptable for T9 because the task explicitly asked for a focused verifier and not a broad new component/browser framework. A dedicated exported presenter/helper would be cleaner if this verification grows, but creating or moving production modules would exceed T9's write scope.

## Scope Drift

Scope stayed inside the allowed ownership:

- backend test file only for API coverage
- one existing frontend verifier script
- task evidence JSON
- this code-quality/slop artifact

No product UI/API implementation, package scripts, plan checkbox, staging, or commits were changed.

## Secret Handling

Verification loads `.env.test` via the local dotenv CLI without printing environment values. Evidence records command names and sanitized outcomes only. No tokens, database URLs, cookies, auth headers, or raw env values are included.

## Remaining Risks

- The frontend verifier is static/transpiled, not browser visual QA. This is acceptable for T9 because T12 owns browser/visual coverage.
- The extraction boundary depends on `interface InventoryView` and `function Metric` remaining stable. If the component is refactored, the verifier fails loudly instead of silently passing.
- The backend tests use the configured test database and require network access when that database is remote. This is acceptable because the command is explicit, env values are not printed, and sandbox DNS blockers are handled via approved escalation.

## Final Assessment

The remediation addresses the rejected gaps without widening implementation scope: `set_logistics` next-action precedence is now covered, cross-brokerage scoping remains covered, the frontend verifier no longer duplicates inventory behavior logic, and the evidence records the remaining bounded risks.
