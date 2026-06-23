import { tmpdir } from 'node:os'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  defaultFrontendRoot,
  explicitSafeEnv,
  repoRoot,
} from './final-surface-constants.mjs'
import { existingRealPath } from './final-surface-safe-env.mjs'

function redactionPairsForTranscript(envValues = {}, extraValues = {}) {
  const pairs = []
  const add = (raw, replacement) => {
    if (typeof raw !== 'string' || raw.length < 3) return
    pairs.push({ raw, replacement })
  }

  add(repoRoot, '<REPO_ROOT>')
  add(defaultFrontendRoot, '<FRONTEND_ROOT>')
  add(existingRealPath(process.env.HOME ?? ''), '<ENV:HOME>')
  add(existingRealPath(process.env.TMPDIR ?? ''), '<ENV:TMPDIR>')
  add(existingRealPath(tmpdir()), '<ENV:TMPDIR>')
  add(existsSync('/tmp') ? existingRealPath('/tmp') : '', '<TEMP_ROOT>')
  add(existsSync('/private/tmp') ? existingRealPath('/private/tmp') : '', '<TEMP_ROOT>')
  for (const [name, value] of Object.entries({
    PATH: process.env.PATH ?? '',
    HOME: process.env.HOME ?? '',
    TMPDIR: process.env.TMPDIR ?? '',
    USER: process.env.USER ?? '',
    LOGNAME: process.env.LOGNAME ?? '',
    ...explicitSafeEnv,
    ...envValues,
    ...extraValues,
  })) {
    add(value, `<ENV:${name}>`)
  }

  return pairs
    .sort((left, right) => right.raw.length - left.raw.length)
    .filter((pair, index, sorted) => sorted.findIndex((candidate) => candidate.raw === pair.raw) === index)
}

function redactStringForTranscript(text, redactionPairs) {
  if (!text) return ''
  let redacted = text
  for (const { raw, replacement } of redactionPairs) {
    redacted = redacted.replaceAll(raw, replacement)
  }
  return redacted.replace(/(NEXT_PUBLIC_SUPABASE_ANON_KEY|SUPABASE_SERVICE_ROLE_KEY|DATABASE_URL|TOKEN|SECRET|PASSWORD)=\S+/gi, '$1=[REDACTED_ENV_VALUE]')
}

function redactForTranscript(value, redactionPairs) {
  if (typeof value === 'string') {
    return redactStringForTranscript(value, redactionPairs)
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactForTranscript(item, redactionPairs))
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [key, redactForTranscript(nestedValue, redactionPairs)]),
    )
  }
  return value
}

function envLeakNamesInText(text, envValues = {}, extraValues = {}) {
  const leaks = []
  for (const [name, value] of Object.entries({
    PATH: process.env.PATH ?? '',
    HOME: process.env.HOME ?? '',
    TMPDIR: process.env.TMPDIR ?? '',
    USER: process.env.USER ?? '',
    LOGNAME: process.env.LOGNAME ?? '',
    ...explicitSafeEnv,
    ...envValues,
    ...extraValues,
  })) {
    if (typeof value === 'string' && value.length >= 3 && text.includes(value)) {
      leaks.push(name)
    }
  }
  return [...new Set(leaks)]
}

function transcriptValuePolicy() {
  return {
    environmentValues: 'redacted before transcript write',
    paths: 'repo, temp, cache, and environment-derived paths are tokenized when recorded',
  }
}

export function writeTranscript(outputDir, transcript, envValues = {}, extraValues = {}) {
  const redactionPairs = redactionPairsForTranscript(envValues, extraValues)
  const safeTranscript = {
    ...redactForTranscript(transcript, redactionPairs),
    transcriptValuePolicy: transcriptValuePolicy(),
  }
  const serialized = `${JSON.stringify(safeTranscript, null, 2)}\n`
  const leaks = envLeakNamesInText(serialized, envValues, extraValues)
  if (leaks.length > 0) {
    throw new Error(`refusing to write transcript with raw environment values: ${leaks.join(', ')}`)
  }
  writeFileSync(resolve(outputDir, 'transcript.json'), serialized)
}

export function writeBlocked(outputDir, reason, details = {}, envValues = {}, extraValues = {}) {
  mkdirSync(outputDir, { recursive: true })
  const transcript = {
    scenario: 'F3 final next MVP surface QA',
    passed: false,
    blocked: true,
    reason,
    ...details,
  }
  writeTranscript(outputDir, transcript, envValues, extraValues)
  const body = [
    '# Final Next MVP Surface QA Blocked',
    '',
    `Reason: ${reason}`,
    '',
    '```json',
    JSON.stringify(details, null, 2),
    '```',
    '',
  ].join('\n')
  const redactionPairs = redactionPairsForTranscript(envValues, extraValues)
  writeFileSync(resolve(outputDir, 'BLOCKED.md'), redactStringForTranscript(body, redactionPairs))
  console.log(JSON.stringify({ passed: false, blocked: true, outputDir, reason }, null, 2))
}
