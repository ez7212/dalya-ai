---
name: Dalya
description: Practical implementation contract for Dalya agent and listings surfaces.
---

# Dalya Agent Surface Contract

This is the implementation checklist for new `/agent` and `/listings` work. Use `brand/BRAND.md` and `brand/applications/_tokens.css` for the full system; use this file to decide whether a screen can ship.

## Non-Negotiables

- Light default surfaces: page `#FAFAF9`, working panels `#FFFFFF` or `#F4F4F2`, recessed rows `#E8E8E5`, and 1px neutral borders. New agent surfaces should not default to dark chrome.
- Slate is the product action color. Use `#3D5A80` for links, focus, selected states, and normal brand accents; use deep slate `#324B6B` only for the top-tier CTA on a screen.
- No gold/dark legacy classes in new agent surfaces. Banned legacy class/token list: `text-gold`, `btn-gold`, `surface-1`, `text-sand`, `border-gold`, `bg-deep`, `ghost-border`, `shadow-gold`, `#C9A96E`.
- Use an 8px operational radius for buttons, inputs, filters, table rows, and working cards. Smaller status chips may use 4px; avoid decorative rounding beyond that.
- Use Inter for UI and AED values. AED, counts, percentages, and dates use `tabular-nums`; IBM Plex Mono is for RERA IDs, code, and machine output only.
- Keep the UI dense, calm, and operational: compact rows, direct labels, one clear primary action, restrained empty states, no decorative gradients or ornamental cards.
- Status palette is fixed: sage `#4A7C6F` for confirmed/live/verified, copper `#B7793A` for pending/attention, brick `#B84838` for blocked/error/destructive, slate for neutral/info/selected.

## Tables And Cards

- Desktop inventory surfaces use tables when users compare listings, buyers, offers, viewings, or tasks across rows. Keep columns stable, scannable, and aligned.
- Mobile and narrow tablet views convert comparison rows into stable cards with the same fields and actions; do not force horizontal scrolling for the primary workflow.
- Fixed-format data such as AED values, bedrooms, counts, status, and dates must not resize controls on hover, loading, or empty states.
- Cards are for repeated items, modals, and genuinely framed tools. Do not put cards inside cards; use spacing, tone, and hairline dividers for hierarchy.

## Route-Backed Workflows

- Multi-step workflows and meaningful listing workspace decisions are route-backed. Use links or router navigation so browser Back returns to the previous screen.
- Do not replace page-level listing navigation with in-component step state. Temporary component state is only for fields within one screen.
- Avoid duplicate inline Back/Previous controls when the global app Back button already handles the flow.

## Listings Workspace

- Listings workspace routes live under `/listings`: `/listings`, `/listings/[id]`, `/listings/[id]/knowledge`, `/listings/[id]/logistics`, `/listings/[id]/offers`, and `/listings/[id]/documents`.
- `/listings` answers which listings need attention. Rows/cards should expose title, community, type, bedrooms, asking price, live/draft/incomplete state, health, conversations/leads, offers, viewings, knowledge, logistics, assigned agent, last activity, and next action.
- Workspace detail pages share one header: breadcrumb, listing title/status, assigned agent, price/community/type metadata, health badges, route-backed tabs, and one primary next action.
- Canonical listing actions target `/listings/*`, not `/dashboard/listings/*`. Legacy dashboard listing paths may redirect or compatibility-wrap only.
- Off-plan and ready-property documents both belong in `/listings/[id]/documents`; do not make SPA the universal document model.

## Visual QA Requirements

- Verify desktop, tablet, and mobile widths for new agent/listings surfaces. Minimum widths: 1280px, 768px, and 375px.
- Capture screenshots or equivalent artifacts for any changed UI route and record the path in the task evidence.
- Run a brand scan for banned legacy classes and `#C9A96E` on canonical listings files before claiming the route is migrated.
- Check for text overlap, horizontal overflow, unstable table/card dimensions, unreadable status colors, missing focus states, and links that escape to legacy listing routes.
