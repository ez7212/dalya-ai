import { resolve } from 'node:path'

export const repoRoot = resolve(import.meta.dirname, '../..')
export const defaultFrontendRoot = resolve(repoRoot, 'frontend')
export const authCookieName = 'sb-127-auth-token'

export const explicitSafeEnvNames = [
  'NEXT_TELEMETRY_DISABLED',
  'NEXT_PUBLIC_SUPABASE_ANON_KEY',
]

export const explicitSafeEnv = {
  NEXT_TELEMETRY_DISABLED: '1',
  NEXT_PUBLIC_SUPABASE_ANON_KEY: 'test-anon-key',
}

export const envVarCategories = {
  PATH: 'process-runtime',
  HOME: 'process-runtime',
  TMPDIR: 'process-runtime',
  USER: 'process-runtime',
  LOGNAME: 'process-runtime',
  NEXT_TELEMETRY_DISABLED: 'explicit-safe-control',
  NEXT_PUBLIC_SUPABASE_URL: 'local-synthetic-supabase-stub',
  NEXT_PUBLIC_SUPABASE_ANON_KEY: 'explicit-synthetic-public-key',
  npm_config_cache: 'safe-temp-cache-path',
}

export const safeTempMarker = '.dalya-final-surface-verifier-temp'
export const safeTempPrefixes = ['dalya-final-surface-', 'dalya-next-mvp-final-surface-']

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
