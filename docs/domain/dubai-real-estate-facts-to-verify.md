# Dubai Real Estate — Facts to Verify (v1)

**For Eric.** This is the checklist of specific facts Dalya needs you to verify **before** they may be used in chatbot or dashboard copy. Until a row is checked and the value copied into [dubai-real-estate-verified-facts.md](./dubai-real-estate-verified-facts.md), Dalya must draft-for-agent or decline rather than state the fact.

**Ground rule:** No exact regulatory/DLD/RERA/Trakheesi/NOC/fee/timeline/form/mortgage/legal-process value has been invented as authoritative in these docs. Rows below marked `repo-asserted` already appear in the codebase (usually in `BOT_RULES.md` or the reviewer knowledge pack) but were never formally verified — confirming or correcting them is the priority because runtime behavior already leans on them.

How to use: for each row, set the real value (or "correct as stated"), then move it into the verified-facts file with a date. Strike rows that Dalya should never state directly even if true (mark "draft-for-agent only").

---

## A. Fees & transfer costs (highest risk)

- [ ] **DLD transfer fee** — repo says "commonly 4% of purchase price + admin fees." Confirm exact %, what base it applies to, and admin fee amount. `repo-asserted`
- [ ] **Who pays the DLD transfer fee** (buyer / split) in the resale transactions Dalya handles.
- [ ] **Standard buyer agency commission** — repo references "~2% + VAT, subject to agreement." Confirm whether Dalya states a market-standard figure at all.
- [ ] **Dalya / managing-brokerage fee** — repo references a 0.15% flat figure tied to legacy Mahoroba pricing. Confirm what Dalya states now that Mahoroba is one tenant among many (likely: nothing generic — it's per-brokerage). `repo-asserted`
- [ ] **VAT applicability** on brokerage commission.
- [ ] **NOC fee** — developer-specific. Confirm whether Dalya ever quotes a figure or always defers.
- [ ] **Trustee office / transfer registration fee.**
- [ ] **Mortgage registration fee** (if Dalya ever references it).
- [ ] **Whether any "buyer saves X%" comparison is allowed** in the multi-tenant model (legacy Mahoroba framing).

## B. Forms & documents

- [ ] **Form A** — seller–agent listing agreement: confirm name, purpose, when it applies. `repo-asserted`
- [ ] **Form B** — buyer–agent agreement: confirm. `repo-asserted`
- [ ] **Form F / MOU** — sale agreement: confirm. `repo-asserted`
- [ ] **Buyer document checklist (ready resale).**
- [ ] **Seller document checklist (ready resale).**
- [ ] **Buyer document checklist (off-plan resale).**
- [ ] **Seller document checklist (off-plan resale).**
- [ ] **Proof-of-funds / mortgage pre-approval** — what Dalya may ask a buyer for, and at what stage.

## C. NOC / transfer / trustee sequencing

- [ ] **NOC issuance timeline** — repo says "typically 2–4 weeks." Confirm or correct. `repo-asserted`
- [ ] **Trustee office title-registration timeline** — repo says "typically 30–45 days from offer acceptance." Confirm or correct. `repo-asserted`
- [ ] **Full off-plan closing sequence** (offer → MOU → NOC → trustee registration → owner of record → takes over SPA schedule → physical handover later) — confirm the sequence is accurate as a general statement. `repo-asserted`
- [ ] **Ready-resale transfer sequence** (if it differs from off-plan).
- [ ] **NOC sequencing** — does the seller settle a balance/gap before NOC is issued? Confirm.

## D. Off-plan resale restrictions

- [ ] **Developer approval required to resell/assign before handover?** Confirm the general rule and whether it's developer-specific.
- [ ] **Minimum % paid to developer before resale/assignment is allowed.** Confirm whether Dalya states any general threshold.
- [ ] **"Off-plan cannot be legally rented before handover and title transfer"** — repo states this as law in `BOT_RULES.md`. Confirm it is accurate before Dalya asserts it. `repo-asserted`
- [ ] **Oqood registration** — what it is, whether Dalya references it.

## E. Mortgage / cash buyer

- [ ] **Whether Dalya may state ANY mortgage eligibility / LTV / pre-approval rule** (default assumption: no — refer to a mortgage professional). Confirm.
- [ ] **Mortgage pre-approval requirement** — what Dalya should ask for, and what "pre-approved" must mean before treating a buyer as financing-ready.
- [ ] **Process/speed differences** between cash and mortgage buyers worth surfacing to agents.

## F. Trakheesi / permit / advertising

- [ ] **Trakheesi advertising permit requirement** — confirm and decide what (if anything) Dalya says about it.
- [ ] **Co-broker Form A / BRN requests** — what Dalya may say vs must escalate. (Repo currently escalates.)
- [ ] **Advertising-claim constraints** — what Dalya must never claim about a listing.

## G. Edge cases

- [ ] **Company / corporate buyer** — any different document or process Dalya should flag to the agent.
- [ ] **Overseas / non-resident buyer** — anything different (power of attorney, remote signing, fund transfer) worth flagging.
- [ ] **Joint buyers / multiple decision-makers** — what the agent needs to know.
- [ ] **PDPL data-rights response window** — repo references handling data-rights requests; confirm any stated timeline before Dalya commits to one.

## H. Claims that require agent approval (confirm the list)

- [ ] Confirm the list in verified-facts §10 ("must draft for agent approval") matches how Eric wants Dalya to behave.
- [ ] Confirm the "must never say" hard invariants in verified-facts §11.
- [ ] Confirm buyer-qualification rules (verified-facts §1) — the actual bar Eric uses to decide a buyer is worth attention.

---

## Current repo alignment

- **Likely current matching concepts:** `BOT_RULES.md` (fees, off-plan sequence, privacy invariants), `dalya-reviewers/real-estate-guru/knowledge-pack.md` + `transaction-reference.md` (forms/fees as general guidance), `knowledge_base/*.json` (per-listing facts), `app/core/ready_property_knowledge.py` (`verified` flag defaults False).
- **Likely gaps:** values are stated as general knowledge ("commonly/typically/often") and were never verified; the Mahoroba fee framing predates multi-tenant.
- **Files likely affected later:** `app/core/prompt_builder.py`, `app/core/response_validator.py`, plus a verified-facts loader (do not change now).
- **Implementation ticket suggestion:** "Route exact Dubai claims through Verified Facts register."
