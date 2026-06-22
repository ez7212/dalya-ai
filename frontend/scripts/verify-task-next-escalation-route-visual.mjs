import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { chromium } from '@playwright/test'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const evidenceRoot = resolve(repoRoot, '.omo/evidence/task-1-escalation-route')
const outputArgIndex = process.argv.indexOf('--output')
const outputPath = outputArgIndex >= 0 ? resolve(frontendRoot, process.argv[outputArgIndex + 1] ?? '') : resolve(repoRoot, '.omo/evidence/task-1-escalation-route.png')
const transcriptPath = resolve(evidenceRoot, 'visual-transcript.json')
const authCookieName = 'sb-127-auth-token'

function assertCheck(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label}: ${JSON.stringify(details)}`)
  }
  return { label, passed: true, details }
}

function jsonResponse(body) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

async function findFreePort() {
  return await new Promise((resolvePort, reject) => {
    const server = createServer()
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close(() => {
        if (address && typeof address === 'object') {
          resolvePort(address.port)
        } else {
          reject(new Error('Could not allocate a local port'))
        }
      })
    })
    server.on('error', reject)
  })
}

async function waitForServer(baseUrl, child) {
  const startedAt = Date.now()
  let lastError = ''
  while (Date.now() - startedAt < 90_000) {
    if (child.exitCode !== null) {
      throw new Error(`Next dev server exited early with code ${child.exitCode}`)
    }
    try {
      const response = await fetch(baseUrl)
      if (response.status < 500) return
      lastError = `HTTP ${response.status}`
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error)
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 500))
  }
  throw new Error(`Timed out waiting for ${baseUrl}: ${lastError}`)
}

function startNext(port, supabaseUrl) {
  const child = spawn('npm', ['run', 'dev', '--', '--hostname', '127.0.0.1', '--port', String(port)], {
    cwd: frontendRoot,
    env: {
      ...process.env,
      NEXT_TELEMETRY_DISABLED: '1',
      NEXT_PUBLIC_SUPABASE_URL: supabaseUrl,
      NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-anon-key',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  let logs = ''
  child.stdout.on('data', (chunk) => {
    logs += chunk.toString()
  })
  child.stderr.on('data', (chunk) => {
    logs += chunk.toString()
  })
  return { child, readLogs: () => logs.slice(-6000) }
}

async function startSupabaseAuthStub() {
  const port = await findFreePort()
  const user = authSession().user
  const server = createServer((request, response) => {
    if (request.url === '/auth/v1/user') {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify(user))
      return
    }
    response.writeHead(404, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ error: 'not_found' }))
  })

  await new Promise((resolveListen, reject) => {
    server.listen(port, '127.0.0.1', resolveListen)
    server.on('error', reject)
  })

  return {
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolveClose) => server.close(resolveClose)),
  }
}

function authSession() {
  return {
    access_token: 'task-1-access-token',
    refresh_token: 'task-1-refresh-token',
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    expires_in: 3600,
    token_type: 'bearer',
    user: {
      id: '00000000-0000-4000-8000-000000000001',
      aud: 'authenticated',
      role: 'authenticated',
      email: 'agent@example.com',
      app_metadata: { role: 'agent' },
      user_metadata: { display_name: 'Leila Agent' },
      created_at: '2026-06-22T06:00:00.000Z',
    },
  }
}

function encodeCookieSession(session) {
  return `base64-${Buffer.from(JSON.stringify(session), 'utf8').toString('base64url')}`
}

function dashboardPayload() {
  return {
    generated_at: '2026-06-22T10:00:00+04:00',
    agent: { display_name: 'Leila Agent' },
    brokerage: { name: 'Luqman Realty' },
    metrics: { open_tasks: 0, hot_leads: 0, viewings_today: 0, stale_leads: 0, open_escalations: 1 },
    conversations: [],
    tasks: [],
    hot_leads: [],
    campaigns: [],
    viewings: [],
    drafts: { reply_drafts: [], outreach_drafts: [] },
    marketing: { pages: [] },
    escalation_threads: [threadPayload('esc-critical-1', 'Aisha Rahman', 'updated', 'critical')],
    performance: { scope: 'agent', primary: { key: 'today', label: 'Today', metrics: {} }, windows: [] },
  }
}

function inboxPayload() {
  const filler = Array.from({ length: 7 }, (_, index) => (
    threadPayload(`esc-filler-${index + 1}`, `Buyer ${index + 1}`, 'open', 'normal')
  ))
  return {
    generated_at: '2026-06-22T10:01:00+04:00',
    counts: { total: 8, critical: 1, high: 0 },
    threads: [...filler, threadPayload('esc-critical-1', 'Aisha Rahman', 'updated', 'critical')],
  }
}

function threadPayload(threadId, buyerName, state, urgency) {
  return {
    thread_id: threadId,
    envelope_token: `REF-${threadId.toUpperCase()}`,
    conversation_id: `conv-${threadId}`,
    ai_mode: 'active',
    category: 'viewing',
    state,
    urgency,
    buyer: { name: buyerName, phone: '+971500000001' },
    listing: { project: 'Emaar Oasis Villa', unit_number: 'V-12' },
    latest_question: threadId === 'esc-critical-1'
      ? 'Can we confirm access before the 11 AM viewing?'
      : 'Can you confirm the viewing detail?',
    question_count: 2,
    last_buyer_message_at: '2026-06-22T09:50:00+04:00',
    opened_at: '2026-06-22T09:10:00+04:00',
    latest_route_expires_at: '2026-06-22T10:20:00+04:00',
    questions: [
      { question_id: `${threadId}-q1`, question_text: 'Is the property ready to view today?', added_at: '2026-06-22T09:10:00+04:00' },
      { question_id: `${threadId}-q2`, question_text: 'Can we confirm access before the 11 AM viewing?', added_at: '2026-06-22T09:50:00+04:00' },
    ],
  }
}

async function installApiMocks(page) {
  await page.route('https://test.supabase.co/**', (route) => route.fulfill(jsonResponse({})))
  await page.route('**/api/v1/me/brokerages', (route) => route.fulfill(jsonResponse({
    active_brokerages: [{ brokerage_id: 'brokerage-1', name: 'Luqman Realty', role: 'agent', membership_id: 'membership-1' }],
    requires_selection: false,
    default_brokerage_id: 'brokerage-1',
  })))
  await page.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(dashboardPayload())))
  await page.route('**/api/v1/agent/escalations?**', (route) => route.fulfill(jsonResponse(inboxPayload())))
}

async function screenshotStep(page, name) {
  const path = resolve(evidenceRoot, `${name}.png`)
  await page.screenshot({ path, fullPage: true })
  return path
}

async function buildComposite(browser, stepPaths) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1400 }, deviceScaleFactor: 1 })
  const cards = stepPaths.map((step) => {
    const image = readFileSync(step.path).toString('base64')
    return `<section><h2>${step.title}</h2><p>${step.detail}</p><img src="data:image/png;base64,${image}" /></section>`
  }).join('')
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;background:#FAFAF9;color:#3D3D39;font-family:Inter,system-ui,sans-serif;padding:24px}
    h1{font-size:24px;margin:0 0 18px} section{border:1px solid #D6D6D2;background:white;border-radius:8px;margin:0 0 18px;padding:14px}
    h2{font-size:16px;margin:0 0 4px} p{font-size:13px;color:#5C5C57;margin:0 0 10px} img{width:100%;border:1px solid #E8E8E5;border-radius:6px}
  </style></head><body><h1>Task 1 escalation route browser QA</h1>${cards}</body></html>`)
  await page.screenshot({ path: outputPath, fullPage: true })
  await page.close()
}

