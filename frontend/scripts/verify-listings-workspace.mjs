import { lstatSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')
const paths = {
  actions: resolve(frontendRoot, 'src/components/listings/listingIndexActions.ts'),
  controls: resolve(frontendRoot, 'src/components/listings/AgentListingsControls.tsx'),
  index: resolve(frontendRoot, 'src/components/listings/AgentListingsIndex.tsx'),
  table: resolve(frontendRoot, 'src/components/listings/AgentListingsTable.tsx'),
}
const scanRoots = ['src/components/listings', 'src/app/(app)/listings'].map((path) => resolve(frontendRoot, path))
const fixedNowMs = Date.parse('2026-06-24T12:00:00+04:00')

function check(condition, label, details = {}) {
  if (!condition) throw new Error(`${label}: ${JSON.stringify(details)}`)
  return { label, passed: true, details }
}

function read(path) {
  return readFileSync(path, 'utf8')
}

function compileActions() {
  const output = ts.transpileModule(read(paths.actions), {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      strict: true,
      verbatimModuleSyntax: true,
    },
    fileName: paths.actions,
    reportDiagnostics: true,
  })
  const diagnostics = output.diagnostics ?? []
  if (diagnostics.length > 0) {
    throw new Error(diagnostics.map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')).join('\n'))
  }
  const tempDir = mkdtempSync(join(tmpdir(), 'dalya-listing-actions-'))
  const compiledPath = join(tempDir, 'listingIndexActions.mjs')
  writeFileSync(compiledPath, output.outputText)
  return { compiledPath, tempDir }
}

function compileInventoryView() {
  const source = read(paths.index)
  const start = source.indexOf('interface InventoryView')
  const end = source.indexOf('\nfunction Metric', start)
  if (start === -1 || end === -1) {
    throw new Error('Unable to extract inventory view helpers from AgentListingsIndex.tsx')
  }
  const helperSource = source.slice(start, end).replace('\nfunction applyInventoryView', '\nexport function applyInventoryView')
  const output = ts.transpileModule(helperSource, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
      strict: true,
      verbatimModuleSyntax: true,
    },
    fileName: paths.index,
    reportDiagnostics: true,
  })
  const diagnostics = output.diagnostics ?? []
  if (diagnostics.length > 0) {
    throw new Error(diagnostics.map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')).join('\n'))
  }
  const tempDir = mkdtempSync(join(tmpdir(), 'dalya-listing-inventory-view-'))
  const compiledPath = join(tempDir, 'inventoryView.mjs')
  writeFileSync(compiledPath, output.outputText)
  return { compiledPath, tempDir, helperSource }
}

function listing(overrides) {
  return {
    id: 'listing-default',
    title: 'Default Listing',
    property_type: 'ready',
    community: null,
    subcommunity: null,
    building_or_project: null,
    unit_number: null,
    status: 'live',
    asking_price_aed: null,
    created_at: '2026-06-01T08:00:00+04:00',
    last_activity_at: null,
    knowledge_status: 'ready',
    logistics_status: 'ready',
    missing_fact_count: 0,
    buyer_conversation_count: 0,
    active_viewing_count: 0,
    open_offer_count: 0,
    primary_next_action: 'open_listing',
    ...overrides,
  }
}

const rows = [
  listing({
    id: 'listing-knowledge',
    title: 'Canal View Apartment',
    community: 'Business Bay',
    building_or_project: 'Bay Tower',
    unit_number: '1201',
    asking_price_aed: 2_400_000,
    created_at: '2026-06-02T08:00:00+04:00',
    last_activity_at: '2026-06-18T10:00:00+04:00',
    buyer_conversation_count: 3,
    knowledge_status: 'needs_attention',
    missing_fact_count: 2,
    primary_next_action: 'review_knowledge',
  }),
  listing({
    id: 'listing-logistics',
    title: 'Palm Villa',
    community: 'Palm Jumeirah',
    asking_price_aed: 10_500_000,
    created_at: '2026-06-03T08:00:00+04:00',
    last_activity_at: '2026-06-21T10:00:00+04:00',
    active_viewing_count: 2,
    open_offer_count: 1,
    logistics_status: 'needs_attention',
    primary_next_action: 'set_logistics',
  }),
  listing({
    id: 'listing-offplan',
    title: 'Creek Launch Residence',
    property_type: 'off_plan',
    community: 'Dubai Creek Harbour',
    status: 'draft',
    asking_price_aed: 1_900_000,
    created_at: '2026-06-04T08:00:00+04:00',
    last_activity_at: '2026-05-01T10:00:00+04:00',
  }),
]

function ids(listings) {
  return listings.map((item) => item.id).join(',')
}

function collectFiles(root) {
  return readdirSync(root).sort().flatMap((entry) => {
    const path = resolve(root, entry)
    const stats = lstatSync(path)
    if (stats.isSymbolicLink()) return []
    if (stats.isDirectory()) return collectFiles(path)
    return /\.(tsx?|jsx?|mjs)$/.test(path) ? [path] : []
  })
}

function assertNoLegacyDashboardListingHrefs(files) {
  const offenders = files.filter((path) => read(path).includes('/dashboard/listings'))
  if (offenders.length > 0) throw new Error(`Legacy dashboard listing hrefs found: ${offenders.join(', ')}`)
}

