import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function assertIncludes(source, expected, label) {
  if (!source.includes(expected)) {
    throw new Error(`${label}: missing ${expected}`)
  }
}

const agentDashboard = read('src/components/agent-dashboard/AgentDashboard.tsx')
const types = read('src/components/agent-dashboard/types.ts')
const todayQueue = read('src/components/agent-dashboard/today-queue.ts')

assertIncludes(agentDashboard, 'readonly needs_reply_priority_score?: number | null', 'API conversation contract')
assertIncludes(agentDashboard, 'needsReplyPriorityScore: conversation.needs_reply_priority_score ?? null', 'API mapping')
assertIncludes(agentDashboard, '1000 + Number(item.needsReplyPriorityScore ?? 0)', 'client needs-reply fallback ordering')
assertIncludes(types, 'needsReplyPriorityScore?: number | null', 'conversation inbox type')
assertIncludes(todayQueue, 'urgencyScore: item.needsReplyPriorityScore ?? null', 'Today Queue needs-reply item')
assertIncludes(todayQueue, "left.kind === 'needs_reply' && right.kind === 'needs_reply'", 'Today Queue comparator')

console.log('PASS needs_reply priority metadata reaches Today Queue ordering')
