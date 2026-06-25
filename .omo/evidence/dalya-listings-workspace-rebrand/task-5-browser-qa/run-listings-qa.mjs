import { createRequire } from 'node:module'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve, relative } from 'node:path'
import {
  defaultFrontendRoot,
} from '../../../../frontend/scripts/final-surface-constants.mjs'
import {
  removeValidatedSafeTempWorkdir,
  sanitizedEnv,
  scanEnvFiles,
  stageSafeFrontend,
  validateSafeTempWorkdir,
} from '../../../../frontend/scripts/final-surface-safe-env.mjs'
import {
  seedAuth,
  startDevServer,
  startSupabaseAuthStub,
  stopServer,
  waitForServer,
} from '../../../../frontend/scripts/final-surface-server.mjs'

const repoRoot = resolve(import.meta.dirname, '../../../..')
const evidenceDir = resolve(repoRoot, '.omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa')
const safeTempWorkdir = '/private/tmp/dalya-final-surface-listings-qa'
const baseUrl = 'http://127.0.0.1:3197'
const invocation = 'node .omo/evidence/dalya-listings-workspace-rebrand/task-5-browser-qa/run-listings-qa.mjs'
const requireFromFrontend = createRequire(resolve(defaultFrontendRoot, 'package.json'))
const { chromium } = requireFromFrontend('@playwright/test')

function jsonResponse(body, status = 200) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  }
}

function listingPayload() {
  return {
    listings: [
      {
        id: 'lst-ready-dubai-hills-001',
        title: 'Sidra upgraded five bedroom villa',
        property_type: 'ready',
        community: 'Dubai Hills Estate',
        subcommunity: 'Sidra 1',
        building_or_project: 'Sidra Villas',
        unit_number: 'V-42',
        bedrooms: 5,
        bathrooms: 6,
        size_sqft: 4628,
        asking_price_aed: 14250000,
        price_per_sqft_aed: 3079,
        status: 'live',
        lead_count: 9,
        escalated_count: 3,
        source_url: null,
        first_image_url: null,
        reference_document_count: 4,
        created_at: '2026-06-14T08:00:00+04:00',
        last_activity_at: '2026-06-24T09:20:00+04:00',
        assigned_agent_name: 'Leila Agent',
        knowledge_status: 'needs_attention',
        missing_fact_count: 3,
        active_viewing_count: 2,
        open_offer_count: 1,
        buyer_conversation_count: 12,
        logistics_status: 'needs_attention',
        primary_next_action: 'review_knowledge',
      },
      {
        id: 'lst-offplan-oasis-002',
        title: 'Emaar Oasis four bedroom villa',
        property_type: 'off_plan',
        community: 'The Oasis by Emaar',
        subcommunity: 'Palmiera',
        building_or_project: 'Palmiera 2',
        unit_number: 'P2-118',
        bedrooms: 4,
        bathrooms: 5,
        size_sqft: 3840,
        asking_price_aed: 9800000,
        price_per_sqft_aed: 2552,
        status: 'live',
        lead_count: 5,
        escalated_count: 1,
        source_url: null,
        first_image_url: null,
        reference_document_count: 2,
        created_at: '2026-06-11T11:30:00+04:00',
        last_activity_at: '2026-06-23T18:10:00+04:00',
        assigned_agent_name: 'Omar Faris',
        knowledge_status: 'ready',
        missing_fact_count: 0,
        active_viewing_count: 0,
        open_offer_count: 2,
        buyer_conversation_count: 7,
        logistics_status: 'ready',
        primary_next_action: 'review_offers',
      },
      {
        id: 'lst-ready-marina-003',
        title: 'Marina Gate two bedroom apartment',
        property_type: 'ready',
        community: 'Dubai Marina',
        subcommunity: 'Marina Gate',
        building_or_project: 'Marina Gate 1',
        unit_number: '2805',
        bedrooms: 2,
        bathrooms: 3,
        size_sqft: 1352,
        asking_price_aed: 3420000,
        price_per_sqft_aed: 2529,
        status: 'draft',
        lead_count: 2,
        escalated_count: 0,
        source_url: null,
        first_image_url: null,
        reference_document_count: 1,
        created_at: '2026-06-20T15:45:00+04:00',
        last_activity_at: '2026-06-21T12:00:00+04:00',
        assigned_agent_name: null,
        knowledge_status: 'ready',
        missing_fact_count: 0,
        active_viewing_count: 1,
        open_offer_count: 0,
        buyer_conversation_count: 2,
        logistics_status: 'needs_attention',
        primary_next_action: 'set_logistics',
      },
    ],
    total_listings: 3,
    total_conversations: 21,
    total_escalated: 4,
  }
}

async function installMocks(page) {
  await page.route('**/api/v1/me/brokerages', (route) => route.fulfill(jsonResponse({
    active_brokerages: [{ brokerage_id: 'brokerage-1', name: 'Luqman Realty', role: 'agent', membership_id: 'membership-1' }],
    requires_selection: false,
    default_brokerage_id: 'brokerage-1',
  })))
  await page.route('**/api/v1/listings/mine', (route) => route.fulfill(jsonResponse(listingPayload())))
  await page.route('https://test.supabase.co/**', (route) => route.fulfill(jsonResponse({})))
}

