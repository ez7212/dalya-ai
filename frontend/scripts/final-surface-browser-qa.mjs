import { resolve } from 'node:path'
import { assertCheck, jsonResponse } from './final-surface-cli.mjs'
import { fakeOperationalTexts } from './final-surface-constants.mjs'
import {
  dashboardPayloadWithEscalation,
  emptyDashboardPayload,
  inboxPayload,
  installSharedMocks,
} from './final-surface-browser-fixtures.mjs'
import { seedAuth } from './final-surface-server.mjs'

async function bodyText(page) {
  return await page.locator('body').innerText()
}

function assertNoFakeOperationalData(text, label) {
  const leakedTexts = fakeOperationalTexts.filter((value) => text.includes(value))
  return assertCheck(leakedTexts.length === 0, label, { leakedTexts })
}

async function capture(page, outputDir, name) {
  const path = resolve(outputDir, `${name}.png`)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(100)
  await page.screenshot({ path, fullPage: true })
  return path
}

async function captureFocusedViewport(page, outputDir, name, locator) {
  const path = resolve(outputDir, `${name}.png`)
  await locator.scrollIntoViewIfNeeded()
  await page.waitForTimeout(100)
  await page.screenshot({ path, fullPage: false })
  return path
}

async function captureAgentSurface(context, baseUrl, outputDir, checks, captures) {
  const page = await context.newPage()
  await installSharedMocks(page)
  await page.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(dashboardPayloadWithEscalation())))
  await page.goto(`${baseUrl}/agent`, { waitUntil: 'domcontentloaded' })
  await page.getByText('Good morning, Leila Agent').waitFor({ timeout: 20_000 })
  const text = await bodyText(page)
  checks.push(assertCheck(text.includes('Good morning, Leila Agent'), '/agent renders authenticated workspace header'))
  checks.push(assertCheck(text.includes('Can we confirm access before the 11 AM viewing?'), 'Today Queue focused escalation text is visible'))
  checks.push(assertNoFakeOperationalData(text, '/agent surface does not render fake fallback operational rows'))
  captures.push({
    name: 'agent',
    path: await capture(page, outputDir, 'agent'),
    route: '/agent',
    captureKind: 'full-page',
    assertions: ['Good morning, Leila Agent', 'Can we confirm access before the 11 AM viewing?'],
  })
  const escalationQuestion = page.getByText('Can we confirm access before the 11 AM viewing?').first()
  captures.push({
    name: 'today-queue-escalation-focus',
    path: await captureFocusedViewport(page, outputDir, 'today-queue-escalation-focus', escalationQuestion),
    route: '/agent',
    captureKind: 'viewport-focused',
    assertions: ['Can we confirm access before the 11 AM viewing?'],
  })
  await page.close()
}

async function captureDashboardFailure(context, baseUrl, outputDir, checks, captures, name) {
  const page = await context.newPage()
  await installSharedMocks(page)
  await page.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse({ detail: 'upstream unavailable' }, 503)))
  await page.goto(`${baseUrl}/agent`, { waitUntil: 'domcontentloaded' })
  await page.getByText("Couldn't load your live workspace").waitFor({ timeout: 20_000 })
  const text = await bodyText(page)
  checks.push(assertCheck(text.includes('Retry'), `${name} exposes retry action`))
  checks.push(assertCheck(text.includes('Manual fallback'), `${name} exposes manual fallback text`))
  checks.push(assertCheck(text.includes('do not use demo data as live activity'), `${name} warns against demo data as live activity`))
  checks.push(assertNoFakeOperationalData(text, `${name} does not render fake fallback operational rows`))
  captures.push({
    name,
    path: await capture(page, outputDir, name),
    route: '/agent',
    captureKind: 'full-page',
    assertions: ['Retry', 'Manual fallback', 'do not use demo data as live activity'],
  })
  await page.close()
}

async function captureEscalationReplyAffordance(context, baseUrl, outputDir, checks, captures) {
  const page = await context.newPage()
  await installSharedMocks(page)
  await page.route('**/api/v1/agent/escalations?**', (route) => route.fulfill(jsonResponse(inboxPayload())))
  await page.goto(`${baseUrl}/agent/escalations?thread=esc-critical-1`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: 'Escalation inbox' }).waitFor({ timeout: 20_000 })
  const replyLabel = page.getByText('Reply to buyer', { exact: true })
  const replyBox = page.getByPlaceholder('Write the buyer-safe answer', { exact: false })
  await replyLabel.waitFor({ timeout: 20_000 })
  await replyBox.waitFor({ timeout: 20_000 })
  const text = await bodyText(page)
  const sendButton = page.getByRole('button', { name: /Send to buyer/i }).first()
  checks.push(assertCheck(await replyLabel.isVisible(), 'escalation reply affordance label is visible'))
  checks.push(assertCheck(await replyBox.isVisible(), 'escalation reply placeholder gives buyer-safe instruction'))
  checks.push(assertCheck(await sendButton.isDisabled(), 'empty escalation reply keeps Send to buyer disabled', { reason: 'reply body is empty' }))
  checks.push(assertCheck(text.includes('Can we confirm access before the 11 AM viewing?'), 'selected escalation question text is visible'))
  checks.push(assertNoFakeOperationalData(text, 'escalation reply affordance does not render fake fallback operational rows'))
  captures.push({
    name: 'escalation-reply-affordance',
    path: await capture(page, outputDir, 'escalation-reply-affordance'),
    route: '/agent/escalations?thread=esc-critical-1',
    captureKind: 'full-page',
    assertions: ['Reply to buyer', 'Write the buyer-safe answer', 'Send to buyer disabled because reply body is empty'],
  })
  await page.close()
}

