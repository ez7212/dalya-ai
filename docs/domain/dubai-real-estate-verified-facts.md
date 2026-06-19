# Dubai Real Estate — Verified Facts Pack (v1)

**Status:** Confirmed

**Last research pass:** 2026-06-19. Sources are listed in §15. I prioritized Dubai Land Department / RERA / UAE government sources. Where I used market-practice or brokerage sources, the row is marked for Eric verification.

## Purpose

This is Dalya's proposed single source of truth for Dubai regulatory, DLD, RERA, Trakheesi, NOC, fee, timeline, form, mortgage, and legal-process facts. The chatbot may only state a fact directly after Eric marks it `confirmed`. Until then, Dalya should draft for agent approval or say it cannot answer.

### Fact-status legend

- `confirmed` — Eric has verified and approved this for the stated use. Source-backed rows keep their `[Sx]` citation; rows without one are Eric's confirmed operational or product policy.
- `Eric decision required` — a source may exist, but Dalya's policy/wording depends on how Eric wants the brokerage to operate.
- `draft-for-agent only` — even if true, Dalya should not state it directly to buyers without agent review.
- `do not state` — Dalya should never say this.
- `repo-asserted (unverified)` — appears in code/docs today but needs correction or confirmation.

> Important: This file deliberately separates **official service facts** from **brokerage practice**. Dubai transactions can vary by developer, building, mortgage status, company/person status, POA, and the written agreements between parties.

### Runtime usage policy

This file is the policy source for what Dalya may say. A future loader (see [verified-facts-runtime-handoff](../product/verified-facts-runtime-handoff.md)) will read each row's status label and enforce:

