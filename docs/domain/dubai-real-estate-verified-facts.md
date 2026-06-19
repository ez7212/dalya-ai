# Dubai Real Estate — Verified Facts Pack (v1)

**Status:** Template awaiting verification. **Do not treat any value in this file as confirmed until the "Last verified" and "Verified by" fields at the bottom are filled.**

## Purpose

This is the single source of truth for exact Dubai regulatory, DLD, RERA, Trakheesi, NOC, fee, timeline, form, mortgage, and legal-process facts that Dalya is allowed to **state directly** to a buyer. If a fact is not in this file and confirmed, Dalya must not assert it — it must draft for agent approval or say it cannot answer (see [chatbot-qualification-rules-v1](../product/chatbot-qualification-rules-v1.md)).

### How this file is used (intended)
- The chatbot's "answer directly" path may only quote exact regulatory/fee/process numbers that appear here **and** are marked `confirmed`.
- Anything marked `[Eric to fill]`, `[from general knowledge — Eric to verify]`, or left blank is **not** clearable for direct buyer statements yet.
- Items needing Eric's review live in [dubai-real-estate-facts-to-verify.md](./dubai-real-estate-facts-to-verify.md). When Eric verifies one, the confirmed value is copied here and removed from the to-verify checklist.

### Fact-status legend
- `confirmed` — Eric has verified this is currently accurate for the transactions Dalya handles.
- `[Eric to fill]` — value not yet provided.
- `[from general knowledge — Eric to verify]` — a placeholder drawn from general market knowledge, **not** safe to state until verified.
- `repo-asserted (unverified)` — a value already hard-coded or stated somewhere in the repo today, but never formally verified. Flagged so Eric knows current runtime behavior already depends on it.

> ⚠️ Nothing in this file was invented as authoritative. Where a number appears, it is either a blank, a clearly-marked general-knowledge placeholder, or a pointer to where the repo already asserts it (with `repo-asserted (unverified)`). Eric fills the real values.

---

## 1. Buyer qualification rules Eric uses

What actually makes a buyer worth an agent's time, in Eric's own words. This drives readiness stages in [deal-readiness-v1](../product/deal-readiness-v1.md) and scoring in [hot-list-scoring-v1](../product/hot-list-scoring-v1.md).

- Minimum signals before a buyer is "worth a call": `[Eric to fill]`
- What disqualifies a buyer (time-wasters, tyre-kickers, spam-offer pattern): `[Eric to fill]`
- How Eric weights cash vs mortgage-with-preapproval vs mortgage-unknown: `[Eric to fill]`
- How Eric weights end-use vs investor buyers for resale stock: `[Eric to fill]`
- What "urgent" actually means in days for a Dubai resale buyer: `[Eric to fill]`
- Red flags that mean "agent handles this, not the bot": `[Eric to fill]`

## 2. Ready property resale facts

- Documents a ready-resale seller must have ready: `[Eric to fill]` (general list to verify in to-verify §buyer/seller doc checklist)
- Title deed: who holds it, what proves clean title: `[Eric to fill]`
- Tenancy/Ejari: how a tenanted unit affects sale and vacant-possession timing: `[from general knowledge — Eric to verify]`
- Service charges: how they're quoted, who owes outstanding amounts at transfer: `[Eric to fill]`
- Typical ready-resale close timeline (offer → transfer): `[Eric to fill]`

## 3. Off-plan resale facts

- Off-plan resale (assignment/transfer) prerequisites: `[Eric to fill]`
- Developer approval / NOC requirement to resell before handover: `repo-asserted (unverified)` — repo states an NOC-gated closing sequence (see §7); verify exact requirement and sequencing.
- Minimum % paid to developer before a resale/assignment is permitted: `[Eric to fill]` (developer-specific; confirm whether Dalya states a general rule at all)
- "Can off-plan be rented before handover?": `repo-asserted (unverified)` — `BOT_RULES.md` currently states off-plan cannot be legally rented before handover and title transfer. **Verify before Dalya states this as law.**
- Branded-villa resale premium: **scope-locked.** The "15–25% resale premium" figure is sourced from `knowledge_base/emaar_oasis.json` for **branded Emaar Oasis villas only** and is described there as a projection/analyst estimate, not a guarantee. Must **not** be generalized to other listings. (Per `CLAUDE.md`.) Treat as listing-data, not a verified market law.

