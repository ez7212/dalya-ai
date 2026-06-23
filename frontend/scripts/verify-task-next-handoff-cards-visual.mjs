import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { chromium } from '@playwright/test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const evidenceRoot = resolve(repoRoot, '.omo/evidence/task-11-handoff-cards')
const tempRoot = resolve(frontendRoot, '.task-11-handoff-cards-visual')
const outputArgIndex = process.argv.indexOf('--output')
const outputPath = outputArgIndex >= 0
  ? resolve(frontendRoot, process.argv[outputArgIndex + 1] ?? '')
  : resolve(repoRoot, '.omo/evidence/task-11-handoff-cards.png')
const transcriptPath = resolve(evidenceRoot, 'visual-transcript.json')
const htmlPath = resolve(evidenceRoot, 'handoff-cards.html')
const compiledQueuePath = resolve(tempRoot, 'today-queue.mjs')
const compiledCardPath = resolve(tempRoot, 'QueueHandoffCard.mjs')
const compiledTodayQueuePath = resolve(tempRoot, 'TodayQueue.mjs')

function assertCheck(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label}: ${JSON.stringify(details)}`)
  }
  return { label, passed: true, details }
}

function compileModule(sourcePath, compiledPath, jsx = ts.JsxEmit.Preserve) {
  let source = readFileSync(sourcePath, 'utf8')
  source = source.replace(
    "import Link from 'next/link'",
    "function Link({ href, children, ...props }) { return <a href={typeof href === 'string' ? href : '#'} {...props}>{children}</a> }",
  )
  source = source.replace(
    "import { QueueHandoffCard, queueActionLabel } from './QueueHandoffCard'",
    "import { QueueHandoffCard, queueActionLabel } from './QueueHandoffCard.mjs'",
  )
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      jsx,
      strict: true,
      verbatimModuleSyntax: true,
    },
    fileName: sourcePath,
    reportDiagnostics: true,
  })

  const diagnostics = output.diagnostics ?? []
  if (diagnostics.length > 0) {
    const rendered = diagnostics.map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')).join('\n')
    throw new Error(`Transpilation diagnostics for ${sourcePath}:\n${rendered}`)
  }
  writeFileSync(compiledPath, output.outputText)
}

function dashboardFixture() {
  return {
    agent: { name: 'Leila', brokerage: 'Dalya Pilot', market: 'Dubai', lastUpdated: '10:00' },
    summary: { openTasks: 0, qualifiedBuyers: 1, viewingsToday: 0, offersAtRisk: 0, openEscalations: 1 },
    performance: { scope: 'agent', primary: { key: 'today', label: 'Today', metrics: {} }, windows: [] },
    conversationInbox: [
      {
        id: 'conv-offer',
        buyerName: 'Yusuf Mansour',
        buyerPhone: '+971500000002',
        listingName: 'Emaar Oasis Villa',
        summary: 'Buyer asked whether the seller would consider a counter range.',
        nextStep: 'Prepare counter guidance for agent review',
        lastMessage: 'Can we offer AED 4.2M today?',
        lastSeen: '09:48',
        messageCount: 9,
        offerCount: 1,
        openEscalationCount: 0,
        interestLevel: 'high',
        needsReply: true,
        needsReplyReason: 'Offer-intent buyer message is newer than the last agent response.',
        needsReplyPriorityScore: 96,
        hasPendingDraft: false,
        lastBuyerMessageAt: '09:48',
        lastBuyerMessageAtRaw: '2026-06-22T09:48:00+04:00',
        readiness: {
          stage: 'offer_ready',
          missingFields: ['proof_of_funds', 'seller_floor'],
          nextBestAction: 'prepare_counter_guidance',
          nextBestActionReason: 'Budget and target listing are known, but proof of funds is not confirmed.',
          score: 91,
          priorityBand: 'high',
          presentFields: { budget: 'AED 4.2M', target_listing: 'Emaar Oasis Villa' },
        },
      },
    ],
    morningQueue: [],
    escalationInbox: [
      escalationFixture(),
    ],
    drafts: { replyDrafts: [], outreachDrafts: [] },
    campaignSnapshot: { headline: '', activeCampaigns: 0, newLeads: 0, qualifiedLeads: 0, responseRate: '0%', costPerQualifiedLead: 'AED 0', campaigns: [] },
    overnightBuyerDigest: [],
    todaysViewings: [],
    personalMomentum: { weekLabel: '', stats: [], focus: '', streaks: [] },
  }
}

function escalationFixture() {
  return {
    id: 'esc-offer',
    token: 'ABCD12',
    conversationId: 'conv-offer',
    aiMode: 'agent_controlled',
    category: 'offer_counter',
    state: 'updated',
    urgency: 'critical',
    buyerName: 'Yusuf Mansour',
    buyerPhone: '+971500000002',
    listingName: 'Emaar Oasis Villa',
    unitNumber: 'V-14',
    latestQuestion: 'Can we offer AED 4.2M today?',
    questionCount: 2,
    lastBuyerMessageAt: '09:48',
    lastBuyerMessageAtRaw: '2026-06-22T09:48:00+04:00',
    openedAt: '09:30',
    openedAtRaw: '2026-06-22T09:30:00+04:00',
    routeExpiresAt: '10:30',
    routeExpiresAtRaw: '2026-06-22T10:30:00+04:00',
    questions: [],
  }
}

function renderHtml(queueMarkup, escalationMarkup) {
  return `<!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Task 11 handoff cards QA</title>
      <style>
        body { margin: 0; background: #FAFAF9; color: #3D3D39; font-family: Inter, system-ui, sans-serif; }
        main { max-width: 1040px; margin: 0 auto; padding: 24px 18px 40px; }
        h1 { margin: 0 0 18px; font-size: 26px; line-height: 1.1; letter-spacing: 0; }
        section, .inbox-panel { border: 1px solid #D6D6D2; background: #FFFFFF; border-radius: 12px; overflow: hidden; }
        section > div:first-child { padding: 16px 20px; border-bottom: 1px solid #E8E8E5; }
        h2 { margin: 4px 0 0; font-size: 17px; }
        p { margin: 6px 0 0; color: #5C5C57; font-size: 14px; line-height: 1.45; }
        ol { list-style: none; margin: 0; padding: 0; }
        li { display: grid; grid-template-columns: 48px minmax(0, 1fr) 210px; gap: 14px; padding: 18px 20px; border-top: 1px solid #E8E8E5; }
        li:first-child { border-top: 0; }
        li > div:first-child > div { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 8px; background: #EEF2F7; color: #324B6B; }
        li > div:nth-child(3) { display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-start; justify-content: flex-end; }
        span { border-radius: 4px; background: #F4F4F2; padding: 3px 7px; font-size: 11px; font-weight: 650; color: #5C5C57; }
        h3 { margin: 9px 0 0; font-size: 15px; }
        a, button { display: inline-flex; align-items: center; gap: 6px; border: 1px solid #D6D6D2; background: white; border-radius: 8px; color: #324B6B; font-weight: 650; padding: 6px 10px; text-decoration: none; }
        dl, dt, dd { margin: 0; }
        .mt-3.rounded-md, .inbox-panel > div { margin-top: 12px; border: 1px solid #D6D6D2; border-radius: 8px; background: #F4F4F2; padding: 12px; }
        .grid { display: grid; gap: 12px; }
        .sm\\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        dt, .text-\\[10px\\] { color: #7B7B76; font-size: 10px; font-weight: 750; text-transform: uppercase; letter-spacing: .1em; }
        dd { margin-top: 4px; color: #3D3D39; font-size: 12px; font-weight: 650; line-height: 1.45; }
        .bg-warning-50 { background: #F4DFC8; }
        .text-warning-800 { color: #7A4F25; }
        .inbox-panel { margin-top: 20px; padding: 18px 20px; }
        .inbox-panel h2 { margin: 0 0 10px; }
        .material-symbols-outlined { display: inline-block; width: 16px; height: 16px; overflow: hidden; color: transparent; vertical-align: middle; }
        .material-symbols-outlined::before { content: ""; display: block; width: 8px; height: 8px; margin: 4px; border-radius: 999px; background: #324B6B; }
        @media (max-width: 680px) {
          main { padding: 16px 12px 32px; }
          li { grid-template-columns: 1fr; }
          li > div:nth-child(3) { justify-content: flex-start; }
          .sm\\:grid-cols-2 { grid-template-columns: 1fr; }
        }
      </style>
    </head>
    <body>
      <main>
        <h1>Task 11 structured handoff cards</h1>
        ${queueMarkup}
        <div class="inbox-panel">
          <h2>Escalation inbox row handoff</h2>
          ${escalationMarkup}
        </div>
      </main>
    </body>
  </html>`
}

mkdirSync(evidenceRoot, { recursive: true })
mkdirSync(tempRoot, { recursive: true })
mkdirSync(dirname(outputPath), { recursive: true })
compileModule(resolve(frontendRoot, 'src/components/agent-dashboard/today-queue.ts'), compiledQueuePath)
compileModule(resolve(frontendRoot, 'src/components/agent-dashboard/QueueHandoffCard.tsx'), compiledCardPath, ts.JsxEmit.ReactJSX)
compileModule(resolve(frontendRoot, 'src/components/agent-dashboard/TodayQueue.tsx'), compiledTodayQueuePath, ts.JsxEmit.ReactJSX)

const { buildTodayQueue } = await import(pathToFileURL(compiledQueuePath).href)
const { EscalationHandoffPanel } = await import(pathToFileURL(compiledCardPath).href)
const { TodayQueue } = await import(pathToFileURL(compiledTodayQueuePath).href)
const data = dashboardFixture()
const queue = buildTodayQueue({ data, needsReply: data.conversationInbox, now: new Date('2026-06-22T10:00:00+04:00') })
const queueMarkup = renderToStaticMarkup(createElement(TodayQueue, {
  items: queue,
  actionsEnabled: true,
  taskActionState: {},
  escalationActionState: {},
  refreshState: 'idle',
  onTaskDone: () => {},
  onTaskSnooze: () => {},
  onResolveEscalation: () => {},
  onRefreshHotList: () => {},
}))
const escalationMarkup = renderToStaticMarkup(createElement(EscalationHandoffPanel, { thread: escalationFixture() }))
writeFileSync(htmlPath, renderHtml(queueMarkup, escalationMarkup))

const checks = [
  assertCheck(queue.some((item) => item.kind === 'escalation'), 'fixture renders escalation handoff card'),
  assertCheck(queue.some((item) => item.kind === 'needs_reply'), 'fixture renders offer-intent conversation handoff card'),
]

let browser = null
try {
  browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 })
  await page.goto(pathToFileURL(htmlPath).href)
  const body = await page.locator('body').innerText()
  const normalizedBody = body.toLowerCase()
  checks.push(assertCheck(normalizedBody.includes('buyer intent'), 'browser renders buyer intent label'))
  checks.push(assertCheck(normalizedBody.includes('known'), 'browser renders known field label'))
  checks.push(assertCheck(normalizedBody.includes('missing'), 'browser renders missing blocker label'))
  checks.push(assertCheck(normalizedBody.includes('suggested action'), 'browser renders suggested action label'))
  checks.push(assertCheck(normalizedBody.includes('work surface'), 'browser renders route target label'))
  checks.push(assertCheck(normalizedBody.includes('source'), 'browser renders source label'))
  checks.push(assertCheck(normalizedBody.includes('agent review/counter guidance only'), 'browser renders offer review-only copy'))
  checks.push(assertCheck(!body.includes('\nOpen\n'), 'browser does not expose generic Open action text'))
  await page.screenshot({ path: outputPath, fullPage: true })
  await page.close()
} finally {
  if (browser) await browser.close()
  rmSync(compiledQueuePath, { force: true })
  rmSync(compiledCardPath, { force: true })
  rmSync(compiledTodayQueuePath, { force: true })
}

const transcript = {
  scenario: 'Task 11 visual QA: structured queue and escalation handoff cards',
  invocation: `cd frontend && node scripts/verify-task-next-handoff-cards-visual.mjs --output ${outputPath.startsWith(repoRoot) ? outputPath.slice(repoRoot.length + 1) : outputPath}`,
  htmlPath,
  outputPath,
  checks,
  cleanup: 'Closed Playwright browser/page and removed compiled temporary modules.',
}
writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
console.log(JSON.stringify({ outputPath, transcriptPath, checks: checks.length }, null, 2))