async function captureFirstRunEmpty(context, baseUrl, outputDir, checks, captures) {
  const page = await context.newPage()
  await installSharedMocks(page)
  await page.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(emptyDashboardPayload())))
  await page.goto(`${baseUrl}/agent`, { waitUntil: 'domcontentloaded' })
  await page.getByText('Start with an internal pilot rehearsal').waitFor({ timeout: 20_000 })
  const text = await bodyText(page)
  checks.push(assertCheck(text.includes('Start with an internal pilot rehearsal'), 'first-run empty state shows safe activation headline'))
  checks.push(assertCheck(text.includes('synthetic/internal records'), 'first-run empty state requires safe synthetic/internal activation'))
  checks.push(assertCheck(text.includes('Real customer data stays blocked'), 'first-run empty state keeps real customer data blocked'))
  checks.push(assertNoFakeOperationalData(text, 'first-run empty state does not render fake fallback operational rows'))
  captures.push({
    name: 'first-run-empty-state',
    path: await capture(page, outputDir, 'first-run-empty-state'),
    route: '/agent',
    captureKind: 'full-page',
    assertions: ['Start with an internal pilot rehearsal', 'synthetic/internal records', 'Real customer data stays blocked'],
  })
  await page.close()
}

async function captureFirstRunError(context, baseUrl, outputDir, checks, captures) {
  const page = await context.newPage()
  await installSharedMocks(page)
  await page.route('**/api/v1/agent/dashboard', (route) => route.fulfill(jsonResponse(emptyDashboardPayload())))
  await page.route('**/api/v1/agent/hot-list/refresh', (route) => route.fulfill(jsonResponse({ detail: 'synthetic refresh unavailable' }, 503)))
  await page.goto(`${baseUrl}/agent`, { waitUntil: 'domcontentloaded' })
  await page.getByText('Start with an internal pilot rehearsal').waitFor({ timeout: 20_000 })
  await page.getByRole('button', { name: 'Refresh hot list' }).first().click()
  await page.getByText('Refresh failed.').waitFor({ timeout: 20_000 })
  const text = await bodyText(page)
  checks.push(assertCheck(text.includes('Start with an internal pilot rehearsal'), 'first-run error state preserves safe activation headline'))
  checks.push(assertCheck(text.includes('Refresh failed.'), 'first-run error state shows synthetic refresh failure'))
  checks.push(assertCheck(text.includes('synthetic/internal records'), 'first-run error state keeps safe synthetic/internal activation visible'))
  checks.push(assertCheck(text.includes('Real customer data stays blocked'), 'first-run error state keeps real customer data blocked'))
  checks.push(assertNoFakeOperationalData(text, 'first-run error state does not render fake fallback operational rows'))
  captures.push({
    name: 'first-run-error-state',
    path: await capture(page, outputDir, 'first-run-error-state'),
    route: '/agent',
    captureKind: 'full-page',
    assertions: ['Start with an internal pilot rehearsal', 'Refresh failed.', 'synthetic/internal records', 'Real customer data stays blocked'],
  })
  await page.close()
}

export async function runBrowserQa(baseUrl, outputDir) {
  const { chromium } = await import('@playwright/test')
  const browser = await chromium.launch()
  const context = await browser.newContext({ viewport: { width: 1280, height: 760 }, deviceScaleFactor: 1 })
  await seedAuth(context, baseUrl)

  const checks = []
  const captures = []
  try {
    await captureAgentSurface(context, baseUrl, outputDir, checks, captures)
    await captureDashboardFailure(context, baseUrl, outputDir, checks, captures, 'dashboard-fetch-failure')
    await captureEscalationReplyAffordance(context, baseUrl, outputDir, checks, captures)
    await captureFirstRunEmpty(context, baseUrl, outputDir, checks, captures)
    await captureFirstRunError(context, baseUrl, outputDir, checks, captures)
    return { checks, captures }
  } catch (error) {
    if (error && typeof error === 'object') {
      error.partialQa = { checks, captures }
    }
    throw error
  } finally {
    await context.close()
    await browser.close()
  }
}
