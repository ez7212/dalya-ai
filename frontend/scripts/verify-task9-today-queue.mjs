import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const evidenceRoot = resolve(repoRoot, '.omo/ulw-loop/evidence')
const queueSourcePath = resolve(frontendRoot, 'src/components/agent-dashboard/today-queue.ts')
const navSourcePath = resolve(frontendRoot, 'src/components/app/nav-items.ts')
const compiledQueuePath = resolve(evidenceRoot, 'task9-today-queue-builder.mjs')
const compiledNavPath = resolve(evidenceRoot, 'task9-nav-items.mjs')
const edgeArtifactPath = resolve(evidenceRoot, 'task9-C002-empty-edge.txt')
const navArtifactPath = resolve(evidenceRoot, 'task9-C003-nav-scope-regression.txt')

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

function baseDashboardData() {
  return {
    agent: { name: 'Leila', brokerage: 'Dalya Pilot', market: 'Dubai', lastUpdated: '10:00' },
    summary: { openTasks: 0, qualifiedBuyers: 0, viewingsToday: 0, offersAtRisk: 0, openEscalations: 0 },
    performance: {
      scope: 'agent',
      primary: { key: 'today', label: 'Today', metrics: emptyMetrics() },
      windows: [],
    },
    conversationInbox: [],
    morningQueue: [],
    escalationInbox: [],
    drafts: { replyDrafts: [], outreachDrafts: [] },
    campaignSnapshot: {
      headline: 'No owner outreach campaigns are active yet.',
      activeCampaigns: 0,
      newLeads: 0,
      qualifiedLeads: 0,
      responseRate: '0%',
      costPerQualifiedLead: 'AED 0',
      campaigns: [],
    },
    overnightBuyerDigest: [],
    todaysViewings: [],
    personalMomentum: { weekLabel: 'This week', stats: [], focus: '', streaks: [] },
  }
}

function emptyMetrics() {
  return {
    newBuyerConversations: 0,
    escalationsHandled: 0,
    avgResponseMinutes: null,
    followUpsSent: 0,
    viewingsProposed: 0,
    viewingsConfirmed: 0,
    viewingsCompleted: 0,
    offersDetected: 0,
    hotLeadsActive: 0,
    tasksOverdue: 0,
  }
}

function populatedDashboardData() {
  const data = baseDashboardData()
  data.escalationInbox = [
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
    {
      id: 'esc-high',
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
  ]
  data.morningQueue = [
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
    {
      id: 'task-future',
      source: 'task',
      priority: 'normal',
      title: 'Follow up after bank letter',
      context: 'Buyer asked to continue after financing proof arrives.',
      buyerName: 'Noura Ali',
      listingName: 'Dubai Hills',
      nextAction: 'Follow up tomorrow',
      due: 'Tomorrow',
      dueAt: '2026-06-23T09:00:00+04:00',
      createdAt: '2026-06-22T09:20:00+04:00',
    },
    {
      id: 'excluded-hot-lead',
      source: 'hot_lead',
      priority: 'critical',
      title: 'Hot buyer: duplicate',
      context: 'Should be represented by the hot buyer bucket, not future follow-ups.',
      buyerName: 'Duplicate',
      listingName: 'Listing',
      nextAction: 'Open brief',
      due: '08:00',
      dueAt: '2026-06-22T08:00:00+04:00',
    },
    {
      id: 'excluded-page',
      source: 'page',
      priority: 'normal',
      title: 'One-pager ready',
      context: 'Deferred owner surface should not enter the pilot queue.',
      buyerName: 'Marketing page',
      listingName: 'Page',
      nextAction: 'Preview page',
      due: 'Today',
    },
  ]
  data.conversationInbox = [
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
      lastAgentResponseAt: '09:00',
    },
  ]
  data.todaysViewings = [
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
  ]
  data.drafts.replyDrafts = [
    {
      id: 'draft-1',
      conversationId: 'conv-2',
      buyerName: 'Sara Khan',
      listingName: 'Arabian Ranches',
      category: 'viewing_follow_up',
      body: 'Draft reply asks for buyer availability and financing status.',
      createdAt: '2026-06-22T09:05:00+04:00',
    },
  ]
  data.overnightBuyerDigest = [
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
    {
      id: 'hot-2',
      buyerName: 'Lina Patel',
      intent: 'viewing_ready',
      message: 'Requested a weekend viewing.',
      budget: 'AED 2,800,000',
      target: 'Dubai Hills',
      recommendedAction: 'Offer viewing slots',
      lastSeen: '09:40',
      urgencyScore: 82,
      lastMessageAt: '2026-06-22T09:40:00+04:00',
    },
  ]
  return data
}

