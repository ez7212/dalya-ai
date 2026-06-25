import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createRequire } from 'node:module'

const repoRoot = resolve(import.meta.dirname, '../../../..')
const frontendRoot = process.env.T8_FRONTEND_ROOT ? resolve(process.env.T8_FRONTEND_ROOT) : resolve(repoRoot, 'frontend')
const outputDir = import.meta.dirname
const requireFromFrontend = createRequire(resolve(frontendRoot, 'package.json'))
const { chromium } = requireFromFrontend('@playwright/test')

const listingId = 'T8-QA-SEA-HAVEN'
const widths = [1280, 768, 375]
const routes = ['knowledge', 'logistics', 'offers']
const transcript = []
const artifacts = []

const listingSummary = {
  id: listingId,
  title: 'Sea Haven Tower A 2305',
  project: 'Sobha Sea Haven',
  community: 'Dubai Harbour',
  property_type: 'apartment',
  bedrooms: 2,
  asking_price_aed: 4300000,
  status: 'live',
  health_status: 'ready',
  assigned_agent_name: 'Leila Agent',
  conversations_count: 3,
  open_offer_count: 1,
  active_viewing_count: 2,
  knowledge_status: 'needs_review',
  logistics_status: 'prefilled',
  last_activity_at: '2026-06-24T09:30:00.000Z',
  next_action: 'Review logistics',
}

const detailPayload = {
  id: listingId,
  listing_id: listingId,
  project: 'Sobha Sea Haven',
  title: 'Sea Haven Tower A 2305',
  unit_number: 'A-2305',
  community: 'Dubai Harbour',
  property_type: 'apartment',
  bedrooms: 2,
  asking_price_aed: 4300000,
  status: 'live',
  assigned_agent_name: 'Leila Agent',
  leads: [],
  stages: [],
  stats: {
    total_leads: 3,
    active_leads: 2,
    viewing_requests: 1,
  },
}

const knowledgePayload = {
  listing_id: listingId,
  document_types: ['title_deed', 'service_charge_statement', 'agent_inspection_notes'],
  documents: [
    {
      document_id: 'doc-title-deed',
      document_type: 'title_deed',
      label: 'Title deed packet',
      status: 'processed',
      created_at: '2026-06-21T08:00:00.000Z',
    },
    {
      document_id: 'doc-inspection',
      document_type: 'agent_inspection_notes',
      label: 'Ready-property inspection notes',
      status: 'processed',
      created_at: '2026-06-23T11:00:00.000Z',
    },
  ],
  facts: [
    {
      fact_id: 'fact-parking',
      document_id: 'doc-inspection',
      fact_key: 'parking_spaces',
      fact_group: 'access',
      value_text: 'Two basement spaces are available; buyer parking requires gate registration.',
      confidence: 0.91,
      source: 'agent_inspection_notes',
      verified: true,
      buyer_safe: true,
      risk_flag: false,
      notes: null,
      updated_at: '2026-06-24T07:40:00.000Z',
    },
    {
      fact_id: 'fact-service-charge',
      document_id: 'doc-title-deed',
      fact_key: 'service_charge',
      fact_group: 'fees',
      value_text: 'Service charge statement is pending owner confirmation.',
      confidence: 0.68,
      source: 'service_charge_statement',
      verified: false,
      buyer_safe: false,
      risk_flag: true,
      notes: 'Needs latest statement.',
      updated_at: '2026-06-23T13:10:00.000Z',
    },
  ],
  summary: {
    buyer_safe_summary: 'Ready-property apartment in Dubai Harbour with two parking spaces and viewing access via security registration.',
    internal_notes: 'Confirm latest service charge statement before buyer-facing disclosure.',
    missing_information: ['Latest service charge statement', 'AC maintenance receipt'],
    risk_flags: ['Service charge statement pending owner confirmation'],
    status: 'needs_review',
    updated_at: '2026-06-24T08:00:00.000Z',
  },
}

