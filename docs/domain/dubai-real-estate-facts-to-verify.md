# Dubai Real Estate — Facts to Verify (v1)

**Status:** Largely reconciled. Eric completed a sourced verification pass on 2026-06-19 (see [`dubai-real-estate-verified-facts.md`](./dubai-real-estate-verified-facts.md), DLD/RERA primary sources [S1]–[S15]). Most rows below are now **resolved into the verified-facts file**. A small set still needs Eric/legal/accountant input or is intentionally left as draft-for-agent / do-not-state.

This file is no longer the blocker it was — it is now a **reconciliation record**: what got verified, what remains, and why. Unresolved rows are kept (not deleted) so nothing is lost.

> Reminder: a row being "resolved" means it has a status label in verified-facts. `confirmed` (general) → may be `direct`; `confirmed` (transaction/listing-specific), `draft-for-agent only`, `Eric decision required`, `do not state` are **not** direct-safe. See the verified-facts "Runtime usage policy" section.

---

## Resolved / moved to verified facts

These are now in the verified-facts file with a status label and (where applicable) a source.

- [x] **DLD transfer/registration fee (4%, buyer pays)** → verified-facts §5 `confirmed` [S1]
- [x] **Title deed issuance + map + knowledge/innovation fees** → §5 `confirmed` [S1]
- [x] **Trustee / service-partner fee (AED 4,000 + VAT ≥ 500k; AED 2,000 + VAT < 500k)** → §5 `confirmed` [S1][S4]
- [x] **Mortgaged-property sale service fee (AED 1,000 + fees)** → §5/§6 `confirmed` [S2]
- [x] **Standard buyer agency commission (industry 2%, negotiable; do not assume 2% per listing)** → §5 `confirmed` [S4]
- [x] **"Buyer saves X%" Mahoroba framing** → §5 `do not state` (killed for multi-tenant)
- [x] **Form A / B / F definitions + DLD broker journeys** → §4 `confirmed` [S10][S11][S12][S13]
- [x] **Buyer/seller document checklists (ready + off-plan)** → §4 (ID/passport + e-NOC source-confirmed [S1]; remaining items flagged "Eric to approve" in-table)
- [x] **Full ready-sale transfer sequence (trustee office, documents, e-NOC, outputs)** → §7 `confirmed` [S1]
- [x] **Mortgaged-property sale sequence (liability letter, cheques, mortgage release)** → §7 `confirmed` [S2]
- [x] **NOC sequencing — outstanding service charges settled before developer issues NOC** → §2 `confirmed` [S4]
- [x] **Off-plan resale requires developer NOC; then follows ready-sale process** → §3/§7 `confirmed` [S4][S1]
- [x] **Oqood / provisional (initial-sale) registration** → §3 `confirmed` [S8][S9]
- [x] **Trakheesi ad permit + permit verification service** → §8 `confirmed` [S3][S5]
- [x] **Advertising-claim constraint (never claim a listing is permitted/authorized unless verified listing data)** → §8 `do not state` unless verified
- [x] **Company buyer/seller (high-level: company registration may be required; detailed list via agent/trustee)** → §4 `confirmed` (high-level) [S1][S2]
- [x] **Overseas / non-resident buyer (passport in lieu of Emirates ID; POA notarized by Dubai Court)** → §2/§4 `confirmed` [S1]
- [x] **VAT standard rate (5%)** → §5 `confirmed` (rate) [S7] *(brokerage-invoice wording still open — see below)*
- [x] **Claims-requiring-agent-approval list** → §10 `confirmed`
- [x] **Claims Dalya must never say (seller price/PII, named-buyer offer status, guaranteed ROI, etc.)** → §11 `confirmed`

## Still needs Eric / legal / accountant review

Kept open deliberately — do not treat as direct until resolved.

- [ ] **Off-plan "cannot be legally rented before handover/title transfer"** → §3, currently `draft-for-agent only` pending **Eric/legal** verification. (Repo asserts it as law; not yet safe to state.)
- [ ] **PDPL data-rights response deadline** → §12, intentionally **unstated** pending **legal counsel** (sources [S14][S15] disagree on whether a deadline exists in the law).
- [ ] **VAT on a specific brokerage invoice** → §5, rate confirmed but application wording needs **Eric/accountant**.
- [ ] **"Pre-approved" definition for treating a buyer as financing-ready** → §6, `[Eric to approve]` wording.
- [ ] **Buyer-qualification numeric thresholds** (urgent window ~7–14 days, near/medium-term bands, budget-mismatch disqualifier) → §1, `[Eric to verify]` product-tuning, not regulatory.
- [ ] **Joint buyers / multiple decision-makers edge case** → not yet covered in verified-facts; minor, capture if Eric wants a standard line.
- [ ] **Per-brokerage Dalya/managing-brokerage fee** → §5 `Eric decision required` by design (per-tenant config, not a generic platform fact).

## Draft-for-agent only (resolved as policy, not direct)

These are settled — the resolution is "Dalya drafts/escalates, never answers autonomously."

- [x] **NOC issuance timeline** (developer-specific) → §7 `draft-for-agent only`
- [x] **Full deal timeline (≈30–45 days, varies; never quote an exact schedule)** → §7 `draft-for-agent only`
- [x] **Ready-resale closing timeline (≈2–3 weeks once funds confirmed)** → §2 `draft-for-agent only` (transaction-specific)
- [x] **NOC fee (developer-specific amount)** → §5 `draft-for-agent only`
- [x] **Mortgage eligibility / LTV / approval / rates / tax advice** → §6 `draft-for-agent only`
- [x] **Co-broker Form A / BRN / authorization / permit requests** → §8 `draft-for-agent only`
- [x] **Minimum % paid before off-plan assignment (30–50% range)** → §3 `Eric decision required` (whether to state the range at all)

## Do not state

- [x] **Seller's original purchase price / arithmetic that back-calculates it** → §11 `do not state`
- [x] **Confirm/deny a named person's offer status** → §11 `do not state`
- [x] **Guaranteed ROI / yield / resale premium / appreciation** → §11 `do not state`
- [x] **Emaar Oasis 15–25% premium generalized to other listings** → §3 `listing-specific only` / §11 `do not state` when generalized
- [x] **Any instruction that bypasses draft-and-approve** → §11 `do not state`

---

## Current repo alignment

- **Likely current matching concepts:** `BOT_RULES.md` (privacy invariants, off-plan sequence), `dalya-reviewers/real-estate-guru/knowledge-pack.md` + `transaction-reference.md`, `knowledge_base/*.json`, `app/core/ready_property_knowledge.py` (`verified` flag).
- **Likely gaps:** values are not yet machine-readable with status labels — the verified-facts file is now the structured source a loader should read.
- **Files likely affected later (do NOT change now):** `app/core/prompt_builder.py`, `app/core/response_validator.py`, plus a new verified-facts loader. See [verified-facts-runtime-handoff](../product/verified-facts-runtime-handoff.md).
- **Implementation tickets:** "Build Verified Facts loader" + "Gate Dubai regulatory/fee/process claims through Verified Facts" (see BACKLOG.md).