function edgeDashboardData() {
  const data = baseDashboardData()
  data.morningQueue = [
    {
      id: 'missing-due',
      source: 'task',
      priority: 'normal',
      title: 'Missing due task',
      context: 'No due date is available yet.',
      buyerName: 'Workspace',
      listingName: 'Agent task',
      nextAction: 'Review later',
      due: 'Today',
      dueAt: null,
    },
    {
      id: 'invalid-due',
      source: 'task',
      priority: 'normal',
      title: 'Invalid due task',
      context: 'The API gave a malformed due date.',
      buyerName: 'Workspace',
      listingName: 'Agent task',
      nextAction: 'Review manually',
      due: 'Today',
      dueAt: 'not-a-date',
      createdAt: 'not-a-date',
    },
    {
      id: 'tie-a',
      source: 'task',
      priority: 'high',
      title: 'Tie A',
      context: 'Created first.',
      buyerName: 'A',
      listingName: 'Listing',
      nextAction: 'Follow up',
      due: '08:30',
      dueAt: '2026-06-22T08:30:00+04:00',
      createdAt: '2026-06-22T07:00:00+04:00',
    },
    {
      id: 'tie-b',
      source: 'task',
      priority: 'high',
      title: 'Tie B',
      context: 'Created second.',
      buyerName: 'B',
      listingName: 'Listing',
      nextAction: 'Follow up',
      due: '08:30',
      dueAt: '2026-06-22T08:30:00+04:00',
      createdAt: '2026-06-22T07:05:00+04:00',
    },
  ]
  return data
}

compileModule(queueSourcePath, compiledQueuePath)
compileModule(navSourcePath, compiledNavPath)

const { buildTodayQueue } = await import(pathToFileURL(compiledQueuePath).href)
const { getAppNavItems } = await import(pathToFileURL(compiledNavPath).href)

const now = new Date('2026-06-22T10:00:00+04:00')
const data = populatedDashboardData()
const queue = buildTodayQueue({ data, needsReply: data.conversationInbox, now })
const edgeData = edgeDashboardData()
const edgeQueue = buildTodayQueue({ data: edgeData, needsReply: [], now })
const emptyQueue = buildTodayQueue({ data: baseDashboardData(), needsReply: [], now })
const visibleText = queue.map((item) => `${item.kind} ${item.status} ${item.title} ${item.subject} ${item.reason}`).join('\n')
const edgeVisibleText = edgeQueue.map((item) => `${item.kind} ${item.status} ${item.title} ${item.subject} ${item.reason} ${item.timestampLabel}`).join('\n')

const expectedKinds = ['escalation', 'overdue_task', 'needs_reply', 'viewing', 'reply_draft', 'hot_buyer', 'hot_buyer', 'follow_up']
const yusufQueueItem = queue.find((item) => item.title === 'Yusuf Mansour')
const checks = [
  assertCheck(JSON.stringify(queue.map((item) => item.kind)) === JSON.stringify(expectedKinds), 'ranked queue follows required bucket order', { actual: queue.map((item) => item.kind) }),
  assertCheck(!queue.some((item) => item.title === 'High Escalation Buyer'), 'non-critical open escalations do not outrank overdue tasks in the critical escalation bucket'),
  assertCheck(queue[5]?.title === 'Yusuf Mansour' && queue[6]?.title === 'Lina Patel', 'hot buyers sort by urgency_score descending', { hotBuyers: queue.filter((item) => item.kind === 'hot_buyer').map((item) => `${item.title}:${item.urgencyScore}`) }),
  assertCheck(yusufQueueItem?.readiness?.nextBestActionReason === 'Buyer has budget and target community aligned.', 'hot buyer readiness metadata is preserved for Today Queue rendering', { readiness: yusufQueueItem?.readiness }),
  assertCheck(!queue.some((item) => item.id.includes('excluded-hot-lead') || item.id.includes('excluded-page')), 'generated hot-lead/page morning items do not duplicate pilot queue buckets'),
  assertCheck(emptyQueue.length === 0, 'empty dashboard returns an empty Today Queue'),
  assertCheck(edgeQueue[0]?.title === 'Tie A' && edgeQueue[1]?.title === 'Tie B', 'created_at ascending tie-break is deterministic for same due_at'),
  assertCheck(!visibleText.includes('Invalid Date') && !visibleText.includes('[object Object]'), 'main queue labels avoid invalid date/object placeholders'),
  assertCheck(!edgeVisibleText.includes('Invalid Date') && !edgeVisibleText.includes('[object Object]'), 'edge queue labels avoid invalid date/object placeholders'),
]

