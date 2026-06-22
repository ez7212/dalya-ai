import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  assertCheck,
  closeHarness,
  evidenceRoot,
  fakeOperationalTexts,
  installSharedMocks,
  jsonResponse,
  liveDashboardPayload,
  startHarness,
} from './dashboard-fallback-harness.mjs'

const redMode = process.argv.includes('--red')
const transcriptPath = resolve(evidenceRoot, redMode ? 'functional-red-transcript.json' : 'functional-transcript.json')
const checks = []
const observations = {}
let harness = null
let failureDebug = null

async function bodyIncludes(page, text) {
  return await page.locator('body').evaluate((body, value) => body.innerText.includes(value), text)
}

try {
  harness = await startHarness()
  const failurePage = await harness.context.newPage()
  await installSharedMocks(failurePage)
  await failurePage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse({ detail: 'upstream unavailable' }, 503)))
  await failurePage.goto(`${harness.baseUrl}/agent`)
  await failurePage.getByText("Couldn't load your live workspace").waitFor({ timeout: 15_000 })
  const failureBody = await failurePage.locator('body').innerText()
  const leakedTexts = fakeOperationalTexts.filter((text) => failureBody.includes(text))
  observations.failureBodyText = failureBody.slice(0, 2500)
  observations.leakedTexts = leakedTexts
  checks.push(assertCheck(leakedTexts.length === 0, 'failed live dashboard fetch renders no fake operational rows', { leakedTexts }))
  checks.push(assertCheck(await bodyIncludes(failurePage, 'Retry'), 'failed live dashboard fetch exposes retry action'))

  if (!redMode) {
    const successPage = await harness.context.newPage()
    await installSharedMocks(successPage)
    await successPage.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(liveDashboardPayload())))
    await successPage.goto(`${harness.baseUrl}/agent`)
    await successPage.getByText('Noura Live').first().waitFor({ timeout: 15_000 })
    const successBody = await successPage.locator('body').innerText()
    const successLeaks = fakeOperationalTexts.filter((text) => successBody.includes(text))
    observations.successBodyText = successBody.slice(0, 2500)
    observations.successLeaks = successLeaks
    checks.push(assertCheck(successBody.includes('Live workspace'), 'successful dashboard payload renders live workspace label'))
    checks.push(assertCheck(successBody.includes('Noura Live'), 'successful dashboard payload renders mocked live buyer'))
    checks.push(assertCheck(successLeaks.length === 0, 'successful dashboard payload does not render fallback sample rows', { successLeaks }))
    await successPage.close()
  }

  await failurePage.close()
} catch (error) {
  failureDebug = {
    message: error instanceof Error ? error.message : String(error),
    nextDevLogTail: harness?.server.readLogs() ?? '',
  }
  throw error
} finally {
  if (harness) await closeHarness(harness)
  const transcript = {
    scenario: redMode
      ? 'RED: authenticated /agent dashboard API failure must not render fake fallback rows'
      : 'GREEN: authenticated /agent dashboard API failure renders error/retry shell and successful mocked payload renders live workspace',
    invocation: `cd frontend && node scripts/verify-task-next-dashboard-fallback.mjs${redMode ? ' --red' : ''}`,
    baseUrl: harness?.baseUrl ?? null,
    checks,
    observations,
    failureDebug,
    cleanup: 'Closed Playwright browser/context, sent SIGTERM to the local Next dev server, and closed the local Supabase auth stub.',
  }
  writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
}

console.log(JSON.stringify({ transcriptPath, checks: checks.length, cleanup: 'browser/server/auth-stub closed' }, null, 2))
