# 04 — Test Matrix (template — Agent F fills `Actual` + `Status`)

Status legend: ✅ pass · ❌ fail · ⛔ blocked · ⬜ not run. Fill `Actual` and `Notes` (with file:line or
endpoint refs) during the run. Keep the row order — it doubles as a coverage checklist.

## A. /agent Dashboard
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| A1 | Eric logs in (Supabase JWT + Mahoroba membership) | Reaches `/agent`, brokerage = Mahoroba | | |
| A2 | Dashboard healthy load | Real pilot data; **no `fallback-data.ts` rows**; no warning banner | | |
| A3 | Metrics | Counts match seed (buyers, viewings, escalations, drafts) | | |
| A4 | Escalation routing | Items link to `/agent/escalations?thread=<id>` | | |
| A5 | Hot-list refresh | `POST /agent/hot-list/refresh` recomputes or fails cleanly (no 500) | | |

## B. Today Queue (ordering + item quality)
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| B1 | Ordering | critical escalations → overdue tasks → needs-reply → actionable viewings → reply drafts → hot buyers → future follow-ups | | |
| B2 | Item completeness | each item: title, subject, reason, status, timestamp, working href | | |

## C. Buyer-facing chatbot (per persona)
| # | Persona/Scenario | Expected | Actual | Status |
|---|------------------|----------|--------|--------|
| C1 | Adam (hot ready) | qualifies one-question-at-a-time, listing-aware, becomes viewing-ready/hot | | |
| C2 | Priya (off-plan analytical) | verified-facts answers; escalates unverified/legal/fee | | |
| C3 | Low-context "price?/pics" | one useful qualifying Q; no over-qualify; low/partial readiness | | |
| C4 | Hassan (offer) | firm below-threshold offer detected + escalated; revise-up tracked | | |
| C5 | Mei (human takeover) | speak-to-human → escalation + AI pause | | |
| C6 | Media/voice | private-media posture or graceful fallback (or documented limit) | | |
| C7 | Opt-out "stop" | suppression recorded; dashboard reflects | | |
| C8 | Tom (weak listing L2) | safe failure + agent-confirmation language on missing facts | | |
| C9 | Off-plan no-viewing | no physical viewing push; brochure/renders/agent follow-up | | |
| C10 | Leak checks | no seller-sensitive / internal-note leakage in any buyer text | | |

## D. DealReadiness
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| D1 | Per-buyer stage/score/missing/next-action/next-question correct | | | |
| D2 | Agent-confirmed fields override inferred | | | |
| D3 | Readiness consistent across dashboard, buyer list, buyer card, draft assist, hot list | | | |

## E. Escalations & relay
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| E1 | Trigger: offer / legal / human / unverified fact / viewing | each creates the right thread+type | | |
| E2 | Bundling | multiple questions → one thread; no dup spam | | |
| E3 | Reply from dashboard | updates thread | | |
| E4 | `[Ref: TOKEN]` agent reply relay | routed back to buyer; thread updated | | |
| E5 | Manual resolve | thread closes | | |

## F. Drafts
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| F1 | Drafts exist: price follow-up, post-viewing, agent-confirm-needed, offer response | | | |
| F2 | edit / send / reject / snooze | all work | | |
| F3 | Sent draft writes message + action + compliance event | | | |
| F4 | Draft assist payload | verified-fact metadata + missing facts + readiness + suggested Q | | |

## G. Conversations
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| G1 | Detail completeness | timeline, listing snapshot, AI mode, media, brief, summary, next action, active escalation, offer strip, assets shortcut | | |
| G2 | Pause / resume AI | both work; resume confirmation | | |
| G3 | "Don't need to read transcript" | next action is clear without raw transcript | | |

## H. Buyers & cards
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| H1 | Filters: all / open offer / viewing scheduled / stale | | | |
| H2 | Sorts: score / last activity / name | | | |
| H3 | Card: qualification, provenance, editable fields, readiness, conversations, viewings, offer history, escalation count, opt-out | | | |

## I. Offers
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| I1 | Create buyer offer | record created | | |
| I2 | Confirm AI-proposed draft offer | confirmed | | |
| I3 | Discard bad draft offer | discarded | | |
| I4 | Seller counter + transition with notes | history correct | | |
| I5 | Buyer card + conversation reflect offer history | | | |

## J. Viewings
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| J1 | Ready (L1): logistics → availability → propose → confirm → tenant notice → confirmations → complete → buyer+agent feedback | | | |
| J2 | Off-plan (L3): no physical logistics; brochure/floorplan/renders/agent follow-up | | | |

## K. Lead ingest
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| K1 | Property Finder payload → Mahoroba resolution | conversation + ingest record | | |
| K2 | Bayut payload dedup | no duplicate buyer | | |
| K3 | Template-locked first touch only (not free-form AI) | | | |
| K4 | Assignment / nudge / compliance trail | present | | |

## L. Verified Facts / safety
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| L1 | DLD / NOC / LTV / remaining payment / tenancy / conveyancing / commission Qs | direct only when verified+safe | | |
| L2 | Unsupported claim rewrite | → agent-confirmation language | | |
| L3 | do-not-state / seller-private | never leaked | | |

## M. Security / tenant sanity
| # | Scenario | Expected | Actual | Status |
|---|----------|----------|--------|--------|
| M1 | Mahoroba data isolation | not visible under other brokerage context | | |
| M2 | Unauth / wrong-agent access | denied (401/403) on buyer/conversation/escalation | | |
| M3 | Debug routes | disabled in live-class env (or documented) | | |
| M4 | Media URLs | private/signed, not public (where testable) | | |
