# §4 — The Gap Analysis Money Table

_Dalya content gap analysis — 2026-04-24_

## Methodology

We translated the five language-specific demand + supply research reports into a **priority score** for every topic × language cell in the opportunity map. The unified demand CSV (347 observed queries across EN / AR / RU / ZH / HI) feeds a scoring pipeline that harmonises queries into 16 topic clusters and computes:

- **demand_score (1–10)** — aggregated from query-level H/M/L counts and coverage breadth per topic × language. Formula: `min(10, 2 + 0.9·H + 0.5·M + 0.25·L)` where H/M/L are observed-query counts in that cell. A cell with no observed queries defaults to 1 and is flagged in the notes column.
- **supply_score (1–10)** — qualitative verdict from the six research files (§5 saturation tables in each) and the competitive-landscape language-coverage matrix. 1 = empty, 5 = moderate, 10 = saturated.
- **gap_score = demand_score − supply_score**. Positive = opportunity, negative = over-supplied.
- **language_weight** — Dalya's strategic weighting: EN=1.0 baseline, AR=0.9 (regulatory/GCC/regional), RU=0.7 (post-2022 exit cohort), ZH=0.4 (selective — WeChat/XHS carry the funnel), HI=0.2 (selective — Hinglish compliance wedge only).
- **dalya_strategic_fit (0.5–1.5)** — 1.5 if the topic demonstrates licensing / data / 0.15% positioning; 1.0 default; 0.5 if off-brand (e.g. market news).
- **priority_score = gap_score × language_weight × dalya_strategic_fit**. Sorted descending. This is the number that should drive the publishing plan.
- **recommended** — TRUE when priority_score ≥ 2.5 AND gap_score > 0. Hindi and Mandarin cells have stricter thresholds (priority ≥ 1.0 / 1.2) to enforce the 'selective' rule from the language-weighting framework.

Every priority rank in the table below is reproducible from `reports/data/gap-money-table.csv` and the underlying `reports/data/demand.csv`.

## Full money table (sorted by priority_score, descending)