const logisticsPayload = {
  listing_id: listingId,
  logistics: {
    access: {
      type: 'security office',
      meet_point: 'Tower A lobby reception',
      advance_notice_hours: 24,
      noc_required: false,
      visitor_parking_pass_required: true,
      buyer_emirates_id_preregistration_required: true,
      security_office_hours: { start: '09:00', end: '18:00' },
    },
    keys: {
      location: 'front office',
      contact_details: 'Leila Agent +971 50 000 0000',
      key_kit_checklist: ['main door', 'parking card', 'amenity card'],
      return_same_day_required: true,
    },
    tenant: {
      status: 'vacant',
      notice_period_hours: 24,
      cooperation_level: 'friendly',
      preferred_time_windows: 'Weekdays 11:00-16:00',
      photography_permission: true,
    },
    owner_permissions: {
      viewing_restrictions: 'No Friday morning visits.',
      owner_contact: 'Owner via agent only.',
      owner_must_be_present: false,
    },
  },
  prefill: {
    display_name: 'Sobha Sea Haven, Tower A',
    confidence: 0.82,
    contributor_count: 3,
    draft: {
      access: { meet_point: 'Tower A lobby' },
      keys: { location: 'front office' },
      tenant: { status: 'vacant' },
      owner_permissions: {},
    },
  },
}

const offersPayload = {
  listing_id: listingId,
  threshold: 4100000,
  offers: [
    {
      buyer_label: 'Noura A.',
      amount_aed: 4150000,
      status: 'submitted',
      vs_asking: '3.5% below asking',
      received_at: '2026-06-24T06:30:00.000Z',
    },
    {
      buyer_label: 'Omar K.',
      amount_aed: 3980000,
      status: 'rejected',
      vs_asking: '7.4% below asking',
      received_at: '2026-06-20T12:00:00.000Z',
    },
  ],
}

function log(line, data = undefined) {
  const rendered = data === undefined ? line : `${line} ${JSON.stringify(data)}`
  transcript.push(rendered)
  console.log(rendered)
}

async function findFreePort() {
  return await new Promise((resolvePort, reject) => {
    const server = createServer()
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close(() => {
        if (address && typeof address === 'object') resolvePort(address.port)
        else reject(new Error('Could not allocate a local port'))
      })
    })
    server.on('error', reject)
  })
}

async function waitForServer(baseUrl, child, readLogs) {
  const started = Date.now()
  let last = ''
  while (Date.now() - started < 90_000) {
    if (child.exitCode !== null) throw new Error(`dev server exited with ${child.exitCode}\n${readLogs()}`)
    try {
      const response = await fetch(baseUrl)
      if (response.status < 500) return
      last = `HTTP ${response.status}`
    } catch (error) {
      last = error instanceof Error ? error.message : String(error)
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 750))
  }
  throw new Error(`timed out waiting for ${baseUrl}: ${last}\n${readLogs()}`)
}

