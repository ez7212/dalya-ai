import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const evidenceRoot = resolve(repoRoot, '.omo/evidence/task-1-escalation-route')
const queueSourcePath = resolve(frontendRoot, 'src/components/agent-dashboard/today-queue.ts')
const inboxSourcePath = resolve(frontendRoot, 'src/components/escalations/EscalationInbox.tsx')
const pageSourcePath = resolve(frontendRoot, 'src/app/(app)/agent/escalations/page.tsx')
const missingDynamicRoutePath = resolve(frontendRoot, 'src/app/(app)/agent/escalations/[id]/page.tsx')
const compiledQueuePath = resolve(evidenceRoot, 'today-queue-builder.mjs')
const redMode = process.argv.includes('--red')

function assertCheck(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label}: ${JSON.stringify(details)}`)
  }
  return { label, passed: true, details }
}

function compileModule(sourcePath, compiledPath) {
  const source = readFileSync(sourcePath, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
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
    summary: { openTasks: 0, qualifiedBuyers: 0, viewingsToday: 0, offersAtRisk: 0, openEscalations: 2 },
    performance: {
      scope: 'agent',
      primary: { key: 'today', label: 'Today', metrics: {} },
      windows: [],
    },
    conversationInbox: [],
    morningQueue: [],
    escalationInbox: [
      {
        id: 'esc-critical-1',
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
      {
        id: 'esc-high-1',
        category: 'finance',
        state: 'updated',
        urgency: 'high',
        buyerName: 'High Escalation Buyer',
        buyerPhone: '+971500000009',
        listingName: 'Business Bay',
        latestQuestion: 'Can the buyer ask a financing question?',
        questionCount: 1,
        lastBuyerMessageAt: '09:59',
        lastBuyerMessageAtRaw: '2026-06-22T09:59:00+04:00',
        openedAt: '09:55',
        openedAtRaw: '2026-06-22T09:55:00+04:00',
        questions: [],
      },
    ],
    drafts: { replyDrafts: [], outreachDrafts: [] },
    campaignSnapshot: { headline: '', activeCampaigns: 0, newLeads: 0, qualifiedLeads: 0, responseRate: '0%', costPerQualifiedLead: 'AED 0', campaigns: [] },
    overnightBuyerDigest: [],
    todaysViewings: [],
    personalMomentum: { weekLabel: '', stats: [], focus: '', streaks: [] },
  }
}

function sourceChecks() {
  const inboxSource = readFileSync(inboxSourcePath, 'utf8')
  const pageSource = readFileSync(pageSourcePath, 'utf8')
  return [
    assertCheck(
      pageSource.includes('searchParams') && pageSource.includes('selectedThreadId'),
      'escalations-page passes thread query to inbox',
    ),
    assertCheck(
      inboxSource.includes('selectedThreadId') && inboxSource.includes('scrollIntoView') && inboxSource.includes('data-selected-thread={isSelected'),
      'inbox supports selected-thread focus, highlight, and scroll',
    ),
    assertCheck(
      inboxSource.includes('selectedThreadId === thread.id') && inboxSource.includes('selectedThreadRef'),
      'missing thread parameter preserves normal inbox rendering',
    ),
  ]
}

async function run() {
  rmSync(compiledQueuePath, { force: true })
  compileModule(queueSourcePath, compiledQueuePath)
  const { buildTodayQueue } = await import(pathToFileURL(compiledQueuePath).href)
  const queue = buildTodayQueue({
    data: dashboardFixture(),
    needsReply: [],
    now: new Date('2026-06-22T10:00:00+04:00'),
  })
  const escalationItems = queue.filter((item) => item.kind === 'escalation')
  const critical = escalationItems.find((item) => item.escalation?.id === 'esc-critical-1')
  const high = escalationItems.find((item) => item.escalation?.id === 'esc-high-1')
  const routeExists = existsSync(resolve(frontendRoot, 'src/app/(app)/agent/escalations/page.tsx'))
  const dynamicRouteExists = existsSync(missingDynamicRoutePath)
  const legacyDynamicHref = `/agent/escalations/${encodeURIComponent('esc-critical-1')}`

  const checks = [
    assertCheck(routeExists, 'base escalation inbox route exists', { route: '/agent/escalations' }),
    assertCheck(!dynamicRouteExists, 'no dynamic escalation detail route exists', { route: '/agent/escalations/[id]' }),
    assertCheck(
      !dynamicRouteExists,
      'regression: old dynamic Today Queue href pattern would target a missing route',
      { legacyDynamicHref, missingDynamicRoutePath },
    ),
    assertCheck(Boolean(critical), 'critical open escalation renders in Today Queue'),
    assertCheck(!high, 'high-priority escalation remains intentionally excluded from Today Queue'),
    assertCheck(
      critical?.href === '/agent/escalations?thread=esc-critical-1',
      'critical escalation href targets live inbox query route',
      { actual: critical?.href, expected: '/agent/escalations?thread=esc-critical-1' },
    ),
    ...sourceChecks(),
  ]

  const report = {
    mode: redMode ? 'red' : 'green',
    checks,
    observedQueueHref: critical?.href ?? null,
    missingDynamicRoutePath,
  }

  console.log(JSON.stringify(report, null, 2))
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
