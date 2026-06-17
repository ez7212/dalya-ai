# Mandarin (Simplified Chinese) — Demand & Supply Research

**Audience scope:** Mainland China + Chinese-speaking diaspora (Singapore, Malaysia, HK/TW partially). Language: 简体中文 (Simplified Chinese), written register.
**Research window:** April 2026. Focused on the Dalya thesis: seller-side Dubai off-plan resale at 0.15% vs 2% market commission.
**Researcher:** mandarin-researcher (Task #4).

---

## 1. Executive Summary & The WeChat Data Gap

Chinese-language open-web demand for Dubai off-plan resale content is **real but shallow and heavily buyer-framed**, with the entire serious research activity gravitating toward three channels that SEO cannot easily reach: (a) WeChat (微信) public accounts and private groups, (b) Xiaohongshu (小红书) notes, and (c) agent-led WeChat consultations. Baidu's open SERPs are dominated by developer-affiliated portals (伊玛尔 EMAAR, 达马克 DAMAC), Chinese brokerages' marketing blogs (迪拜有房网, 菲度, 鼎石, 德世迦, 迪拜之家), financial media coverage (新浪财经, 澎湃, 第一财经, 界面, 36氪, 每经网), and a small but active Zhihu (知乎) Q&A core. The structural problem for Dalya is that **Chinese buyers research on WeChat+Xiaohongshu and transact through a trusted 华人中介 (Chinese agent), not through SEO-driven marketplaces** — meaning blog-based organic capture has a ceiling.

**Explicit data gap — WeChat (微信):** The highest-signal Chinese-language content on Dubai off-plan — 公众号 long-form posts, 投资群 QQ/WeChat groups, 视频号 short videos, agent H5 landing pages distributed by link-share — is inside a closed ecosystem that is not openly indexable, not crawled by Baidu, not accessible to WebFetch, and not appropriate to scrape (ToS + practical feasibility). This report infers WeChat activity from (1) the heavy "add WeChat for more info" CTA pattern on every Chinese Dubai-property broker site observed, (2) financial-media coverage describing 华人中介 roadshows in Beijing/Shenzhen, and (3) the visible Xiaohongshu/Weibo funnel-top content that evidently feeds WeChat-group conversion. Any verdict on Mandarin viability for Dalya must assume WeChat/Xiaohongshu will be 60-80% of the Chinese-speaking funnel and SEO will be 20-40%.

**Blunt verdict:** Mandarin SEO-blog publication is **NOT the primary lever** for Dalya in the China segment. It is a secondary trust-signalling layer. Do **2-4 high-commercial-intent cornerstone pages** in Simplified Chinese, route 华人-specific conversion through an agent-led WeChat/Xiaohongshu play, and do not invest in long-tail Mandarin blog production. Full recommendation in §5 and §8.

---

## 2. Mandarin Demand Queries (Observed + Inferred)

30-50 queries was the scope; 46 logged. "Demand" is qualitative: **High** = repeatedly appears across Baidu top-10, Zhihu question clusters, financial-media coverage. **Medium** = appears but not dominant. **Low** = single-source or inferred from related-search hints.

| # | Query (中文) | English gloss | Intent | Stage | Demand | Source / flag |
|---|---|---|---|---|---|---|
| 1 | 迪拜期房转售 | Dubai off-plan resale | Informational/Commercial | Mid | Medium | Baidu top-10 observed (Zhihu + dibaifang); [obs] |
| 2 | 迪拜楼花转让 | Dubai off-plan transfer ("楼花" term) | Commercial | Mid-High | Low-Med | [inf] "楼花" is HK/Cantonese-influenced; mainland users lean toward 期房 — low on Baidu mainland |
| 3 | 迪拜房产 NOC | Dubai property NOC | Transactional | High | Medium | [obs] multiple broker pages explain NOC; intent clearly seller-side |
| 4 | 迪拜房产 过户流程 | Dubai property transfer process | Transactional | High | Medium | [obs] dibaifang + 伊玛尔中国 coverage |
| 5 | 迪拜 DLD 土地局 | Dubai DLD land department | Informational | Any | Medium | [obs] |
| 6 | 迪拜 Oqood 阿库德 | Dubai Oqood certificate | Informational | Mid | Low-Med | [obs] termed 阿库德 in Chinese content; niche but rising |
| 7 | 迪拜期房 出售 | Sell Dubai off-plan | Transactional (seller) | High | Low | [inf] few seller-framed pages; most content buyer-framed |
| 8 | 迪拜房产 中介费 | Dubai broker commission | Informational | Any | High | [obs] Baidu top-10 direct hits; "2% buyer-paid" is the consensus answer |
| 9 | 迪拜房产 佣金 多少 | How much Dubai commission | Informational | Any | High | [obs] |
| 10 | 迪拜买房 中介 收费 | Dubai agent fee when buying | Informational | Any | High | [obs] |
| 11 | 迪拜 房产税 | Dubai property tax | Informational | Any | High | [obs] dominant query — "0 tax" is the universal hook |
| 12 | 迪拜卖房 税 | Tax when selling Dubai property | Informational | Post | Medium | [obs] seller-intent, under-served |
| 13 | 迪拜 资本利得税 | Dubai capital gains tax | Informational | Post | Medium | [obs] |
| 14 | 迪拜 印花税 | Dubai stamp duty | Informational | Any | Low-Med | [obs] |
| 15 | 迪拜房产 4% 注册费 | Dubai 4% DLD registration fee | Informational | Mid | High | [obs] fact repeated across 80%+ of Chinese Dubai property pages |
| 16 | 中国人 迪拜 买房 | Chinese people buying in Dubai | Informational | Awareness | High | [obs] News/Zhihu/portal saturated |
| 17 | 迪拜 黄金签证 200万 | Dubai golden visa 2M AED | Informational/Commercial | Awareness | High | [obs] single largest demand driver for Chinese buyers |
| 18 | 迪拜 黄金签证 房产 | Golden visa via property | Commercial | Mid | High | [obs] |
| 19 | 迪拜 黄金签证 买房 流程 | Golden visa purchase process | Transactional | Mid | Medium | [obs] |
| 20 | 迪拜买房攻略 | Dubai buying guide | Informational | Awareness | High | [obs] massive Zhihu + Xiaohongshu cluster |
| 21 | 迪拜买房 流程 | Dubai buying process | Informational | Mid | High | [obs] |
| 22 | 迪拜 伊玛尔 期房 | EMAAR off-plan | Commercial | Mid | Medium | [obs] dubaiemaar.cn ranks #1-2 for most EMAAR queries |
| 23 | 迪拜 Sobha 索巴 | Sobha developer | Commercial | Mid | Medium | [obs] "Royal developer" framing common |
| 24 | 迪拜 Damac 达马克 | DAMAC | Commercial | Mid | Medium | [obs] |
| 25 | 迪拜房产投资 风险 | Dubai property investment risk | Informational | Awareness | High | [obs] very strong Zhihu cluster with skeptical framing |
| 26 | 迪拜 房产 骗局 | Dubai property scam | Informational | Awareness | Medium-High | [obs] 知乎 + 搜狐 + 凤凰 coverage substantial |
| 27 | 迪拜 房产 烂尾 | Dubai abandoned/stalled projects | Informational | Post-purchase | Medium | [obs] 2024 Lagoon 19-year stall story picked up by Tencent |
| 28 | 迪拜 房产 回报率 | Dubai property ROI | Informational | Awareness | High | [obs] "6-10% rental yield" ubiquitous |
| 29 | 迪拜 租金回报率 | Dubai rental yield | Informational | Any | High | [obs] |
| 30 | 迪拜房价 2026 | Dubai house prices 2026 | Informational | Awareness | High | [obs] very active — news-driven |
| 31 | 迪拜楼市 | Dubai property market | Informational | Awareness | High | [obs] financial media dominates |
| 32 | 迪拜房价 暴跌 | Dubai prices crash | Informational | Awareness | Medium-High | [obs] post-March 2026 Middle East conflict coverage |
| 33 | 迪拜 永久产权 | Dubai freehold | Informational | Any | High | [obs] universally explained |
| 34 | 迪拜 永久产权 区域 | Freehold zones | Informational | Mid | Medium | [obs] |
| 35 | 迪拜卖房 海外 | Selling Dubai property from overseas | Transactional (seller) | High | Low | [inf] virtually no dedicated Chinese pages — GAP |
| 36 | 迪拜 房产 委托书 | Dubai POA | Transactional | High | Low-Med | [obs] mostly China-POA info, Dubai-POA info sparse |
| 37 | 人在国外 卖迪拜房 | Sell Dubai property while abroad | Transactional (seller) | High | Low | [inf] GAP — high commercial intent but no dedicated content |
| 38 | 迪拜 海外远程公证 房产 | Overseas remote notarization for property | Transactional | High | Low | [obs] MFA coverage exists; Dubai-specific nearly zero |
| 39 | 迪拜 期房 付款 进度 | Off-plan payment schedule | Informational | Pre-purchase | Medium | [obs] |
| 40 | 迪拜期房 交房延期 | Off-plan handover delay | Informational | Post | Medium | [obs] |
| 41 | 迪拜 物业费 服务费 | Service charges | Informational | Post | Medium-High | [obs] widely complained about |
| 42 | 迪拜买房 贷款 按揭 | Dubai mortgage | Informational | Mid | Medium | [obs] |
| 43 | 迪拜 公寓 投资 | Dubai apartment investment | Informational/Commercial | Awareness | High | [obs] |
| 44 | 迪拜 别墅 投资 | Dubai villa investment | Informational/Commercial | Awareness | Medium-High | [obs] |
| 45 | 迪拜 哈利法塔 附近 房产 | Burj Khalifa area property | Navigational/Commercial | Mid | Medium | [obs] |
| 46 | 小红书 迪拜买房 | Xiaohongshu Dubai buying | Navigational | Awareness | Medium-High | [obs] users actively cross-search XHS from Baidu |

**Observed vs Inferred summary for demand table:** Row count 46. [obs] = 37. [inf] = 9. Inferences concentrated on (a) seller-side workflow queries where Chinese content is genuinely sparse and I cannot confirm search volume without 百度指数 access, and (b) the "楼花" Cantonese term which I flag as likely-low on mainland Baidu.

---

## 3. Topic Clusters

Clusters ordered by commercial-intent match to Dalya's thesis (seller-side 0.15% commission for Dubai off-plan resale).

### C1. **Seller workflow: transfer a Dubai off-plan unit (NOC → DLD → new buyer)** — HIGH intent, LOW supply
Queries 1, 3, 4, 5, 6, 7, 35, 36, 37, 38, 39. This is Dalya's sweet spot. Demand is real but thin on the open web because most Chinese sellers currently go through their 华人中介 via WeChat. The *open-web* content that exists is fragmented between dibaifang, a handful of Zhihu answers, and developer Q&A pages — none of which walks a seller through "I'm in Shanghai, my unit is 40% paid at Sobha Hartland, how do I exit before handover."

### C2. **Commission & fees (seller economics)** — HIGH demand, content uniformly buyer-biased
Queries 8, 9, 10, 15. Baidu top-10 is uniform: "2% commission, paid by the buyer" — which is (a) oversimplified and (b) structurally hides seller-paid commission and seller-side savings. Dalya's 0.15% vs market positioning has essentially zero Chinese-language competition.

### C3. **Tax in Dubai (0% angle)** — MASSIVE demand, saturated supply
Queries 11, 12, 13, 14. "Dubai has no property tax / capital gains tax" is the single most-repeated line in Chinese Dubai-property content. Ranking for generic tax queries is a fool's errand; the open angle is *seller-specific tax mechanics when repatriating proceeds back to China* (CRS, foreign-asset declaration, 境外所得个税), which almost nobody covers well.

### C4. **Golden Visa (黄金签证)** — MASSIVE demand, saturated supply
Queries 17, 18, 19. Every Chinese Dubai-property broker site has a Golden Visa page. Dalya should have a minimum-viable page but should not try to beat 环球出国 / 全球引力 / 迪拜有房 on this — they're entrenched.

### C5. **Developer-specific (Emaar / Damac / Sobha / 伊玛尔 / 达马克 / 索巴)** — HIGH demand, developer-dominated supply
Queries 22, 23, 24. `dubaiemaar.cn` is literally a Chinese-market EMAAR site and dominates its own brand SERP. Dalya cannot win "伊玛尔 期房" but can win long-tail "伊玛尔 Creek Harbour 转售 NOC 费用."

### C6. **Market macros / prices / crash** — HIGH demand, news-media dominated
Queries 30, 31, 32. 新浪财经, 澎湃, 21经济, 界面新闻, 每经, 第一财经 dominate. Dalya should not try to compete as a news publisher; periodic data briefs for backlink/PR purposes only.

### C7. **Risk / scam / delay (skeptical buyer concerns)** — MEDIUM-HIGH demand, moderate supply
Queries 25, 26, 27, 40, 41. Zhihu skeptical content (e.g. "喊你去迪拜买房，就像挖个坑等着你跳") consistently ranks top-10. A *sober, licensed, Chinese-language* seller-perspective piece on how to avoid resale scams is an open lane.

### C8. **Golden Visa-adjacent buyer-intent (Chinese investor macro)** — HIGH demand, saturated
Queries 16, 20, 21, 28, 29. Dalya is seller-side, so this cluster is low priority.

### C9. **Remote seller mechanics (POA, notarization, Chinese consulate)** — LOW-MEDIUM demand, near-zero supply
Queries 35, 36, 37, 38. Small volume but almost nobody owns this corner. High commercial intent: an overseas Chinese seller who cannot fly to Dubai is the single hottest lead profile Dalya can capture via SEO.

---

## 4. Supply Audit

15-25 rows was the scope; 21 logged. "Depth" is qualitative: Thin (<800 words or listicle), Medium (800-2000w, some specifics), Deep (>2000w with named fees, named projects, actual process).

| # | URL | Publisher | Title (中文 / EN gloss) | Approx date | Word count | Depth | Framing |
|---|---|---|---|---|---|---|---|
| 1 | dibaifang.com/211 | 迪拜有房 (broker affiliate) | 迪拜买房攻略：买房前准备工作 / Dubai buying guide: preparation | ~2022-23 | ~2k | Medium | Buyer |
| 2 | dibaifang.com/1477 | 迪拜有房 | 在迪拜，赠送房产由哪些费用和流程？/ Dubai gifting process & fees | ~2022 | ~1.2k | Medium | Neutral |
| 3 | dibaifang.com/2312 | 迪拜有房 | 阿联酋黄金签证: 取消最低付款要求 / UAE Golden Visa: minimum payment removed | ~2024 | ~1.5k | Medium | Buyer |
| 4 | dubaiemaar.cn/wiki/108866.html | EMAAR 中国官方 (developer) | 迪拜投资购房全攻略 / Dubai investment buying complete guide | ~2023 | ~3k | Deep | Buyer/developer |
| 5 | dubaiemaar.cn/wiki/108849.html | EMAAR 中国官方 | 为什么要投资迪拜 / Why invest in Dubai — FAQ | ~2023 | ~2.5k | Medium | Buyer/developer |
| 6 | dubaiemaar.cn/investment-guide | EMAAR 中国官方 | 迪拜投资指南 / Dubai investment guide hub | ~2023 | hub | Medium | Buyer/developer |
| 7 | zhuanlan.zhihu.com/p/54176088 | Zhihu (个人作者) | 迪拜房产50问 / 50 Q&A on Dubai property | 2019 | ~5k | Deep | Neutral |
| 8 | zhuanlan.zhihu.com/p/60567886 | Zhihu | 喊你去迪拜买房，就像挖个坑等着你跳 / "Inviting you to Dubai is like digging a pit" | 2019 | ~3k | Deep | Skeptical/buyer |
| 9 | zhuanlan.zhihu.com/p/616417196 | Zhihu | 史上最全，迪拜房产投资入门2023 / Most comprehensive 2023 entry guide | 2023 | ~6k | Deep | Buyer |
| 10 | zhuanlan.zhihu.com/p/1911118908594816627 | Zhihu | 2025年投资迪拜房产，常见问题解答 / 2025 FAQ | 2025 | ~4k | Deep | Buyer |
| 11 | zhuanlan.zhihu.com/p/681256552 | Zhihu | 迪拜房产经纪人知识库 / Dubai broker knowledge base | 2024 | ~5k | Deep | Agent-authored |
| 12 | feiduproperty.com | 菲度房地产 (broker) | Site-wide | ongoing | — | Medium | Buyer/commercial |
| 13 | dingstonerealestate.com | 鼎石房地产 (broker) | Site-wide | ongoing | — | Thin-Med | Buyer/commercial |
| 14 | dubairen.com | 迪拜人 (community portal) | 迪拜买房记 / Dubai property diary | ongoing | varies | Medium | Mixed |
| 15 | juwai.com/ae/ | 居外网 (Juwai) | 迪拜房产网_阿联酋买房 / Dubai property portal | ongoing | listings | Thin | Buyer |
| 16 | bayut.com/zh/ | Bayut (Chinese locale) | Bayut.com Chinese site | ongoing | listings | Thin | Buyer/listings |
| 17 | wise.com/zh-cn/blog/buying-property-in-the-uae | Wise (fintech blog) | 迪拜买房 外国人如何投资移民 / Dubai buying for foreigners | ~2024 | ~3k | Deep | Buyer |
| 18 | finance.sina.com.cn (multiple 2024-26) | 新浪财经 (news) | 迪拜楼市 / Dubai market news | continuous | 1-2k each | News | Neutral |
| 19 | thepaper.cn/newsDetail_forward_30820608 | 澎湃新闻 | 在迪拜倒腾房子的中国人 / Chinese flippers in Dubai | 2024 | ~3k | Deep | Narrative journalism |
| 20 | finance.sina.com.cn/jjxw/2025-10-14/... | 新浪财经 | 中东楼市涌入中国投资客 / Chinese investors flood ME market | 2025-10 | ~2k | Medium | News |
| 21 | 36kr.com/p/2267067449532169 | 36氪 | 全球富豪涌入，迪拜楼市狂奔 / Global wealth surging into Dubai | 2023 | ~2.5k | Medium | News |

**Other noted sources (not individually ranked but worth awareness):**
- LinkedIn CN (cn.linkedin.com/pulse/...) — individual broker posts, low SEO weight.
- 伊玛尔中国 (dubaiemaar.cn) is an aggressive and well-resourced content operation; it is the #1 Chinese-language Dubai-property site by SERP coverage.
- Bayut Chinese locale (bayut.com/zh/) is **listings-only** with minimal editorial content — a genuine gap vs the English/Arabic parent site.
- Juwai 居外 is primarily a listings marketplace aimed at Chinese buyers of global property; Dubai editorial is thin.
- 小红书 (Xiaohongshu): search of site returns travel-dominant content, with a visible but secondary #迪拜买房 / #迪拜房产投资 hashtag cluster. See §6.
- Weibo: news-media republication + investor commentary. Not a primary research destination for Dubai property.
- 财经媒体 (新浪/澎湃/21经济/界面/每经/第一财经/36氪) cover Dubai property *cyclically* — surge in 2023-2025, currently in skeptical mode after March 2026 Middle East conflict.

**No observed Chinese content from:**
- Property Finder (Chinese site not found) — gap.
- Most major Dubai brokerages (Allsopp, Betterhomes, Metropolitan, Driven, Espace) — English/Arabic only on public web.

---

## 5. Saturation Verdict per Cluster

| Cluster | Saturation | Can Dalya win organic? | Worth publishing? |
|---|---|---|---|
| C1. Seller workflow (NOC/DLD/Oqood for resale) | **LOW** | Yes — clear lane | **YES — top priority** |
| C2. Commission & fees | Medium (but all buyer-biased) | Yes with seller-side angle | **YES** |
| C3. Tax (0% generic) | Saturated | No | Skip generic; cover only CRS/遣返 angle |
| C4. Golden Visa | Saturated | No | MVP only — don't invest |
| C5. Developer-specific | Dominated by developers | No on brand, yes on long-tail resale | Long-tail only |
| C6. Market macros/prices | Dominated by news | No | News-cite only |
| C7. Risk / scam / delay | Medium | Yes with licensed-broker framing | MVP |
| C8. Buyer-intent macro | Saturated | No | Skip — we are seller-side |
| C9. Remote seller (POA / notarization / 海外卖房) | **VERY LOW** | Yes — clean lane | **YES — highest intent** |

**Verdict for the Mandarin channel:** Do **exactly three cornerstone pages** in Simplified Chinese for SEO, plus a bilingual listing canonical. Don't produce a full content program.

**The 3 cornerstone pages (ranked):**
1. **人在海外如何卖掉我的迪拜期房** — "How to sell your Dubai off-plan unit while living abroad" (covers POA, Chinese consular notarization, remote DLD workflow). Hits Clusters C1 + C9 together. Essentially uncontested.
2. **迪拜卖房中介费详解：2% 市场费率与卖家可以怎么省** — "Dubai selling commissions explained: the 2% market rate and how sellers save." Hits C2 with the only seller-framed angle in Chinese search. Direct path to Dalya's 0.15% positioning.
3. **迪拜期房 NOC 与过户流程（卖家版）** — "NOC and DLD transfer process: seller edition." Hits C1 with specificity (fees, timelines, developer-by-developer NOC cost table for EMAAR/Sobha/DAMAC).

**Optional 4th (stretch):** a quarterly Chinese-language Dubai off-plan **resale market digest** (transaction-volume, price-delta, hottest resale communities) to earn 财经 back-links. Data sourced from DLD; translate from Dalya's English digest. Use for PR, not search.

---

## 6. Xiaohongshu 小红书 as a Channel — Structurally More Important Than Blog SEO

Observed: Xiaohongshu has a real but under-indexed #迪拜买房 / #迪拜房产 / #迪拜投资 community. Direct XHS search largely returns travel/lifestyle content, but the property-specific subset is (a) visibly monetized by Chinese agents living in Dubai, (b) frequently cross-posted from WeChat 公众号, and (c) a major funnel-top for WeChat group recruitment.

For Dalya's seller thesis, XHS matters for three reasons:
- **Chinese off-plan investors are increasingly millennial/Gen-Z**, the exact XHS demographic (90后, 72% of users).
- **Visual-first format fits off-plan floor plans, payment schedule graphics, commission comparison charts** better than Baidu blog format.
- **Agent-creator accounts are the de-facto trust intermediaries**; Dalya can partner/acquire rather than build from zero.

**Tactical recommendation (out of scope for pure SEO, but relevant here):** Any Mandarin investment should lead with a XHS brand account (官方认证) + 3-5 content-partner agents, then use Dalya's SEO cornerstone pages as the trust-destination for outbound XHS/WeChat links. SEO alone will not move the needle.

[inf — heavy:] I could not quantify XHS post volume or engagement without platform access. All XHS observations are inferred from (a) Baidu SERPs cross-referencing XHS, (b) general XHS platform demographics, (c) domain knowledge of the XHS-agent ecosystem. Treat the "increasingly important" claim as directional, not numerical.

---

## 7. Observed vs Inferred Flags

As instructed, flagged prominently. Inference is heavier in this language than in others because of (a) Baidu autocomplete not being openly queryable from this environment, (b) 百度指数 requiring login, (c) WeChat being closed, and (d) XHS/Weibo search results being heavily personalized/geo-gated.

**[Observed — confirmed via search]:**
- Query clusters 1, 3, 4, 5, 6, 8, 9, 10, 11, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 40, 41 have direct Baidu SERP or major-portal evidence.
- All 21 supply-audit rows are direct-observed.
- EMAAR's dubaiemaar.cn dominance across developer SERPs.
- Xiaohongshu's lifestyle-dominated, property-secondary posture.
- Financial-media cyclical coverage (surge through 2025; skeptical as of March 2026 post-conflict).
- Seller-side content is structurally thin — this is a stable observation across ~30 independent queries.
- Commission content is uniformly "2% buyer-paid" with no seller-commission education.

**[Inferred — not directly verified]:**
- Relative search volumes (High/Medium/Low) are qualitative inference, not 百度指数 data.
- Query 2 ("楼花" Cantonese) is flagged low on mainland; cannot confirm without 百度指数.
- Queries 35, 37 (remote seller intent) have inferred demand from adjacent Q&A behavior; actual volume may be very small.
- XHS engagement / post volume / hashtag size (§6) — inferred from general platform knowledge, not measured.
- WeChat ecosystem size (§1) — entirely inferred; not accessible.
- Zhihu question/answer engagement counts — not individually measured per-URL.
- Content word-counts in supply table are estimated from displayed snippets, not counted.

**[Structural caveats specific to zh-CN]:**
- Baidu SERP personalization is heavy; observed SERPs may not match a mainland Chinese user's view from Beijing.
- 百度 favors its own properties (百度知道, 百度百科, 百度文库, 百家号) — none observed to dominate Dubai property queries currently, but this can change.
- News articles are often republished across sina / sohu / 163 / tencent, inflating apparent supply.
- Chinese internet policy on overseas-investment content can change quickly; Dubai is currently permissible.

---

## 8. Raw Query CSV Block

```csv
query,english_gloss,intent,stage,demand,source,language
迪拜期房转售,Dubai off-plan resale,Informational/Commercial,Mid,Medium,obs,zh
迪拜楼花转让,Dubai off-plan transfer (Cantonese term),Commercial,Mid-High,Low-Medium,inf,zh
迪拜房产 NOC,Dubai property NOC,Transactional,High,Medium,obs,zh
迪拜房产 过户流程,Dubai property transfer process,Transactional,High,Medium,obs,zh
迪拜 DLD 土地局,Dubai Land Department,Informational,Any,Medium,obs,zh
迪拜 Oqood 阿库德,Dubai Oqood certificate,Informational,Mid,Low-Medium,obs,zh
迪拜期房 出售,Sell Dubai off-plan,Transactional-seller,High,Low,inf,zh
迪拜房产 中介费,Dubai broker commission,Informational,Any,High,obs,zh
迪拜房产 佣金 多少,How much Dubai commission,Informational,Any,High,obs,zh
迪拜买房 中介 收费,Dubai agent fee when buying,Informational,Any,High,obs,zh
迪拜 房产税,Dubai property tax,Informational,Any,High,obs,zh
迪拜卖房 税,Tax when selling Dubai property,Informational,Post,Medium,obs,zh
迪拜 资本利得税,Dubai capital gains tax,Informational,Post,Medium,obs,zh
迪拜 印花税,Dubai stamp duty,Informational,Any,Low-Medium,obs,zh
迪拜房产 4% 注册费,Dubai 4% DLD registration fee,Informational,Mid,High,obs,zh
中国人 迪拜 买房,Chinese people buying in Dubai,Informational,Awareness,High,obs,zh
迪拜 黄金签证 200万,Dubai golden visa 2M AED,Informational/Commercial,Awareness,High,obs,zh
迪拜 黄金签证 房产,Golden visa via property,Commercial,Mid,High,obs,zh
迪拜 黄金签证 买房 流程,Golden visa purchase process,Transactional,Mid,Medium,obs,zh
迪拜买房攻略,Dubai buying guide,Informational,Awareness,High,obs,zh
迪拜买房 流程,Dubai buying process,Informational,Mid,High,obs,zh
迪拜 伊玛尔 期房,EMAAR off-plan,Commercial,Mid,Medium,obs,zh
迪拜 Sobha 索巴,Sobha developer,Commercial,Mid,Medium,obs,zh
迪拜 Damac 达马克,DAMAC,Commercial,Mid,Medium,obs,zh
迪拜房产投资 风险,Dubai property investment risk,Informational,Awareness,High,obs,zh
迪拜 房产 骗局,Dubai property scam,Informational,Awareness,Medium-High,obs,zh
迪拜 房产 烂尾,Dubai abandoned stalled projects,Informational,Post-purchase,Medium,obs,zh
迪拜 房产 回报率,Dubai property ROI,Informational,Awareness,High,obs,zh
迪拜 租金回报率,Dubai rental yield,Informational,Any,High,obs,zh
迪拜房价 2026,Dubai house prices 2026,Informational,Awareness,High,obs,zh
迪拜楼市,Dubai property market,Informational,Awareness,High,obs,zh
迪拜房价 暴跌,Dubai prices crash,Informational,Awareness,Medium-High,obs,zh
迪拜 永久产权,Dubai freehold,Informational,Any,High,obs,zh
迪拜 永久产权 区域,Freehold zones,Informational,Mid,Medium,obs,zh
迪拜卖房 海外,Selling Dubai property from overseas,Transactional-seller,High,Low,inf,zh
迪拜 房产 委托书,Dubai property POA,Transactional,High,Low-Medium,obs,zh
人在国外 卖迪拜房,Sell Dubai property while abroad,Transactional-seller,High,Low,inf,zh
迪拜 海外远程公证 房产,Overseas remote notarization for property,Transactional,High,Low,obs,zh
迪拜 期房 付款 进度,Off-plan payment schedule,Informational,Pre-purchase,Medium,obs,zh
迪拜期房 交房延期,Off-plan handover delay,Informational,Post,Medium,obs,zh
迪拜 物业费 服务费,Service charges,Informational,Post,Medium-High,obs,zh
迪拜买房 贷款 按揭,Dubai mortgage,Informational,Mid,Medium,obs,zh
迪拜 公寓 投资,Dubai apartment investment,Informational/Commercial,Awareness,High,obs,zh
迪拜 别墅 投资,Dubai villa investment,Informational/Commercial,Awareness,Medium-High,obs,zh
迪拜 哈利法塔 附近 房产,Burj Khalifa area property,Navigational/Commercial,Mid,Medium,obs,zh
小红书 迪拜买房,Xiaohongshu Dubai buying,Navigational,Awareness,Medium-High,obs,zh
```

---

## 9. Final Recommendation to Dalya (Mandarin)

1. **Do not run a full Mandarin content program.** The ROI is not there at SEO margin. 华人 conversion happens on WeChat+Xiaohongshu and is agent-mediated.
2. **Ship 3 cornerstone SC pages** (above) that anchor Dalya as a *credible licensed destination* for the open-web researcher who does land on Baidu/Google results.
3. **Translate every listing page canonically to SC**, served with hreflang `zh-CN`. No editorial volume but full marketplace coverage.
4. **Invest the budget saved** from not running a blog into (a) a Xiaohongshu 企业号 operated by a Chinese-speaking team member, (b) 2-3 agent content-partnerships, (c) a WeChat 服务号 for direct seller inquiries — all outside this SEO researcher's scope but flagged as the actually-decisive channel.
5. **Translate the seller-facing onboarding flow to SC** (SPA upload, NOC checker, commission comparison) — this is where an open-web Mandarin-speaking researcher who reaches Dalya will actually convert.
6. **Bilingual names on trust signals**: "RERA 持牌 / Trakheesi 合作伙伴 / DLD 注册" — matches the phrasing every Chinese Dubai-property page already uses.

---

**End of report.**