function check(condition, label, details = {}) {
  const result = { label, passed: Boolean(condition), details }
  return result
}

async function pageSummary(page) {
  return await page.evaluate(() => {
    const links = [...document.querySelectorAll('a[href]')].map((node) => node.getAttribute('href'))
    const bodyText = document.body.innerText
    const overflowing = [...document.querySelectorAll('body *')]
      .map((node) => {
        const element = node
        const rect = element.getBoundingClientRect()
        return {
          tag: element.tagName.toLowerCase(),
          text: (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
          rect: { left: rect.left, right: rect.right, width: rect.width },
        }
      })
      .filter((item) => item.rect.right > document.documentElement.clientWidth + 1 || item.rect.left < -1)
      .slice(0, 20)
    return {
      url: location.href,
      title: document.title,
      bodyText,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      viewportHorizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      links,
      overflowing,
    }
  })
}

async function captureViewport(context, width, checks, captures, observations) {
  const page = await context.newPage()
  await installMocks(page)
  await page.setViewportSize({ width, height: 900 })
  await page.goto(`${baseUrl}/listings`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: 'Listings' }).waitFor({ timeout: 30_000 })
  await page.waitForFunction(() => document.body.innerText.includes('Sidra upgraded five bedroom villa'), null, { timeout: 30_000 })
  await page.evaluate(() => document.fonts?.ready)

  const summary = await pageSummary(page)
  const badgeMetrics = await page.evaluate(() => {
    return [...document.querySelectorAll('span')]
      .map((node) => {
        const element = node
        const text = (element.innerText || element.textContent || '').trim().replace(/\s+/g, ' ')
        const rect = element.getBoundingClientRect()
        return {
          text,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
          overflowX: getComputedStyle(element).overflowX,
        }
      })
      .filter((item) => /Knowledge|Logistics|missing facts/.test(item.text))
  })
  observations.push({
    width,
    clientWidth: summary.clientWidth,
    scrollWidth: summary.scrollWidth,
    viewportHorizontalOverflow: summary.viewportHorizontalOverflow,
    badgeMetrics,
  })
  const screenshotPath = resolve(evidenceDir, `listings-${width}.png`)
  await page.screenshot({ path: screenshotPath, fullPage: true })
  captures.push({
    id: `screenshot-${width}`,
    kind: 'screenshot',
    description: `/listings populated command center at ${width}px width`,
    path: screenshotPath,
  })

  const requiredText = [
    'Inventory command center',
    'Search',
    'Status',
    'Work',
    'Sort',
    'Sidra upgraded five bedroom villa',
    'Live',
    'Ready property',
    'Dubai Hills Estate',
    'AED 14,250,000',
    'Leila Agent',
    '12 conversations',
    'Knowledge needs attention',
    '3 missing facts',
    'Logistics needs attention',
    '2 viewings',
    '1 offers',
    'Review knowledge',
  ]
  const lowerBodyText = summary.bodyText.toLowerCase()
  for (const text of requiredText) {
    checks.push(check(lowerBodyText.includes(text.toLowerCase()), `${width}px includes ${text}`))
  }

  const dashboardLinks = summary.links.filter((href) => href?.includes('/dashboard/listings'))
  checks.push(check(dashboardLinks.length === 0, `${width}px has no /dashboard/listings links`, { dashboardLinks }))
  const canonicalLinks = summary.links.filter((href) => href?.startsWith('/listings/lst-'))
  checks.push(check(canonicalLinks.includes('/listings/lst-ready-dubai-hills-001/knowledge'), `${width}px exposes knowledge next-action route`, { canonicalLinks }))
  checks.push(check(canonicalLinks.includes('/listings/lst-offplan-oasis-002/offers'), `${width}px exposes offers next-action route`, { canonicalLinks }))
  checks.push(check(canonicalLinks.includes('/listings/lst-ready-marina-003/logistics'), `${width}px exposes logistics next-action route`, { canonicalLinks }))
  checks.push(check(!summary.viewportHorizontalOverflow, `${width}px has no page-level horizontal overflow`, {
    clientWidth: summary.clientWidth,
    scrollWidth: summary.scrollWidth,
    overflowing: summary.overflowing,
  }))
  const clippedBadges = badgeMetrics.filter((item) => item.scrollWidth > item.clientWidth + 1)
  checks.push(check(clippedBadges.length === 0, `${width}px readiness badges are not visually clipped`, { clippedBadges }))

  await page.getByPlaceholder('Title, community, unit, listing id').fill('no-result-token')
  await page.getByText('No listings match these filters.').waitFor({ timeout: 10_000 })
  const noResultsSummary = await pageSummary(page)
  checks.push(check(noResultsSummary.bodyText.includes('Adjust search, status, attention, or activity filters.'), `${width}px no-results state renders after unmatched search`))
  if (width === 375) {
    const noResultsPath = resolve(evidenceDir, 'listings-375-no-results.png')
    await page.screenshot({ path: noResultsPath, fullPage: true })
    captures.push({
      id: 'screenshot-375-no-results',
      kind: 'screenshot',
      description: '/listings no-results state at 375px width after unmatched search',
      path: noResultsPath,
    })
  }

  await page.close()
}