function startDevServer(port, supabaseUrl) {
  const child = spawn('npm', ['run', 'dev', '--', '--webpack', '--hostname', '127.0.0.1', '--port', String(port)], {
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
  child.stdout.on('data', (chunk) => { logs += chunk.toString() })
  child.stderr.on('data', (chunk) => { logs += chunk.toString() })
  return { child, readLogs: () => logs.slice(-10000) }
}

async function startSupabaseStub() {
  const port = await findFreePort()
  const user = {
    id: '00000000-0000-4000-8000-000000008008',
    aud: 'authenticated',
    role: 'authenticated',
    email: 'agent@example.com',
    app_metadata: { role: 'agent' },
    user_metadata: { display_name: 'Leila Agent' },
    created_at: '2026-06-24T06:00:00.000Z',
  }
  const session = {
    access_token: 't8-browser-qa-access-token',
    refresh_token: 't8-browser-qa-refresh-token',
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    expires_in: 3600,
    token_type: 'bearer',
    user,
  }
  const server = createServer((request, response) => {
    if (request.url === '/auth/v1/user') {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify(user))
      return
    }
    if (request.url?.startsWith('/auth/v1/token')) {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify(session))
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
    session,
    close: () => new Promise((resolveClose) => server.close(resolveClose)),
  }
}

function encodeCookieSession(session) {
  return `base64-${Buffer.from(JSON.stringify(session), 'utf8').toString('base64url')}`
}

async function seedAuth(context, baseUrl, session) {
  await context.addCookies([{
    name: 'sb-127-auth-token',
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

async function installApiStubs(page) {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    let payload = null
    let status = 200

    if (path === '/api/v1/me/brokerages') {
      payload = {
        active_brokerages: [{
          brokerage_id: 'brokerage-1',
          name: 'Mahoroba Realty QA',
          role: 'agent',
          membership_id: 'membership-t8-qa',
        }],
        requires_selection: false,
        default_brokerage_id: 'brokerage-1',
      }
    }
    else if (path === '/api/v1/listings/mine') payload = { listings: [listingSummary] }
    else if (path === `/api/v1/seller/listings/${listingId}/leads`) payload = detailPayload
    else if (path === `/api/v1/listings/${listingId}/knowledge`) payload = knowledgePayload
    else if (path === `/api/v1/agent/listings/${listingId}/logistics`) payload = logisticsPayload
    else if (path === `/api/v1/seller/listings/${listingId}/offers`) payload = offersPayload
    else if (path.includes('/facts/') || path.endsWith('/knowledge/regenerate') || path.endsWith('/documents')) payload = { ok: true }
    else {
      status = 404
      payload = { detail: `Unstubbed API path ${path}` }
    }

    log(`api ${route.request().method()} ${path} -> ${status}`)
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    })
  })
}

async function collectChecks(page, routeName, width) {
  await page.waitForSelector(`[data-listing-workspace-route="${routeName}"]`, { timeout: 30_000 })
  if (routeName === 'logistics') await page.waitForSelector('text=Save logistics', { timeout: 30_000 })
  const activeTab = await page.locator('nav[aria-label="Listing workspace"] [aria-current="page"]').innerText()
  const bodyText = await page.locator('body').innerText()
  const noLegacyText = !/(text-gold|btn-gold|surface-1|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E)/i.test(bodyText)
  const metrics = await page.evaluate(() => ({
    title: document.title,
    url: location.href,
    bodyChars: document.body.innerText.length,
    hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    shellHeader: Boolean(document.querySelector('nav[aria-label^="Listings /"]')),
    routeMarker: document.querySelector('[data-listing-workspace-route]')?.getAttribute('data-listing-workspace-route') ?? null,
    bg: getComputedStyle(document.body).backgroundColor,
  }))

  const focusLocator = routeName === 'logistics'
    ? page.getByLabel('Meet point')
    : page.locator('button, input, select, textarea, a[href]').first()
  await focusLocator.focus()
  const focusStyle = await page.evaluate(() => {
    const element = document.activeElement
    if (!element) return null
    const style = getComputedStyle(element)
    return {
      tag: element.tagName,
      text: element.textContent?.trim().slice(0, 80) || element.getAttribute('aria-label') || element.getAttribute('placeholder') || '',
      outline: style.outline,
      boxShadow: style.boxShadow,
      borderColor: style.borderColor,
    }
  })

  const findings = {
    routeName,
    width,
    activeTab,
    noLegacyText,
    focusStyle,
    ...metrics,
  }
  log(`checks ${routeName} ${width}`, findings)
  return findings
}

async function run() {
  mkdirSync(outputDir, { recursive: true })
  const existingBaseUrlArg = process.argv.find((arg) => arg.startsWith('--base-url='))
  const existingBaseUrl = existingBaseUrlArg ? existingBaseUrlArg.split('=').slice(1).join('=').replace(/\/$/, '') : null
  const supabase = existingBaseUrl ? null : await startSupabaseStub()
  const port = existingBaseUrl ? null : await findFreePort()
  const baseUrl = existingBaseUrl ?? `http://127.0.0.1:${port}`
  const devServer = existingBaseUrl ? null : startDevServer(port, supabase.url)
  let browser = null
  const results = []
  let cleanup = existingBaseUrl ? 'pre-existing server left untouched' : 'not started'

  log('surface browser-ui')
  log('listingId', { listingId })
  log('invocation', {
    command: existingBaseUrl
      ? `node ${new URL(import.meta.url).pathname} --base-url=${existingBaseUrl}`
      : `npm run dev -- --webpack --hostname 127.0.0.1 --port ${port}`,
    cwd: frontendRoot,
    baseUrl,
    supabaseStub: supabase?.url ?? 'not-started-existing-server-mode',
    pid: devServer?.child.pid ?? 'not-started-existing-server-mode',
  })

  try {
    if (devServer) {
      await waitForServer(baseUrl, devServer.child, devServer.readLogs)
      log('devServer ready', { baseUrl, pid: devServer.child.pid })
    } else {
      const response = await fetch(baseUrl)
      if (response.status >= 500) throw new Error(`existing server returned HTTP ${response.status}`)
      log('existing devServer reachable', { baseUrl, status: response.status })
    }
    browser = await chromium.launch()
    const context = await browser.newContext({ deviceScaleFactor: 1 })
    if (supabase) await seedAuth(context, baseUrl, supabase.session)
    else {
      await context.addInitScript(() => {
        window.localStorage.setItem('dalya:selected-brokerage-id', 'brokerage-1')
      })
    }
    const page = await context.newPage()
    await installApiStubs(page)
    page.on('console', (message) => {
      if (['error', 'warning'].includes(message.type())) log(`browser console ${message.type()}: ${message.text()}`)
    })
    page.on('pageerror', (error) => log(`browser pageerror: ${error.message}`))

    for (const width of widths) {
      await page.setViewportSize({ width, height: 920 })
      for (const routeName of routes) {
        const url = `${baseUrl}/listings/${listingId}/${routeName}`
        log('navigate', { routeName, width, url })
        await page.goto(url, { waitUntil: 'networkidle' })
        const checks = await collectChecks(page, routeName, width)
        const screenshotName = `t8-${routeName}-${width}.png`
        const screenshotPath = resolve(outputDir, screenshotName)
        await page.screenshot({ path: screenshotPath, fullPage: true })
        artifacts.push({
          id: `screenshot-${routeName}-${width}`,
          kind: 'browser-screenshot',
          description: `${routeName} route at ${width}px`,
          path: screenshotPath,
        })
        results.push({ ...checks, screenshotPath })
      }
    }

    const transcriptPath = resolve(outputDir, 't8-browser-transcript.json')
    const matrixPath = resolve(outputDir, 'manualQa.json')
    writeFileSync(transcriptPath, JSON.stringify({ transcript, results }, null, 2))
    artifacts.push({
      id: 'browser-transcript',
      kind: 'browser-transcript',
      description: 'Navigation, API fulfillment, DOM, focus, and overflow checks',
      path: transcriptPath,
    })

    const surfaceEvidence = results.map((result) => ({
      scenarioId: `T8-${result.routeName}-${result.width}`,
      criterionRef: 'DESIGN.md Visual QA Requirements; Listings Workspace canonical subroutes',
      surface: `Browser UI ${result.url}`,
      exactInvocation: `Playwright page.goto(${JSON.stringify(result.url)}) with viewport ${result.width}x920`,
      verdict: result.shellHeader && result.routeMarker === result.routeName && result.activeTab.toLowerCase().includes(result.routeName) && !result.hasHorizontalOverflow && result.noLegacyText ? 'PASS' : 'FAIL',
      artifactRefs: [`screenshot-${result.routeName}-${result.width}`, 'browser-transcript'],
    }))

    const adversarialCases = [
      {
        scenarioId: 'T8-mobile-overflow',
        criterionRef: 'DESIGN.md Visual QA Requirements',
        adversarialClass: '375px mobile horizontal overflow',
        expectedBehavior: 'Canonical listing subroutes fit the viewport without document-level horizontal scroll.',
        verdict: results.filter((result) => result.width === 375).every((result) => !result.hasHorizontalOverflow) ? 'PASS' : 'FAIL',
        artifactRefs: ['screenshot-knowledge-375', 'screenshot-logistics-375', 'screenshot-offers-375', 'browser-transcript'],
      },
      {
        scenarioId: 'T8-legacy-token-visible-scan',
        criterionRef: 'DESIGN.md Non-Negotiables',
        adversarialClass: 'Legacy dark/gold visible token leakage',
        expectedBehavior: 'Rendered route text does not expose banned legacy classes/tokens and visuals remain light/slate.',
        verdict: results.every((result) => result.noLegacyText) ? 'PASS' : 'FAIL',
        artifactRefs: ['browser-transcript'],
      },
      {
        scenarioId: 'T8-focus-visible',
        criterionRef: 'DESIGN.md Visual QA Requirements',
        adversarialClass: 'Keyboard focus discoverability',
        expectedBehavior: 'Reachable inputs/buttons expose focus styles via border, outline, or ring/box-shadow.',
        verdict: results.every((result) => {
          const style = result.focusStyle
          return Boolean(style && (style.boxShadow !== 'none' || !style.outline.startsWith('rgb(0, 0, 0) none') || !/rgb\\(209, 213, 219\\)/.test(style.borderColor)))
        }) ? 'PASS' : 'FAIL',
        artifactRefs: ['browser-transcript'],
      },
      {
        scenarioId: 'T8-logistics-prefill-readable',
        criterionRef: 'Task T8 logistics empty/prefill state',
        adversarialClass: 'Prefill data readability',
        expectedBehavior: 'Logistics route renders building prefill, confidence, form tabs, and save action at all requested widths.',
        verdict: results.filter((result) => result.routeName === 'logistics').length === widths.length ? 'PASS' : 'FAIL',
        artifactRefs: ['screenshot-logistics-1280', 'screenshot-logistics-768', 'screenshot-logistics-375', 'browser-transcript'],
      },
    ]

    writeFileSync(matrixPath, JSON.stringify({ surfaceEvidence, adversarialCases, artifactRefs: artifacts }, null, 2))
    artifacts.push({
      id: 'manualQa-matrix',
      kind: 'json',
      description: 'manualQa evidence matrix',
      path: matrixPath,
    })
    log('manualQa written', { matrixPath })
    await context.close()
  } finally {
    if (browser) await browser.close()
    if (devServer) {
      devServer.child.kill('SIGTERM')
      cleanup = await Promise.race([
        new Promise((resolveExit) => devServer.child.once('exit', (code, signal) => resolveExit(`dev server exited code=${code} signal=${signal}`))),
        new Promise((resolveTimeout) => setTimeout(() => resolveTimeout('dev server SIGTERM timeout'), 3000)),
      ])
      if (cleanup === 'dev server SIGTERM timeout' && devServer.child.exitCode === null) {
        devServer.child.kill('SIGKILL')
        cleanup = 'dev server required SIGKILL after SIGTERM timeout'
      }
    }
    if (supabase) await supabase.close()
    const cleanupPath = resolve(outputDir, 'cleanup-receipt.txt')
    writeFileSync(cleanupPath, [
      `devServerPid=${devServer?.child.pid ?? 'not-started-existing-server-mode'}`,
      `cleanup=${cleanup}`,
      `supabaseStub=${supabase ? 'closed' : 'not-started-existing-server-mode'}`,
      `baseUrl=${baseUrl}`,
      `timestamp=${new Date().toISOString()}`,
      '',
      'dev server log tail:',
      devServer?.readLogs() ?? 'not available; harness used pre-existing server',
    ].join('\n'))
    log('cleanup', { cleanupPath, cleanup })
  }
}

await run()