const pilotNav = getAppNavItems({ ownerSurfacesEnabled: false })
const fullNav = getAppNavItems({ ownerSurfacesEnabled: true })
const adminNav = getAppNavItems({ ownerSurfacesEnabled: false, role: 'admin' })
const ownerNav = getAppNavItems({ ownerSurfacesEnabled: false, role: 'owner' })
const teamLeadNav = getAppNavItems({ ownerSurfacesEnabled: false, role: 'team_lead' })
const pilotLabels = pilotNav.map((item) => item.label)
const fullLabels = fullNav.map((item) => item.label)
const adminLabels = adminNav.map((item) => item.label)
const ownerLabels = ownerNav.map((item) => item.label)
const teamLeadLabels = teamLeadNav.map((item) => item.label)
const deferredLabels = ['Campaigns', 'Inbox', 'Listings', 'Pages']
const routeFiles = [
  'frontend/src/app/(app)/campaigns/page.tsx',
  'frontend/src/app/(app)/inbox/page.tsx',
  'frontend/src/app/(app)/listings/page.tsx',
  'frontend/src/app/(app)/pages/page.tsx',
]
const trackedDiffNames = execFileSync('git', ['diff', '--name-only'], { cwd: repoRoot, encoding: 'utf8' }).trim().split('\n').filter(Boolean)
const untrackedNames = execFileSync('git', ['ls-files', '--others', '--exclude-standard'], { cwd: repoRoot, encoding: 'utf8' }).trim().split('\n').filter(Boolean)
const diffNames = [...new Set([...trackedDiffNames, ...untrackedNames])].filter((name) => !name.startsWith('.omo/'))
const diffStat = execFileSync('git', ['diff', '--stat'], { cwd: repoRoot, encoding: 'utf8' })
const allowedDiffNames = new Set([
  'frontend/src/app/(app)/layout.tsx',
  'frontend/src/components/agent-dashboard/AgentDashboard.tsx',
  'frontend/src/components/agent-dashboard/TodayQueue.tsx',
  'frontend/src/components/agent-dashboard/today-queue.ts',
  'frontend/src/components/agent-dashboard/types.ts',
  'frontend/src/components/app/AppSidebar.tsx',
  'frontend/src/components/app/nav-items.ts',
  'frontend/scripts/verify-task9-today-queue.mjs',
  'frontend/scripts/verify-task9-today-queue-visual.mjs',
])
const navChecks = [
  assertCheck(deferredLabels.every((label) => !pilotLabels.includes(label)), 'pilot nav hides deferred owner surfaces by default', { pilotLabels }),
  assertCheck(deferredLabels.every((label) => fullLabels.includes(label)), 'full nav exposes deferred owner surfaces when flag is enabled', { fullLabels }),
  assertCheck(deferredLabels.every((label) => adminLabels.includes(label)), 'admin role exposes deferred owner surfaces', { adminLabels }),
  assertCheck(deferredLabels.every((label) => ownerLabels.includes(label)), 'owner role exposes deferred owner surfaces', { ownerLabels }),
  assertCheck(deferredLabels.every((label) => teamLeadLabels.includes(label)), 'team_lead role exposes deferred owner surfaces', { teamLeadLabels }),
  assertCheck(routeFiles.every((file) => existsSync(resolve(repoRoot, file))), 'deferred route files remain present', { routeFiles }),
  assertCheck(diffNames.every((name) => allowedDiffNames.has(name)), 'Task 9 tracked and untracked diff names stay within the explicit allowlist', { diffNames }),
]

const cleanupReceipt = `cleanup: removed compiled temp modules ${compiledQueuePath} and ${compiledNavPath}; no server/browser/database/external service spawned`
const edgeArtifact = {
  scenario: 'Task 9 Today Queue builder edge and ordering QA',
  invocation: 'cd frontend && node scripts/verify-task9-today-queue.mjs',
  checks,
  queueOrder: queue.map((item) => ({ kind: item.kind, title: item.title, status: item.status, reason: item.reason })),
  edgeOrder: edgeQueue.map((item) => ({ kind: item.kind, title: item.title, timestampLabel: item.timestampLabel })),
  cleanup: cleanupReceipt,
}
const navArtifact = {
  scenario: 'Task 9 pilot nav scope regression QA',
  invocation: 'cd frontend && node scripts/verify-task9-today-queue.mjs',
  checks: navChecks,
  pilotLabels,
  fullLabels,
  adminLabels,
  ownerLabels,
  teamLeadLabels,
  routeFiles,
  diffNames,
  diffStat,
  noProductionOrStagingDdl: true,
  noMigrationsRlsEnvDependencyFilesExternalDbTestsOrLiveWrites: true,
  cleanup: cleanupReceipt,
}

mkdirSync(dirname(edgeArtifactPath), { recursive: true })
writeFileSync(edgeArtifactPath, `${JSON.stringify(edgeArtifact, null, 2)}\n`)
writeFileSync(navArtifactPath, `${JSON.stringify(navArtifact, null, 2)}\n`)
rmSync(compiledQueuePath, { force: true })
rmSync(compiledNavPath, { force: true })
console.log(JSON.stringify({ edgeArtifactPath, navArtifactPath, checks: checks.length + navChecks.length, cleanup: cleanupReceipt }, null, 2))