- **Facts may be used only according to their status label.** The label, not the prose, governs runtime behavior.
- **`confirmed` + general fact → may be answered `direct`** if the listing/context matches. (A `direct` runtime policy is only granted to a `confirmed` row that is *not* transaction- or listing-specific.)
- **`confirmed` + transaction-/listing-specific (timing, this buyer's NOC, a specific unit's service charge) → `draft-for-agent only`.** Being source-confirmed does not make a per-transaction value safe to assert; it must be drafted/escalated. The "Dalya direct-answer policy" notes inside each section say which confirmed facts are general vs transaction-specific.
- **`draft-for-agent only` → Dalya must draft/escalate and never answer autonomously.**
- **`do not state` → Dalya must never say this buyer-facing.**
- **`Eric decision required` / `repo-asserted (unverified)` → treat as not-yet-direct; draft for agent until promoted.**
- **Listing-specific facts override generic facts only for that listing** (e.g. a unit's actual service charge from verified listing data overrides any generic statement).
- **If a fact is missing, ambiguous, or stale → Dalya drafts for agent approval.** Absence is never a license to improvise.

---

## 1. Buyer qualification rules Eric uses

**Status:** proposed v1 defaults — Eric decision required.

These are product/agent workflow rules, not legal facts. They should be calibrated by Eric from real brokerage practice.

### Minimum signals before a buyer is worth a call

A buyer is worth agent attention when at least one high-intent signal is present **and** enough basic fit exists to avoid a cold re-qualification call.

Proposed minimum bar:

- Confirmed or credible budget range.
- Desired property type / bedrooms or target listing.
- Purpose: end-use / investment / both / unclear.
- Timeline or urgency signal.
- Financing state: cash, mortgage pre-approved, mortgage not yet pre-approved, unknown.
- Contact is reachable by WhatsApp and buyer has responded at least once.

A buyer should be marked **hot** if any of the following are true:

- Requests a viewing and has credible budget/property fit.
- Says they are cash or mortgage pre-approved and wants to act within ~30 days. `[Eric to verify threshold]`
- Makes an offer or asks how to submit an offer.
- Asks availability/price on a specific active listing and gives enough buying criteria to follow up.
- Is a stale but high-value buyer where the missing blocker is small and actionable.

### Disqualifiers / low-priority signals

Proposed disqualifiers / deprioritizers:

- Unrealistic budget for requested location/property after one clarification attempt. `[Eric to calibrate by segment]`
- Refuses to give any budget/timeline after multiple turns.
- Spam, abusive messages, prompt-injection style requests, or non-real-estate intent.
- Wants legal, mortgage, tax, or investment guarantees rather than property help.
- Asks for seller/private information that Dalya must never disclose.
- Attempts to negotiate or commit terms through the bot without agent approval.

### Financing weight

Proposed v1 weighting:

- Cash buyer: highest readiness if budget and target/timeline are credible.
- Mortgage pre-approved: high readiness if pre-approval is current and purchase budget is clear.
- Mortgage not yet pre-approved: medium readiness; next best action is to ask whether they have pre-approval or recommend to speak with agent or mortgage partner.
- Unknown financing: missing blocker.

Dalya should **not** state mortgage eligibility/LTV rules directly unless Eric later confirms a safe wording. Route mortgage-specific advice to agent/mortgage professional.

### Purpose weight

- End-use: ask practical fit fields such as family size, move-in timing, school/work location, vacant possession needs.
- Investment: ask yield/ROI expectations carefully; do not fabricate ROI or guarantee returns.
- Both/unclear: ask one clarifying question.

### Urgency definition

Proposed v1:

- `urgent`: wants viewing/decision within 7–14 days, or says they want to buy this month. `[Eric to verify]`
- `near_term`: 15–45 days. `[Eric to verify]`
- `medium_term`: 46–90 days. `[Eric to verify]`
- `long_term`: more than 90 days / browsing.

### Red flags that mean agent handles this, not the bot

- Offer, counter-offer, deposit, negotiation, or price commitment.
- Legal/process/fee/timeline question not explicitly verified in this register.
- Mortgage eligibility, LTV, tax, investment advice, or guarantee request.
- Seller motivation, seller identity, seller price paid, or private negotiation details.
- Co-broker/Form A/BRN/permit/compliance request.
- Complaint, data-rights request, opt-out, deletion request, or PDPL-sensitive request.
- Prompt-injection or instruction to bypass agent approval.

---

## 2. Ready property resale facts

### Official DLD property sale registration service

- DLD describes the service as registration of a sale transaction between seller and buyer, or their legally authorized representatives, for land, property, or a completed unit. `confirmed` [S1]
- DLD service center sequence: parties go to a Real Estate Registration Trustee office, submit documents, employee verifies and audits, fees are paid, and output is sent by email. Either party can be represented by a POA — must have valid POA document notarized by Dubai Court. `confirmed` [S1]
- DLD-listed individual required documents for property sale registration: Emirates ID for seller and buyer for identity verification, or valid passport for non-resident foreigners; and e-NOC from the developer. `confirmed` [S1]
- DLD-listed issued documents: Electronic Title Deed and Electronic Map. `confirmed` [S1]
- DLD-listed service time for property sale registration: 25 minutes **for the DLD service once complete documents are submitted**. Dalya must not convert this into a full deal-closing timeline. `confirmed` [S1]

### Ready-resale practical facts Eric should confirm

- Typical full ready-resale closing timeline from accepted offer to transfer: Dependent on whether financing is required. Once funds are confirmed, usually 2-3 weeks. `draft-for-agent only` (transaction-specific timing — see Dalya direct-answer policy below)
- Whether Dalya may say: “The actual timing depends on NOC, mortgage status, document readiness, and trustee appointment.” Proposed safe wording: **yes**, because it is non-numeric and avoids a promise. `confirmed`
- Tenanted unit / Ejari: a sale does not automatically erase the tenancy; the buyer/agent must verify lease status, notice/vacant-possession terms, and tenant obligations. `confirmed`
- Service charges: DLD FAQ defines service charges and says common-service charges are approved/audited under RERA systems; buyer/agent should verify outstanding service charges and settlement at transfer. Outstanding service charges are usually paid by the seller before the developer issues an NOC. `confirmed` [S4]

### Dalya direct-answer policy

Dalya may state DLD-listed service facts above only if Eric approves. For anything transaction-specific — tenanted status, outstanding service charges, NOC timing, mortgage release timing, exact trustee booking availability — Dalya should draft for agent approval.

---

## 3. Off-plan resale facts

### Oqood / provisional registration

- DLD's “Request to register the initial sale” service allows a real estate developer to register units sold off-plan, or land plots whose value has not been fully paid, at the provisional register. `confirmed` [S8]
- DLD's “Request to complete the initial procedures data” service is handled through the Oqood portal and involves selecting a property, filling details, attaching documents, selecting payment method, and receiving output by email. `confirmed` [S9]

### Developer NOC / approval

- DLD FAQ says that if a property is sold off-plan, the department must be provided with a No Objection Certificate from the competent authority, the developer. `confirmed` [S4]
- DLD property sale registration for freehold areas requires a developer e-NOC. `confirmed` [S1]

### What not to state directly yet

- Minimum percentage paid before off-plan resale/assignment is allowed: **developer-specific; do not state a generic threshold.** Many market sources mention 30–50% and Dalya can safely state this range, but must not promise that a specific project will allow off-plan assignment at that percentage. `Eric decision required` (whether Dalya may state the 30–50% range at all)
- “Off-plan cannot be legally rented before handover and title transfer”: **do not state directly.** This repo assertion needs Eric/legal verification. Proposed safe replacement: “For off-plan rental/occupation questions, I’ll have the agent confirm the current status and what is legally possible for that project.” `draft-for-agent only` (pending Eric/legal verification)
- NOC issuance timeline for off-plan resale: `draft-for-agent only` until Eric verifies.
- Physical handover date, developer decisions, construction completion, service-charge estimates, or future resale premium: `draft-for-agent only` unless explicitly present in verified listing data. Some payments are based on construction completion percentage and construction may be delayed due to unforseen events. 

### Scope-locked listing facts

- The Emaar Oasis “15–25% branded-villa premium” remains listing-data scoped only if it is present in a specific listing knowledge base and labelled as a projection/analyst estimate. It must never be generalized as a market rule. `listing-specific only` (do not generalize)

---

## 4. Required documents by transaction type

| Transaction | Documents Dalya may reference after Eric approval | Status |
|---|---|---|
| Ready resale — buyer side | Emirates ID for UAE residents; valid passport for non-resident foreigners; proof of funds or mortgage pre-approval when relevant; Form B if brokerage uses it; manager cheque/payment details as guided by agent/trustee. | DLD ID/passport source-confirmed; other items Eric to approve. [S1] |
| Ready resale — seller side | Emirates ID/passport; NOC from developer in freehold areas; title deed; Form A/listing authority; Form F/MOU once terms agreed; POA if representative; mortgage liability/release documents if mortgaged. | e-NOC + ID/passport source-confirmed; other items Eric to approve. [S1][S2] |
| Off-plan resale — buyer side | Emirates ID/passport; proof of funds/mortgage readiness; developer/Oqood transfer requirements; Form B if used; payment-plan acknowledgement. | Eric to approve. |
| Off-plan resale — seller side | SPA; Oqood / provisional registration evidence; payment receipts / statement; developer NOC; ID/passport; POA if applicable; Form A/F as applicable. | Eric to approve. |
| Mortgaged ready property | Bank liability letter or developer remaining-amount letter; UAE ID/passport; manager cheques; POA if representative; mortgage release letter before final completion. | DLD source-confirmed for mortgaged-sale service. [S2] |
| Company buyer/seller | Company registration procedure may be required for an unregistered company. Company-specific document list should be handled by agent/trustee. | DLD source-confirmed at high level; exact list Eric/trustee to verify. [S1][S2] |

### RERA / DLD contracts and forms

- Contract A / Form A: agreement to market a property between seller and real estate brokerage. `confirmed` [S10]
- Contract B / Form B: agreement of desire to purchase a property between buyer and real estate broker. `confirmed` [S10]
- Contract F / Form F: agreement to sell a property between seller and buyer. `confirmed` [S10]
- DLD has published broker journeys for creating Contract A, B, and F via Dubai REST / Dubai Brokers workflow. `confirmed` [S11][S12][S13]

Dalya should avoid telling buyers “you need Form X now” unless the agent has confirmed the transaction stage. Don't push the buyer to ask for a specific Form - instead direct the agent to initiate the form filing process. Safer wording: “The agent will confirm the right DLD/RERA forms for this stage.”

---

## 5. Fees and commissions

> Fees are high-risk. Even source-confirmed values should be approved by Eric before buyer-facing use.

| Fee | Value / policy | Paid to | Status |
|---|---|---|---|
| DLD sale registration fee | Industry standard is buyer pays 4% of transaction price. | DLD | `confirmed` [S1] |
| Title Deed Certificate Issuance Fee | AED 250. | DLD | `confirmed` [S1] |
| Map fees | AED 225 unified map under Dubai Municipality; AED 100 map for lands not under Dubai Municipality; AED 250 villas/apartments. | DLD | `confirmed` [S1] |
| Knowledge / innovation fees | AED 10 knowledge fee + AED 10 innovation fee listed in DLD sale registration fees. | DLD | `confirmed` [S1] |
| Service partner / trustee fee | DLD sale registration page lists AED 4,000 + VAT if sale value is AED 500,000 or more; AED 2,000 + VAT if less than AED 500,000.| Real Estate Registration Trustee / service partner | `confirmed` [S1][S4] |
| Mortgaged property sale service fee | DLD mortgaged-sale service lists AED 1,000 plus knowledge/innovation and additional mortgage-release/registrar fees. | DLD / registrar | `confirmed` [S2] |
| Mortgage fee, if any | Varies depending on the bank | DLD | `confirmed` [S2] |
| Broker commission | Commissions are set by seller agent and buyer agent and confirmed in Form A/B. The industry standard is 2%, but commonly negotiated. Dalya should not infer that it is 2% for every listing. | Broker | `confirmed` [S4] |
| VAT on commission | UAE VAT standard rate is 5% on taxable supplies. Whether and how it applies to a particular brokerage invoice depends on VAT registration/supply facts. | FTA / tax authority | `confirmed` (standard 5% VAT rate); brokerage-invoice wording: `Eric decision required` (accountant) [S7] |
| Dalya / managing-brokerage fee | No generic multi-tenant fee should be stated. Any brokerage-specific fee must come from that brokerage’s configured policy/contract. | Brokerage | `Eric decision required` |
| NOC fee | Developer-specific. Dalya should not quote a generic NOC fee unless listing/developer source is verified. | Developer | `draft-for-agent only` |
| Buyer “saves X%” comparison | Do not use legacy Mahoroba 0.15% / “save 1.85%” framing in the multi-tenant product. | N/A | `do not state unless tenant-specific marketing copy is explicitly approved` |

---

## 6. Mortgage / cash buyer notes

- Dalya may ask whether the buyer is cash, mortgage pre-approved, mortgage in progress, or not sure. `confirmed`
- Dalya should not state mortgage eligibility, LTV, approval likelihood, bank timing, interest rates, or legal/tax advice. `draft-for-agent only`
- “Pre-approved” should mean the buyer says they already have bank/mortgage pre-approval; Dalya should still mark it as buyer-stated until the agent verifies evidence. `[Eric to approve]`
- Cash buyers are usually operationally faster/easier than mortgage buyers, but exact timing should not be stated. `[from general market practice — Eric to verify]`
- Mortgaged property sale has a DLD-defined process involving liability letter, cheques, bank/developer debt payment, mortgage release letter, and completion of mortgage release/sale/mortgage procedures. `confirmed` [S2]

---

## 7. NOC / transfer / trustee office process

### Ready sale / completed unit

Source-confirmed DLD sale registration basics:

1. Parties go to a Real Estate Registration Trustee office.
2. Required documents are submitted and uploaded via the digital vault.
3. Employee enters transaction details and performs an audit.
4. Fees are paid and a receipt/output is sent by email.
5. Buyer information is entered by Emirates ID or passport.
6. DLD service page lists 25 minutes service time once the service is processed. [S1]

Required DLD documents include buyer/seller Emirates ID or passport for non-resident foreigners, plus developer e-NOC in freehold areas via Dubai REST. [S1]

### Mortgaged property sale

Source-confirmed DLD mortgaged-sale basics:

1. Parties go to a Real Estate Registration Trustee center.
2. Customer submits required documents.
3. Transaction details are entered.
4. Fees are paid.
5. DLD auditor sends a real estate registration certificate link and the bank indebtedness cheque is delivered so the seller can obtain mortgage release.
6. After mortgage release letter is submitted, mortgage release, sale, and mortgage procedures are completed if applicable. [S2]

### Off-plan resale / assignment

- DLD FAQ says off-plan sale requires NOC from the developer/competent authority. `confirmed` [S4]
- Once NOC is obtained, process follows the same as ready sale. `confirmed`

### Timelines

- NOC issuance timeline: dependent on developer, can be as quick as 1 day if all outstanding service charges and payments are fulfilled. `draft-for-agent only` (developer-specific timing)
- Full deal timeline from accepted offer to transfer: typically within 30-45 days, but can vary. Should not quote an exact schedule. `draft-for-agent only`
- DLD service time (25 minutes / 15–20 minutes for specific services) is not the same as end-to-end transaction timeline. `confirmed` [S1][S2]

---

## 8. Trakheesi / permit / advertising rules

- DLD has a Real Estate Ad Permit service through the Tarakhesi system. The service flow: login to Tarakhesi, select service, fill required information/upload documents, employee reviews/approves, pay, receive e-permit certificate. `confirmed` [S3]
- DLD has a service to verify licenses and permits issued by the Land Department via Trakheesi; the service is immediate and available through DLD website / Dubai REST App. `confirmed` [S5]
- DLD FAQ says obtaining a permit from RERA to advertise real estate projects is mandatory for developers. `confirmed` [S4]
- DLD rules/regulations list circulars for linking real estate permits with Form A and real estate advertisement terms/QR code systems. `confirmed` [S6]

Dalya policy:

- Co-broker requests for Form A, BRN, authorization, permit, or listing compliance should go to agent approval. `draft-for-agent only`
- Dalya must never claim a listing is authorized/permitted unless the listing record contains a verified permit/authorization source. `do not state unless verified listing data`
- Dalya should not generate or promise Trakheesi/permit status; it may say the agent will confirm permit/authorization.

---

## 9. Claims Dalya MAY say directly

Only after Eric marks the row confirmed.

### Allowed directly from listing data

- Price, bedrooms, bathrooms, size, community, view, parking, furnishing, service-charge figure, payment plan, handover date, permit number, and availability **only if present in verified listing/source data**.
- If data is missing or stale, Dalya should draft for agent or say it will confirm.

### Proposed safe general statements

- “The agent will confirm the exact transfer costs and documents for this transaction.”
- “If you are using a mortgage, the agent/mortgage advisor should confirm the approval and bank process.”
- “For off-plan resale, developer/project requirements can vary, so the agent will confirm the applicable NOC/assignment conditions.”
- “I can share the listing details we have, but I’ll have the agent confirm anything legal, financial, or process-specific.”

### DLD/source-confirmed facts that can become direct after Eric approval

- DLD property sale registration documents and DLD service fees in §2/§5. [S1]
- DLD mortgaged-sale high-level process/fees in §6/§7. [S2]
- Contract A/B/F definitions from the DLD brokerage practice guide in §4. [S10]
- DLD/Tarakhesi ad-permit and permit-verification service facts in §8. [S3][S5]

---

## 10. Claims Dalya MUST draft for agent approval

- Any offer, counter-offer, negotiation move, deposit, MOU term, or price concession.
- Any exact regulatory/fee/timeline number not marked confirmed in this file.
- Anything about DLD/NOC/trustee timing in a specific transaction.
- Mortgage eligibility, LTV, interest, bank approval, valuation, or tax advice.
- Investment advice, ROI/yield promise, resale premium, guaranteed appreciation.
- Legal advice, contract interpretation, tenant/vacant-possession legal rights.
- Co-broker fee splits, Form A/BRN/permit/authorization requests.
- Developer approval/assignment requirements unless verified for that exact project/listing.
- Specific other buyer’s offer status or identity.
- Any statement based on private agent notes.

---

## 11. Claims Dalya MUST NEVER say

- Seller’s original purchase price, seller PII, seller motivation if private, or arithmetic allowing back-calculation of seller’s original price.
- Confirm or deny whether a named person has made an offer.
- “This will definitely close by [date]” or “NOC will take [X] days” unless agent approves in context.
- Guaranteed ROI, yield, resale premium, rental income, appreciation, or “best investment” claims.
- That a buyer is mortgage eligible or approved unless buyer/agent has provided verified pre-approval context — and even then phrase as buyer-stated/agent-verified, not Dalya’s guarantee.
- That an off-plan property can/cannot legally be rented before handover/title transfer until Eric/legal confirms exact safe wording.
- The Emaar Oasis 15–25% premium applied to any other listing or as a guarantee.
- Any instruction that bypasses draft-and-approve.

---

## 12. PDPL / data-rights handling

- UAE PDPL gives data subjects rights relating to personal data, but public summaries differ on whether the federal law itself specifies a response deadline. Some legal summaries say there is no explicit timescale in the law/executive regulations; others cite one month with possible extension. Dalya should **not state a response deadline** until legal counsel/Eric confirms. `draft-for-agent / compliance only` [S14][S15]
- Any deletion/access/correction/opt-out request should be escalated to a human/admin workflow and logged without exposing buyer PII in broad logs.

---

## 13. Last verified date

`[2026-06-20]`

## 14. Verified by

`Eric Zhu`

---

## 15. Source register

- [S1] Dubai Land Department — Property Sale Registration: https://dubailand.gov.ae/en/eservices/property-sale-registration/
- [S2] Dubai Land Department — Registering the Sale of a Mortgaged Property: https://dubailand.gov.ae/en/eservices/registering-the-sale-of-a-mortgaged-property/
- [S3] Dubai Land Department — Real Estate Ad Permit: https://dubailand.gov.ae/en/eservices/real-estate-ad-permit/
- [S4] Dubai Land Department — Frequently Asked Questions: https://dubailand.gov.ae/en/frequently-asked-questions/
- [S5] Dubai Land Department — Verify License and Permits: https://dubailand.gov.ae/en/eservices/validate-real-estate-licenses-and-permits/
- [S6] Dubai Land Department — Rules & Regulations / license circulars: https://dubailand.gov.ae/en/about-dubai-land-department/rules-regulations/
- [S7] UAE Government / FTA VAT pages: https://u.ae/en/information-and-services/finance-and-investment/taxation/vat/valueaddedtaxvat and https://tax.gov.ae/en/
- [S8] Dubai Land Department — Request to register the initial sale: https://dubailand.gov.ae/en/eservices/request-to-register-the-initial-sale/
- [S9] Dubai Land Department — Request to complete the initial procedures data: https://dubailand.gov.ae/en/eservices/request-to-complete-the-initial-procedures-data/
- [S10] DLD/RERA Real Estate Brokerage Practice Guide 2024: https://dubailand.gov.ae/media/i31iv1n0/real_estate_brokerage_practice_guide_2024.pdf
- [S11] DLD Broker journey to create Contract A: https://dubailand.gov.ae/media/xcrjstjp/brokers-journey-to-create-contract-a_en.pdf
- [S12] DLD Broker journey to create Contract B: https://dubailand.gov.ae/media/0n2dbynt/broker-s-journey-to-create-contract-b_en.pdf
- [S13] DLD Broker journey to create Contract F: https://dubailand.gov.ae/media/ofeb4lyy/broker-s-journey-to-create-contract-f_en.pdf
- [S14] UAE official data-protection overview: https://u.ae/en/about-the-uae/digital-uae/data/data-protection-laws
- [S15] CMS UAE data protection overview noting no response timescale in UAE DPL summary: https://cms.law/en/int/expert-guides/cms-expert-guide-to-data-protection-and-cyber-security-laws/uae

---

## Current repo alignment

- Likely current matching concepts: `BOT_RULES.md`, `dalya-reviewers/real-estate-guru/knowledge-pack.md`, `transaction-reference.md`, `knowledge_base/*.json`, `app/core/ready_property_knowledge.py`, `app/core/prompt_builder.py`, and `app/core/response_validator.py`.
- Likely gaps: exact values appear inline in prompts/reviewer docs without machine-readable verified status; legacy Mahoroba fee framing is not safe for a multi-tenant product.
- Files likely affected later: `app/core/prompt_builder.py`, `app/core/response_validator.py`, and a new verified-facts loader.
- Implementation ticket: “Route exact Dubai claims through Verified Facts register.”
