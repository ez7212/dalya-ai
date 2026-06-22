import { chromium } from '@playwright/test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'
import { mkdirSync, writeFileSync } from 'node:fs'
import { readFileSync, rmSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const presenterSourcePath = resolve(frontendRoot, 'src/components/readiness/deal-readiness.ts')
const calloutSourcePath = resolve(frontendRoot, 'src/components/readiness/DealReadinessCallout.tsx')
const compiledPresenterPath = resolve(frontendRoot, '.task8-deal-readiness-presenter-visual.mjs')
const compiledCalloutPath = resolve(frontendRoot, '.task8-deal-readiness-callout-visual.mjs')
const htmlPath = resolve(repoRoot, '.omo/ulw-loop/evidence/task8-C001-readiness-reasons-visual.html')
const screenshotPath = resolve(repoRoot, '.omo/ulw-loop/evidence/task8-C001-readiness-reasons-visual.png')
const transcriptPath = resolve(repoRoot, '.omo/ulw-loop/evidence/task8-C001-readiness-reasons-visual.txt')

function compileModule(sourcePath, outputPath, options = {}) {
  const source = readFileSync(sourcePath, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      strict: true,
    },
    fileName: sourcePath,
    reportDiagnostics: true,
  })

  const diagnostics = output.diagnostics ?? []
  if (diagnostics.length > 0) {
    const rendered = diagnostics
      .map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'))
      .join('\n')
    throw new Error(`Transpilation diagnostics for ${sourcePath}:\n${rendered}`)
  }

  mkdirSync(dirname(outputPath), { recursive: true })
  writeFileSync(outputPath, options.rewrite ? options.rewrite(output.outputText) : output.outputText)
}

compileModule(presenterSourcePath, compiledPresenterPath)
compileModule(calloutSourcePath, compiledCalloutPath, {
  rewrite: (outputText) => outputText.replace("'./deal-readiness'", "'./.task8-deal-readiness-presenter-visual.mjs'"),
})

const {
  buildDealReadinessDisplay,
  normalizeDealReadiness,
} = await import(pathToFileURL(compiledPresenterPath).href)
const {
  DealReadinessPanel,
  DealReadinessSummaryLine,
} = await import(pathToFileURL(compiledCalloutPath).href)

const hotBuyerSummary = normalizeDealReadiness({
  stage: 'viewing_ready',
  missing_fields: ['other_agent_status'],
  next_best_action: 'prepare_viewing_brief',
  next_best_action_reason: 'Viewing window is confirmed; validate access notes before proposing slots.',
  score: 82,
  priority_band: 'high',
  present_fields: {
    budget_max_aed: 2_500_000,
    financing: 'cash',
    viewing_availability: 'Saturday afternoon',
  },
})

const buyerCardSummary = normalizeDealReadiness({
  stage: 'partially_qualified',
  missing_fields: ['purpose', 'viewing_availability', 'other_agent_status'],
  next_best_action: 'ask_next_readiness_question',
  next_best_action_reason: 'Budget and financing are present; timeline still needs agent confirmation.',
  score: 55,
  priority_band: 'normal',
  present_fields: {
    budget_max_aed: 2_500_000,
    financing: 'mortgage',
    timeline: 'this_month',
  },
})

const hotBuyerDisplay = buildDealReadinessDisplay(hotBuyerSummary)
const buyerCardDisplay = buildDealReadinessDisplay(buyerCardSummary)
const hotBuyerLineHtml = renderToStaticMarkup(createElement(DealReadinessSummaryLine, { readiness: hotBuyerSummary }))
const conversationLineHtml = renderToStaticMarkup(createElement(DealReadinessSummaryLine, { readiness: buyerCardSummary }))
const buyerListLineHtml = renderToStaticMarkup(createElement(DealReadinessSummaryLine, {
  compact: true,
  readiness: buyerCardSummary,
}))
const buyerCardPanelHtml = renderToStaticMarkup(createElement(DealReadinessPanel, { readiness: buyerCardSummary }))

