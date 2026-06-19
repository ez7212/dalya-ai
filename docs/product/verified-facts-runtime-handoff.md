# Verified Facts — Runtime Handoff (implementation note)

**Status:** Implementation handoff. **Docs only — no code here, and none to be written yet.** This describes how a future loader and the chatbot should consume [`dubai-real-estate-verified-facts.md`](../domain/dubai-real-estate-verified-facts.md). It changes no runtime behavior.

> ⚠️ **Do not implement while DAL-172A (explicit brokerage context) is still in progress**, unless Eric approves a separate, non-overlapping branch. The likely implementation files (`prompt_builder.py`, `response_validator.py`, `chatbot_engine.py`) are chatbot-runtime and must not be touched in parallel with DAL-172A.

## 1. What the future loader should read

The loader's input is the verified-facts markdown file. It should parse:

- **Each fact row** and its **status label** — the inline code-span at the end of the row, one of the labels defined in the file's *Fact-status legend*: `confirmed`, `Eric decision required`, `draft-for-agent only`, `do not state`, `repo-asserted (unverified)`, `listing-specific only`.
- **Source references** — the `[Sx]` citations, resolvable against the §15 source register.
- **Section context** — which of §1–§12 a fact lives under (fees, NOC/transfer, off-plan, etc.), plus any per-section "Dalya direct-answer policy" note that distinguishes *general* confirmed facts from *transaction/listing-specific* ones.
- **The "Runtime usage policy" section** at the top, which is the authoritative mapping from status label → runtime behavior.
- **`Last verified` (§13) and `Verified by` (§14)** — to expose provenance/staleness.

The loader should **reject unrecognized status labels** rather than guessing, and should treat a missing label as not-direct (draft-for-agent).

## 2. Suggested runtime policy labels

The markdown status labels map to a small runtime enum:

| Markdown status | Runtime policy label | Meaning |
|---|---|---|
| `confirmed` (general fact) | `direct` | May answer directly if listing/context matches |
| `confirmed` (transaction-/listing-specific) | `draft_for_agent_only` | Source-confirmed but per-deal → must draft/escalate |
| `draft-for-agent only` | `draft_for_agent_only` | Draft/escalate, never autonomous |
| `Eric decision required` | `draft_for_agent_only` | Not direct until Eric promotes |
| `repo-asserted (unverified)` | `draft_for_agent_only` | Not direct until verified |
| `listing-specific only` | `listing_specific_only` | Usable only from that listing's verified data; never generalized |
| `do not state` | `do_not_state` | Never buyer-facing |

The runtime enum: **`direct` · `draft_for_agent_only` · `do_not_state` · `listing_specific_only`.**

Key rule the loader must encode: **`direct` is granted only to a `confirmed` row that is not transaction- or listing-specific.** Source-confirmed ≠ direct-safe. The per-section "direct-answer policy" notes are how a confirmed-but-per-deal fact (e.g. a closing timeline) is held to `draft_for_agent_only`.

## 3. How the chatbot should behave

- **`direct`** — Dalya may state the fact directly **only when the live listing/context matches** the fact's scope. If listing data is missing or stale, fall back to `draft_for_agent_only`.
- **`draft_for_agent_only`** — Dalya does not answer the buyer with the value; it drafts a reply / escalates to the agent for approval. (Consistent with the response-planner `draft_for_agent_approval` / `escalate_to_agent` outcomes in [chatbot-qualification-rules-v1](./chatbot-qualification-rules-v1.md).)
- **`do_not_state`** — Dalya refuses safely / redirects, never states it. (The existing privacy invariants in `BOT_RULES.md` already cover the seller-price / named-buyer-offer cases.)
- **`listing_specific_only`** — usable only from that specific listing's verified data; never generalized to other listings (e.g. the Emaar Oasis premium).
- **Missing / ambiguous / stale fact** — Dalya drafts for agent approval. Absence is never a license to improvise an exact regulatory/fee/timeline number.

## 4. Examples that CAN be direct after verification

(All `confirmed`, general, source-backed — subject to the listing/context match rule.)

- DLD sale-registration documents required (Emirates ID/passport, developer e-NOC). [S1]
- DLD/RERA Contract A/B/F definitions. [S10]
- That an off-plan sale requires a developer NOC before registration. [S4]
- The Trakheesi advertising-permit and permit-verification services exist. [S3][S5]
- Standard DLD registration fee is 4% (buyer), as a general fee fact — paired with "the agent will confirm exact costs for this transaction." [S1]

## 5. Examples that MUST draft for agent

- "How long will *my* NOC / transfer take?" — developer/transaction-specific timing (`draft_for_agent_only`). [§7]
- The full deal timeline / closing timeline for a specific deal (≈30–45 days varies; never quote an exact schedule). [§7/§2]
- Any offer, counter-offer, negotiation, or deposit move.
- Mortgage eligibility / LTV / approval likelihood / rates / tax.
- Whether a specific project allows off-plan assignment at X% paid.
- Co-broker Form A / BRN / authorization requests.

## 6. Examples that MUST NEVER be said

- The seller's original purchase price, or arithmetic that back-calculates it.
- Confirm/deny whether a named person has made an offer.
- Guaranteed ROI / yield / rental income / appreciation / "best investment."
- The Emaar Oasis 15–25% premium applied to any other listing.
- Off-plan "cannot be legally rented before handover" **as stated law** — pending Eric/legal (currently `draft_for_agent_only`).

## 7. Likely future implementation files

- **New** `app/core/verified_facts.py` — the loader/registry.
- `app/core/prompt_builder.py` — gate exact regulatory/fee/process claims through the registry (chatbot-runtime — do not touch during DAL-172A).
- `app/core/response_validator.py` — extend the existing fabrication guard to an "unverified-claim" guard (chatbot-runtime — do not touch during DAL-172A).
- `app/core/chatbot_engine.py` — route the planner's answer/draft/refuse decision through the policy label (chatbot-runtime — do not touch during DAL-172A).
- `tests/` — regression fixtures for direct / draft-only / never-say cases.

## 8. Implementation guardrail

**Do not implement the loader or any runtime gating while DAL-172A is still in progress** unless Eric explicitly approves a separate branch that does not overlap DAL-172A's files (auth, tenant context, agent routes, API client brokerage headers). This handoff is a plan, not a green light.