mkdirSync(evidenceRoot, { recursive: true })
mkdirSync(dirname(outputPath), { recursive: true })

const supabaseStub = await startSupabaseAuthStub()
const port = await findFreePort()
const baseUrl = `http://127.0.0.1:${port}`
const server = startNext(port, supabaseStub.url)
let browser = null
const checks = []
let failureDebug = null
try {
  if (server.child) {
    try {
      await waitForServer(baseUrl, server.child)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      throw new Error(`${message}\nNext dev log tail:\n${server.readLogs()}`)
    }
  }
  browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1280, height: 760 }, deviceScaleFactor: 1 })
  await context.addCookies([
    {
      name: authCookieName,
      value: encodeCookieSession(authSession()),
      url: baseUrl,
      httpOnly: false,
      sameSite: 'Lax',
      expires: Math.floor(Date.now() / 1000) + 3600,
    },
  ])
  await context.addInitScript((session) => {
    window.localStorage.setItem('dalya:selected-brokerage-id', 'brokerage-1')
    document.cookie = `sb-127-auth-token=base64-${btoa(JSON.stringify(session)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')}; path=/; SameSite=Lax`
  }, authSession())
  const page = await context.newPage()
  await installApiMocks(page)
  const seededCookies = await context.cookies(baseUrl)
  checks.push(assertCheck(
    seededCookies.some((cookie) => cookie.name === authCookieName),
    'auth cookie is seeded before protected-route navigation',
    { cookieNames: seededCookies.map((cookie) => cookie.name) },
  ))

  await page.goto(`${baseUrl}/agent`)
  try {
    await page.getByText('Ranked work for this pilot day').waitFor()
  } catch (error) {
    const failurePath = await screenshotStep(page, 'visual-failure-agent')
    failureDebug = {
      url: page.url(),
      title: await page.title(),
      bodyText: (await page.locator('body').innerText()).slice(0, 2000),
      screenshot: failurePath,
      error: error instanceof Error ? error.message : String(error),
    }
    writeFileSync(transcriptPath, `${JSON.stringify({
      scenario: 'Task 1 visual browser QA failed before Today Queue rendered',
      invocation: `cd frontend && node scripts/verify-task-next-escalation-route-visual.mjs --output ${outputPath.startsWith(repoRoot) ? outputPath.slice(repoRoot.length + 1) : outputPath}`,
      baseUrl,
      outputPath,
      checks,
      failureDebug,
      nextDevLogTail: server.readLogs(),
    }, null, 2)}\n`)
    throw error
  }
  const agentPath = await screenshotStep(page, 'visual-01-agent')
  const escalationLink = page.locator('a[href="/agent/escalations?thread=esc-critical-1"]').first()
  checks.push(assertCheck(await escalationLink.count() === 1, 'agent Today Queue exposes query-param escalation link'))
  await escalationLink.click()
  await page.waitForURL('**/agent/escalations?thread=esc-critical-1')
  const selectedRow = page.locator('article[data-selected-thread="true"][data-thread-id="esc-critical-1"]')
  await selectedRow.waitFor()
  await page.waitForFunction(() => {
    const row = document.querySelector('article[data-selected-thread="true"][data-thread-id="esc-critical-1"]')
    const box = row?.getBoundingClientRect()
    return Boolean(box && box.y >= 0 && box.y < 620)
  })
  const selectedIsFocused = await selectedRow.evaluate((node) => document.activeElement === node)
  const selectedBox = await selectedRow.boundingBox()
  const scrollY = await page.evaluate(() => window.scrollY)
  checks.push(assertCheck(selectedIsFocused, 'selected inbox row receives browser focus'))
  checks.push(assertCheck(Boolean(selectedBox) && selectedBox.y >= 0 && selectedBox.y < 620, 'selected inbox row is scrolled into viewport', { selectedBox, scrollY }))
  const selectedPath = await screenshotStep(page, 'visual-02-selected-inbox')
  await page.goBack()
  await page.waitForURL(`${baseUrl}/agent`)
  await page.getByText('Ranked work for this pilot day').waitFor()
  checks.push(assertCheck(new URL(page.url()).pathname === '/agent', 'browser Back returns to /agent', { url: page.url() }))
  const backPath = await screenshotStep(page, 'visual-03-back-agent')
  await buildComposite(browser, [
    { title: '1. Start at /agent', detail: 'Today Queue shows the critical escalation link.', path: agentPath },
    { title: '2. Click opens /agent/escalations?thread=esc-critical-1', detail: 'Selected row is highlighted, focused, and scrolled into view.', path: selectedPath },
    { title: '3. Browser Back returns to /agent', detail: 'The browser history returns to the agent workspace.', path: backPath },
  ])
  await context.close()
} finally {
  if (browser) await browser.close()
  if (server.child) {
    server.child.kill('SIGTERM')
  }
  if (supabaseStub) {
    await supabaseStub.close()
  }
}

const transcript = {
  scenario: 'Task 1 visual browser QA: /agent Today Queue escalation click-through, selected inbox focus, Back to /agent',
  invocation: `cd frontend && node scripts/verify-task-next-escalation-route-visual.mjs --output ${outputPath.startsWith(repoRoot) ? outputPath.slice(repoRoot.length + 1) : outputPath}`,
  baseUrl,
  outputPath,
  checks,
  failureDebug,
  nextDevLogTail: server.readLogs(),
  cleanup: 'Closed Playwright browser/context, sent SIGTERM to the local Next dev server, and closed the local Supabase auth stub.',
}
writeFileSync(transcriptPath, `${JSON.stringify(transcript, null, 2)}\n`)
console.log(JSON.stringify({ outputPath, transcriptPath, checks: checks.length, cleanup: transcript.cleanup }, null, 2))