| # | Topic cluster | Lang | Demand | Supply | Gap | Weight | Fit | **Priority** | Intent | Rec | Notes |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 1 | Marketplace / listing channels | EN | 6.2 | 2 | +4.20 | 1.0 | 1.4 | **5.88** | transactional | TRUE | No guide on 'list your off-plan without an agent' — EMPTY — 0H 4M 9L queries; 13 total |
| 2 | Banking / getting paid | RU | 7.2 | 2 | +5.20 | 0.7 | 1.5 | **5.46** | transactional | TRUE | EMPTY from brokerage voice; VC.ru + MIGRON hold it from diaspora angle — 3H 5M 0L queries; 8 total |
| 3 | Tax — home-country residual | RU | 10.0 | 5 | +5.00 | 0.7 | 1.5 | **5.25** | informational | TRUE | 3-НДФЛ/CRS owned by legal blogs; brokerage voice EMPTY — biggest RU opportunity — 8H 7M 0L queries; 15 total |
| 4 | NOC procedures | EN | 8.0 | 4 | +4.00 | 1.0 | 1.3 | **5.20** | commercial-investigational | TRUE | Generic NOC guides exist; no developer-by-developer fee table — gap — 3H 5M 3L queries; 11 total |
| 5 | Fees & net proceeds | EN | 7.0 | 4 | +3.00 | 1.0 | 1.4 | **4.20** | commercial-investigational | TRUE | DLD fees covered verbally; no seller calculator — gap — 2H 6M 1L queries; 9 total |
| 6 | Tax — home-country residual | EN | 6.0 | 3 | +3.00 | 1.0 | 1.3 | **3.90** | informational | TRUE | US covered (TaxesForExpats); UK/India/GCC fragmented — 2H 4M 1L queries; 7 total |
| 7 | Payment plan arrears / distress | AR | 6.2 | 3 | +3.20 | 0.9 | 1.2 | **3.46** | informational | TRUE | Excel + fragmented legal; consequences explainer missing — 3H 3M 0L queries; 6 total |
| 8 | Process & eligibility | AR | 9.9 | 6 | +3.90 | 0.9 | 0.9 | **3.16** | informational | TRUE | DXB+Bayut-AR cover basics; not journey-framed — 6H 3M 4L queries; 13 total |
| 9 | NOC procedures | AR | 4.7 | 2 | +2.70 | 0.9 | 1.3 | **3.16** | commercial-investigational | TRUE | EMPTY: no Emaar/Damac/Sobha/Nakheel Arabic NOC guide — highest-intent gap — 1H 2M 3L queries; 6 total |
| 10 | Process & eligibility | RU | 9.9 | 5 | +4.90 | 0.7 | 0.9 | **3.09** | informational | TRUE | VC.ru legal + 2 brokerages; no canonical brokerage guide — 6H 5M 0L queries; 11 total |
| 11 | Commission — 0.15% vs 2% | EN | 6.8 | 5 | +1.80 | 1.0 | 1.5 | **2.70** | commercial-investigational | TRUE | Rate explained; 0.15% framing owned by nobody — core Dalya lane — 2H 5M 2L queries; 9 total |
| 12 | Tax — home-country residual | AR | 5.3 | 3 | +2.30 | 0.9 | 1.3 | **2.69** | informational | TRUE | APIL + Al Khaleej fragments; resident-vs-non-resident definitive explainer missing — 2H 3M 0L queries; 5 total |
| 13 | Developer-specific rules | AR | 3.0 | 1 | +2.00 | 0.9 | 1.1 | **1.98** | commercial-investigational | FALSE | EMPTY (Dalya's biggest Arabic opening per research) — 0H 2M 0L queries; 2 total |
| 14 | Regulatory / RERA | AR | 8.2 | 6 | +2.20 | 0.9 | 0.9 | **1.78** | informational | FALSE | Trakheesi well-covered by Bayut/Dubizzle/DLD; competitive — 6H 1M 1L queries; 8 total |
| 15 | Commission — 0.15% vs 2% | AR | 6.3 | 5 | +1.30 | 0.9 | 1.5 | **1.76** | commercial-investigational | FALSE | Commission at 2% covered; 0.15% framing absent — 2H 4M 2L queries; 8 total |
| 16 | Payment plan arrears / distress | EN | 5.4 | 4 | +1.40 | 1.0 | 1.2 | **1.68** | informational | FALSE | Buyer-cancellation dominant; seller distress missing — 1H 5M 0L queries; 6 total |
| 17 | Developer-specific rules | RU | 4.0 | 2 | +2.00 | 0.7 | 1.1 | **1.54** | commercial-investigational | FALSE | Emaar-40% mentioned; others unaddressed in Russian — 0H 4M 0L queries; 4 total |
| 18 | Oqood & DLD mechanics | AR | 8.3 | 7 | +1.30 | 0.9 | 1.3 | **1.52** | informational | FALSE | DLD service catalog + Westgate + Taraf; competitive — 4H 5M 1L queries; 10 total |
| 19 | Remote selling / POA | RU | 5.7 | 4 | +1.70 | 0.7 | 1.2 | **1.43** | transactional | FALSE | Fragments exist; integrated 'sell from Moscow without flying' playbook missing — 3H 2M 0L queries; 5 total |
| 20 | Tax — home-country residual | HI | 8.9 | 4 | +4.90 | 0.2 | 1.4 | **1.37** | informational | FALSE | BS Hindi has one FEMA piece; Hinglish wedge is real — ED/FAIU compliance — 1H 11M 2L queries; 14 total |
| 21 | Process & eligibility | ZH | 7.7 | 4 | +3.70 | 0.4 | 0.9 | **1.33** | informational | FALSE | Buyer-framed only; no seller-exit guide — 3H 5M 2L queries; 10 total |
| 22 | NOC procedures | RU | 4.4 | 3 | +1.40 | 0.7 | 1.3 | **1.27** | commercial-investigational | FALSE | Housearch generic; Emaar-only mentioned; Damac/Sobha/Nakheel almost nothing — 1H 3M 0L queries; 4 total |
| 23 | Fees & net proceeds | RU | 5.2 | 4 | +1.20 | 0.7 | 1.4 | **1.18** | commercial-investigational | FALSE | Goldenbee covers fees; no calculator for distressed exit — 3H 1M 0L queries; 4 total |
| 24 | Regulatory / RERA | ZH | 5.7 | 3 | +2.70 | 0.4 | 0.9 | **0.97** | informational | FALSE | Golden Visa saturated; RERA thin — 3H 2M 0L queries; 5 total |
| 25 | Process & eligibility | EN | 10.0 | 9 | +1.00 | 1.0 | 0.9 | **0.90** | informational | FALSE | Bayut/PF/Provident/Betterhomes saturated; template-uniform — 5H 11M 3L queries; 19 total |
| 26 | Marketplace / listing channels | RU | 2.9 | 2 | +0.90 | 0.7 | 1.4 | **0.88** | transactional | FALSE | Listings only on portals; propertyfinder/bayut lack RU blog — 1H 0M 0L queries; 1 total |
| 27 | Commission — 0.15% vs 2% | RU | 4.8 | 4 | +0.80 | 0.7 | 1.5 | **0.84** | commercial-investigational | FALSE | Prian explains 2%; no 'save AED while underwater' framing — 2H 2M 0L queries; 4 total |
| 28 | Pricing & benchmarking | EN | 3.5 | 3 | +0.50 | 1.0 | 1.3 | **0.65** | commercial-investigational | FALSE | Edwards & Towers exit guide; no public AVM — 0H 3M 0L queries; 3 total |
| 29 | Process & eligibility | HI | 5.3 | 2 | +3.30 | 0.2 | 0.9 | **0.59** | informational | FALSE | Observed machine-translations only; structurally unwinnable in pure Hindi — 2H 1M 4L queries; 7 total |
| 30 | Remote selling / POA | ZH | 3.0 | 2 | +1.00 | 0.4 | 1.2 | **0.48** | transactional | FALSE | Near-empty; overseas-seller path uncontested — 0H 1M 2L queries; 3 total |
| 31 | Oqood & DLD mechanics | ZH | 3.9 | 3 | +0.90 | 0.4 | 1.3 | **0.47** | informational | FALSE | 阿库德 niche but rising; very thin — 1H 2M 0L queries; 3 total |
| 32 | Tax — home-country residual | ZH | 3.9 | 3 | +0.90 | 0.4 | 1.3 | **0.47** | informational | FALSE | Generic 'no tax Dubai'; CRS+遣返 angle empty — 1H 2M 0L queries; 3 total |
| 33 | Pricing & benchmarking | RU | 3.5 | 3 | +0.50 | 0.7 | 1.3 | **0.45** | commercial-investigational | FALSE | Goldenbee index only; no seller-facing valuation tool — 0H 3M 0L queries; 3 total |
| 34 | Documents & forms (Form F/A, Trakheesi) | RU | 5.5 | 5 | +0.50 | 0.7 | 1.2 | **0.42** | informational | FALSE | Form F via VC.ru; Form A/Trakheesi thin — 3H 1M 1L queries; 5 total |
| 35 | Commission — 0.15% vs 2% | ZH | 4.7 | 4 | +0.70 | 0.4 | 1.5 | **0.42** | commercial-investigational | FALSE | Uniform 2%-buyer-paid; seller-side commission savings absent — 3H 0M 0L queries; 3 total |
| 36 | Commission — 0.15% vs 2% | HI | 2.2 | 1 | +1.20 | 0.2 | 1.5 | **0.36** | commercial-investigational | FALSE | Zero organic Hindi supply on commission; wedge lives inside compliance pieces — 0H 0M 1L queries; 1 total |
| 37 | NOC procedures | HI | 2.2 | 1 | +1.20 | 0.2 | 1.3 | **0.31** | commercial-investigational | FALSE | Zero native Hindi NOC content; English supply dominates — 0H 0M 1L queries; 1 total |
| 38 | SPA transfer | HI | 2.2 | 1 | +1.20 | 0.2 | 1.3 | **0.31** | informational | FALSE | Empty — 0H 0M 1L queries; 1 total |
| 39 | Oqood & DLD mechanics | HI | 2.2 | 1 | +1.20 | 0.2 | 1.3 | **0.31** | informational | FALSE | Effectively empty — 0H 0M 1L queries; 1 total |
| 40 | Regulatory / RERA | HI | 2.5 | 1 | +1.50 | 0.2 | 0.9 | **0.27** | informational | FALSE | News-framed only; procedural empty — 0H 1M 0L queries; 1 total |
| 41 | Developer-specific rules | HI | 2.2 | 1 | +1.20 | 0.2 | 1.1 | **0.26** | commercial-investigational | FALSE | Zero dedicated coverage — 0H 0M 1L queries; 1 total |
| 42 | Banking / getting paid | ZH | 2.5 | 2 | +0.50 | 0.4 | 1.3 | **0.26** | transactional | FALSE | Near-empty — 0H 1M 0L queries; 1 total |
| 43 | Payment plan arrears / distress | ZH | 3.5 | 3 | +0.50 | 0.4 | 1.2 | **0.24** | informational | FALSE | Lagoon-19 news only; procedural absent — 0H 3M 0L queries; 3 total |
| 44 | Remote selling / POA | HI | 2.2 | 2 | +0.20 | 0.2 | 1.2 | **0.05** | transactional | FALSE | All Indian-POA content; zero Dubai-specific Hindi POA — 0H 0M 1L queries; 1 total |
| 45 | Documents & forms (Form F/A, Trakheesi) | HI | 1.0 | 1 | +0.00 | 0.2 | 1.2 | **0.00** | informational | FALSE | Empty — no observed queries |
| 46 | Fees & net proceeds | HI | 1.0 | 1 | +0.00 | 0.2 | 1.4 | **0.00** | commercial-investigational | FALSE | Empty — no observed queries |
| 47 | Payment plan arrears / distress | HI | 1.0 | 1 | +0.00 | 0.2 | 1.2 | **0.00** | informational | FALSE | Not observed — no observed queries |
| 48 | Pricing & benchmarking | HI | 1.0 | 1 | +0.00 | 0.2 | 1.3 | **0.00** | commercial-investigational | FALSE | Empty — no observed queries |
| 49 | Marketplace / listing channels | HI | 1.0 | 1 | +0.00 | 0.2 | 1.4 | **0.00** | transactional | FALSE | No Hindi portal edition; empty — no observed queries |
| 50 | Oqood & DLD mechanics | RU | 3.9 | 4 | -0.10 | 0.7 | 1.3 | **-0.09** | informational | FALSE | Fragmented; Metropolitan has buy-side, no seller-side Oqood — 1H 2M 0L queries; 3 total |
| 51 | Pricing & benchmarking | ZH | 3.8 | 4 | -0.20 | 0.4 | 1.3 | **-0.10** | commercial-investigational | FALSE | ROI/yield ubiquitous; seller pricing missing — 2H 0M 0L queries; 2 total |
| 52 | Documents & forms (Form F/A, Trakheesi) | EN | 5.9 | 6 | -0.10 | 1.0 | 1.2 | **-0.12** | informational | FALSE | Form F covered; Form A weak; Trakheesi moderate — 1H 5M 2L queries; 8 total |
| 53 | NOC procedures | ZH | 2.5 | 3 | -0.50 | 0.4 | 1.3 | **-0.26** | commercial-investigational | FALSE | Broker pages explain NOC abstractly; no developer tables — 0H 1M 0L queries; 1 total |
| 54 | Marketplace / listing channels | ZH | 2.5 | 3 | -0.50 | 0.4 | 1.4 | **-0.28** | transactional | FALSE | Bayut zh is listings-only; Juwai thin; gap — 0H 1M 0L queries; 1 total |
| 55 | Market context / oversupply | ZH | 6.6 | 8 | -1.40 | 0.4 | 0.5 | **-0.28** | informational | FALSE | 新浪/澎湃/36氪 dominate; Zhihu skeptical cluster; saturated — 4H 2M 0L queries; 6 total |
| 56 | Regulatory / RERA | RU | 2.5 | 3 | -0.50 | 0.7 | 0.9 | **-0.32** | informational | FALSE | Metropolitan has RERA explainer; thin beyond that — 0H 1M 0L queries; 1 total |
| 57 | Market context / oversupply | HI | 3.4 | 7 | -3.60 | 0.2 | 0.5 | **-0.36** | informational | FALSE | AajTak/TV9/Patrika/IndiaTV — saturated news — 1H 1M 0L queries; 2 total |
| 58 | Payment plan arrears / distress | RU | 3.5 | 4 | -0.50 | 0.7 | 1.2 | **-0.42** | informational | FALSE | Housebook + emirates.estate cover risk; seller handholding missing — 0H 3M 0L queries; 3 total |
| 59 | Documents & forms (Form F/A, Trakheesi) | ZH | 1.0 | 2 | -1.00 | 0.4 | 1.2 | **-0.48** | informational | FALSE | Empty — no observed queries |
| 60 | Banking / getting paid | HI | 1.0 | 3 | -2.00 | 0.2 | 1.3 | **-0.52** | transactional | FALSE | Bring-money-to-India angle covered by CA blogs; Dubai-exit-specific empty — no observed queries |
| 61 | Documents & forms (Form F/A, Trakheesi) | AR | 4.5 | 5 | -0.50 | 0.9 | 1.2 | **-0.54** | informational | FALSE | Form A/B Arabic = EMPTY; Trakheesi competitive — 2H 1M 1L queries; 4 total |
| 62 | Developer-specific rules | ZH | 3.5 | 5 | -1.50 | 0.4 | 1.1 | **-0.66** | commercial-investigational | FALSE | dubaiemaar.cn dominates brand SERP; long-tail resale/NOC open — 0H 3M 0L queries; 3 total |
| 63 | Market context / oversupply | RU | 3.9 | 6 | -2.10 | 0.7 | 0.5 | **-0.73** | informational | FALSE | Forbes + Kommersant — Forbes.ru 'Слезинка инвестора' owns narrative — 1H 2M 0L queries; 3 total |
| 64 | Remote selling / POA | EN | 5.3 | 6 | -0.70 | 1.0 | 1.2 | **-0.84** | transactional | FALSE | EGSH + Sara Advocates; no country-by-country attestation chain — 2H 1M 4L queries; 7 total |
| 65 | Remote selling / POA | AR | 5.2 | 6 | -0.80 | 0.9 | 1.2 | **-0.86** | transactional | FALSE | POA.ae + Private Notary; GCC-specific missing — 3H 1M 0L queries; 4 total |
| 66 | Oqood & DLD mechanics | EN | 8.3 | 9 | -0.70 | 1.0 | 1.3 | **-0.91** | informational | FALSE | EGSH + Bayut + Pearlshire saturated; legal-firm dominance — 4H 4M 3L queries; 11 total |
| 67 | SPA transfer | ZH | 1.0 | 3 | -2.00 | 0.4 | 1.3 | **-1.04** | informational | FALSE | Very thin — no observed queries |
| 68 | Market context / oversupply | EN | 5.9 | 8 | -2.10 | 1.0 | 0.5 | **-1.05** | informational | FALSE | Khaleej Times + Knight Frank + Prelaunch — saturated — 1H 3M 6L queries; 10 total |
| 69 | Fees & net proceeds | ZH | 3.0 | 5 | -2.00 | 0.4 | 1.4 | **-1.12** | commercial-investigational | FALSE | 4% DLD repeated everywhere; net-proceeds math absent — 0H 2M 0L queries; 2 total |
| 70 | Marketplace / listing channels | AR | 1.0 | 2 | -1.00 | 0.9 | 1.4 | **-1.26** | transactional | FALSE | Bayut-filter pages; no standalone guide — no observed queries |
| 71 | Banking / getting paid | AR | 2.8 | 4 | -1.20 | 0.9 | 1.3 | **-1.40** | transactional | FALSE | Escrow + law refs; seller-proceeds chain missing — 0H 1M 1L queries; 2 total |
| 72 | Developer-specific rules | EN | 2.5 | 4 | -1.50 | 1.0 | 1.1 | **-1.65** | commercial-investigational | FALSE | Thin — no per-developer NOC+%paid+timing table — 0H 0M 2L queries; 2 total |
| 73 | SPA transfer | RU | 2.9 | 5 | -2.10 | 0.7 | 1.3 | **-1.91** | informational | FALSE | VC.ru owns with deep legal pieces — 1H 0M 0L queries; 1 total |
| 74 | Market context / oversupply | AR | 4.3 | 9 | -4.70 | 0.9 | 0.5 | **-2.12** | informational | FALSE | Al Bayan + Al Khaleej + Asharq — saturated news — 2H 1M 0L queries; 3 total |
| 75 | Banking / getting paid | EN | 3.2 | 5 | -1.80 | 1.0 | 1.3 | **-2.34** | transactional | FALSE | Mortgaged-property sale covered; broader banking friction absent — 0H 2M 1L queries; 3 total |
| 76 | Pricing & benchmarking | AR | 1.0 | 3 | -2.00 | 0.9 | 1.3 | **-2.34** | commercial-investigational | FALSE | DLD valuation procedural; seller AVM missing — no observed queries |
| 77 | SPA transfer | AR | 3.9 | 6 | -2.10 | 0.9 | 1.3 | **-2.46** | informational | FALSE | Taraf/ATB cover; lane open for seller-exit framing — 1H 2M 0L queries; 3 total |
| 78 | Regulatory / RERA | EN | 2.2 | 5 | -2.80 | 1.0 | 0.9 | **-2.52** | informational | FALSE | Trakheesi + RERA explainers moderate; seller rulebook missing — 0H 0M 1L queries; 1 total |
| 79 | Fees & net proceeds | AR | 2.9 | 6 | -3.10 | 0.9 | 1.4 | **-3.91** | commercial-investigational | FALSE | Westgate/Taraf cover 2025; 2026 + calculator = gap — 1H 0M 0L queries; 1 total |
| 80 | SPA transfer | EN | 3.1 | 7 | -3.90 | 1.0 | 1.3 | **-5.07** | informational | FALSE | EGSH + Form F sites cover; moderate-saturated — 1H 0M 1L queries; 2 total |

## Top 10 priority opportunities — narrative

### 1. Marketplace / listing channels × English  (priority 5.88)

**Demand** 6.2 · **Supply** 2 · **Gap** +4.2 · **Weight** 1.0 · **Strategic fit** 1.4 · **Intent** transactional

**Own the empty English SERP for 'list my off-plan without an agent.'** Bayut, PropertyFinder and Dubizzle require agency uploads but never say so on a seller-facing page. Thirteen observed queries (iBuyer Dubai, off-plan resale platform, sell off-plan online, FSBO Dubai) return empty SERPs. Dalya's product surface — the listing grid, upload flow, verified SPA badge — is literally the canonical answer; the content job is to make that product surface the page search engines index.

### 2. Banking / getting paid × Russian  (priority 5.46)

**Demand** 7.2 · **Supply** 2 · **Gap** +5.2 · **Weight** 0.7 · **Strategic fit** 1.5 · **Intent** transactional

**Russian banking friction is Dalya's operational moat.** Mid-2025 rule: sellers must receive proceeds into a UAE bank account in their own name. Russian nationals face enhanced EDD, week-long account-opening timelines and frequent refusals. Brokerage voice is empty; VC.ru + MIGRON own the diaspora-legal framing. Dalya positioning: 'мы не только продадим, мы проведём вас через открытие счёта' — bank pre-qualification as part of the listing intake. Priority 5.46 because this is the difference between a signed MOU and a dead deal.

### 3. Tax — home-country residual × Russian  (priority 5.25)

**Demand** 10.0 · **Supply** 5 · **Gap** +5.0 · **Weight** 0.7 · **Strategic fit** 1.5 · **Intent** informational

**3-НДФЛ × CRS × 183-day is the single most-searched-yet-least-answered question on the Russian seller web.** 15 Russian queries, 8 High-demand, covering RF tax residency, 30% non-resident rate, RF-UAE DTT, automatic FNS exchange. Every piece of quality content lives on legal blogs (irinauae.law, mnp.ru, Forbes); not one licensed Dubai brokerage has claimed the lane. The E-E-A-T upside for Dalya is huge — this is where regulatory authority compounds into advisor-chat trust.

### 4. NOC procedures × English  (priority 5.20)

**Demand** 8.0 · **Supply** 4 · **Gap** +4.0 · **Weight** 1.0 · **Strategic fit** 1.3 · **Intent** commercial-investigational

**Per-developer NOC fee tables are the English gap everyone knows and nobody plugs.** 11 observed queries (Emaar/Sobha/Damac/Nakheel/Meraas/Azizi/Danube NOC fee, 30%/40%-paid thresholds). All English incumbents publish generic 'what is a NOC' pages; none hold a developer-by-developer fee/timeline/threshold table. Programmatic: one page per developer with fee, % threshold, processing time, required docs — directly wired to Dalya's SPA parser output.

### 5. Fees & net proceeds × English  (priority 4.20)

**Demand** 7.0 · **Supply** 4 · **Gap** +3.0 · **Weight** 1.0 · **Strategic fit** 1.4 · **Intent** commercial-investigational

**No English page publishes a live off-plan seller calculator.** DLD 4% is explained everywhere; nobody says 'for your specific unit, after NOC + DLD + commission + VAT, you walk away with AED X.' Nine observed queries including Empty-SERP rows for 'Dubai off-plan assignment fee calculator', 'how much will I net selling off-plan', 'total cost to sell'. Build the calculator, publish the methodology, dominate the net-proceeds cluster.

### 6. Tax — home-country residual × English  (priority 3.90)

**Demand** 6.0 · **Supply** 3 · **Gap** +3.0 · **Weight** 1.0 · **Strategic fit** 1.3 · **Intent** informational

**Nationality-segmented seller tax pages.** UK/US/Indian/GCC non-resident sellers each want 'what do I owe back home?' and get generic 'no CGT in UAE' copy. Only TaxesForExpats covers the US angle well. Seven observed queries; E-E-A-T-friendly if co-authored with a tax consultancy partner. Pairs with the Russian 3-НДФЛ piece on a shared template.

### 7. Payment plan arrears / distress × Arabic  (priority 3.46)

**Demand** 6.2 · **Supply** 3 · **Gap** +3.2 · **Weight** 0.9 · **Strategic fit** 1.2 · **Intent** informational

**Seller-distress in Arabic is thin; buyer-cancellation is moderate.** Six observed Arabic queries including 3 High — متأخرات خطة الدفع, إذا لم يدفع, إلغاء مشروع عقاري. Existing Arabic coverage is generic payment-plan-types copy. Dalya wedge: the consequences ladder — missed-installment → developer cancellation → DLD auction — with a licensed-brokerage reassurance that controlled exit is the cheaper path. Ships as Dalya's 'if you can't pay, we can sell' landing page in Arabic before English.

### 8. Process & eligibility × Arabic  (priority 3.16)

**Demand** 9.9 · **Supply** 6 · **Gap** +3.9 · **Weight** 0.9 · **Strategic fit** 0.9 · **Intent** informational

**Arabic head-terms are competitive but the journey framing is open.** Bayut-AR, DXB Properties, Offplan-Dubai cover the basics but always in a pros-and-cons/procedural register. Dalya opportunity: seller-first narrative with specific AED figures, the Khaleeji-dialect case-study layer on top of MSA canonical, and the 0.15% framing repeated inline. 13 observed queries (6H + 3M + 4L).

### 9. NOC procedures × Arabic  (priority 3.16)

**Demand** 4.7 · **Supply** 2 · **Gap** +2.7 · **Weight** 0.9 · **Strategic fit** 1.3 · **Intent** commercial-investigational

**Arabic developer-specific NOC = empty.** Emaar/Damac/Sobha/Nakheel all publish their English NOC workflows; none publish Arabic seller guides. شهادة عدم ممانعة + developer-name returns either corporate pages or fragmentary broker mentions. Six observed queries. This is Dalya's single biggest Arabic opening per the Arabic researcher — ship per-developer Arabic NOC pages with fee ranges, processing times and required docs; programmatic with the English set.

### 10. Process & eligibility × Russian  (priority 3.09)

**Demand** 9.9 · **Supply** 5 · **Gap** +4.9 · **Weight** 0.7 · **Strategic fit** 0.9 · **Intent** informational

**One canonical Russian brokerage seller guide does not exist.** VC.ru legal + Goldenbee + 2 niche brokerages cover basics; none consolidate the full off-plan exit journey from a licensed brokerage voice. 11 observed queries (6H + 5M). Dalya deliverable: the Russian 'продажа off-plan: полный гайд от лицензированного брокера' that replaces 3–5 VC.ru posts for the target reader.

---

## Supply/demand reading notes

- **Priority ≥ 5** cells map 1:1 to the cornerstone pieces in the publishing plan (see Task #8). Treat these as the must-ship minimum.
- **Priority 2.5–5** are recommended secondary pieces — strong cluster support but not standalone hero pages.
- **Negative gap** cells should **not** be published even if demand is high — the incumbents already win these SERPs. Target adjacent long-tail instead.
- **Observed vs inferred** flags from the source research files are preserved in per-query rows in `demand.csv`; use that file when validating before a specific piece ships.
- **Cells with `no observed queries`** are carried as demand_score=1 placeholders; they are not invented demand. Skip unless a specific investor ask (e.g. from a broker or a prospect) later justifies them.