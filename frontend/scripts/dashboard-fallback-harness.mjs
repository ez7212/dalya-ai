import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from '@playwright/test'

export const repoRoot = resolve(import.meta.dirname, '../..')
export const frontendRoot = resolve(repoRoot, 'frontend')
export const evidenceRoot = resolve(repoRoot, '.omo/evidence/task-2-dashboard-fallback')
export const authCookieName = 'sb-127-auth-token'

export const fakeOperationalTexts = [
  'Karim A.',
  'Neha S.',
  'Omar R.',
  'Ahmed K.',
  'Faisal Al N.',
  '+971502148821',
  '+971501112233',
  'AED 3.42M',
  'Offer expires before lunch',
  'Viewing-ready family needs slots',
  'Mortgage buyer waiting on NOC timing',
  'Showing the local dashboard fallback',
]

export function assertCheck(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label}: ${JSON.stringify(details)}`)
  }
  return { label, passed: true, details }
}

export function jsonResponse(body, status = 200) {
  return {
    status,
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

function authSession() {
  return {
    access_token: 'task-2-access-token',
    refresh_token: 'task-2-refresh-token',
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    expires_in: 3600,
    token_type: 'bearer',
    user: {
      id: '00000000-0000-4000-8000-000000000002',
      aud: 'authenticated',
      role: 'authenticated',
      email: 'agent@example.com',
      app_metadata: { role: 'agent' },
      user_metadata: { display_name: 'Leila Agent' },
      created_at: '2026-06-22T06:00:00.000Z',
    },
  }
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

function encodeCookieSession(session) {
  return `base64-${Buffer.from(JSON.stringify(session), 'utf8').toString('base64url')}`
}

export function liveDashboardPayload() {
  return {
    generated_at: '2026-06-22T10:00:00+04:00',
    agent: { display_name: 'Leila Agent' },
    brokerage: { name: 'Luqman Realty' },
    metrics: { open_tasks: 1, hot_leads: 1, viewings_today: 0, stale_leads: 0, open_escalations: 0 },
    tasks: [],
    hot_leads: [{
      id: 'lead-live-1',
      buyer: { name: 'Noura Live', phone: '+971500000777', budget_aed: 4200000 },
      listing: { project: 'Dubai Creek Residence', unit_number: '1802' },
      signal: 'ready_to_view',
      signal_key: 'ready_to_view',
      next_action: 'Confirm viewing window',
      reason: 'Live payload buyer asked for a same-day viewing slot.',
      urgency_score: 91,
      last_message: 'Can I view after 6 today?',
      last_message_at: '2026-06-22T09:44:00+04:00',
      due_at: '2026-06-22T10:30:00+04:00',
    }],
    conversations: [{
      conversation_id: 'conv-live-1',
      buyer: { name: 'Noura Live', phone: '+971500000777' },
      listing: { project: 'Dubai Creek Residence', unit_number: '1802' },
      summary: 'Ready to view and waiting on agent confirmation.',
      last_message: 'Can I view after 6 today?',
      next_step_hint: 'Confirm viewing window',
      interest_level: 'high',
      last_message_at: '2026-06-22T09:44:00+04:00',
      updated_at: '2026-06-22T09:44:00+04:00',
      message_count: 4,
      offer_count: 0,
      open_escalation_count: 0,
      needs_reply: true,
    }],
    campaigns: [],
    viewings: [],
    escalation_threads: [],
    drafts: { reply_drafts: [], outreach_drafts: [] },
    marketing: { pages: [] },
    performance: {
      scope: 'agent',
      primary: { key: 'today', label: 'Today', metrics: { new_buyer_conversations: 1, hot_leads_active: 1 } },
      windows: [],
    },
  }
}

export async function installSharedMocks(page) {
  await page.route('https://test.supabase.co/**', (route) => route.fulfill(jsonResponse({})))
  await page.route('**/api/v1/me/brokerages', (route) => route.fulfill(jsonResponse({
    active_brokerages: [{ brokerage_id: 'brokerage-1', name: 'Luqman Realty', role: 'agent', membership_id: 'membership-1' }],
    requires_selection: false,
    default_brokerage_id: 'brokerage-1',
  })))
}

export async function seedAuth(context, baseUrl) {
  const session = authSession()
  await context.addCookies([{
    name: authCookieName,
    value: encodeCookieSession(session),
    url: baseUrl,
    httpOnly: false,
    sameSite: 'Lax',
    expires: Math.floor(Date.now() / 1000) + 3600,
  }])
  await context.addInitScript((storedSession) => {
    window.localStorage.setItem('dalya:selected-brokerage-id', 'brokerage-1')
    document.cookie = `sb-127-auth-token=base64-${btoa(JSON.stringify(storedSession)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')}; path=/; SameSite=Lax`
  }, session)
}

export async function startHarness() {
  mkdirSync(evidenceRoot, { recursive: true })
  const supabaseStub = await startSupabaseAuthStub()
  const port = await findFreePort()
  const baseUrl = `http://127.0.0.1:${port}`
  const server = startNext(port, supabaseStub.url)
  await waitForServer(baseUrl, server.child).catch((error) => {
    const message = error instanceof Error ? error.message : String(error)
    throw new Error(`${message}\nNext dev log tail:\n${server.readLogs()}`)
  })
  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1280, height: 760 }, deviceScaleFactor: 1 })
  await seedAuth(context, baseUrl)
  return { baseUrl, browser, context, server, supabaseStub }
}

export async function closeHarness(harness) {
  await harness.context.close()
  await harness.browser.close()
  harness.server.child.kill('SIGTERM')
  await harness.supabaseStub.close()
}
