import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  assertCheck,
  closeHarness,
  fakeOperationalTexts,
  installSharedMocks,
  jsonResponse,
  liveDashboardPayload,
  repoRoot,
  startHarness,
} from './dashboard-fallback-harness.mjs'

const redMode = process.argv.includes('--red')
const evidenceRoot = resolve(repoRoot, '.omo/evidence/task-12-first-run-state')
const transcriptPath = resolve(evidenceRoot, redMode ? 'functional-red-transcript.json' : 'functional-transcript.json')
const cleanupReceipt = 'Closed Playwright browser/context, sent SIGTERM to the local Next dev server, and closed the local Supabase auth stub.'
const checks = []
const observations = {}
let harness = null
let caughtError = null
let failureDebug = null

function emptyDashboardPayload() {
  return {
    generated_at: '2026-06-23T09:00:00+04:00',
    sample_data: false,
    agent: { display_name: 'Leila Agent' },
    brokerage: { name: 'Luqman Realty' },
    empty_state: {
      reason: 'no_workspace_activity',
      message: 'No live buyer activity is assigned to this agent workspace yet.',
    },
    metrics: {
      open_tasks: 0,
      hot_leads: 0,
      viewings_today: 0,
      stale_leads: 0,
      open_escalations: 0,
    },
    tasks: [],
    hot_leads: [],
    conversations: [],
    campaigns: [],
    viewings: [],
    escalation_threads: [],
    drafts: { reply_drafts: [], outreach_drafts: [] },
    marketing: { pages: [], events_7d: 0 },
    performance: {
      scope: 'agent',
      primary: { key: 'today', label: 'Today', metrics: {} },
      windows: [],
    },
  }
}

function liveZeroQueuePayload() {
  const payload = emptyDashboardPayload()
  return {
    ...payload,
    empty_state: undefined,
  }
}

async function pageBody(page) {
  return await page.locator('body').innerText()
}

function assertIncludes(body, expected, label) {
  return assertCheck(body.includes(expected), label, { expected })
}

function assertExcludesAll(body, forbidden, label) {
  const leaks = forbidden.filter((text) => body.includes(text))
  return assertCheck(leaks.length === 0, label, { leaks })
}

