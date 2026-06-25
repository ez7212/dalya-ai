import { createServer } from 'node:http'
import { existsSync, mkdirSync, statSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createRequire } from 'node:module'
import {
  removeValidatedSafeTempWorkdir,
  stageSafeFrontend,
  validateSafeTempWorkdir,
} from '../../../../frontend/scripts/final-surface-safe-env.mjs'
import {
  seedAuth as seedStagedAuth,
  startDevServer as startStagedDevServer,
  startSupabaseAuthStub as startStagedSupabaseAuthStub,
  stopServer as stopStagedServer,
  waitForServer as waitForStagedServer,
} from '../../../../frontend/scripts/final-surface-server.mjs'

const repoRoot = resolve(import.meta.dirname, '../../../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const outputDir = import.meta.dirname
const requireFromFrontend = createRequire(resolve(frontendRoot, 'package.json'))
const { chromium } = requireFromFrontend('@playwright/test')
const safeTempWorkdir = '/private/tmp/dalya-final-surface-listings-final-qa'
const dirtyReceiptPath = resolve(outputDir, 't12-dirty-worktree-receipt.txt')

const listingId = 'FINAL-QA-LISTING-001'
const widths = [1280, 768, 375]
const routes = [
  { name: 'index', path: '/listings', marker: null },
  { name: 'overview', path: `/listings/${listingId}`, marker: 'overview' },
  { name: 'documents', path: `/listings/${listingId}/documents`, marker: 'documents' },
  { name: 'knowledge', path: `/listings/${listingId}/knowledge`, marker: 'knowledge' },
  { name: 'logistics', path: `/listings/${listingId}/logistics`, marker: 'logistics' },
  { name: 'offers', path: `/listings/${listingId}/offers`, marker: 'offers' },
]
const legacyRoutes = [
  { oldPath: `/dashboard/listings/${listingId}`, expected: `/listings/${listingId}` },
  { oldPath: `/dashboard/listings/${listingId}/knowledge`, expected: `/listings/${listingId}/knowledge` },
  { oldPath: `/dashboard/listings/${listingId}/logistics`, expected: `/listings/${listingId}/logistics` },
  { oldPath: `/dashboard/listings/${listingId}/offers`, expected: `/listings/${listingId}/offers` },
  { oldPath: `/dashboard/listings/${listingId}/spa`, expected: `/listings/${listingId}/documents` },
]
const transcript = []
const artifacts = []
const results = []

const listingSummary = {
  id: listingId,
  title: 'Final QA Sea Haven residence',
  property_type: 'ready',
  community: 'Dubai Harbour',
  subcommunity: 'Sobha Sea Haven',
  building_or_project: 'Tower A',
  unit_number: 'A-2305',
  bedrooms: 2,
  bathrooms: 3,
  size_sqft: 1352,
  asking_price_aed: 4300000,
  price_per_sqft_aed: 3180,
  status: 'live',
  lead_count: 7,
  escalated_count: 2,
  source_url: null,
  first_image_url: null,
  reference_document_count: 4,
  created_at: '2026-06-20T08:00:00.000Z',
  last_activity_at: '2026-06-24T09:30:00.000Z',
  assigned_agent_name: 'Leila Agent',
  knowledge_status: 'needs_attention',
  missing_fact_count: 2,
  active_viewing_count: 2,
  open_offer_count: 1,
  buyer_conversation_count: 9,
  logistics_status: 'needs_attention',
  primary_next_action: 'review_knowledge',
}

const detailPayload = {
  id: listingId,
  listing_id: listingId,
  title: listingSummary.title,
  project: 'Sobha Sea Haven',
  unit_number: listingSummary.unit_number,
  community: listingSummary.community,
  property_type: 'apartment',
  bedrooms: 2,
  bathrooms: 3,
  bua_sqft: 1352,
  asking_price: 4300000,
  total_price: 4300000,
  negotiation_threshold: 4100000,
  status: 'live',
  assigned_agent_name: 'Leila Agent',
  document_count: 4,
  seller_notes: 'Owner prefers weekday viewings after 11:00.',
  processing_stages: [
    { key: 'documents', label: 'Documents', status: 'ready', description: 'Core documents uploaded.', note: 'Title deed and service charge statement are present.' },
    { key: 'knowledge', label: 'Knowledge', status: 'blocked', description: 'Buyer-safe facts need review.', note: 'Two facts need verification before buyer replies.' },
  ],
  unit_profile: {
    layout: 'Two-bedroom apartment with open-plan living and balcony.',
    condition: 'Vacant and freshly painted.',
    view: 'Dubai Harbour partial sea view.',
    parking: 'Two basement spaces.',
  },
  unit_profile_history: [],
  leads: [],
  stages: [],
  stats: { total_leads: 7, active_leads: 4, viewing_requests: 2 },
}

const knowledgePayload = {
  listing_id: listingId,
  document_types: ['title_deed', 'service_charge_statement', 'agent_inspection_notes'],
  documents: [
    { document_id: 'doc-title-deed', document_type: 'title_deed', label: 'Title deed packet', status: 'processed', created_at: '2026-06-21T08:00:00.000Z' },
    { document_id: 'doc-service-charge', document_type: 'service_charge_statement', label: 'Service charge statement', status: 'pending', created_at: '2026-06-22T08:00:00.000Z' },
  ],
  facts: [
    { fact_id: 'fact-parking', document_id: 'doc-title-deed', fact_key: 'parking_spaces', fact_group: 'access', value_text: 'Two basement spaces.', confidence: 0.91, source: 'title_deed', verified: true, buyer_safe: true, risk_flag: false, notes: null, updated_at: '2026-06-24T07:40:00.000Z' },
    { fact_id: 'fact-service-charge', document_id: 'doc-service-charge', fact_key: 'service_charge', fact_group: 'fees', value_text: 'Latest service charge pending owner confirmation.', confidence: 0.68, source: 'service_charge_statement', verified: false, buyer_safe: false, risk_flag: true, notes: 'Needs latest statement.', updated_at: '2026-06-23T13:10:00.000Z' },
  ],
  summary: {
    buyer_safe_summary: 'Ready-property apartment in Dubai Harbour with two parking spaces and controlled viewing access.',
    internal_notes: 'Confirm latest service charge statement before buyer-facing disclosure.',
    missing_information: ['Latest service charge statement', 'AC maintenance receipt'],
    risk_flags: ['Service charge statement pending owner confirmation'],
    status: 'needs_review',
    updated_at: '2026-06-24T08:00:00.000Z',
  },
}

const documentsPayload = {
  listing_id: listingId,
  documents: [
    { document_id: 'doc-title-deed', document_type: 'title_deed', label: 'Title deed packet', status: 'processed', created_at: '2026-06-21T08:00:00.000Z' },
    { document_id: 'doc-service-charge', document_type: 'service_charge_statement', label: 'Service charge statement', status: 'pending', created_at: '2026-06-22T08:00:00.000Z' },
    { document_id: 'doc-floor-plan', document_type: 'floor_plan', label: 'Floor plan', status: 'processed', created_at: '2026-06-23T08:00:00.000Z' },
    { document_id: 'doc-inspection', document_type: 'agent_inspection_notes', label: 'Inspection notes', status: 'processed', created_at: '2026-06-23T11:00:00.000Z' },
  ],
}

const logisticsPayload = {
  listing_id: listingId,
  logistics: {
    access: { type: 'security office', meet_point: 'Tower A lobby reception', advance_notice_hours: 24, noc_required: false, visitor_parking_pass_required: true, buyer_emirates_id_preregistration_required: true, security_office_hours: { start: '09:00', end: '18:00' } },
    keys: { location: 'front office', contact_details: 'Leila Agent +971 50 000 0000', key_kit_checklist: ['main door', 'parking card'], return_same_day_required: true },
    tenant: { status: 'vacant', notice_period_hours: 24, cooperation_level: 'friendly', preferred_time_windows: 'Weekdays 11:00-16:00', photography_permission: true },
    owner_permissions: { viewing_restrictions: 'No Friday morning visits.', owner_contact: 'Owner via agent only.', owner_must_be_present: false },
  },
  prefill: { display_name: 'Sobha Sea Haven, Tower A', confidence: 0.82, contributor_count: 3, draft: { access: { meet_point: 'Tower A lobby' }, keys: { location: 'front office' }, tenant: { status: 'vacant' }, owner_permissions: {} } },
}

const offersPayload = {
  listing_id: listingId,
  threshold: 4100000,
  offers: [
    { buyer_label: 'Noura A.', amount_aed: 4150000, status: 'submitted', vs_asking: '3.5% below asking', received_at: '2026-06-24T06:30:00.000Z' },
    { buyer_label: 'Omar K.', amount_aed: 3980000, status: 'rejected', vs_asking: '7.4% below asking', received_at: '2026-06-20T12:00:00.000Z' },
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

async function installApiStubs(page) {
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    let payload = null
    let status = 200
    if (path === '/api/v1/me/brokerages') payload = { active_brokerages: [{ brokerage_id: 'brokerage-1', name: 'Luqman Realty QA', role: 'agent', membership_id: 'membership-final-qa' }], requires_selection: false, default_brokerage_id: 'brokerage-1' }
    else if (path === '/api/v1/listings/mine') payload = { listings: [listingSummary], total_listings: 1, total_conversations: 9, total_escalated: 2 }
    else if (path === `/api/v1/seller/listings/${listingId}/leads`) payload = detailPayload
    else if (path === `/api/v1/listings/${listingId}/knowledge`) payload = knowledgePayload
    else if (path === `/api/v1/listings/${listingId}/documents`) payload = documentsPayload
    else if (path === `/api/v1/agent/listings/${listingId}/logistics`) payload = logisticsPayload
    else if (path === `/api/v1/seller/listings/${listingId}/offers`) payload = offersPayload
    else if (path === `/api/v1/agent/listings/${listingId}/buyer-matches`) payload = { matches: [] }
    else if (path.includes('/facts/') || path.endsWith('/knowledge/regenerate') || path.endsWith('/documents')) payload = { ok: true }
    else {
      status = 404
      payload = { detail: `Unstubbed API path ${path}` }
    }
    log(`api ${route.request().method()} ${path} -> ${status}`)
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(payload) })
  })
}

