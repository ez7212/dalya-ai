# Dalya Multilingual SEO Architecture Notes

_Content planner — 2026-04-24_
_Scope: technical + editorial architecture for EN / AR / RU / ZH / HI publishing per the 12-week plan in `publishing-plan.md`. Brand/CTA tokens per CLAUDE.md._

## 1. URL structure and canonicals

**Subdirectories, not subdomains.** Use `/en/`, `/ar/`, `/ru/`, `/zh/`, `/hi/` on the single `dalya.ai` origin. Subdirectories concentrate domain authority on one property, simplify hreflang, and avoid the inter-locale cookie/JS fragmentation that subdomains introduce. This matches the pattern used by most globally-scaled content operations (Stripe, Airbnb, Booking, Notion) and contradicts the pattern used by `bayut.com/zh/` / `bayut.com/ru/`, which are separate CMS trees behind the same domain and suffer from cross-locale link equity fragmentation.

**Canonical rules.**
- Each locale version of a post has its own canonical URL pointing to itself (`<link rel="canonical" href="https://dalya.ai/en/selling-off-plan-fees">` on the EN page, `https://dalya.ai/ar/selling-off-plan-fees` on the AR page).
- `x-default` hreflang points to the EN version for all posts.
- Untranslated posts (e.g. Mandarin or Hindi versions that don't exist) must **not** include a hreflang pointing to the EN page as a stand-in. Missing locales are silent — do not publish fallback redirects that return EN content on an `/ar/` URL, since this fragments CTR and confuses the locale signal.

**Slugs — recommendation: Latin slugs for all languages.**

Tradeoff analysis:

- **Native-script slugs** (e.g. `/ar/بيع-عقار-على-الخارطة`, `/ru/переуступка-прав-дубай`, `/zh/迪拜期房转售`, `/hi/एलआरएस-नियम`) carry two benefits: (a) modest keyword-in-URL SEO lift in the target locale, and (b) higher perceived authenticity for native-speaker readers. They carry three costs: (a) percent-encoded URLs become 300+ characters and get truncated in WhatsApp / Twitter / Telegram previews, which is the dominant share surface for the Dalya audience; (b) analytics, internal tooling and support tickets become harder to read and dictate; (c) native-script slugs sometimes break older email clients and mobile keyboards.
- **Latin slugs across all locales** (`/ar/selling-off-plan-fees`, `/ru/peredacha-prav-dubai`, `/zh/selling-off-plan-fees`, `/hi/fema-lrs-dubai-property`) avoid the share-truncation problem, are readable in every tool, and match the convention of PropertyFinder, Bayut's English side, and DLD's English domain. The SEO lift from native-script slugs is real but small — 1–3% on target-language head terms in most studies — and the `<title>`, `<h1>`, meta description and body text carry the majority of the on-page keyword signal, not the slug.

**Recommendation: Latin slugs for all locales.** This is the same recommendation the Arabic researcher independently arrived at (§6 point 8), and the share-surface UX argument applies even more strongly for RU (Telegram-native audience), ZH (WeChat 服务号 link-previews) and HI (WhatsApp-forwardable PDFs as the primary distribution format per the Hindi researcher's explicit format discipline). For Arabic, wrap the Latin slug in Arabic metadata: `<title>` and `<h1>` in Arabic, `<meta description>` in Arabic, but URL in transliterated Latin. Optionally transliterate key terms into the slug (`/ar/shahadat-adam-mumana3a-emaar` rather than `/ar/emaar-noc-fees`) where the Arabic transliteration reads as natural Latin to a native speaker.

## 2. hreflang matrix (example for a post published in EN + AR + RU)

```html
<!-- In the <head> of all three pages -->
<link rel="alternate" hreflang="en" href="https://dalya.ai/en/selling-off-plan-fees" />
<link rel="alternate" hreflang="ar" href="https://dalya.ai/ar/selling-off-plan-fees" />
<link rel="alternate" hreflang="ar-AE" href="https://dalya.ai/ar/selling-off-plan-fees" />
<link rel="alternate" hreflang="ru" href="https://dalya.ai/ru/selling-off-plan-fees" />
<link rel="alternate" hreflang="x-default" href="https://dalya.ai/en/selling-off-plan-fees" />
```

Rules:
- hreflang tags are **symmetric** — each locale page lists all other locales, not just itself.
- `ar-AE` is the primary Arabic regional code for Dalya. `ar` is the generic fallback for non-AE Arabic browsers; list both.
- Add `ar-SA` only on posts where Saudi is a named audience segment (post 8 GCC POA, post 12 not applicable).
- `ru` has no regional variants — list as plain `ru`.
- `zh` on Dalya is Simplified Chinese; use `zh-Hans` rather than `zh-CN`, since audiences in Singapore, Malaysia, HK (partially) all read Simplified but the `CN` region code implies mainland-only.
- `hi-IN` for Hindi — the `-IN` code is appropriate because the content is Indian-investor-specific (FEMA is an Indian regulation).
- For posts not translated into a given language, **omit the hreflang entry** — do not list an untranslated locale.
- `x-default` always points at the EN version.

## 3. RTL and Arabic rendering

CLAUDE.md already mandates logical CSS properties (`margin-inline-start`, `padding-inline-end`, `inset-inline-*`) rather than directional ones. That foundation is in place. The AR-specific layer on top:

**Direction attribute.**
- `<html lang="ar" dir="rtl">` on every `/ar/` page.
- `<html lang="en" dir="ltr">` on `/en/`, `<html lang="ru" dir="ltr">` on `/ru/`, `<html lang="zh" dir="ltr">` on `/zh/`, `<html lang="hi" dir="ltr">` on `/hi/`.

**Bi-directional inline content.** Any AED figure, English developer name, or English regulatory term inside Arabic prose must be wrapped:
```html
<p>رسوم التحويل هي <span dir="ltr">AED 48,000</span> في عقار بقيمة <span dir="ltr">AED 2.4M</span>.</p>
```
Without the `dir="ltr"` wrapper, ligature-break artefacts and BiDi ordering issues break the figure display — particularly on iOS Safari and older Android WebViews.

**Numerals.** Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) vs Western Arabic digits (0123456789): **recommend Western digits** for all AED amounts, fee tables, and percentage figures on Dalya's Arabic pages. Rationale:
- DLD's own Arabic service catalog uses Western digits.
- Al Bayan, Emarat Al Youm and Al Khaleej — Dalya's benchmark Arabic publishers — use Western digits for currency figures.
- The target audience (GCC / Emirati investors) reads both fluently and copy-pastes figures into Excel / WhatsApp where Western digits are the expected input.
- Dalya's brand token `JetBrains Mono` for figures has no Arabic-Indic numeral variant; forcing Arabic-Indic digits breaks the type pairing.

Render as `1,250,000 د.إ` not `١٬٢٥٠٬٠٠٠ درهم`.

**Date formatting.** Use Gregorian dates (الميلادي) for all publication dates and procedural deadlines — matches DLD and every AR publisher. Hijri dates are not appropriate for commercial real estate content. Format: `2026-04-24` or `24 أبريل 2026` in prose.

**Font fallback stack.** The project tokens are `Plus Jakarta Sans` (UI) and `JetBrains Mono` (figures). Neither covers Arabic, Cyrillic, CJK or Devanagari. Recommended fallback cascade:

```css
/* Dalya multilingual font stack */
font-family:
  'Plus Jakarta Sans',        /* EN, RU (Cyrillic), most Latin */
  'IBM Plex Sans Arabic',     /* AR — matches Jakarta Sans geometry */
  'Noto Sans SC',             /* ZH Simplified */
  'Noto Sans Devanagari',     /* HI */
  -apple-system, 'Segoe UI', Roboto, sans-serif;

font-family:
  'JetBrains Mono',           /* figures, code */
  'IBM Plex Mono Arabic',     /* AR figures */
  'Noto Sans Mono CJK SC',    /* ZH figures */
  monospace;
```

IBM Plex Arabic pairs geometrically with Plus Jakarta Sans (both are neo-grotesque sans-serifs designed for cross-script pairing). Plus Jakarta Sans covers Cyrillic natively, so `/ru/` pages do not need an additional Cyrillic fallback. Noto Sans SC covers Simplified Chinese; Noto Sans Devanagari covers Hindi — both are open-license Google Fonts with predictable rendering across iOS/Android/Windows.

## 4. Translation workflow and glossary

**The workflow, post by post:**
1. EN post drafted and approved in CMS (authoritative version for most posts; AR on post 3; RU on posts 5 and 6; HI on post 12).
2. Translation model assigned per the per-post brief (A / B / C / D — see publishing-plan.md).
3. For Model A (direct LLM): machine translation pass, spot-check by a native-speaker reviewer on regulatory passages only.
4. For Model B (LLM + native edit): machine translation pass + full native-speaker editorial pass focusing on tone, regulatory accuracy, named-figure preservation.
5. For Model C (full human): professional translator, not LLM-assisted, with a second native-speaker QA pass for compliance content.
6. For Model D (deferred): no translation; locale page does not exist; no hreflang entry.
7. Each locale version goes through a metadata pass: `<title>`, `<meta description>`, OG tags, structured data all translated; URL slug remains Latin (per §1).
8. Final QA: numeral rendering, BiDi wrapper check for AR, font-fallback visual check per locale.

**Translation-scoped CMS fields.** Per post, the following fields must be locale-specific:
- Title, subtitle, body content, meta title, meta description, OG title, OG description, OG image alt text.
- Author bio text (author name stays in native script; bio blurb translates).
- CTA button label (per the locked CTA table in §4 below).
- Internal-link anchor text (translated — do not leave English anchors inside Arabic prose).
- Structured-data `inLanguage` field.

**CTA lock table (never machine-translate, never deviate):**

| Language | Seller CTA (primary) | Buyer CTA (primary) | AI naming |
|---|---|---|---|
| EN | "Upload your SPA" | "Ask Dalya" | Dalya's property advisor |
| AR | «ارفع عقد البيع والشراء» | «اسأل داليا» | مستشار داليا العقاري |
| RU | (native reviewer to finalise — candidate: «Загрузите договор купли-продажи») | (candidate: «Спросите Далю») | (candidate: «Консультант Дали по недвижимости») |
| ZH | (native reviewer to finalise — candidate: 「上传您的 SPA 合同」) | (candidate: 「咨询 Dalya」) | (candidate: Dalya 房产顾问) |
| HI (Hinglish) | "Apna SPA upload karein" | "Dalya se poochein" | Dalya ka property advisor |

Arabic translations are finalised per the Arabic researcher's recommendation (§6 point 6). Russian and Chinese CTA translations are candidates only and require native-speaker review before publication; do not ship auto-translated CTAs.

**Starter glossary (Dalya-specific terms):**

| EN | AR | RU | ZH (Simplified) | HI / Hinglish |
|---|---|---|---|---|
| Off-plan resale | إعادة بيع عقار على الخارطة | переуступка прав / резале off-plan | 期房转售 | Off-plan resale (Latin kept) |
| SPA (Sales & Purchase Agreement) | اتفاقية البيع والشراء | договор купли-продажи (SPA) | 买卖协议 (SPA) | SPA (Latin kept) |
| NOC (No-Objection Certificate) | شهادة عدم الممانعة | NOC (сертификат о неимении возражений) | NOC (无异议证书) | NOC (Latin kept) |
| Form F | نموذج F | Form F | Form F | Form F |
| Form A | نموذج A (اتفاقية تسويق البائع والوسيط) | Form A (соглашение продавца и брокера) | Form A | Form A |
| Trakheesi permit | تصريح تراخيصي | разрешение Trakheesi | Trakheesi 许可证 | Trakheesi permit |
| Oqood | أوقود | Oqood / Окуд | 阿库德 (Oqood) | Oqood |
| DLD (Dubai Land Department) | دائرة الأراضي والأملاك في دبي | Земельный департамент Дубая (DLD) | 迪拜土地局 (DLD) | DLD |
| RERA | وكالة التنظيم العقاري (ريرا) | RERA (Агентство регулирования недвижимости) | RERA (房地产监管局) | RERA |
| 0.15% (Dalya commission) | 0.15٪ | 0,15% | 0.15% | 0.15% |
| 2% (market commission) | 2٪ (المعتاد) | 2% (рыночная) | 2%（市场费率） | 2% (market rate) |
| AED | د.إ (or AED) | AED (дирхам ОАЭ) | 迪拉姆 (AED) | AED |
| Verified SPA (Dalya badge) | عقد بيع موثّق | SPA проверен | 已验证 SPA | Verified SPA |
| NOC-eligible (status pill, sage) | مؤهل لعدم الممانعة | готов к NOC | 可申请 NOC | NOC-eligible |
| Payment plan | خطة الدفع | рассрочка / план платежей | 付款计划 | Payment plan |
| Assignment of contract | تنازل عن العقد | переуступка прав | 合同转让 | Assignment |
| Non-resident (tax) | غير مقيم ضريبياً | налоговый нерезидент | 非税务居民 | Non-resident |

This glossary is **authoritative for Dalya content** — use it in every locale, do not free-translate. Route all additions through a review before adding. Particularly important for AR (where شهادة عدم الممانعة has competing short forms in the wild) and for RU (where переуступка vs ассайнмент vs цессия are used inconsistently by competitors).

## 5. Dalya brand transliteration — requires native-speaker review before publishing

**Arabic.** `داليا` — confirmed by the Arabic researcher as the correct transliteration (§6 point 7). Alif-yaa-alif pattern reads as a feminine name in Gulf Arabic; keeps phonetic parity across MSA and Khaleeji. **Verify with one native speaker before shipping the first Arabic post.**

**Russian.** Two candidates: `Даля` (shorter, matches Slavic given-name convention, phonetic to "Da-lya") vs `Далия` (longer, matches the Arabic `داليا` more literally, reads as a feminine given-name common in Tatar / Kazakh Russian-speakers). Recommendation: **`Даля`** as primary — shorter, cleaner in headlines, more phonetic to the intended pronunciation. `Далия` as an allowed alternate transliteration for formal contexts (byline, legal footer). Native-speaker review required before locking.

**Chinese (Simplified).** Two candidates: `达利亚` (purely phonetic, neutral semantics — 达 "reach/arrive", 利 "benefit", 亚 "Asia/second") vs `黛利亚` (黛 = a deep blue-black, used in feminine names, slightly more elegant but less neutral). Recommendation: **`达利亚`** as primary — the 达 / 利 semantic field aligns loosely with the "property intelligence" positioning ("to reach" + "benefit"), and 达利亚 is the standard mainland rendering of the name Dalia. Native-speaker review required.

**Hindi (Devanagari).** `डालिया` — phonetic, reads correctly in Devanagari. Unambiguous. The Hinglish post (post 12) uses `Dalya` in Latin inside Hinglish prose, not Devanagari — per HI researcher format discipline.

All four non-English transliterations must be confirmed with a native speaker before the first piece of content ships in that locale. Do not treat this as a solved problem based on planner recommendations alone.

## 6. Social / alt-channel caveat

The publishing plan is a blog-and-canonical-pages program. For Mandarin specifically, the Mandarin researcher's verdict must be honoured in the architecture: `60–80% of the Chinese-speaking funnel is WeChat + Xiaohongshu, not SEO`. The two `/zh/` blog posts (post 8 remote-selling, post 10 commission) are a **trust layer** and a funnel entry for Baidu searchers — they are not the primary Chinese-market growth channel.

The architectural implication: the `/zh/` pages should each include a visible WeChat QR block and a Xiaohongshu handle block in the footer, so the Baidu-entry reader can convert to the WeChat / XHS funnel where the actual conversion happens. Do not measure `/zh/` page performance purely by on-site conversion; measure it by WeChat/XHS follower acquisition attributable to the blog traffic source.

For Russian, the blog is a primary channel — VC.ru / Forbes.ru / Telegram are secondary trust layers. For Hindi, the WhatsApp-forwardable PDF is the **primary** artefact for post 12; the blog page is secondary. The `/hi/` page should include a prominent "Download the PDF" CTA and a WhatsApp-share button; the PDF is the asset that actually travels in the audience's native distribution pattern.

## 7. Crawl and indexation

**Robots.txt.** Single robots file at `https://dalya.ai/robots.txt`. Allow all locales; disallow any staging / admin paths. Do not geo-block.

**Sitemap structure.** One XML sitemap index at the root (`https://dalya.ai/sitemap.xml`) pointing to five locale-specific sitemaps:

```xml
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://dalya.ai/sitemap-en.xml</loc></sitemap>
  <sitemap><loc>https://dalya.ai/sitemap-ar.xml</loc></sitemap>
  <sitemap><loc>https://dalya.ai/sitemap-ru.xml</loc></sitemap>
  <sitemap><loc>https://dalya.ai/sitemap-zh.xml</loc></sitemap>
  <sitemap><loc>https://dalya.ai/sitemap-hi.xml</loc></sitemap>
</sitemapindex>
```

Each locale sitemap includes `xhtml:link rel="alternate"` hreflang entries per URL, matching the in-page hreflang tags. This gives search engines two consistent signals (sitemap + in-page) rather than one, which is the Google-documented best practice for multi-lingual sites.

**Search-engine submission per language:**

| Locale | Primary engines | Webmaster tools |
|---|---|---|
| EN | Google, Bing | Google Search Console (global), Bing Webmaster |
| AR | Google | GSC property for `dalya.ai/ar/` |
| RU | Google, **Yandex** | GSC + Yandex.Webmaster — Yandex is ~60% of RU search share and has different ranking signals |
| ZH | **Baidu** primarily, Bing secondary | Baidu Webmaster Tools (requires ICP filing for deep indexing; without ICP, expect reduced crawl depth but surface indexation works) |
| HI | Google | GSC only |

Yandex.Webmaster submission for `/ru/` content is non-optional — without it, the Russian posts will rank on Google but miss the ~60% of RU-language searches that happen on Yandex. Baidu submission for `/zh/` will have limited impact without ICP filing (Chinese internet regulation requires ICP for full Baidu indexation of sites targeting mainland China), which is a significant business decision separate from this architecture — flag to Dalya leadership that without ICP, `/zh/` pages will under-index on Baidu and the WeChat/XHS social route is even more important.

## 8. Performance and schema

**Font subsetting.** Each locale should load only the font subsets it needs. Serve the Latin subset of Plus Jakarta Sans on `/en/`, Latin + Cyrillic subset on `/ru/`, Latin only on `/en/` and `/zh/`, plus the corresponding IBM Plex Arabic / Noto Sans SC / Noto Sans Devanagari subset for the target script. Unicode-range `@font-face` with subset URLs is the standard mechanism. Target: ~25KB additional font payload per locale beyond the Latin baseline.

**Image alt text localisation.** Every `<img alt>` must be translated per locale. A common failure pattern is an Arabic page with English alt text on data-table screenshots — breaks screen readers, hurts accessibility, breaks image-search ranking in the target locale.

**Structured data — `RealEstateListing` schema with `inLanguage`.** Every listing page (not blog post; listing pages specifically) should carry schema.org `RealEstateListing` structured data. Required properties: `name`, `description`, `price`, `priceCurrency: "AED"`, `address` (with `addressCountry: "AE"`, `addressLocality: "Dubai"`), `inLanguage` set to the locale code (`en`, `ar`, `ru`, `zh-Hans`, `hi-IN`). Blog posts should use `Article` schema with `inLanguage` and `translationOfWork` pointing to the canonical EN version (for non-EN translations) or to itself (for EN and natively-authored non-EN posts like the AR-primary post 3 and the HI-primary post 12).

Example `Article` schema for the RU primary post 6:

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "inLanguage": "ru",
  "headline": "3-НДФЛ, CRS и ставка 30%: что реально платит российский нерезидент при продаже недвижимости в Дубае",
  "author": {"@type": "Organization", "name": "Dalya", "alternateName": "داليا / Даля / 达利亚"},
  "publisher": {"@type": "Organization", "name": "Dalya", "logo": {...}},
  "datePublished": "2026-05-29",
  "workTranslation": [
    {"@type": "Article", "inLanguage": "en", "url": "https://dalya.ai/en/russian-tax-dubai-property-sale"}
  ]
}
```

For the AR-primary post 3 and HI-primary post 12, `translationOfWork` is omitted because these are native works, not translations — this is a common error that misrepresents the content's authority to search engines.

---

**Review trigger.** Any publishing decision that conflicts with these notes — native-script slugs on Arabic, Yandex submission skipped, CTAs free-translated, `داليا` transliteration changed without review — should pause for explicit sign-off. The CTA lock table and the brand transliteration candidates in §5 are the two most common failure points for multilingual publishing programs and warrant an explicit go/no-go from a native reviewer before the first post ships in that locale.