try {
  mkdirSync(evidenceRoot, { recursive: true })
  harness = await startHarness()

  const emptyPage = await harness.context.newPage()
  await installSharedMocks(emptyPage)
  await emptyPage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(emptyDashboardPayload())))
  await emptyPage.goto(`${harness.baseUrl}/agent`)
  await emptyPage.getByRole('heading', { name: 'Good morning, Leila Agent' }).waitFor({ timeout: 15_000 })
  const emptyBody = await pageBody(emptyPage)
  observations.emptyBodyText = emptyBody.slice(0, 3000)

  if (redMode) {
    checks.push(assertCheck(!emptyBody.includes('Start with an internal pilot rehearsal'), 'RED empty workspace lacks internal pilot activation guidance'))
    checks.push(assertCheck(!emptyBody.includes('Preview safe demo states'), 'RED empty workspace lacks an explicit safe demo action'))
  } else {
    checks.push(assertIncludes(emptyBody, 'Start with an internal pilot rehearsal', 'empty workspace names the safe first-run path'))
    checks.push(assertIncludes(emptyBody, 'synthetic/internal records only', 'empty workspace constrains pilot data class'))
    checks.push(assertExcludesAll(emptyBody, ['Preview safe demo states', '/component-showcase'], 'empty workspace does not link to fake operational demo rows'))
    checks.push(assertIncludes(emptyBody, 'Refresh hot list', 'empty workspace keeps retry/refresh action visible'))
    checks.push(assertExcludesAll(emptyBody, fakeOperationalTexts, 'empty workspace renders no fake buyer, phone, queue, offer, or sample rows'))
  }
  await emptyPage.close()

  const clearPage = await harness.context.newPage()
  await installSharedMocks(clearPage)
  await clearPage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(liveZeroQueuePayload())))
  await clearPage.goto(`${harness.baseUrl}/agent`)
  await clearPage.getByRole('heading', { name: 'Good morning, Leila Agent' }).waitFor({ timeout: 15_000 })
  const clearBody = await pageBody(clearPage)
  observations.clearBodyText = clearBody.slice(0, 3000)

  if (!redMode) {
    checks.push(assertIncludes(clearBody, 'Your day is clear', 'live zero-queue dashboard keeps a neutral clear-day heading'))
    checks.push(assertIncludes(clearBody, 'No buyers waiting on a reply', 'live zero-queue dashboard explains the neutral empty queue'))
    checks.push(assertExcludesAll(clearBody, [
      'Start with an internal pilot rehearsal',
      'synthetic/internal records only',
      'Confirm pilot scope',
      'data class',
      'Preview safe demo states',
    ], 'live zero-queue dashboard renders no first-run/internal-pilot/data-class copy'))
    checks.push(assertExcludesAll(clearBody, fakeOperationalTexts, 'live zero-queue dashboard renders no fake buyer, phone, queue, offer, or sample rows'))
  }
  await clearPage.close()

  const errorPage = await harness.context.newPage()
  await installSharedMocks(errorPage)
  await errorPage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse({ detail: 'upstream unavailable' }, 503)))
  await errorPage.goto(`${harness.baseUrl}/agent`)
  await errorPage.getByText("Couldn't load your live workspace").waitFor({ timeout: 15_000 })
  const errorBody = await pageBody(errorPage)
  observations.errorBodyText = errorBody.slice(0, 3000)

  if (redMode) {
    checks.push(assertCheck(!errorBody.includes('Manual fallback'), 'RED connection error lacks a named manual fallback'))
  } else {
    checks.push(assertIncludes(errorBody, 'Retry', 'connection error exposes retry action'))
    checks.push(assertIncludes(errorBody, 'Manual fallback', 'connection error names manual fallback'))
    checks.push(assertIncludes(errorBody, 'Use WhatsApp directly', 'connection error explains the manual channel'))
    checks.push(assertExcludesAll(errorBody, fakeOperationalTexts, 'connection error renders no fake operational rows'))
  }
  await errorPage.close()

  if (!redMode) {
    const livePage = await harness.context.newPage()
    await installSharedMocks(livePage)
    await livePage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(liveDashboardPayload())))
    await livePage.goto(`${harness.baseUrl}/agent`)
    await livePage.getByText('Noura Live').first().waitFor({ timeout: 15_000 })
    const liveBody = await pageBody(livePage)
    observations.liveBodyText = liveBody.slice(0, 2500)
    checks.push(assertIncludes(liveBody, 'Live workspace', 'successful dashboard payload still renders live workspace label'))
    checks.push(assertIncludes(liveBody, 'Noura Live', 'successful dashboard payload still renders mocked live buyer'))
    await livePage.close()
  }
} catch (error) {
  failureDebug = {
    message: error instanceof Error ? error.message : String(error),
    nextDevLogTail: harness?.server.readLogs() ?? '',
  }
  caughtError = error
} finally {
  if (harness) await closeHarness(harness)

  const transcript = {
    scenario: redMode
      ? 'RED: first-run empty state lacks activation guidance and connection error lacks manual fallback'
      : 'GREEN: first-run empty state gives safe synthetic/internal next steps and connection error gives retry/manual fallback',
    invocation: `cd frontend && node scripts/verify-task-next-first-run-state.mjs${redMode ? ' --red' : ''}`,
    baseUrl: harness?.baseUrl ?? null,
    checks,
    observations,
    failureDebug,
    cleanup: cleanupReceipt,
  }
  writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
}

if (caughtError) {
  throw caughtError
}

console.log(JSON.stringify({ transcriptPath, checks: checks.length, cleanup: cleanupReceipt }, null, 2))
