import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const redMode = process.argv.includes('--red')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function assertCheck(condition, label, details = {}) {
  if (!condition) {
    throw new Error(`${label}: ${JSON.stringify(details)}`)
  }
  return { label, passed: true, details }
}

const todayQueue = read('src/components/agent-dashboard/TodayQueue.tsx')
const todayQueueBuilder = read('src/components/agent-dashboard/today-queue.ts')
const escalationInbox = read('src/components/escalations/EscalationInbox.tsx')
const handoffCardPath = 'src/components/agent-dashboard/QueueHandoffCard.tsx'
let handoffCard = ''
try {
  handoffCard = read(handoffCardPath)
} catch (error) {
  if (!redMode) {
    throw error
  }
}

function runRedChecks() {
  return [
    assertCheck(todayQueue.includes('label="Open"'), 'current queue still uses generic Open action text'),
    assertCheck(!todayQueue.includes('QueueHandoffCard'), 'current queue lacks structured handoff card component'),
    assertCheck(!escalationInbox.includes('EscalationHandoffPanel'), 'current escalation inbox lacks structured handoff panel'),
  ]
}

function runGreenChecks() {
  const sources = `${todayQueue}\n${todayQueueBuilder}\n${escalationInbox}\n${handoffCard}`
  return [
    assertCheck(todayQueue.includes('QueueHandoffCard'), 'Today Queue renders structured handoff cards'),
    assertCheck(escalationInbox.includes('EscalationHandoffPanel'), 'Escalation inbox renders handoff panel'),
    assertCheck(!todayQueue.includes('label="Open"'), 'Today Queue no longer renders generic Open link labels'),
    assertCheck(sources.includes('Buyer intent'), 'handoff card exposes buyer intent'),
    assertCheck(sources.includes('Known'), 'handoff card exposes known readiness fields'),
    assertCheck(sources.includes('Missing'), 'handoff card exposes missing readiness blockers'),
    assertCheck(sources.includes('Suggested action'), 'handoff card exposes one suggested action'),
    assertCheck(sources.includes('Work surface'), 'handoff card exposes exact work surface route target'),
    assertCheck(sources.includes('Source'), 'handoff card exposes source'),
    assertCheck(sources.includes('Agent review/counter guidance only'), 'offer handoff copy stays review-only'),
    assertCheck(sources.includes('/agent/escalations?thread='), 'escalation route target remains exact inbox thread'),
    assertCheck(sources.includes('/agent/conversations/'), 'conversation route target remains exact conversation surface'),
    assertCheck(!sources.includes('send_to_buyer: true') || escalationInbox.includes('send_to_buyer: true'), 'handoff card adds no new send behavior'),
  ]
}

const checks = redMode ? runRedChecks() : runGreenChecks()
console.log(JSON.stringify({
  scenario: redMode
    ? 'Task 11 RED/current state: generic queue and escalation cards'
    : 'Task 11 GREEN: structured handoff cards',
  mode: redMode ? 'red' : 'green',
  checks,
}, null, 2))
