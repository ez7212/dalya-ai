import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { chromium } from '@playwright/test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const evidenceRoot = resolve(repoRoot, '.omo/ulw-loop/evidence')
const queueSourcePath = resolve(frontendRoot, 'src/components/agent-dashboard/today-queue.ts')
const todayQueueSourcePath = resolve(frontendRoot, 'src/components/agent-dashboard/TodayQueue.tsx')
const compiledQueuePath = resolve(frontendRoot, '.task9-today-queue-visual-builder.mjs')
const compiledTodayQueuePath = resolve(frontendRoot, '.task9-today-queue-component.mjs')
const htmlPath = resolve(evidenceRoot, 'task9-C001-today-queue.html')
const screenshotPath = resolve(evidenceRoot, 'task9-C001-today-queue.png')
const desktopPath = resolve(evidenceRoot, 'task9-C001-today-queue-desktop.png')
const mobilePath = resolve(evidenceRoot, 'task9-C001-today-queue-mobile.png')
const transcriptPath = resolve(evidenceRoot, 'task9-C001-today-queue.txt')

function assertCheck(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label}: ${JSON.stringify(details)}`)
  }
  return { label, passed: true, details }
}

function compileModule({ sourcePath, compiledPath, jsx = ts.JsxEmit.Preserve }) {
  let source = readFileSync(sourcePath, 'utf8')
  if (sourcePath === todayQueueSourcePath) {
    source = source.replace(
      "import Link from 'next/link'",
      "function Link({ href, children, ...props }) { return <a href={typeof href === 'string' ? href : '#'} {...props}>{children}</a> }",
    )
    source = source.replace(
      "import { DealReadinessSummaryLine } from '../readiness/DealReadinessCallout'",
      `function DealReadinessSummaryLine({ readiness }) {
        if (!readiness) return null
        const headline = [readiness.stage, readiness.priorityBand ? readiness.priorityBand + ' priority' : null, readiness.score === null || readiness.score === undefined ? null : readiness.score + '/100'].filter(Boolean).join(' · ')
        return <div className="deal-readiness-line"><p>{headline}</p><p>Next: {readiness.nextBestAction}</p><p>{readiness.nextBestActionReason}</p></div>
      }`,
    )
  }
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

  mkdirSync(dirname(compiledPath), { recursive: true })
  writeFileSync(compiledPath, output.outputText)
}

function dashboardFixture() {
  return {
    agent: { name: 'Leila', brokerage: 'Dalya Pilot', market: 'Dubai', lastUpdated: '10:00' },
    summary: { openTasks: 1, qualifiedBuyers: 2, viewingsToday: 1, offersAtRisk: 0, openEscalations: 1 },
    performance: {
      scope: 'agent',
      primary: { key: 'today', label: 'Today', metrics: {} },
      windows: [],
    },
    conversationInbox: [
      {
        id: 'conv-1',
        buyerName: 'Maya Chen',
        buyerPhone: '+971500000002',
        listingName: 'Creek Harbour',
        summary: 'Asked whether the viewing can move earlier.',
        nextStep: 'Reply with two available slots',
        lastMessage: 'Can we view before lunch?',
        lastSeen: '09:45',
        messageCount: 8,
        offerCount: 0,
        openEscalationCount: 0,
        needsReply: true,
        needsReplyReason: 'Buyer message is newer than the last agent response.',
        hasPendingDraft: false,
        lastBuyerMessageAt: '09:45',
        lastBuyerMessageAtRaw: '2026-06-22T09:45:00+04:00',
      },
    ],
    morningQueue: [
      {
        id: 'task-overdue',
        source: 'task',
        priority: 'critical',
        title: 'Call seller before buyer reply',
        context: 'Seller approval is needed before sending the next message.',
        buyerName: 'Rami Haddad',
        listingName: 'Downtown resale',
        nextAction: 'Call seller',
        due: '09:00',
        dueAt: '2026-06-22T09:00:00+04:00',
        createdAt: '2026-06-22T08:30:00+04:00',
      },
    ],
    escalationInbox: [
      {
        id: 'esc-1',
        category: 'viewing',
        state: 'updated',
        urgency: 'critical',
        buyerName: 'Aisha Rahman',
        buyerPhone: '+971500000001',
        listingName: 'Emaar Oasis Villa',
        latestQuestion: 'Can we confirm access before the 11 AM viewing?',
        questionCount: 2,
        lastBuyerMessageAt: '09:50',
        lastBuyerMessageAtRaw: '2026-06-22T09:50:00+04:00',
        openedAt: '09:10',
        openedAtRaw: '2026-06-22T09:10:00+04:00',
        routeExpiresAt: '10:20',
        routeExpiresAtRaw: '2026-06-22T10:20:00+04:00',
        questions: [],
      },
    ],
    drafts: {
      replyDrafts: [
        {
          id: 'draft-1',
          conversationId: 'conv-2',
          buyerName: 'Sara Khan',
          listingName: 'Arabian Ranches',
          category: 'viewing_follow_up',
          body: 'Draft reply asks for buyer availability and financing status.',
          createdAt: '2026-06-22T09:05:00+04:00',
        },
      ],
      outreachDrafts: [],
    },
    campaignSnapshot: { headline: '', activeCampaigns: 0, newLeads: 0, qualifiedLeads: 0, responseRate: '0%', costPerQualifiedLead: 'AED 0', campaigns: [] },
    overnightBuyerDigest: [
      {
        id: 'hot-1',
        buyerName: 'Yusuf Mansour',
        intent: 'offer_ready',
        message: 'Asked about acceptable offer range.',
        budget: 'AED 4,200,000',
        target: 'Emaar Oasis',
        recommendedAction: 'Prepare offer context',
        lastSeen: '09:30',
        urgencyScore: 96,
        lastMessageAt: '2026-06-22T09:30:00+04:00',
        readiness: {
          stage: 'offer_ready',
          missingFields: ['proof_of_funds'],
          nextBestAction: 'prepare_offer_context',
          nextBestActionReason: 'Buyer has budget and target community aligned.',
          score: 92,
          priorityBand: 'high',
          presentFields: { budget: true, target: true },
        },
      },
    ],
    todaysViewings: [
      {
        id: 'viewing-1',
        time: '10:45',
        scheduledFor: '2026-06-22T10:45:00+04:00',
        buyerName: 'Omar Saleh',
        property: 'Palm Jumeirah',
        location: 'Access check',
        status: 'confirmed',
        preparation: 'Send reminder and gate access note.',
      },
    ],
    personalMomentum: { weekLabel: '', stats: [], focus: '', streaks: [] },
  }
}

function renderHtml(queueMarkup) {
  return `<!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Task 9 Today Queue QA</title>
      <style>
        body { margin: 0; background: #FAFAF9; color: #3D3D39; font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif; }
        main { max-width: 980px; margin: 0 auto; padding: 24px 20px 40px; }
        header { display: flex; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
        h1 { margin: 4px 0 0; font-size: 28px; line-height: 1.1; letter-spacing: 0; }
        .metrics { display: grid; grid-template-columns: repeat(4, minmax(86px, 1fr)); gap: 8px; }
        .metric, section { border: 1px solid #D6D6D2; background: #FFFFFF; border-radius: 12px; }
        .metric { padding: 12px; }
        .metric span { display: block; color: #7B7B76; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
        .metric strong { display: block; margin-top: 4px; font-family: "IBM Plex Mono", monospace; font-size: 20px; }
        .eyebrow { color: #7B7B76; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; }
        h2 { margin: 4px 0 0; font-size: 17px; letter-spacing: 0; }
        ol { list-style: none; margin: 0; padding: 0; }
        section { overflow: hidden; }
        section > div:first-child { padding: 16px 20px; border-bottom: 1px solid #E8E8E5; }
        li { display: grid; grid-template-columns: 48px minmax(0, 1fr) 190px; gap: 12px; padding: 16px 20px; border-top: 1px solid #E8E8E5; }
        li:first-child { border-top: 0; }
        li > div:first-child > div { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 8px; background: #EEF2F7; color: #324B6B; }
        li > div:nth-child(3) { display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-start; justify-content: flex-end; }
        li > div:nth-child(2) > div:first-child { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
        li span { border-radius: 4px; background: #F4F4F2; padding: 3px 7px; font-size: 11px; font-weight: 650; color: #5C5C57; }
        li span:first-child { background: #EEF2F7; color: #324B6B; }
        h3 { margin: 9px 0 0; font-size: 15px; }
        p { margin: 6px 0 0; color: #5C5C57; font-size: 14px; line-height: 1.45; }
        li p:last-child { margin-top: 10px; border-radius: 8px; background: #F4F4F2; padding: 9px 10px; color: #3D3D39; font-size: 12px; font-weight: 600; }
        .deal-readiness-line { margin-top: 8px; border: 1px solid #D7E4F2; border-radius: 8px; background: #EEF6FF; padding: 8px 10px; color: #243B55; font-size: 12px; }
        .deal-readiness-line p { margin: 3px 0 0; color: #243B55; font-size: 12px; line-height: 1.35; }
        .deal-readiness-line p:first-child { margin-top: 0; font-weight: 700; }
        a, button { display: inline-flex; align-items: center; gap: 6px; border: 1px solid #D6D6D2; background: white; border-radius: 8px; color: #324B6B; font-weight: 650; padding: 6px 10px; text-decoration: none; }
        .material-symbols-outlined {
          display: inline-block;
          width: 16px;
          height: 16px;
          overflow: hidden;
          color: transparent;
          vertical-align: middle;
        }
        .material-symbols-outlined::before {
          content: "";
          display: block;
          width: 8px;
          height: 8px;
          margin: 4px;
          border-radius: 999px;
          background: #324B6B;
        }
        @media (max-width: 640px) {
          main { padding: 16px 12px 32px; }
          header { display: block; }
          h1 { font-size: 24px; }
          .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; }
          li { grid-template-columns: 1fr; }
          li > div:first-child { display: flex; align-items: center; gap: 10px; }
          li > div:first-child > div { width: 36px; justify-content: center; padding-left: 0; place-items: center; }
          li > div:nth-child(3) { justify-content: flex-start; }
        }
      </style>
    </head>
    <body>
      <main>
        <header>
          <div><div class="eyebrow">Dubai / Live workspace / Updated 10:00</div><h1>Good morning, Leila</h1></div>
          <div class="metrics">
            <div class="metric"><span>Open tasks</span><strong>1</strong></div>
            <div class="metric"><span>Qualified buyers</span><strong>2</strong></div>
            <div class="metric"><span>Viewings today</span><strong>1</strong></div>
            <div class="metric"><span>Escalations</span><strong>1</strong></div>
          </div>
        </header>
        ${queueMarkup}
      </main>
    </body>
  </html>`
}

compileModule({ sourcePath: queueSourcePath, compiledPath: compiledQueuePath })
compileModule({ sourcePath: todayQueueSourcePath, compiledPath: compiledTodayQueuePath, jsx: ts.JsxEmit.ReactJSX })
const { buildTodayQueue } = await import(pathToFileURL(compiledQueuePath).href)
const { TodayQueue } = await import(pathToFileURL(compiledTodayQueuePath).href)
const data = dashboardFixture()
const queue = buildTodayQueue({ data, needsReply: data.conversationInbox, now: new Date('2026-06-22T10:00:00+04:00') })
const expectedKinds = ['escalation', 'overdue_task', 'needs_reply', 'viewing', 'reply_draft', 'hot_buyer']
const checks = [
  assertCheck(JSON.stringify(queue.map((item) => item.kind)) === JSON.stringify(expectedKinds), 'visual fixture queue order matches Task 9 priority order', { actual: queue.map((item) => item.kind) }),
  assertCheck(queue.every((item) => item.status && item.reason), 'each visual row carries status and reason text'),
]

mkdirSync(dirname(htmlPath), { recursive: true })
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
writeFileSync(htmlPath, renderHtml(queueMarkup))

let browser = null
try {
  browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 })
  await page.goto(pathToFileURL(htmlPath).href)
  const desktopKinds = await page.locator('[data-kind]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-kind')))
  const componentHeading = await page.getByText('Ranked work for this pilot day').count()
  const readinessReasonCount = await page.getByText('Buyer has budget and target community aligned.').count()
  checks.push(assertCheck(componentHeading === 1, 'browser rendered the shipped TodayQueue component heading'))
  checks.push(assertCheck(JSON.stringify(desktopKinds) === JSON.stringify(expectedKinds), 'desktop browser sees rows in ranked order', { desktopKinds }))
  checks.push(assertCheck(readinessReasonCount === 1, 'desktop browser renders hot buyer readiness reason text'))
  await page.screenshot({ path: desktopPath, fullPage: true })
  copyFileSync(desktopPath, screenshotPath)
  await page.setViewportSize({ width: 390, height: 844 })
  const mobileKinds = await page.locator('[data-kind]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-kind')))
  checks.push(assertCheck(JSON.stringify(mobileKinds) === JSON.stringify(expectedKinds), 'mobile browser sees rows in ranked order', { mobileKinds }))
  await page.screenshot({ path: mobilePath, fullPage: true })
  await page.close()
} finally {
  if (browser) {
    await browser.close()
  }
  rmSync(compiledQueuePath, { force: true })
  rmSync(compiledTodayQueuePath, { force: true })
}

const cleanupReceipt = `cleanup: Playwright browser closed; page closed; removed compiled temp modules ${compiledQueuePath} and ${compiledTodayQueuePath}; no dev server/database/external service spawned`
const transcript = {
  scenario: 'Task 9 browser visual QA for one ranked Today Queue first viewport',
  invocation: 'cd frontend && node scripts/verify-task9-today-queue-visual.mjs',
  checks,
  htmlPath,
  screenshotPath,
  desktopPath,
  mobilePath,
  queueOrder: queue.map((item) => ({ kind: item.kind, title: item.title, status: item.status, reason: item.reason })),
  cleanup: cleanupReceipt,
}
writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
console.log(JSON.stringify({ transcriptPath, screenshotPath, desktopPath, mobilePath, checks: checks.length, cleanup: cleanupReceipt }, null, 2))