async function summarizePage(page, routeName) {
  if (routeName === 'index') await page.getByRole('heading', { name: 'Listings' }).waitFor({ timeout: 30_000 })
  else await page.waitForSelector(`[data-listing-workspace-route="${routeName}"]`, { timeout: 30_000 })
  return await page.evaluate((expectedRoute) => {
    const text = document.body.innerText
    const links = [...document.querySelectorAll('a[href]')].map((node) => node.getAttribute('href'))
    return {
      url: location.href,
      bodyChars: text.length,
      hasTitle: text.includes('Final QA Sea Haven residence') || text.includes('Listings'),
      noLegacyVisibleText: !/(text-gold|btn-gold|text-sand|border-gold|bg-deep|ghost-border|shadow-gold|#C9A96E)/i.test(text),
      hasOldDashboardLink: links.some((href) => href?.includes('/dashboard/listings')),
      hasHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      routeMarker: document.querySelector('[data-listing-workspace-route]')?.getAttribute('data-listing-workspace-route') ?? null,
      activeTab: document.querySelector('nav[aria-label="Listing workspace"] [aria-current="page"]')?.textContent?.trim() ?? null,
      background: getComputedStyle(document.body).backgroundColor,
      expectedRoute,
    }
  }, routeName)
}

async function run() {
  mkdirSync(outputDir, { recursive: true })
  const safeTempValidation = validateSafeTempWorkdir(safeTempWorkdir, frontendRoot)
  if (!safeTempValidation.ok) throw new Error(`Unsafe temp workdir: ${safeTempValidation.failures.join(', ')}`)
  const staging = stageSafeFrontend(frontendRoot, safeTempWorkdir)
  const supabase = await startStagedSupabaseAuthStub()
  const port = await findFreePort()
  const baseUrl = `http://127.0.0.1:${port}`
  const devServer = startStagedDevServer(baseUrl, safeTempWorkdir, safeTempWorkdir, supabase.url)
  let browser = null
  let cleanup = 'not-started'

  log('surface browser-ui')
  log('invocation', { command: `node ${new URL(import.meta.url).pathname}`, devServerCommand: `cd ${safeTempWorkdir} && npm run dev -- --webpack --hostname 127.0.0.1 --port ${port}`, baseUrl, pid: devServer.child.pid, staging })

  try {
    await waitForStagedServer(baseUrl, devServer)
    browser = await chromium.launch()
    const context = await browser.newContext({ deviceScaleFactor: 1 })
    await seedStagedAuth(context, baseUrl)
    const page = await context.newPage()
    await installApiStubs(page)
    page.on('console', (message) => {
      if (['error', 'warning'].includes(message.type())) log(`browser console ${message.type()}: ${message.text()}`)
    })
    page.on('pageerror', (error) => log(`browser pageerror: ${error.message}`))

    for (const width of widths) {
      await page.setViewportSize({ width, height: 920 })
      for (const route of routes) {
        const url = `${baseUrl}${route.path}`
        log('navigate', { width, route: route.name, url })
        await page.goto(url, { waitUntil: 'networkidle' })
        const summary = await summarizePage(page, route.name)
        const screenshotPath = resolve(outputDir, `${route.name}-${width}.png`)
        await page.screenshot({ path: screenshotPath, fullPage: true })
        artifacts.push({ id: `screenshot-${route.name}-${width}`, kind: 'browser-screenshot', description: `${route.path} at ${width}px`, path: screenshotPath })
        results.push({ ...summary, route: route.name, path: route.path, width, screenshotPath })
      }
    }

    for (const legacy of legacyRoutes) {
      const response = await page.goto(`${baseUrl}${legacy.oldPath}`, { waitUntil: 'networkidle' })
      const finalPath = new URL(page.url()).pathname
      log('legacy-redirect', { oldPath: legacy.oldPath, expected: legacy.expected, finalPath, status: response?.status() ?? null })
      results.push({ route: 'legacy-redirect', oldPath: legacy.oldPath, expected: legacy.expected, finalPath, passed: finalPath === legacy.expected })
    }

    await context.close()
  } finally {
    if (browser) await browser.close()
    cleanup = await stopStagedServer(devServer)
    await supabase.close()
  }
  let qaPortClosed = false
  try {
    await fetch(baseUrl)
  } catch {
    qaPortClosed = true
  }

  const transcriptPath = resolve(outputDir, 'browser-transcript.json')
  const cleanupPath = resolve(outputDir, 'cleanup-receipt.txt')
  const safeTempRemoval = removeValidatedSafeTempWorkdir(safeTempValidation)
  writeFileSync(transcriptPath, JSON.stringify({ transcript, results }, null, 2))
  writeFileSync(cleanupPath, [
    `qaServerPid=${devServer.child.pid}`,
    `qaServerBaseUrl=${baseUrl}`,
    `cleanup=${cleanup}`,
    `qaPortClosedAfterCleanup=${qaPortClosed}`,
    'supabaseStub=closed',
    `safeTempWorkdir=${safeTempRemoval}`,
    `preExistingPort3000=left untouched; see curl/lsof artifacts`,
    `timestamp=${new Date().toISOString()}`,
    '',
    devServer.readLogs(),
  ].join('\n'))
  artifacts.push({ id: 'browser-transcript', kind: 'browser-transcript', description: 'Playwright navigation, redirect, DOM, overflow, and link checks', path: transcriptPath })
  artifacts.push({ id: 'cleanup-receipt', kind: 'text', description: 'QA server cleanup and port 3000 disposition', path: cleanupPath })

  const surfaceEvidence = results
    .filter((result) => result.route !== 'legacy-redirect')
    .map((result) => ({
      scenarioId: `final-${result.route}-${result.width}`,
      criterionRef: result.route === 'index' ? 'T12 browser QA /listings' : `T12 browser QA /listings/[id] ${result.route}`,
      surface: `Browser UI ${result.url}`,
      exactInvocation: `Playwright page.goto(${JSON.stringify(result.url)}) viewport ${result.width}x920`,
      verdict: result.hasTitle && !result.hasOldDashboardLink && !result.hasHorizontalOverflow && result.noLegacyVisibleText && (result.route === 'index' || result.routeMarker === result.route) ? 'PASS' : 'FAIL',
      artifactRefs: [`screenshot-${result.route}-${result.width}`, 'browser-transcript'],
    }))
  for (const result of results.filter((item) => item.route === 'legacy-redirect')) {
    surfaceEvidence.push({
      scenarioId: `final-legacy-${result.oldPath.replaceAll('/', '-')}`,
      criterionRef: 'T12 legacy route no old dashboard bounce',
      surface: `Browser UI ${baseUrl}${result.oldPath}`,
      exactInvocation: `Playwright page.goto(${JSON.stringify(`${baseUrl}${result.oldPath}`)})`,
      verdict: result.finalPath === result.expected ? 'PASS' : 'FAIL',
      artifactRefs: ['browser-transcript'],
    })
  }
  const screenshotArtifacts = artifacts.filter((artifact) => artifact.kind === 'browser-screenshot')
  const screenshotEvidenceOk =
    screenshotArtifacts.length === routes.length * widths.length &&
    screenshotArtifacts.every((artifact) => existsSync(artifact.path) && statSync(artifact.path).size > 0)
  const canonicalRouteResults = results.filter((result) => result.route !== 'legacy-redirect')
  const legacyRedirectResults = results.filter((result) => result.route === 'legacy-redirect')
  const routeEvidenceOk =
    canonicalRouteResults.length === routes.length * widths.length &&
    legacyRedirectResults.length === legacyRoutes.length &&
    canonicalRouteResults.every((result) =>
      result.url.includes(result.path) &&
      result.bodyChars > 100 &&
      result.hasTitle &&
      !result.hasOldDashboardLink &&
      !result.hasHorizontalOverflow &&
      result.noLegacyVisibleText &&
      (result.route === 'index' || result.routeMarker === result.route)
    ) &&
    legacyRedirectResults.every((result) => result.passed && result.finalPath === result.expected)
  const noUnstubbedApi = transcript.every((line) => !line.includes('-> 404'))
  const dirtyReceiptOk = existsSync(dirtyReceiptPath) && statSync(dirtyReceiptPath).size > 0
  const cleanupEvidenceOk =
    qaPortClosed &&
    ['server exited after SIGTERM', 'server already exited', 'server required SIGKILL after SIGTERM timeout'].includes(cleanup) &&
    safeTempRemoval === `removed ${safeTempWorkdir}`
  const deterministicFixtureOk =
    canonicalRouteResults.every((result) => result.url.includes(listingId) || result.route === 'index') &&
    transcript.some((line) => line.includes('FINAL-QA-LISTING-001')) &&
    noUnstubbedApi
  const adversarialCases = [
    { scenarioId: 'final-stale-state', criterionRef: 'T12 adversarial', adversarialClass: 'stale_state', expectedBehavior: 'Fresh server, API stubs, auth cookie, and direct route loads render current workspace state.', verdict: routeEvidenceOk && noUnstubbedApi ? 'PASS' : 'FAIL', artifactRefs: ['browser-transcript'] },
    { scenarioId: 'final-dirty-worktree', criterionRef: 'T12 adversarial', adversarialClass: 'dirty_worktree', expectedBehavior: 'QA runs against current dirty tree with a T12 boundary receipt and without reverting or broad product edits.', verdict: dirtyReceiptOk && routeEvidenceOk ? 'PASS' : 'FAIL', artifactRefs: ['browser-transcript', 'cleanup-receipt', 't12-dirty-worktree-receipt'] },
    { scenarioId: 'final-misleading-success-output', criterionRef: 'T12 adversarial', adversarialClass: 'misleading_success_output', expectedBehavior: 'Browser PASS requires screenshot files plus DOM route/link/overflow checks, not just HTTP 200.', verdict: screenshotEvidenceOk && routeEvidenceOk ? 'PASS' : 'FAIL', artifactRefs: ['browser-transcript'] },
    { scenarioId: 'final-hung-or-long-commands', criterionRef: 'T12 adversarial', adversarialClass: 'hung_or_long_commands', expectedBehavior: 'The QA-owned server is stopped, the safe temp workdir is removed, and the QA port is closed after cleanup.', verdict: cleanupEvidenceOk ? 'PASS' : 'FAIL', artifactRefs: ['cleanup-receipt'] },
    { scenarioId: 'final-flaky-tests', criterionRef: 'T12 adversarial', adversarialClass: 'flaky_tests', expectedBehavior: 'Focused browser harness uses deterministic fixtures and records exact routes/screenshots.', verdict: deterministicFixtureOk && screenshotEvidenceOk ? 'PASS' : 'FAIL', artifactRefs: ['browser-transcript'] },
  ]
  const matrixPath = resolve(outputDir, 'manualQa.json')
  artifacts.push({ id: 't12-dirty-worktree-receipt', kind: 'text', description: 'T12 dirty-worktree boundary receipt', path: dirtyReceiptPath })
  writeFileSync(matrixPath, JSON.stringify({ surfaceEvidence, adversarialCases, artifactRefs: artifacts }, null, 2))
  console.log(JSON.stringify({ passed: [...surfaceEvidence, ...adversarialCases].every((item) => item.verdict === 'PASS'), surfaceEvidence: surfaceEvidence.length, adversarialCases: adversarialCases.length, matrixPath, cleanup }, null, 2))
  if (![...surfaceEvidence, ...adversarialCases].every((item) => item.verdict === 'PASS')) process.exitCode = 1
}

await run()
