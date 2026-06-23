import { tmpdir } from 'node:os'
import {
  existsSync,
  cpSync,
  lstatSync,
  mkdirSync,
  readdirSync,
  realpathSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs'
import { basename, relative, resolve, sep } from 'node:path'
import {
  defaultFrontendRoot,
  envVarCategories,
  explicitSafeEnv,
  repoRoot,
  safeTempMarker,
  safeTempPrefixes,
} from './final-surface-constants.mjs'

export function scanEnvFiles(root) {
  if (!existsSync(root)) return []
  const found = []

  function visit(directory) {
    for (const name of readdirSync(directory)) {
      if (name === 'node_modules' || name === '.next' || name === '.git') continue
      const fullPath = resolve(directory, name)
      const stats = lstatSync(fullPath)
      if (name.startsWith('.env')) {
        found.push(relative(root, fullPath) || basename(fullPath))
        continue
      }
      if (stats.isDirectory() && !stats.isSymbolicLink()) {
        visit(fullPath)
      }
    }
  }

  visit(root)
  return found.sort()
}

export function scanRootNextEnvFiles(root) {
  if (!existsSync(root)) return []
  return readdirSync(root)
    .filter((name) => name.startsWith('.env'))
    .sort()
}

function asChildPath(parent, child) {
  const relativePath = relative(parent, child)
  return relativePath !== '' && !relativePath.startsWith('..') && !relativePath.includes(`..${sep}`)
}

export function existingRealPath(path) {
  return existsSync(path) ? realpathSync(path) : resolve(path)
}

export function validateSafeTempWorkdir(rawSafeTempWorkdir, sourceRoot) {
  const safeTempWorkdir = resolve(rawSafeTempWorkdir)
  const sourceReal = existingRealPath(sourceRoot)
  const repoReal = existingRealPath(repoRoot)
  const parent = resolve(safeTempWorkdir, '..')
  const parentReal = existingRealPath(parent)
  const tmpRealPaths = [...new Set([
    existingRealPath(tmpdir()),
    existingRealPath('/tmp'),
    existsSync('/private/tmp') ? existingRealPath('/private/tmp') : null,
  ].filter(Boolean))]
  const safeReal = existingRealPath(safeTempWorkdir)
  const markerPath = resolve(safeTempWorkdir, safeTempMarker)
  const exists = existsSync(safeTempWorkdir)
  const existingEntries = exists && lstatSync(safeTempWorkdir).isDirectory()
    ? readdirSync(safeTempWorkdir)
    : []

  const failures = []
  if (!rawSafeTempWorkdir || rawSafeTempWorkdir.trim() === '') {
    failures.push('missing_safe_temp_workdir')
  }
  if (safeTempWorkdir === sep || safeTempWorkdir === repoReal || safeTempWorkdir === sourceReal) {
    failures.push('dangerous_root_or_project_path')
  }
  if (asChildPath(sourceReal, safeReal) || asChildPath(safeReal, sourceReal)) {
    failures.push('overlaps_fixture_frontend_root')
  }
  if (asChildPath(repoReal, safeReal)) {
    failures.push('inside_repository')
  }
  if (!tmpRealPaths.some((tmpReal) => safeReal === tmpReal || asChildPath(tmpReal, safeReal))) {
    failures.push('outside_expected_temp_roots')
  }
  if (!safeTempPrefixes.some((prefix) => basename(safeTempWorkdir).startsWith(prefix))) {
    failures.push('unexpected_safe_temp_name_prefix')
  }
  if (exists && !lstatSync(safeTempWorkdir).isDirectory()) {
    failures.push('safe_temp_path_is_not_directory')
  }
  if (exists && existingEntries.length > 0 && !existsSync(markerPath)) {
    failures.push('existing_directory_without_verifier_marker')
  }

  return {
    ok: failures.length === 0,
    failures,
    safeTempWorkdir,
    parentReal,
    expectedTempRoots: tmpRealPaths,
    requiredNamePrefixes: safeTempPrefixes,
    existingPath: exists,
    existingEntryCount: existingEntries.length,
    verifierMarker: safeTempMarker,
  }
}

export function removeValidatedSafeTempWorkdir(safeTempValidation) {
  if (!safeTempValidation?.ok || !safeTempValidation.safeTempWorkdir) {
    return 'not removed: safe temp validation did not pass'
  }
  rmSync(safeTempValidation.safeTempWorkdir, { recursive: true, force: true })
  return `removed ${safeTempValidation.safeTempWorkdir}`
}

export function envSummaryFromNames(names, mode) {
  return {
    mode,
    valuePolicy: 'names-and-categories-only; no environment values recorded',
    variables: names.map((name) => ({
      name,
      category: envVarCategories[name] ?? 'unclassified',
      valueRecorded: false,
    })),
  }
}

export function stageSafeFrontend(sourceRoot, safeTempWorkdir) {
  rmSync(safeTempWorkdir, { recursive: true, force: true })
  mkdirSync(safeTempWorkdir, { recursive: true })
  writeFileSync(resolve(safeTempWorkdir, safeTempMarker), 'owned by frontend/scripts/verify-next-mvp-final-surface.mjs\n')

  const copyEntries = [
    'src',
    'public',
    'scripts',
    'package.json',
    'package-lock.json',
    'tsconfig.json',
    'tailwind.config.ts',
    'postcss.config.mjs',
    'eslint.config.mjs',
    'next.config.ts',
  ]
  const linkEntries = ['node_modules']
  const skippedEntries = [
    '.env*',
    '.next',
    '.turbo',
    '.cache',
    'coverage',
    'playwright-report',
    'test-results',
    'tsconfig.tsbuildinfo',
    'next-env.d.ts',
  ]

  for (const entry of copyEntries) {
    const source = resolve(sourceRoot, entry)
    if (!existsSync(source)) continue
    cpSync(source, resolve(safeTempWorkdir, entry), { recursive: true })
  }

  for (const entry of linkEntries) {
    const source = resolve(sourceRoot, entry)
    if (!existsSync(source)) continue
    symlinkSync(source, resolve(safeTempWorkdir, entry), lstatSync(source).isDirectory() ? 'dir' : 'file')
  }

  return {
    sourceRoot,
    safeTempWorkdir,
    verifierMarker: safeTempMarker,
    copiedEntries: copyEntries.filter((entry) => existsSync(resolve(sourceRoot, entry))),
    linkedEntries: linkEntries.filter((entry) => existsSync(resolve(sourceRoot, entry))),
    skippedEntries,
    sourceEnvFiles: scanEnvFiles(sourceRoot),
    safeTempEnvFiles: scanEnvFiles(safeTempWorkdir),
  }
}

export function sanitizedEnv(supabaseUrl, safeTempWorkdir) {
  return {
    PATH: process.env.PATH ?? '',
    HOME: process.env.HOME ?? '',
    TMPDIR: process.env.TMPDIR ?? '/tmp',
    USER: process.env.USER ?? '',
    LOGNAME: process.env.LOGNAME ?? process.env.USER ?? '',
    NEXT_TELEMETRY_DISABLED: explicitSafeEnv.NEXT_TELEMETRY_DISABLED,
    NEXT_PUBLIC_SUPABASE_URL: supabaseUrl,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: explicitSafeEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    npm_config_cache: resolve(safeTempWorkdir, '.npm-cache'),
  }
}

export function transcriptExtraValues(outputDir, fixtureFrontendRoot, safeTempWorkdir) {
  return {
    OUTPUT_DIR: outputDir,
    FIXTURE_FRONTEND_ROOT: fixtureFrontendRoot,
    SAFE_TEMP_WORKDIR: safeTempWorkdir ?? '',
    npm_config_cache: safeTempWorkdir ? resolve(safeTempWorkdir, '.npm-cache') : '',
  }
}

export function resolveOutputDir(rawOutputDir) {
  return resolve(defaultFrontendRoot, rawOutputDir)
}
