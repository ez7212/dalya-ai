import { jsonResponse } from './final-surface-cli.mjs'

function focusedEscalationThread() {
  return {
    thread_id: 'esc-critical-1',
    envelope_token: 'DL-ESC-001',
    conversation_id: 'conv-final-surface-1',
    ai_mode: 'active',
    category: 'viewing',
    state: 'updated',
    urgency: 'critical',
    buyer: { name: 'Noura Surface', phone: '+971500000777' },
    listing: { project: 'Emaar Oasis Villa', unit_number: 'V-12' },
    latest_question: 'Can we confirm access before the 11 AM viewing?',
    question_count: 2,
    last_buyer_message_at: '2026-06-23T09:50:00+04:00',
    opened_at: '2026-06-23T09:10:00+04:00',
    latest_route_expires_at: '2026-06-23T10:20:00+04:00',
    questions: [
      {
        question_id: 'q-access-1',
        question_text: 'Can we confirm access before the 11 AM viewing?',
        added_at: '2026-06-23T09:50:00+04:00',
      },
      {
        question_id: 'q-parking-1',
        question_text: 'Please confirm visitor parking and gate access.',
        added_at: '2026-06-23T09:52:00+04:00',
      },
    ],
  }
}

export function dashboardPayloadWithEscalation() {
  return {
    generated_at: '2026-06-23T10:00:00+04:00',
    sample_data: false,
    agent: { display_name: 'Leila Agent' },
    brokerage: { name: 'Luqman Realty' },
    metrics: { open_tasks: 0, hot_leads: 0, viewings_today: 0, stale_leads: 0, open_escalations: 1 },
    tasks: [],
    hot_leads: [],
    conversations: [],
    campaigns: [],
    viewings: [],
    escalation_threads: [focusedEscalationThread()],
    drafts: { reply_drafts: [], outreach_drafts: [] },
    marketing: { pages: [], events_7d: 0 },
    performance: { scope: 'agent', primary: { key: 'today', label: 'Today', metrics: {} }, windows: [] },
  }
}

export function emptyDashboardPayload() {
  return {
    generated_at: '2026-06-23T10:00:00+04:00',
    sample_data: false,
    agent: { display_name: 'Leila Agent' },
    brokerage: { name: 'Luqman Realty' },
    empty_state: {
      reason: 'no_workspace_activity',
      message: 'No live buyer activity is assigned to this agent workspace yet.',
    },
    metrics: { open_tasks: 0, hot_leads: 0, viewings_today: 0, stale_leads: 0, open_escalations: 0 },
    tasks: [],
    hot_leads: [],
    conversations: [],
    campaigns: [],
    viewings: [],
    escalation_threads: [],
    drafts: { reply_drafts: [], outreach_drafts: [] },
    marketing: { pages: [], events_7d: 0 },
    performance: { scope: 'agent', primary: { key: 'today', label: 'Today', metrics: {} }, windows: [] },
  }
}

export function inboxPayload() {
  return {
    generated_at: '2026-06-23T10:00:00+04:00',
    counts: { total: 1, critical: 1, high: 0 },
    threads: [focusedEscalationThread()],
  }
}

export async function installSharedMocks(page) {
  await page.route('https://test.supabase.co/**', (route) => route.fulfill(jsonResponse({})))
  await page.route('**/api/v1/me/brokerages', (route) => route.fulfill(jsonResponse({
    active_brokerages: [{ brokerage_id: 'brokerage-1', name: 'Luqman Realty', role: 'agent', membership_id: 'membership-1' }],
    requires_selection: false,
    default_brokerage_id: 'brokerage-1',
  })))
  await page.route('**/api/v1/agent/hot-list/refresh', (route) => route.fulfill(jsonResponse({
    status: 'completed',
    trigger: 'manual',
    last_refresh_at: '2026-06-23T09:00:00+04:00',
    completed_at: '2026-06-23T09:01:00+04:00',
    assignment_count: 0,
    task_count: 0,
    draft_count: 0,
  })))
}
