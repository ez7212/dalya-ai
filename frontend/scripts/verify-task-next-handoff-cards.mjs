import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const root = resolve(import.meta.dirname, '..')
const tempRoot = resolve(root, '.task-11-handoff-cards-verifier')
const redMode = process.argv.includes('--red')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

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
    morningQueue: [
      {
        id: 'task-follow-up',
        source: 'task',
        priority: 'high',
        title: 'Call seller after viewing',
        context: 'Buyer wants seller feedback before deciding.',
        buyerName: 'Nadia Ali',
        listingName: 'Creek Harbour 2BR',
        nextAction: 'Call seller after viewing',
        due: '09:30',
        dueAt: '2026-06-22T09:30:00+04:00',
        createdAt: '2026-06-21T16:00:00+04:00',
      },
    ],
    escalationInbox: [escalationFixture()],
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

function textFromMarkup(markup) {
  return markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

function interactiveLabels(markup) {
  const labels = []
  const interactivePattern = /<(a|button)\b[^>]*>([\s\S]*?)<\/\1>/g
  for (const match of markup.matchAll(interactivePattern)) {
    labels.push(textFromMarkup(match[2]).replace(/\b(open_in_new|task_alt|sync)\b/g, '').replace(/\s+/g, ' ').trim())
  }
  return labels.filter(Boolean)
}

function includesAll(value, expected) {
  return expected.every((item) => value.includes(item))
}

function runRedChecks() {
  const todayQueue = read('src/components/agent-dashboard/TodayQueue.tsx')
  const escalationInbox = read('src/components/escalations/EscalationInbox.tsx')
  return [
    assertCheck(todayQueue.includes('label="Open"'), 'current queue still uses generic Open action text'),
    assertCheck(!todayQueue.includes('QueueHandoffCard'), 'current queue lacks structured handoff card component'),
    assertCheck(!escalationInbox.includes('EscalationHandoffPanel'), 'current escalation inbox lacks structured handoff panel'),
  ]
}

async function runGreenChecks() {
  mkdirSync(tempRoot, { recursive: true })
  const compiledQueuePath = resolve(tempRoot, 'today-queue.mjs')
  const compiledCardPath = resolve(tempRoot, 'QueueHandoffCard.mjs')
  const compiledTodayQueuePath = resolve(tempRoot, 'TodayQueue.mjs')

  try {
    compileModule(resolve(root, 'src/components/agent-dashboard/today-queue.ts'), compiledQueuePath)
    compileModule(resolve(root, 'src/components/agent-dashboard/QueueHandoffCard.tsx'), compiledCardPath, ts.JsxEmit.ReactJSX)
    compileModule(resolve(root, 'src/components/agent-dashboard/TodayQueue.tsx'), compiledTodayQueuePath, ts.JsxEmit.ReactJSX)

    const { buildTodayQueue } = await import(pathToFileURL(compiledQueuePath).href)
    const { EscalationHandoffPanel, QueueHandoffCard, queueActionLabel } = await import(pathToFileURL(compiledCardPath).href)
    const { TodayQueue } = await import(pathToFileURL(compiledTodayQueuePath).href)
    const data = dashboardFixture()
    const queue = buildTodayQueue({ data, needsReply: data.conversationInbox, now: new Date('2026-06-22T10:00:00+04:00') })
    const escalationItem = queue.find((item) => item.kind === 'escalation')
    const taskItem = queue.find((item) => item.kind === 'overdue_task')
    const needsReplyItem = queue.find((item) => item.kind === 'needs_reply')

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
    const escalationCardMarkup = renderToStaticMarkup(createElement(EscalationHandoffPanel, { thread: escalationFixture() }))
    const needsReplyCardMarkup = needsReplyItem
      ? renderToStaticMarkup(createElement(QueueHandoffCard, { item: needsReplyItem }))
      : ''
    const taskCardMarkup = taskItem
      ? renderToStaticMarkup(createElement(QueueHandoffCard, { item: taskItem }))
      : ''
    const taskCardText = textFromMarkup(taskCardMarkup)
    const renderedText = textFromMarkup(`${queueMarkup} ${escalationCardMarkup} ${needsReplyCardMarkup} ${taskCardMarkup}`)
    const labels = interactiveLabels(queueMarkup)
    const forbiddenAutonomousLabels = new Set(['Open', 'Send', 'Send reply', 'Counter', 'Counter offer', 'Accept offer', 'Submit offer', 'Auto-send'])

    return [
      assertCheck(Boolean(escalationItem), 'fixture builds an escalation queue item'),
      assertCheck(Boolean(taskItem), 'fixture builds an overdue task queue item'),
      assertCheck(Boolean(needsReplyItem), 'fixture builds a needs-reply offer queue item'),
      assertCheck(escalationItem?.href === '/agent/escalations?thread=esc-offer', 'escalation queue item has exact route href', { href: escalationItem?.href }),
      assertCheck(needsReplyItem?.href === '/agent/conversations/conv-offer', 'needs-reply queue item has exact route href', { href: needsReplyItem?.href }),
      assertCheck(queueActionLabel(needsReplyItem) === 'Prepare agent review/counter guidance', 'offer queue action label stays review guidance', { label: queueActionLabel(needsReplyItem) }),
      assertCheck(includesAll(renderedText, [
        'Buyer intent',
        'Known',
        'Missing',
        'Suggested action',
        'Work surface',
        'Source',
      ]), 'rendered handoff cards expose required fact labels'),
      assertCheck(includesAll(renderedText, [
        'Offer Counter escalation',
        'Offer conversation',
        'Buyer: Yusuf Mansour',
        'Listing: Emaar Oasis Villa',
        'Proof Of Funds',
        'Seller Floor',
        'Prepare agent review/counter guidance',
        'Escalation inbox thread',
        'Conversation composer',
        'Escalation inbox',
        'Needs-reply signal',
        'Agent review/counter guidance only. No automatic negotiation or send.',
      ]), 'rendered handoff cards expose queue intent, known fields, blockers, action, surface, source, and review-only copy'),
      assertCheck(queueMarkup.includes('href="/agent/escalations?thread=esc-offer"'), 'rendered queue includes exact escalation href'),
      assertCheck(queueMarkup.includes('href="/agent/conversations/conv-offer"'), 'rendered queue includes exact conversation href'),
      assertCheck(escalationCardMarkup.includes('href="/agent/escalations?thread=esc-offer"'), 'rendered escalation panel includes exact thread href'),
      assertCheck(includesAll(taskCardText, [
        'Buyer: Nadia Ali',
        'Listing: Creek Harbour 2BR',
        'Suggested action',
        'Call seller after viewing',
      ]), 'rendered task handoff uses task buyer/listing fields'),
      assertCheck(!taskCardText.includes('Buyer: Call seller after viewing') && !taskCardText.includes('Listing: Nadia Ali'), 'rendered task handoff does not swap task title and buyer'),
      assertCheck(!labels.some((label) => forbiddenAutonomousLabels.has(label)), 'rendered action/link labels do not introduce generic or autonomous send behavior', { labels }),
    ]
  } finally {
    rmSync(tempRoot, { recursive: true, force: true })
  }
}

const checks = redMode ? runRedChecks() : await runGreenChecks()
console.log(JSON.stringify({
  scenario: redMode
    ? 'Task 11 RED/current state: generic queue and escalation cards'
    : 'Task 11 GREEN: structured handoff cards rendered from compiled queue modules',
  mode: redMode ? 'red' : 'green',
  checks,
}, null, 2))
