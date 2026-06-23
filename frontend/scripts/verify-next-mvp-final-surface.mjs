import { existsSync, mkdirSync, rmSync } from 'node:fs'
import { relative, resolve } from 'node:path'
import {
  defaultFrontendRoot,
  explicitSafeEnvNames,
} from './final-surface-constants.mjs'
import { valueAfter } from './final-surface-cli.mjs'
import { runBrowserQa } from './final-surface-browser-qa.mjs'
import {
  envSummaryFromNames,
  removeValidatedSafeTempWorkdir,
  sanitizedEnv,
  scanEnvFiles,
  scanRootNextEnvFiles,
  stageSafeFrontend,
  transcriptExtraValues,
  validateSafeTempWorkdir,
} from './final-surface-safe-env.mjs'
import {
  isReachable,
  startDevServer,
  startSupabaseAuthStub,
  stopServer,
  waitForServer,
} from './final-surface-server.mjs'
import { writeBlocked, writeTranscript } from './final-surface-transcript.mjs'

function invocationText({ safeTempWorkdir, fixtureFrontendRoot, baseUrl, outputDir }) {
  return [
    'cd frontend && node scripts/verify-next-mvp-final-surface.mjs',
    safeTempWorkdir ? `--safe-temp-workdir ${safeTempWorkdir}` : null,
    fixtureFrontendRoot !== defaultFrontendRoot ? `--fixture-frontend-root ${fixtureFrontendRoot}` : null,
    `--base-url ${baseUrl}`,
    `--output-dir ${relative(defaultFrontendRoot, outputDir)}`,
  ].filter(Boolean).join(' ')
}

function envScanFor(fixtureFrontendRoot) {
  return {
    fixtureFrontendRoot,
    fixtureRootNextEnvFiles: scanRootNextEnvFiles(fixtureFrontendRoot),
    fixtureEnvFiles: scanEnvFiles(fixtureFrontendRoot),
  }
}

function envSafetyMode(safeTempValidation) {
  return safeTempValidation ? 'safe-temp-workdir' : 'direct-fixture-no-env-files'
}

function blockedEnvSummary(mode) {
  return envSummaryFromNames(explicitSafeEnvNames, mode)
}

function writeUnsafeSafeTempBlocked({ outputDir, invocation, baseUrl, safeTempValidation, envScanBefore, extraTranscriptValues }) {
  writeBlocked(outputDir, 'unsafe --safe-temp-workdir refused before cleanup or staging', {
    invocation,
    baseUrl,
    serverCwd: null,
    envSafetyMode: 'blocked-unsafe-safe-temp-workdir',
    safeTempValidation,
    envSummary: blockedEnvSummary('blocked-before-server-start'),
    envScan: envScanBefore,
    domAssertions: [],
    screenshotPaths: [],
    cleanup: {
      safeTempWorkdirDeleted: false,
      reason: 'safe temp validation failed before any rmSync cleanup',
    },
  }, {}, extraTranscriptValues)
}

function writeRootEnvBlocked({ outputDir, invocation, baseUrl, fixtureFrontendRoot, envScanBefore, extraTranscriptValues }) {
  writeBlocked(outputDir, 'fixture root has Next-loadable .env* files and no --safe-temp-workdir was supplied', {
    invocation,
    baseUrl,
    serverCwd: null,
    envSafetyMode: 'blocked-direct-root-env-files',
    envSummary: blockedEnvSummary('blocked-before-server-start'),
    envScan: envScanBefore,
    domAssertions: [],
    screenshotPaths: [],
    cleanup: {
      fixtureFrontendRootDeleted: false,
      reason: 'verifier never deletes caller-owned --fixture-frontend-root',
    },
  }, {}, transcriptExtraValues(outputDir, fixtureFrontendRoot, null))
}

function successTranscript({
  invocation,
  baseUrl,
  serverCwd,
  safeTempValidation,
  serverEnvNames,
  envScanBefore,
  staged,
  checks,
  captures,
  cleanupReceipt,
}) {
  return {
    scenario: 'F3 final next MVP surface QA',
    invocation,
    baseUrl,
    serverCwd,
    envSafetyMode: envSafetyMode(safeTempValidation),
    envSummary: envSummaryFromNames(serverEnvNames, envSafetyMode(safeTempValidation)),
    envScan: {
      ...envScanBefore,
      safeTempValidation,
      staging: staged,
    },
    domAssertions: checks,
    screenshotPaths: captures.map((item) => item.path),
    captures,
    cleanup: cleanupReceipt,
    passed: checks.every((item) => item.passed) && captures.length === 6,
  }
}

function failureDetails({
  invocation,
  baseUrl,
  serverCwd,
  safeTempValidation,
  serverEnvNames,
  envScanBefore,
  staged,
  failureDebug,
  cleanupReceipt,
}) {
  return {
    invocation,
    baseUrl,
    serverCwd,
    envSafetyMode: envSafetyMode(safeTempValidation),
    envSummary: envSummaryFromNames(serverEnvNames, envSafetyMode(safeTempValidation)),
    envScan: {
      ...envScanBefore,
      safeTempValidation,
      staging: staged,
    },
    failureDebug,
    cleanup: cleanupReceipt,
  }
}

