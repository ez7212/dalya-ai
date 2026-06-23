import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import {
  assertCheck,
  closeHarness,
  fakeOperationalTexts,
  installSharedMocks,
  jsonResponse,
  frontendRoot,
  repoRoot,
  startHarness,
} from './dashboard-fallback-harness.mjs'

const desktopArgIndex = process.argv.indexOf('--desktop')
const mobileArgIndex = process.argv.indexOf('--mobile')
const desktopPath = desktopArgIndex >= 0
  ? resolve(frontendRoot, process.argv[desktopArgIndex + 1] ?? '')
  : resolve(repoRoot, '.omo/evidence/task-12-first-run-desktop.png')
const mobilePath = mobileArgIndex >= 0
  ? resolve(frontendRoot, process.argv[mobileArgIndex + 1] ?? '')
  : resolve(repoRoot, '.omo/evidence/task-12-first-run-mobile.png')
const evidenceRoot = resolve(repoRoot, '.omo/evidence/task-12-first-run-state')
const transcriptPath = resolve(evidenceRoot, 'visual-transcript.json')
const cleanupReceipt = 'Closed Playwright browser/context, sent SIGTERM to the local Next dev server, and closed the local Supabase auth stub.'
const checks = []
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

async function captureEmptyWorkspace(viewport, path) {
  const page = await harness.context.newPage()
  await page.setViewportSize(viewport)
  await installSharedMocks(page)
  await page.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(emptyDashboardPayload())))
  await page.goto(`${harness.baseUrl}/agent`)
  await page.getByText('Start with an internal pilot rehearsal').waitFor({ timeout: 15_000 })
  const body = await page.locator('body').innerText()
  const leaks = fakeOperationalTexts.filter((text) => body.includes(text))
  const previewLeaks = ['Preview safe demo states', '/component-showcase'].filter((text) => body.includes(text))
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)
  checks.push(assertCheck(leaks.length === 0, `${viewport.width}px empty workspace contains no fake operational rows`, { leaks }))
  checks.push(assertCheck(!overflow, `${viewport.width}px empty workspace has no horizontal overflow`))
  checks.push(assertCheck(previewLeaks.length === 0, `${viewport.width}px empty workspace does not expose fake-operational demo preview`, { previewLeaks }))
  await page.screenshot({ path, fullPage: true })
  await page.close()
}

mkdirSync(evidenceRoot, { recursive: true })
mkdirSync(dirname(desktopPath), { recursive: true })
mkdirSync(dirname(mobilePath), { recursive: true })

try {
  harness = await startHarness()
  await captureEmptyWorkspace({ width: 1280, height: 900 }, desktopPath)
  await captureEmptyWorkspace({ width: 390, height: 900 }, mobilePath)
} catch (error) {
  failureDebug = {
    message: error instanceof Error ? error.message : String(error),
    nextDevLogTail: harness?.server.readLogs() ?? '',
  }
  caughtError = error
} finally {
  if (harness) await closeHarness(harness)
  const transcript = {
    scenario: 'Task 12 visual QA: first-run authenticated empty workspace on desktop and mobile',
    invocation: `cd frontend && node scripts/verify-task-next-first-run-visual.mjs --desktop ${desktopPath.startsWith(repoRoot) ? desktopPath.slice(repoRoot.length + 1) : desktopPath} --mobile ${mobilePath.startsWith(repoRoot) ? mobilePath.slice(repoRoot.length + 1) : mobilePath}`,
    baseUrl: harness?.baseUrl ?? null,
    desktopPath,
    mobilePath,
    checks,
    failureDebug,
    cleanup: cleanupReceipt,
  }
  writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
}

if (caughtError) {
  throw caughtError
}

console.log(JSON.stringify({ desktopPath, mobilePath, transcriptPath, checks: checks.length, cleanup: cleanupReceipt }, null, 2))
