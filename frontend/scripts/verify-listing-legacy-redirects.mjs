import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(scriptDir, '..')
const routeRoot = resolve(frontendRoot, 'src/app/(app)/dashboard/listings/[id]')
const sampleId = 'legacy-smoke-listing-123'

const routeChecks = [
  {
    oldPath: `/dashboard/listings/${sampleId}`,
    file: 'page.tsx',
    targetTemplate: '/listings/${id}',
    finalUrl: `/listings/${sampleId}`,
  },
  {
    oldPath: `/dashboard/listings/${sampleId}/knowledge`,
    file: 'knowledge/page.tsx',
    targetTemplate: '/listings/${id}/knowledge',
    finalUrl: `/listings/${sampleId}/knowledge`,
  },
  {
    oldPath: `/dashboard/listings/${sampleId}/logistics`,
    file: 'logistics/page.tsx',
    targetTemplate: '/listings/${id}/logistics',
    finalUrl: `/listings/${sampleId}/logistics`,
  },
  {
    oldPath: `/dashboard/listings/${sampleId}/offers`,
    file: 'offers/page.tsx',
    targetTemplate: '/listings/${id}/offers',
    finalUrl: `/listings/${sampleId}/offers`,
  },
  {
    oldPath: `/dashboard/listings/${sampleId}/spa`,
    file: 'spa/page.tsx',
    targetTemplate: '/listings/${id}/documents',
    finalUrl: `/listings/${sampleId}/documents`,
  },
]

const bannedLegacyPatterns = [
  { label: 'legacy dashboard link', pattern: /\/dashboard\/listings/ },
  { label: 'gold text class', pattern: /text-gold/ },
  { label: 'gold button class', pattern: /btn-gold/ },
  { label: 'legacy surface class', pattern: /surface-1/ },
  { label: 'legacy sand text class', pattern: /text-sand/ },
  { label: 'gold border class', pattern: /border-gold/ },
  { label: 'legacy deep background class', pattern: /bg-deep/ },
  { label: 'legacy ghost border class', pattern: /ghost-border/ },
  { label: 'legacy gold shadow class', pattern: /shadow-gold/ },
  { label: 'retired gold token', pattern: /#C9A96E/ },
  { label: 'legacy detail data fetch', pattern: /useListingDetail/ },
  { label: 'legacy auth-gated layout', pattern: /useAuth/ },
  { label: 'legacy tab state', pattern: /\bTABS\b/ },
  { label: 'legacy pathname tab matching', pattern: /usePathname/ },
  { label: 'legacy client component marker', pattern: /'use client'|"use client"/ },
  { label: 'legacy animation implementation', pattern: /framer-motion|motion\./ },
  { label: 'legacy route UI links', pattern: /next\/link/ },
  { label: 'legacy direct API implementation', pattern: /apiFetch/ },
  { label: 'legacy logistics form render', pattern: /ListingLogisticsForm/ },
]

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function readRouteFile(relativePath) {
  return readFileSync(resolve(routeRoot, relativePath), 'utf8')
}

const failures = []
const finalUrlMap = {}

const layoutSource = readRouteFile('layout.tsx')
for (const legacyPattern of bannedLegacyPatterns) {
  if (legacyPattern.pattern.test(layoutSource)) {
    failures.push(`layout.tsx contains ${legacyPattern.label}`)
  }
}
if (!/return\s+children/.test(layoutSource)) {
  failures.push('layout.tsx does not return children directly')
}

for (const routeCheck of routeChecks) {
  const source = readRouteFile(routeCheck.file)
  const redirectPattern = new RegExp(`redirect\\(\\s*\`${escapeRegExp(routeCheck.targetTemplate)}\`\\s*\\)`)
  if (!redirectPattern.test(source)) {
    failures.push(`${routeCheck.file} does not redirect to ${routeCheck.targetTemplate}`)
  }

  for (const legacyPattern of bannedLegacyPatterns) {
    if (legacyPattern.pattern.test(source)) {
      failures.push(`${routeCheck.file} contains ${legacyPattern.label}`)
    }
  }

  if (routeCheck.finalUrl.startsWith('/dashboard/listings')) {
    failures.push(`${routeCheck.oldPath} final URL still starts with /dashboard/listings`)
  }

  finalUrlMap[routeCheck.oldPath] = routeCheck.finalUrl
}

const result = {
  scenario: 'listing legacy dashboard route compatibility redirects',
  verification_mode: 'static Next route module verification',
  sample_id: sampleId,
  final_url_map: finalUrlMap,
  checked_files: ['layout.tsx', ...routeChecks.map((routeCheck) => routeCheck.file)],
  limitations: [
    'Live browser navigation was not used because these app routes are auth-protected; this check verifies the Next redirect() targets and legacy UI absence directly in the route modules.',
  ],
  status: failures.length === 0 ? 'pass' : 'fail',
  failures,
}

console.log(JSON.stringify(result, null, 2))

if (failures.length > 0) {
  process.exitCode = 1
}
