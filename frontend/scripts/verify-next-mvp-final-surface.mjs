import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const repoRoot = resolve(import.meta.dirname, '../..')
const frontendRoot = resolve(repoRoot, 'frontend')

function valueAfter(flag, fallback) {
  const index = process.argv.indexOf(flag)
  return index === -1 ? fallback : process.argv[index + 1]
}

function writeBlocked(outputDir, reason, details = {}) {
  mkdirSync(outputDir, { recursive: true })
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
  writeFileSync(resolve(outputDir, 'BLOCKED.md'), body)
  console.log(JSON.stringify({ passed: false, blocked: true, outputDir, reason }, null, 2))
}

async function isReachable(baseUrl) {
  try {
    const response = await fetch(baseUrl)
    return response.status < 500
  } catch {
    return false
  }
}

function startDevServer(baseUrl) {
  const url = new URL(baseUrl)
  const port = url.port || '3000'
  const child = spawn('npm', ['run', 'dev', '--', '--hostname', '127.0.0.1', '--port', port], {
    cwd: frontendRoot,
    env: {
      ...process.env,
      NEXT_TELEMETRY_DISABLED: '1',
      NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://127.0.0.1:54321',
      NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'test-anon-key',
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
  return { child, logs: () => logs.slice(-8000) }
}

async function waitForServer(baseUrl, server) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < 90_000) {
    if (server.child.exitCode !== null) {
      throw new Error(`dev server exited with code ${server.child.exitCode}\n${server.logs()}`)
    }
    if (await isReachable(baseUrl)) return
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 750))
  }
  throw new Error(`timed out waiting for ${baseUrl}\n${server.logs()}`)
}

async function capture(page, baseUrl, outputDir, name, path) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: 'domcontentloaded' })
  await page.screenshot({ path: resolve(outputDir, `${name}.png`), fullPage: true })
  return {
    name,
    path,
    title: await page.title(),
    bodyText: (await page.locator('body').innerText()).slice(0, 2000),
  }
}

async function main() {
  const baseUrl = valueAfter('--base-url', 'http://127.0.0.1:3000')
  const outputDir = resolve(frontendRoot, valueAfter('--output-dir', '../.omo/evidence/final-next-mvp-surface'))
  mkdirSync(outputDir, { recursive: true })

  let server = null
  let startedServer = false
  if (!(await isReachable(baseUrl))) {
    if (existsSync(resolve(frontendRoot, '.env.local'))) {
      writeBlocked(outputDir, 'base URL is not reachable and frontend/.env.local exists, so the verifier did not start a dev server that may load local env-file contents', { baseUrl })
      return 2
    }
    server = startDevServer(baseUrl)
    startedServer = true
    try {
      await waitForServer(baseUrl, server)
    } catch (error) {
      writeBlocked(outputDir, 'local Next dev server could not start', {
        baseUrl,
        error: error instanceof Error ? error.message : String(error),
        logs: server.logs(),
      })
      server.child.kill('SIGTERM')
      return 2
    }
  }

  let browser = null
  try {
    const { chromium } = await import('@playwright/test')
    browser = await chromium.launch()
    const context = await browser.newContext({ viewport: { width: 1280, height: 760 }, deviceScaleFactor: 1 })
    const page = await context.newPage()
    const captures = []
    captures.push(await capture(page, baseUrl, outputDir, 'agent', '/agent'))
    captures.push(await capture(page, baseUrl, outputDir, 'escalations-focus', '/agent/escalations?thread=esc-critical-1'))
    captures.push(await capture(page, baseUrl, outputDir, 'drafts', '/agent/drafts'))
    await context.close()

    const transcript = {
      scenario: 'F3 final next MVP surface smoke',
      invocation: `cd frontend && node scripts/verify-next-mvp-final-surface.mjs --base-url ${baseUrl} --output-dir ${outputDir}`,
      baseUrl,
      startedServer,
      captures,
      passed: captures.every((item) => item.bodyText.length > 0),
    }
    writeFileSync(resolve(outputDir, 'transcript.json'), `${JSON.stringify(transcript, null, 2)}\n`)
    console.log(JSON.stringify({ passed: transcript.passed, outputDir, captures: captures.length }, null, 2))
    return transcript.passed ? 0 : 1
  } catch (error) {
    writeBlocked(outputDir, 'Playwright surface capture failed', {
      baseUrl,
      error: error instanceof Error ? error.message : String(error),
    })
    return 2
  } finally {
    if (browser) await browser.close()
    if (server) server.child.kill('SIGTERM')
  }
}

const exitCode = await main()
process.exit(exitCode)