## 4. Required documents by transaction type

State only documents Eric confirms Dalya should reference. Forms below are referenced in the repo reviewer pack but not verified.

| Transaction | Documents | Status |
|---|---|---|
| Ready resale — buyer side | `[Eric to fill]` (e.g. ID/passport, proof of funds, mortgage pre-approval if financing) | `[from general knowledge — Eric to verify]` |
| Ready resale — seller side | `[Eric to fill]` (e.g. title deed, ID, NOC, service-charge clearance) | `[from general knowledge — Eric to verify]` |
| Off-plan resale — buyer side | `[Eric to fill]` | `[Eric to fill]` |
| Off-plan resale — seller side | `[Eric to fill]` (e.g. SPA, payment receipts, developer NOC) | `[from general knowledge — Eric to verify]` |
| Listing agreement | Form A (seller–agent) | `repo-asserted (unverified)` — referenced in `dalya-reviewers/real-estate-guru/knowledge-pack.md` |
| Buyer–agent agreement | Form B | `repo-asserted (unverified)` |
| Sale agreement / MOU | Form F / MOU | `repo-asserted (unverified)` |

## 5. Fees and commissions

> These are the highest-risk facts to get wrong. Every value below must be verified before Dalya states it directly.

| Fee | Value | Paid to | Status |
|---|---|---|---|
| DLD transfer fee | `[Eric to fill]` (repo uses 4% of price) | Government / DLD | `repo-asserted (unverified)` — `BOT_RULES.md`, knowledge-pack say "commonly 4%" |
| Standard buyer agency commission (market) | `[Eric to fill]` (repo references ~2% + VAT) | Buyer's broker | `repo-asserted (unverified)` — knowledge-pack: "often around 2%... subject to agreement" |
| Dalya/managing-brokerage fee | `[Eric to fill]` | Managing brokerage | `repo-asserted (unverified)` — `BOT_RULES.md` references a 0.15% flat figure tied to legacy Mahoroba framing; **confirm what Dalya states now that Mahoroba is one tenant among many** |
| NOC fee | `[Eric to fill]` (developer-specific) | Developer | `[from general knowledge — Eric to verify]` |
| Trustee office / transfer registration fee | `[Eric to fill]` | Trustee office | `[Eric to fill]` |
| Mortgage registration fee | `[Eric to fill]` | DLD | `[Eric to fill]` |
| VAT applicability on commission | `[Eric to fill]` | — | `[from general knowledge — Eric to verify]` |

**Tenancy note for fees framing:** the legacy "buyer saves X% vs market" comparison in `BOT_RULES.md` is tied to Mahoroba-specific pricing. Confirm whether Dalya should make any savings comparison at all in the multi-tenant model.

## 6. Mortgage / cash buyer notes

- Whether Dalya may state any mortgage eligibility, LTV, or pre-approval rule directly: `[Eric to fill]` (default: **no** — draft for agent / refer to mortgage professional, per repo guardrail "NEVER provide mortgage, investment, or legal advice")
- Difference in process/speed for cash vs mortgage buyers Eric wants surfaced: `[Eric to fill]`
- What "pre-approved" should mean before Dalya treats a buyer as financing-ready: `[Eric to fill]`

## 7. NOC / transfer / trustee office process

Repo currently asserts the following off-plan closing sequence (`BOT_RULES.md`). **All timelines are `repo-asserted (unverified)` and must be verified before Dalya states them:**

