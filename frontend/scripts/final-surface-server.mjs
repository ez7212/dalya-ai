import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { sanitizedEnv } from './final-surface-safe-env.mjs'
import { authCookieName } from './final-surface-constants.mjs'

async function findFreePort() {
  return await new Promise((resolvePort, reject) => {
    const server = createServer()
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close(() => {
        if (address && typeof address === 'object') {
          resolvePort(address.port)
        } else {
          reject(new Error('Could not allocate a local port'))
        }
      })
    })
    server.on('error', reject)
  })
}

function authSession() {
  return {
    access_token: 'task-3-access-token',
    refresh_token: 'task-3-refresh-token',
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    expires_in: 3600,
    token_type: 'bearer',
    user: {
      id: '00000000-0000-4000-8000-000000000003',
      aud: 'authenticated',
      role: 'authenticated',
      email: 'agent@example.com',
      app_metadata: { role: 'agent' },
      user_metadata: { display_name: 'Leila Agent' },
      created_at: '2026-06-23T06:00:00.000Z',
    },
  }
}

export async function startSupabaseAuthStub() {
  const port = await findFreePort()
  const user = authSession().user
  const server = createServer((request, response) => {
    if (request.url === '/auth/v1/user') {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify(user))
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
    close: () => new Promise((resolveClose) => server.close(resolveClose)),
  }
}

export function startDevServer(baseUrl, serverCwd, safeTempWorkdir, supabaseUrl) {
  const url = new URL(baseUrl)
  const port = url.port || '3000'
  const env = sanitizedEnv(supabaseUrl, safeTempWorkdir)
  const child = spawn('npm', ['run', 'dev', '--', '--webpack', '--hostname', '127.0.0.1', '--port', port], {
    cwd: serverCwd,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  let logs = ''
  child.stdout.on('data', (chunk) => {
    logs += chunk.toString()
  })
  child.stderr.on('data', (chunk) => {
    logs += chunk.toString()
  })
  return {
    child,
    envNames: Object.keys(env),
    readLogs: () => logs.slice(-8000),
  }
}

export async function isReachable(baseUrl) {
  try {
    const response = await fetch(baseUrl)
    return response.status < 500
  } catch {
    return false
  }
}

export async function waitForServer(baseUrl, server) {
  const startedAt = Date.now()
  let lastError = ''
  while (Date.now() - startedAt < 90_000) {
    if (server.child.exitCode !== null) {
      throw new Error(`dev server exited with code ${server.child.exitCode}\n${server.readLogs()}`)
    }
    try {
      const response = await fetch(baseUrl)
      if (response.status < 500) return
      lastError = `HTTP ${response.status}`
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error)
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 750))
  }
  throw new Error(`timed out waiting for ${baseUrl}: ${lastError}\n${server.readLogs()}`)
}

export async function stopServer(server) {
  if (!server || server.child.exitCode !== null) return 'server already exited'
  server.child.kill('SIGTERM')
  const exit = await Promise.race([
    new Promise((resolveExit) => server.child.once('exit', () => resolveExit('server exited after SIGTERM'))),
    new Promise((resolveTimeout) => setTimeout(() => resolveTimeout('server SIGTERM timeout'), 3000)),
  ])
  if (exit === 'server SIGTERM timeout' && server.child.exitCode === null) {
    server.child.kill('SIGKILL')
    return 'server required SIGKILL after SIGTERM timeout'
  }
  return exit
}

function encodeCookieSession(session) {
  return `base64-${Buffer.from(JSON.stringify(session), 'utf8').toString('base64url')}`
}

export async function seedAuth(context, baseUrl) {
  const session = authSession()
  await context.addCookies([{
    name: authCookieName,
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