if (!hotBuyerSummary || !buyerCardSummary || !hotBuyerDisplay || !buyerCardDisplay) {
  throw new Error('Expected production readiness presenter to produce visual QA display values')
}
if (!hotBuyerLineHtml.includes('Prepare viewing brief') || !buyerCardPanelHtml.includes('Ask next readiness question')) {
  throw new Error('Expected actual React readiness components to render the presenter output')
}

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Task 8 readiness reasons visual QA</title>
    <style>
      :root {
        color-scheme: light;
        --brand-50: #eef6ff;
        --brand-100: #d6e9ff;
        --brand-600: #2563eb;
        --brand-700: #1d4ed8;
        --brand-800: #1e40af;
        --brand-900: #1e3a8a;
        --neutral-50: #f8fafc;
        --neutral-100: #f1f5f9;
        --neutral-200: #e2e8f0;
        --neutral-500: #64748b;
        --neutral-600: #475569;
        --neutral-700: #334155;
        --neutral-800: #1f2937;
        --neutral-900: #111827;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        background: var(--neutral-50);
        color: var(--neutral-900);
      }

      main {
        margin: 0 auto;
        max-width: 1040px;
        padding: 24px;
      }

      h1 {
        margin: 0 0 18px;
        font-size: 26px;
        font-weight: 650;
        letter-spacing: 0;
      }

      .grid {
        display: grid;
        gap: 18px;
      }

      @media (min-width: 900px) {
        .grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
      }

      .section {
        overflow: hidden;
        border: 1px solid var(--neutral-200);
        border-radius: 8px;
        background: #fff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      }

      .section-header {
        border-bottom: 1px solid var(--neutral-200);
        padding: 16px 18px;
      }

      .eyebrow {
        margin: 0;
        color: var(--neutral-500);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .section-title {
        margin: 4px 0 0;
        font-size: 15px;
        font-weight: 650;
      }

      .row {
        padding: 16px 18px;
      }

      .row + .row {
        border-top: 1px solid var(--neutral-200);
      }

      .row-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
      }

      .buyer {
        margin: 0;
        font-size: 14px;
        font-weight: 650;
      }

      .subtle {
        margin: 4px 0 0;
        color: var(--neutral-500);
        font-size: 12px;
      }

      .body-copy {
        margin: 12px 0 0;
        color: var(--neutral-600);
        font-size: 14px;
        line-height: 1.55;
      }

      .pill {
        flex: none;
        border-radius: 999px;
        background: var(--brand-50);
        padding: 3px 8px;
        color: var(--brand-700);
        font-size: 11px;
        font-weight: 700;
      }

      .readiness {
        margin-top: 12px;
        border: 1px solid var(--brand-100);
        border-radius: 6px;
        background: var(--brand-50);
        padding: 10px 12px;
        color: var(--brand-900);
        font-size: 12px;
      }

      .readiness strong {
        display: block;
        margin-bottom: 3px;
        font-weight: 700;
      }

      .readiness p {
        margin: 3px 0 0;
      }

      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 10px;
      }

      .chip {
        border: 1px solid var(--neutral-200);
        border-radius: 999px;
        background: var(--neutral-50);
        padding: 3px 8px;
        color: var(--neutral-700);
        font-size: 11px;
        font-weight: 600;
      }

      .actual-react {
        margin-top: 12px;
      }

      .actual-react [class*="rounded-md"],
      .actual-react [class*="rounded-lg"] {
        border-radius: 6px;
      }

      .actual-react [class*="border-brand-100"] {
        border: 1px solid var(--brand-100);
      }

      .actual-react [class*="bg-brand-50"] {
        background: var(--brand-50);
      }

      .actual-react [class*="text-brand-950"],
      .actual-react [class*="text-brand-900"] {
        color: var(--brand-900);
      }

      .actual-react [class*="text-brand-800"],
      .actual-react [class*="text-brand-700"] {
        color: var(--brand-800);
      }

      .actual-react [class*="font-semibold"],
      .actual-react [class*="font-medium"] {
        font-weight: 700;
      }

      .actual-react [class*="text-xs"],
      .actual-react [class*="text-\\[11px\\]"] {
        font-size: 12px;
      }

      .actual-react [class*="text-sm"] {
        font-size: 14px;
      }

      .actual-react [class*="leading-relaxed"] {
        line-height: 1.55;
      }

      .actual-react [class*="mt-0\\.5"],
      .actual-react [class*="mt-1"],
      .actual-react [class*="mt-2"],
      .actual-react [class*="mt-3"] {
        margin-top: 6px;
      }

      .actual-react [class*="px-2\\.5"],
      .actual-react [class*="px-3"],
      .actual-react [class*="p-4"] {
        padding-left: 12px;
        padding-right: 12px;
      }

      .actual-react [class*="py-1\\.5"],
      .actual-react [class*="py-2"],
      .actual-react [class*="p-4"] {
        padding-top: 10px;
        padding-bottom: 10px;
      }

      .actual-react [class*="flex"] {
        display: flex;
      }

      .actual-react [class*="items-start"] {
        align-items: flex-start;
      }

      .actual-react [class*="gap-2"] {
        gap: 8px;
      }

      .actual-react [class*="material-symbols"] {
        flex: none;
        color: var(--brand-600);
      }

      .actual-react p {
        margin-bottom: 0;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Task 8 readiness reasons visual QA</h1>
      <div class="grid">
        <section class="section" aria-label="/agent hot buyers">
          <div class="section-header">
            <p class="eyebrow">Hot Buyers</p>
            <h2 class="section-title">High-intent buyers to reach first</h2>
          </div>
          <article class="row">
            <div class="row-top">
              <div>
                <p class="buyer">Maya Shah</p>
                <p class="subtle">Emaar Oasis · Updated today</p>
              </div>
              <span class="pill">Viewing ready</span>
            </div>
            <p class="body-copy">Buyer asked for a weekend viewing and confirmed cash purchase intent.</p>
            <div class="actual-react" data-component="DealReadinessSummaryLine">${hotBuyerLineHtml}</div>
          </article>
        </section>

        <section class="section" aria-label="/agent needs reply conversation context">
          <div class="section-header">
            <p class="eyebrow">Needs Reply</p>
            <h2 class="section-title">Conversation context</h2>
          </div>
          <article class="row">
            <div class="row-top">
              <div>
                <p class="buyer">Omar Khalid</p>
                <p class="subtle">Buyer asked about finance and timing</p>
              </div>
              <span class="pill">Needs reply</span>
            </div>
            <p class="body-copy">Dashboard conversation inbox receives deal_readiness metadata and renders the same callout when present.</p>
            <div class="actual-react" data-component="DealReadinessSummaryLine">${conversationLineHtml}</div>
          </article>
        </section>

        <section class="section" aria-label="/agent/buyers list cards">
          <div class="section-header">
            <p class="eyebrow">Buyers</p>
            <h2 class="section-title">Buyer list readiness card</h2>
          </div>
          <article class="row">
            <div class="row-top">
              <div>
                <p class="buyer">Omar Khalid</p>
                <p class="subtle">+971•••2244 · 2 conversations</p>
                <div class="chips">
                  <span class="chip">AED 2,500,000</span>
                  <span class="chip">Mortgage</span>
                  <span class="chip">This month</span>
                </div>
              </div>
              <span class="pill">Score 68</span>
            </div>
            <div class="actual-react" data-component="DealReadinessSummaryLine compact">${buyerListLineHtml}</div>
            <div class="actual-react" data-component="DealReadinessPanel">${buyerCardPanelHtml}</div>
          </article>
        </section>
      </div>
    </main>
  </body>
</html>`

const expectedTexts = [
  'Viewing ready',
  'Prepare viewing brief',
  'Viewing window is confirmed',
  'Partially qualified',
  'Ask next readiness question',
  'Missing: Purpose, Viewing availability, Other agent status',
  'Conversation context',
]

mkdirSync(dirname(htmlPath), { recursive: true })
writeFileSync(htmlPath, html)

const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 1180, height: 880 }, deviceScaleFactor: 1 })
  await page.goto(`file://${htmlPath}`, { waitUntil: 'load' })

  const checks = []
  for (const text of expectedTexts) {
    const locator = page.getByText(text, { exact: false }).first()
    await locator.waitFor({ state: 'visible', timeout: 5_000 })
    const box = await locator.boundingBox()
    if (!box || box.width <= 0 || box.height <= 0) {
      throw new Error(`Expected visible non-empty text: ${text}`)
    }
    checks.push({ text, passed: true, box })
  }

  await page.screenshot({ path: screenshotPath, fullPage: true })
  writeFileSync(
    transcriptPath,
    `${JSON.stringify({
      scenario: 'Task 8 readiness reasons visual QA',
      productionComponents: {
        componentsRendered: [
          'DealReadinessSummaryLine',
          'DealReadinessSummaryLine compact',
          'DealReadinessPanel',
        ],
        hotBuyerLineHtml,
        conversationLineHtml,
        buyerListLineHtml,
        buyerCardPanelHtml,
      },
      presenterOutput: {
        hotBuyerDisplay,
        buyerCardDisplay,
      },
      htmlPath,
      screenshotPath,
      expectedTexts,
      checks,
    }, null, 2)}\n`,
  )
  console.log(`Task 8 visual QA passed: ${screenshotPath}`)
} finally {
  await browser.close()
  rmSync(compiledPresenterPath, { force: true })
  rmSync(compiledCalloutPath, { force: true })
}