1. Offer accepted → MOU signed
2. Seller pays remaining gap to NOC threshold (if needed)
3. Developer issues NOC — repo says *typically 2–4 weeks* → `[Eric to verify]`
4. RERA trustee office registers title transfer = legal close — repo says *typically 30–45 days from offer acceptance* → `[Eric to verify]`
5. Buyer becomes owner of record
6. Buyer takes over remaining SPA schedule directly with the developer
7. Physical handover occurs later on the developer's original date

- Ready-resale transfer/trustee process (if different): `[Eric to fill]`
- Who books the trustee appointment, and what the buyer needs to bring: `[Eric to fill]`

## 8. Trakheesi / permit / advertising rules

- Trakheesi permit requirement for advertising a listing: `[from general knowledge — Eric to verify]`
- What Dalya may say to a co-broker requesting Form A / BRN / listing authorization: `[Eric to fill]` (repo currently escalates these as compliance items rather than answering)
- Advertising-claim constraints (what Dalya must never claim about a listing): `[Eric to fill]`

## 9. Claims Dalya MAY say directly

Only fill this once §1–§8 are verified. Until then, the safe default for any exact regulatory/fee/process number is **draft-for-agent**.

- Listing facts that are present and verified in the listing's own data (price, bedrooms, size, view, parking) — provided they come from the listing record, not invented. ✅ (already the repo pattern)
- Generic, non-numeric process framing that does not assert a specific timeline/fee: `[Eric to confirm scope]`
- Verified fees from §5: `[blocked until §5 verified]`
- Verified NOC/transfer sequence from §7: `[blocked until §7 verified]`

## 10. Claims Dalya MUST draft for agent approval

(These match current repo escalation behavior — see chatbot-qualification-rules-v1 §triggers.)

- Any offer, counter-offer, or negotiation move.
- Any exact regulatory/fee/timeline number not confirmed in §5/§7.
- Mortgage, investment, or legal advice.
- Anything about a *specific other buyer's* offer status (confirm or deny) — hard privacy invariant.
- Payment-method structuring, co-broker fee splits, partnership terms.
- Construction/handover/developer-decision promises.

## 11. Claims Dalya MUST NEVER say

(Hard invariants in `BOT_RULES.md` today.)

- The seller's original purchase price, or any arithmetic (paid + remaining) that lets a buyer back-calculate it.
- Seller name, contact, or PII.
- Confirm or deny whether a named person has made an offer.
- Fabricated percentages, ROI, yields, or forecasts not present in the listing's verified data.
- The Emaar-Oasis-only "15–25% premium" applied to any other listing.

## 12. Last verified date

`[Eric to fill — YYYY-MM-DD]`

## 13. Verified by

`[Eric to fill — name]`

---

## Current repo alignment

- **Likely current matching concepts:** `BOT_RULES.md` (fee framing, off-plan closing sequence, privacy invariants), `dalya-reviewers/real-estate-guru/knowledge-pack.md` and `transaction-reference.md` (forms, fees as general guidance), `knowledge_base/*.json` (per-listing facts incl. the scope-locked Emaar premium), `app/core/ready_property_knowledge.py` (document-extracted facts carry `confidence` + `verified=False`, not authoritative status), `app/core/prompt_builder.py` (hard rules embedded in the system prompt), `app/core/response_validator.py` (strips fabricated ROI/yield and developer puffery).
- **Likely gaps:** there is no machine-readable "verified facts" register today; exact numbers live inline in prompt text and reviewer markdown, mostly prefaced "commonly/typically" (i.e. general knowledge, not verified). The Mahoroba-specific fee framing predates the multi-tenant model and needs an explicit decision.
- **Files likely affected later (do NOT change now):** `app/core/prompt_builder.py` (route exact claims through this register), `app/core/response_validator.py` (extend fabrication guards to "unverified-fact" guard), and a new loader for this file.
- **Implementation ticket suggestion:** "Route exact Dubai claims through Verified Facts register" (see final output).
