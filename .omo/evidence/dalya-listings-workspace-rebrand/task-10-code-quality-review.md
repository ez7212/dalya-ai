# T10 Code Quality / Slop Review

Scenario: T10 legacy dashboard listing route redirects.

## Source-Backed Findings

- `frontend/src/app/(app)/dashboard/listings/[id]/layout.tsx:1-8` is a thin compatibility wrapper only: it imports `ReactNode`, accepts `children`, and returns `children` directly.
- Old dashboard listing pages are redirect-only route modules:
  - `page.tsx:1-12` redirects to `/listings/${id}`.
  - `knowledge/page.tsx:1-12` redirects to `/listings/${id}/knowledge`.
  - `logistics/page.tsx:1-12` redirects to `/listings/${id}/logistics`.
  - `offers/page.tsx:1-12` redirects to `/listings/${id}/offers`.
  - `spa/page.tsx:1-12` redirects to `/listings/${id}/documents`.
- Static legacy scan found no dark/gold/banned classes or duplicate legacy detail implementation tokens in the old route files. Checked tokens included `text-gold`, `btn-gold`, `surface-1`, `text-sand`, `border-gold`, `bg-deep`, `ghost-border`, `shadow-gold`, `#C9A96E`, `useListingDetail`, `useAuth`, `TABS`, `usePathname`, `framer-motion`, `next/link`, `apiFetch`, and `ListingLogisticsForm`.
- `frontend/scripts/verify-listing-legacy-redirects.mjs:1-123` has no TypeScript escape-hatch/slop tokens: no `any`, no `as any`, no `@ts-ignore`, no `@ts-expect-error`, and no non-null assertions.
- Redirect loop / browser Back behavior is one-way by static route-module evidence: old `/dashboard/listings/[id]` routes redirect to canonical `/listings/[id]` routes, and the canonical checked scope has no redirect back to `/dashboard/listings`, avoiding browser Back bouncing between duplicate UIs.

## remove-ai-slops/programming perspective

- overfit/slop criteria: the verifier checks semantic redirect targets and banned legacy implementation markers, not fragile formatting, snapshots, whitespace, or rendered markup. The pass condition is that each old route maps to the expected canonical listing workspace URL and that legacy detail UI/data-fetch/tab/link/style tokens are absent.
- deletion-only/tautological risk: the review does not claim layout removal alone as proof. The old layout is only a thin `children` wrapper, while each legacy route independently verifies its `redirect()` target, including the `/spa` to `/documents` canonical rename.
- implementation-mirroring tests: the script does inspect route source, so it is static and close to the implementation surface. It mitigates pure mirroring by using an explicit expected route map, banned import/token checks for legacy implementation leakage, and a canonical redirect-back scan showing canonical `/listings/[id]` files do not redirect back to `/dashboard/listings`.
- unnecessary production extraction/parsing/normalization: no new production abstraction, parser, shared normalizer, or route-normalization helper was introduced for this cleanup. The only verification artifact is the static script, and production old-route code remains redirect modules plus the thin pass-through layout.
- false confidence: the limitation is documented because auth-protected app routes were not driven in a live browser. The evidence is intentionally limited to static Next route-module verification and does not overclaim live navigation behavior.
- scope drift: this cleanup did not edit canonical listing content. The review scope is the old `/dashboard/listings/[id]` compatibility routes and their absence of legacy UI implementation markers.

## Known Limitation

Live browser navigation was not used because these app routes are protected by auth. The verification is static route-module verification of Next `redirect()` targets and absence of legacy UI implementation in the old route files.