function captureExpectedFailure(run) {
  try {
    run()
    return null
  } catch (error) {
    if (!(error instanceof Error)) throw error
    return error.message
  }
}

const actionModule = compileActions()
const inventoryModule = compileInventoryView()
const originalDateNow = Date.now
try {
  Date.now = () => fixedNowMs
  const { SUPPORTED_INDEX_ACTIONS, nextActionForListing } = await import(pathToFileURL(actionModule.compiledPath).href)
  const { applyInventoryView } = await import(pathToFileURL(inventoryModule.compiledPath).href)
  const view = (search, statusFilter, attentionFilter, sort) => ids(applyInventoryView(rows, { search, statusFilter, attentionFilter, sort }))
  const actionCases = {
    review_knowledge: '/listings/listing-1/knowledge',
    set_logistics: '/listings/listing-1/logistics',
    manage_viewings: '/listings/listing-1/logistics',
    review_offers: '/listings/listing-1/offers',
    review_documents: '/listings/listing-1/documents',
    upload_documents: '/listings/listing-1/documents',
    follow_up_buyers: '/listings/listing-1',
    open_listing: '/listings/listing-1',
  }
  const actionChecks = Object.entries(actionCases).map(([action, href]) =>
    check(nextActionForListing({ id: 'listing-1', primary_next_action: action }).href === href, `action ${action} maps to canonical workspace href`, { href }),
  )
  const probeDir = mkdtempSync(join(tmpdir(), 'dalya-legacy-href-probe-'))
  const probePath = join(probeDir, 'probe.tsx')
  let legacyProbeMessage
  try {
    writeFileSync(probePath, '<Link href="/dashboard/listings/listing-1">Legacy</Link>')
    legacyProbeMessage = captureExpectedFailure(() => assertNoLegacyDashboardListingHrefs([probePath]))
  } finally {
    rmSync(probeDir, { recursive: true, force: true })
  }
  const unsupportedActionMessage = captureExpectedFailure(() => nextActionForListing({ id: 'listing-1', primary_next_action: 'open_legacy_dashboard' }))

  const sourceFiles = scanRoots.flatMap(collectFiles)
  assertNoLegacyDashboardListingHrefs(sourceFiles)
  const indexSource = read(paths.index)
  const controlsSource = read(paths.controls)
  const tableSource = read(paths.table)
  const checks = [
    ...actionChecks,
    check(view('bay tower', 'all', 'all', 'last_activity') === 'listing-knowledge', 'search matches building/project fields'),
    check(view('LISTING-OFFPLAN', 'all', 'all', 'last_activity') === 'listing-offplan', 'search matches listing id case-insensitively'),
    check(view('', 'ready', 'all', 'created') === 'listing-logistics,listing-knowledge', 'ready status filter uses property type'),
    check(view('', 'draft', 'all', 'created') === 'listing-offplan', 'draft status filter uses listing status'),
    check(view('', 'all', 'attention', 'last_activity') === 'listing-logistics,listing-knowledge', 'attention filter catches knowledge and logistics work'),
    check(view('', 'all', 'buyers', 'buyers') === 'listing-knowledge', 'buyers filter catches active buyer conversations'),
    check(view('', 'all', 'offers', 'offers') === 'listing-logistics', 'offers filter catches open offers'),
    check(view('', 'all', 'viewings', 'viewings') === 'listing-logistics', 'viewings filter catches active viewings'),
    check(view('', 'all', 'recent', 'last_activity') === 'listing-logistics,listing-knowledge', 'recent filter is bounded to seeded timestamps'),
    check(view('', 'all', 'all', 'price').startsWith('listing-logistics'), 'price sort puts highest asking price first'),
    check(view('', 'all', 'all', 'not-supported').startsWith('listing-logistics'), 'unsupported sort falls back to last activity'),
    check(inventoryModule.helperSource.includes('matchesSearch') && inventoryModule.helperSource.includes('matchesStatus') && inventoryModule.helperSource.includes('matchesAttention') && inventoryModule.helperSource.includes('compareListings'), 'extracted inventory helper source wires search, filters, and sort'),
    check(controlsSource.includes("return 'all'") && controlsSource.includes("return 'last_activity'"), 'control parsers default unsupported values safely'),
    check(tableSource.includes('href={`/listings/${listing.id}`}') && !tableSource.includes('/dashboard/listings'), 'row open links use canonical workspace hrefs'),
    check(SUPPORTED_INDEX_ACTIONS.length === Object.keys(actionCases).length, 'all supported action variants are covered by verifier'),
    check(unsupportedActionMessage?.includes('Unsupported listing index action'), 'unsupported action fails loudly', { unsupportedActionMessage }),
    check(legacyProbeMessage?.includes('Legacy dashboard listing hrefs found'), 'legacy href scanner fails on injected old href', { legacyProbeMessage }),
  ]
  console.log(JSON.stringify({
    scenario: 'Task 9 listings workspace inventory verifier',
    invocation: 'cd frontend && node scripts/verify-listings-workspace.mjs',
    binaryObservable: { actionCases: actionChecks.length, checks: checks.length, scannedFiles: sourceFiles.map((path) => path.replace(`${frontendRoot}/`, '')) },
    checks,
  }, null, 2))
} finally {
  Date.now = originalDateNow
  rmSync(actionModule.tempDir, { recursive: true, force: true })
  rmSync(inventoryModule.tempDir, { recursive: true, force: true })
}