function sourceStateEvidence(checks, captures) {
  const agentIndex = readFileSync(resolve(defaultFrontendRoot, 'src/components/listings/AgentListingsIndex.tsx'), 'utf8')
  const table = readFileSync(resolve(defaultFrontendRoot, 'src/components/listings/AgentListingsTable.tsx'), 'utf8')
  const controls = readFileSync(resolve(defaultFrontendRoot, 'src/components/listings/AgentListingsControls.tsx'), 'utf8')
  const sourceReceiptPath = resolve(evidenceDir, 'source-state-receipt.json')
  const sourceChecks = {
    loadingState: agentIndex.includes('function LoadingState()') && agentIndex.includes('aria-label="Loading listings"'),
    errorState: agentIndex.includes('function ErrorState') && agentIndex.includes('role="alert"'),
    emptyState: agentIndex.includes('function EmptyState') && agentIndex.includes('No listings added yet'),
    noResultsState: agentIndex.includes('function NoResultsState') && agentIndex.includes('No listings match these filters.'),
    canonicalLinksOnly: table.includes('href={`/listings/${listing.id}`') && !table.includes('/dashboard/listings'),
    controls: controls.includes('label="Status"') && controls.includes('label="Work"') && controls.includes('label="Sort"'),
  }
  for (const [label, passed] of Object.entries(sourceChecks)) {
    checks.push(check(passed, `source has ${label}`))
  }
  writeFileSync(sourceReceiptPath, `${JSON.stringify(sourceChecks, null, 2)}\n`)
  captures.push({
    id: 'source-state-receipt',
    kind: 'transcript',
    description: 'Source-level receipt for loading/error/empty/no-results states and canonical links',
    path: sourceReceiptPath,
  })
}

async function main() {
  mkdirSync(evidenceDir, { recursive: true })
  const safeTempValidation = validateSafeTempWorkdir(safeTempWorkdir, defaultFrontendRoot)
  if (!safeTempValidation.ok) {
    throw new Error(`Unsafe temp workdir: ${safeTempValidation.failures.join(', ')}`)
  }

  const transcript = {
    scenario: 'T5 visual/manual QA for /listings inventory index',
    invocation,
    surface: `${baseUrl}/listings on staged frontend copy`,
    server: {
      preExistingServerUsed: false,
      startedServer: true,
      baseUrl,
      serverCwd: safeTempWorkdir,
    },
    env: {
      policy: 'sanitized local QA env; values not recorded',
      fixtureFrontendRoot: defaultFrontendRoot,
      sourceEnvFiles: scanEnvFiles(defaultFrontendRoot),
    },
    checks: [],
    captures: [],
    observations: [],
    cleanup: {},
  }

  let server = null
  let supabaseStub = null
  let browser = null
  try {
    transcript.staging = stageSafeFrontend(defaultFrontendRoot, safeTempWorkdir)
    supabaseStub = await startSupabaseAuthStub()
    transcript.env.names = Object.keys(sanitizedEnv(supabaseStub.url, safeTempWorkdir))
    server = startDevServer(baseUrl, safeTempWorkdir, safeTempWorkdir, supabaseStub.url)
    await waitForServer(baseUrl, server)

    sourceStateEvidence(transcript.checks, transcript.captures)
    browser = await chromium.launch()
    const context = await browser.newContext({ deviceScaleFactor: 1 })
    await seedAuth(context, baseUrl)
    for (const width of [1280, 768, 375]) {
      await captureViewport(context, width, transcript.checks, transcript.captures, transcript.observations)
    }
    await context.close()
    transcript.passed = transcript.checks.every((item) => item.passed)
  } catch (error) {
    transcript.passed = false
    transcript.failure = {
      message: error instanceof Error ? error.message : String(error),
      failedCheck: error?.check ?? null,
      nextDevLogTail: server?.readLogs() ?? '',
    }
    process.exitCode = 1
  } finally {
    if (browser) await browser.close()
    transcript.cleanup.server = await stopServer(server)
    if (supabaseStub) {
      await supabaseStub.close()
      transcript.cleanup.supabaseStub = 'closed'
    }
    if (existsSync(safeTempWorkdir)) {
      transcript.cleanup.safeTempWorkdir = removeValidatedSafeTempWorkdir(safeTempValidation)
    }
    transcript.cleanup.receipt = 'Browser/context closed; Next dev server stopped; local Supabase auth stub closed; safe temp frontend removed.'
    transcript.artifactPaths = transcript.captures.map((item) => relative(repoRoot, item.path))
    writeFileSync(resolve(evidenceDir, 'transcript.json'), `${JSON.stringify(transcript, null, 2)}\n`)
    console.log(JSON.stringify({
      passed: transcript.passed,
      checks: transcript.checks.length,
      captures: transcript.captures.length,
      transcriptPath: resolve(evidenceDir, 'transcript.json'),
      cleanup: transcript.cleanup,
    }, null, 2))
  }
}

await main()
