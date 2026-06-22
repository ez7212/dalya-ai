import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import {
  assertCheck,
  closeHarness,
  evidenceRoot,
  fakeOperationalTexts,
  frontendRoot,
  installSharedMocks,
  jsonResponse,
  liveDashboardPayload,
  repoRoot,
  startHarness,
} from './dashboard-fallback-harness.mjs'

const outputArgIndex = process.argv.indexOf('--output')
const outputPath = outputArgIndex >= 0 ? resolve(frontendRoot, process.argv[outputArgIndex + 1] ?? '') : resolve(repoRoot, '.omo/evidence/task-2-dashboard-fallback.png')
const transcriptPath = resolve(evidenceRoot, 'visual-transcript.json')
const cleanupReceipt = 'Closed Playwright browser/context, sent SIGTERM to the local Next dev server, and closed the local Supabase auth stub.'
const checks = []
let harness = null
let failureDebug = null
let caughtError = null

async function screenshotStep(page, name) {
  const path = resolve(evidenceRoot, `${name}.png`)
  await page.screenshot({ path, fullPage: true })
  return path
}

async function buildComposite(browser, steps) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1500 }, deviceScaleFactor: 1 })
  const cards = steps.map((step) => {
    const image = readFileSync(step.path).toString('base64')
    return `<section><h2>${step.title}</h2><p>${step.detail}</p><img src="data:image/png;base64,${image}" /></section>`
  }).join('')
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#FAFAF9;color:#3D3D39;font-family:Inter,system-ui,sans-serif;padding:24px}
    h1{font-size:24px;margin:0 0 18px} section{border:1px solid #D6D6D2;background:white;border-radius:8px;margin:0 0 18px;padding:14px}
    h2{font-size:16px;margin:0 0 4px} p{font-size:13px;color:#5C5C57;margin:0 0 10px} img{width:100%;border:1px solid #E8E8E5;border-radius:6px}
  </style></head><body><h1>Task 2 dashboard fallback browser QA</h1>${cards}</body></html>`)
  await page.screenshot({ path: outputPath, fullPage: true })
  await page.close()
}

mkdirSync(evidenceRoot, { recursive: true })
mkdirSync(dirname(outputPath), { recursive: true })

try {
  harness = await startHarness()
  const failurePage = await harness.context.newPage()
  await installSharedMocks(failurePage)
  await failurePage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse({ detail: 'upstream unavailable' }, 503)))
  await failurePage.goto(`${harness.baseUrl}/agent`)
  await failurePage.getByText("Couldn't load your live workspace").waitFor({ timeout: 15_000 })
  const failureBody = await failurePage.locator('body').innerText()
  const failureLeaks = fakeOperationalTexts.filter((text) => failureBody.includes(text))
  checks.push(assertCheck(failureLeaks.length === 0, 'failed live dashboard fetch renders no fake operational rows', { failureLeaks }))
  checks.push(assertCheck(failureBody.includes('Retry'), 'failed live dashboard fetch exposes retry action'))
  const failurePath = await screenshotStep(failurePage, 'visual-01-error-shell')

  const successPage = await harness.context.newPage()
  await installSharedMocks(successPage)
  await successPage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(liveDashboardPayload())))
  await successPage.goto(`${harness.baseUrl}/agent`)
  await successPage.getByText('Noura Live').first().waitFor({ timeout: 15_000 })
  const successBody = await successPage.locator('body').innerText()
  const successLeaks = fakeOperationalTexts.filter((text) => successBody.includes(text))
  checks.push(assertCheck(successBody.includes('Live workspace'), 'successful dashboard payload renders live workspace label'))
  checks.push(assertCheck(successBody.includes('Noura Live'), 'successful dashboard payload renders mocked live buyer'))
  checks.push(assertCheck(successLeaks.length === 0, 'successful dashboard payload does not render fallback sample rows', { successLeaks }))
  const successPath = await screenshotStep(successPage, 'visual-02-live-workspace')

  await buildComposite(harness.browser, [
    { title: '1. API failure', detail: 'Authenticated /agent shows an error/retry shell with no fake operational rows.', path: failurePath },
    { title: '2. Successful API payload', detail: 'Authenticated /agent renders the mocked live workspace data.', path: successPath },
  ])

  await failurePage.close()
  await successPage.close()
} catch (error) {
  failureDebug = {
    message: error instanceof Error ? error.message : String(error),
    nextDevLogTail: harness?.server.readLogs() ?? '',
  }
  caughtError = error
} finally {
  if (harness) await closeHarness(harness)

  const transcript = {
    scenario: 'Task 2 visual browser QA: authenticated /agent API failure error shell and successful mocked live workspace',
    invocation: `cd frontend && node scripts/verify-task-next-dashboard-fallback-visual.mjs --output ${outputPath.startsWith(repoRoot) ? outputPath.slice(repoRoot.length + 1) : outputPath}`,
    baseUrl: harness?.baseUrl ?? null,
    outputPath,
    checks,
    failureDebug,
    nextDevLogTail: harness?.server.readLogs() ?? '',
    cleanup: cleanupReceipt,
  }
  writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
}

if (caughtError) {
  throw caughtError
}

console.log(JSON.stringify({ outputPath, transcriptPath, checks: checks.length, cleanup: cleanupReceipt }, null, 2))