async function closeRuntime({ server, supabaseStub, cleanupReceipt }) {
  cleanupReceipt.server = await stopServer(server)
  if (supabaseStub) {
    await supabaseStub.close()
    cleanupReceipt.supabaseStub = 'closed'
  }
}

async function main() {
  const fixtureFrontendRoot = resolve(valueAfter('--fixture-frontend-root', defaultFrontendRoot))
  const safeTempWorkdir = valueAfter('--safe-temp-workdir', null)
  const baseUrl = valueAfter('--base-url', 'http://127.0.0.1:3000')
  const outputDir = resolve(defaultFrontendRoot, valueAfter('--output-dir', '../.omo/evidence/final-next-mvp-surface'))
  mkdirSync(outputDir, { recursive: true })

  const envScanBefore = envScanFor(fixtureFrontendRoot)
  const invocation = invocationText({ safeTempWorkdir, fixtureFrontendRoot, baseUrl, outputDir })
  const safeTempValidation = safeTempWorkdir
    ? validateSafeTempWorkdir(safeTempWorkdir, fixtureFrontendRoot)
    : null

  if (safeTempValidation && !safeTempValidation.ok) {
    writeUnsafeSafeTempBlocked({
      outputDir,
      invocation,
      baseUrl,
      safeTempValidation,
      envScanBefore,
      extraTranscriptValues: transcriptExtraValues(outputDir, fixtureFrontendRoot, safeTempWorkdir),
    })
    return 2
  }

  if (!safeTempWorkdir && envScanBefore.fixtureRootNextEnvFiles.length > 0) {
    writeRootEnvBlocked({ outputDir, invocation, baseUrl, fixtureFrontendRoot, envScanBefore })
    return 2
  }

  let staged = null
  let server = null
  let supabaseStub = null
  let serverEnvNames = explicitSafeEnvNames
  let activeEnvValues = {}
  const cleanupReceipt = {}
  const serverCwd = safeTempValidation ? safeTempValidation.safeTempWorkdir : fixtureFrontendRoot
  const extraTranscriptValues = transcriptExtraValues(outputDir, fixtureFrontendRoot, serverCwd)

  try {
    if (safeTempValidation) {
      staged = stageSafeFrontend(fixtureFrontendRoot, serverCwd)
      if (staged.safeTempEnvFiles.length > 0) {
        throw new Error(`safe temp workdir still contains env files: ${staged.safeTempEnvFiles.join(', ')}`)
      }
    }

    supabaseStub = await startSupabaseAuthStub()
    activeEnvValues = sanitizedEnv(supabaseStub.url, serverCwd)
    if (await isReachable(baseUrl)) {
      throw new Error(`${baseUrl} is already reachable; refusing to run against a pre-existing server`)
    }
    server = startDevServer(baseUrl, serverCwd, serverCwd, supabaseStub.url)
    serverEnvNames = server.envNames
    await waitForServer(baseUrl, server)

    const { checks, captures } = await runBrowserQa(baseUrl, outputDir)
    await closeRuntime({ server, supabaseStub, cleanupReceipt })
    server = null
    supabaseStub = null
    if (safeTempValidation) {
      cleanupReceipt.safeTempWorkdir = removeValidatedSafeTempWorkdir(safeTempValidation)
    }

    const transcript = successTranscript({
      invocation,
      baseUrl,
      serverCwd,
      safeTempValidation,
      serverEnvNames,
      envScanBefore,
      staged,
      checks,
      captures,
      cleanupReceipt,
    })
    rmSync(resolve(outputDir, 'BLOCKED.md'), { force: true })
    writeTranscript(outputDir, transcript, activeEnvValues, extraTranscriptValues)
    console.log(JSON.stringify({ passed: transcript.passed, outputDir, captures: captures.length, transcriptPath: resolve(outputDir, 'transcript.json') }, null, 2))
    return transcript.passed ? 0 : 1
  } catch (error) {
    const failureDebug = {
      message: error instanceof Error ? error.message : String(error),
      nextDevLogTail: server?.readLogs() ?? '',
      partialQa: error && typeof error === 'object' ? error.partialQa ?? null : null,
    }
    await closeRuntime({ server, supabaseStub, cleanupReceipt })
    if (safeTempValidation && existsSync(serverCwd)) {
      cleanupReceipt.safeTempWorkdir = removeValidatedSafeTempWorkdir(safeTempValidation)
    }
    writeBlocked(outputDir, 'Playwright final surface QA failed', failureDetails({
      invocation,
      baseUrl,
      serverCwd,
      safeTempValidation,
      serverEnvNames,
      envScanBefore,
      staged,
      failureDebug,
      cleanupReceipt,
    }), activeEnvValues, extraTranscriptValues)
    return 2
  }
}

const exitCode = await main()
process.exit(exitCode)
