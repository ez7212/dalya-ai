'use client'

import { useEffect, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'
import type {
  AgentDashboardData,
  BuyerDigestItem,
  BuyerIntent,
  CampaignItem,
  CampaignSnapshot as CampaignSnapshotType,
  CampaignStatus,
  ConversationInboxItem,
  EscalationState,
  EscalationThreadItem,
  EscalationUrgency,
  MomentumStat,
  MomentumStreak,
  QueueItem,
  QueuePriority,
  ViewingItem,
  ViewingStatus,
} from './types'

interface AgentDashboardProps {
  data: AgentDashboardData
}

export function AgentDashboard({ data }: AgentDashboardProps) {
  const [dashboardData, setDashboardData] = useState<AgentDashboardData | null>(null)
  const [dataState, setDataState] = useState<'fallback' | 'loading' | 'live' | 'error'>('loading')
  const [taskActionState, setTaskActionState] = useState<Record<string, 'done' | 'snoozed' | 'error' | 'working'>>({})
  const [escalationActionState, setEscalationActionState] = useState<Record<string, 'resolved' | 'error' | 'working'>>({})
  const [refreshState, setRefreshState] = useState<'idle' | 'working' | 'error'>('idle')

  useEffect(() => {
    let active = true

    async function loadDashboard() {
      try {
        const res = await apiFetch('/api/v1/agent/dashboard')
        if (!res.ok) {
          throw new Error(`Dashboard API returned ${res.status}`)
        }
        const body = await res.json()
        if (!active) return
        setDashboardData(mapApiDashboard(body, data))
        setDataState(body.sample_data ? 'fallback' : 'live')
      } catch {
        if (!active) return
        setDashboardData(data)
        setDataState('error')
      }
    }

    loadDashboard()
    return () => {
      active = false
    }
  }, [data])

  const sourceLabel = dataState === 'live'
    ? 'Live workspace'
    : dataState === 'loading'
      ? 'Loading workspace'
      : 'Sample workspace'

  if (!dashboardData) {
    return <DashboardLoadingState />
  }

  async function updateTask(taskId: string, action: 'done' | 'snoozed') {
    const endpoint = action === 'done'
      ? `/api/v1/agent/tasks/${taskId}/done`
      : `/api/v1/agent/tasks/${taskId}/snooze`

    setTaskActionState((current) => ({ ...current, [taskId]: 'working' }))

    try {
      const res = await apiFetch(endpoint, {
        method: 'POST',
        headers: action === 'snoozed' ? { 'Content-Type': 'application/json' } : undefined,
        body: action === 'snoozed' ? JSON.stringify({ hours: 24, reason: 'review_later' }) : undefined,
      })
      if (!res.ok) {
        throw new Error(`Task update returned ${res.status}`)
      }

      setDashboardData((current) => {
        if (!current) return current

        return {
          ...current,
          summary: {
            ...current.summary,
            openTasks: Math.max(0, current.summary.openTasks - 1),
          },
          morningQueue: current.morningQueue.filter((item) => item.id !== taskId),
        }
      })
      setTaskActionState((current) => ({ ...current, [taskId]: action }))
    } catch {
      setTaskActionState((current) => ({ ...current, [taskId]: 'error' }))
    }
  }

  async function resolveEscalation(threadId: string) {
    setEscalationActionState((current) => ({ ...current, [threadId]: 'working' }))
    try {
      const res = await apiFetch(`/api/v1/agent/escalations/${threadId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'manual', note: 'Resolved from agent dashboard inbox.' }),
      })
      if (!res.ok) {
        throw new Error(`Escalation resolve returned ${res.status}`)
      }
      setDashboardData((current) => {
        if (!current) return current
        return {
          ...current,
          summary: {
            ...current.summary,
            openEscalations: Math.max(0, current.summary.openEscalations - 1),
          },
          escalationInbox: current.escalationInbox.filter((item) => item.id !== threadId),
        }
      })
      setEscalationActionState((current) => ({ ...current, [threadId]: 'resolved' }))
    } catch {
      setEscalationActionState((current) => ({ ...current, [threadId]: 'error' }))
    }
  }

  async function refreshHotList() {
    setRefreshState('working')
    try {
      const res = await apiFetch('/api/v1/agent/hot-list/refresh', { method: 'POST' })
      if (!res.ok) {
        throw new Error(`Hot-list refresh returned ${res.status}`)
      }
      const body = await res.json()
      const dashboardRes = await apiFetch('/api/v1/agent/dashboard')
      if (!dashboardRes.ok) {
        throw new Error(`Dashboard reload returned ${dashboardRes.status}`)
      }
      const dashboardBody = await dashboardRes.json()
      setDashboardData(mapApiDashboard({
        ...dashboardBody,
        hot_list_refresh: body,
      }, data))
      setDataState(dashboardBody.sample_data ? 'fallback' : 'live')
      setRefreshState('idle')
    } catch {
      setRefreshState('error')
    }
  }

  return (
    <div id="dashboard" className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
      <div className="mx-auto max-w-[1600px]">
        <main className="min-w-0 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <header className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
                <span>{dashboardData.agent.market}</span>
                <span aria-hidden="true">/</span>
                <span>{sourceLabel}</span>
                <span aria-hidden="true">/</span>
                <span>Updated {dashboardData.agent.lastUpdated}</span>
                {dashboardData.hotListRefresh?.lastRefreshAt && (
                  <>
                    <span aria-hidden="true">/</span>
                    <span>Hot list {dashboardData.hotListRefresh.status} {dashboardData.hotListRefresh.completedAt ?? dashboardData.hotListRefresh.lastRefreshAt}</span>
                  </>
                )}
              </div>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
                Good morning, {dashboardData.agent.name}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={refreshHotList}
                  disabled={dataState !== 'live' || refreshState === 'working'}
                  className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[18px]" aria-hidden="true">sync</span>
                  {refreshState === 'working' ? 'Refreshing' : 'Refresh hot list'}
                </button>
                {refreshState === 'error' && <p className="text-sm font-medium text-error-600">Refresh failed.</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:min-w-[560px]">
              <SummaryMetric label="Open tasks" value={dashboardData.summary.openTasks} />
              <SummaryMetric label="Qualified buyers" value={dashboardData.summary.qualifiedBuyers} />
              <SummaryMetric label="Viewings today" value={dashboardData.summary.viewingsToday} />
              <SummaryMetric label="Escalations" value={dashboardData.summary.openEscalations} tone="warning" />
            </div>
          </header>

          <AgentPerformancePanel performance={dashboardData.performance} />

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.85fr)]">
            <div className="space-y-5">
              <MorningQueue
                items={dashboardData.morningQueue}
                taskActionState={taskActionState}
                actionsEnabled={dataState === 'live'}
                onDone={(taskId) => updateTask(taskId, 'done')}
                onSnooze={(taskId) => updateTask(taskId, 'snoozed')}
              />
              <EscalationInboxPanel
                items={dashboardData.escalationInbox}
                actionState={escalationActionState}
                actionsEnabled={dataState === 'live'}
                onResolve={resolveEscalation}
              />
              <CampaignSnapshot snapshot={dashboardData.campaignSnapshot} />
            </div>
            <div className="space-y-5">
              <ConversationInbox items={dashboardData.conversationInbox} />
              <OvernightBuyerDigest items={dashboardData.overnightBuyerDigest} />
              <TodaysViewings items={dashboardData.todaysViewings} />
              <PersonalMomentum momentum={dashboardData.personalMomentum} />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

function DashboardLoadingState() {
  return (
    <div className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
      <div className="mx-auto max-w-[1600px]">
        <main className="min-w-0 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <header className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <div className="h-4 w-72 animate-pulse rounded bg-neutral-200" />
              <div className="mt-3 h-8 w-80 max-w-full animate-pulse rounded bg-neutral-200" />
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:min-w-[560px]">
              {[0, 1, 2, 3].map((item) => (
                <div key={item} className="rounded-lg border border-neutral-200 bg-white p-4">
                  <div className="h-3 w-20 animate-pulse rounded bg-neutral-200" />
                  <div className="mt-3 h-7 w-12 animate-pulse rounded bg-neutral-200" />
                </div>
              ))}
            </div>
          </header>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.85fr)]">
            <div className="space-y-5">
              <LoadingPanel rows={4} />
              <LoadingPanel rows={3} />
            </div>
            <div className="space-y-5">
              <LoadingPanel rows={3} />
              <LoadingPanel rows={2} />
              <LoadingPanel rows={2} />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

function LoadingPanel({ rows }: { rows: number }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
      <div className="border-b border-neutral-200 px-4 py-4 sm:px-5">
        <div className="h-3 w-28 animate-pulse rounded bg-neutral-200" />
        <div className="mt-3 h-5 w-56 animate-pulse rounded bg-neutral-200" />
      </div>
      <div className="divide-y divide-neutral-200">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="px-4 py-4 sm:px-5">
            <div className="h-4 w-3/4 animate-pulse rounded bg-neutral-200" />
            <div className="mt-3 h-3 w-full animate-pulse rounded bg-neutral-100" />
            <div className="mt-2 h-3 w-2/3 animate-pulse rounded bg-neutral-100" />
          </div>
        ))}
      </div>
    </section>
  )
}

function mapApiDashboard(payload: any, fallback: AgentDashboardData): AgentDashboardData {
  const metrics = payload?.metrics ?? {}
  const hotListRefresh = payload?.hot_list_refresh ?? {}
  const hotLeads = Array.isArray(payload?.hot_leads) ? payload.hot_leads : []
  const conversations = Array.isArray(payload?.conversations) ? payload.conversations : []
  const tasks = Array.isArray(payload?.tasks) ? payload.tasks : []
  const campaigns = Array.isArray(payload?.campaigns) ? payload.campaigns : []
  const viewings = Array.isArray(payload?.viewings) ? payload.viewings : []
  const escalationThreads = Array.isArray(payload?.escalation_threads) ? payload.escalation_threads : []
  const replyDrafts = Array.isArray(payload?.drafts?.reply_drafts) ? payload.drafts.reply_drafts : []
  const outreachDrafts = Array.isArray(payload?.drafts?.outreach_drafts) ? payload.drafts.outreach_drafts : []
  const pages = Array.isArray(payload?.marketing?.pages) ? payload.marketing.pages : []

  const morningQueue: QueueItem[] = [
    ...tasks.slice(0, 4).map((task: any, index: number) => ({
      id: task.task_id ?? `task-${index}`,
      priority: priorityFromTask(task.priority),
      title: task.title ?? 'Review task',
      context: task.description ?? task.metadata?.reason ?? 'Review the next action and update the workspace.',
      buyerName: task.buyer_phone ?? 'Workspace',
      listingName: task.metadata?.entity_label ?? task.listing_id ?? 'Agent task',
      nextAction: task.task_type ? labelFromKey(task.task_type) : 'Open task',
      due: formatShortTime(task.due_at),
    })),
    ...hotLeads.slice(0, Math.max(0, 4 - tasks.length)).map((lead: any, index: number) => ({
      id: lead.id ?? `lead-${index}`,
      priority: lead.urgency_score >= 90 ? 'critical' : lead.urgency_score >= 70 ? 'high' : 'normal',
      title: lead.signal ? `Hot buyer: ${lead.listing?.project ?? 'Property'}` : 'Buyer needs follow-up',
      context: lead.reason ?? lead.last_message ?? 'Buyer activity needs agent review.',
      buyerName: lead.buyer?.name ?? lead.buyer?.phone ?? 'Buyer',
      listingName: lead.listing?.project ?? 'Listing',
      nextAction: lead.next_action ?? 'Open brief',
      due: formatShortTime(lead.due_at),
    })),
    ...outreachDrafts.slice(0, 1).map((draft: any, index: number) => ({
      id: draft.outreach_draft_id ?? `outreach-${index}`,
      priority: 'high' as const,
      title: 'Review owner outreach draft',
      context: draft.body ?? 'Campaign draft is ready for review.',
      buyerName: 'Owner campaign',
      listingName: draft.subject ?? 'Outreach',
      nextAction: 'Review draft',
      due: 'Today',
    })),
    ...pages.filter((page: any) => page.status !== 'published').slice(0, 1).map((page: any, index: number) => ({
      id: page.page_id ?? `page-${index}`,
      priority: 'normal' as const,
      title: `One-pager ready: ${page.title ?? 'Marketing page'}`,
      context: 'Review the seller acquisition page before publishing.',
      buyerName: 'Marketing page',
      listingName: page.slug ?? 'Page',
      nextAction: 'Preview page',
      due: 'Today',
    })),
  ].slice(0, 4)

  const mappedCampaigns: CampaignItem[] = campaigns.slice(0, 4).map((campaign: any, index: number) => ({
    id: campaign.campaign_id ?? `campaign-${index}`,
    name: campaign.name ?? 'Owner outreach campaign',
    audience: campaign.audience?.project
      ? `${campaign.audience.project} owners`
      : campaign.campaign_type?.replaceAll('_', ' ') ?? 'Owner acquisition',
    status: campaign.status === 'active' ? 'live' : campaign.status === 'draft' ? 'warming' : 'needs_action',
    spend: campaign.metrics?.spend ?? 'AED 0',
    leads: Number(campaign.metrics?.uploaded ?? campaign.metrics?.sent ?? 0),
    qualified: Number(campaign.metrics?.qualified ?? campaign.metrics?.replies ?? 0),
    insight: campaign.offer?.cta
      ? `CTA: ${campaign.offer.cta}`
      : 'Review qualified owners, drafts, and compliance blockers before launch.',
  }))

  const buyerDigest: BuyerDigestItem[] = hotLeads.slice(0, 3).map((lead: any, index: number) => ({
    id: lead.id ?? `digest-${index}`,
    buyerName: lead.buyer?.name ?? lead.buyer?.phone ?? 'Buyer',
    intent: intentFromSignal(lead.signal_key),
    message: lead.last_message ?? lead.reason ?? 'Buyer activity needs review.',
    budget: lead.buyer?.budget_aed ? `AED ${Number(lead.buyer.budget_aed).toLocaleString()}` : 'Budget not confirmed',
    target: lead.listing?.project ?? 'Listing',
    recommendedAction: lead.next_action ?? 'Open brief',
    lastSeen: formatShortTime(lead.last_message_at),
  }))

  const mappedConversations: ConversationInboxItem[] = conversations.slice(0, 8).map((conversation: any, index: number) => ({
    id: conversation.conversation_id ?? `conversation-${index}`,
    buyerName: conversation.buyer?.name ?? conversation.buyer?.phone ?? 'Buyer',
    buyerPhone: conversation.buyer?.phone ?? '',
    listingName: conversation.listing?.project ?? conversation.listing_id ?? 'Listing',
    unitNumber: conversation.listing?.unit_number,
    summary: conversation.summary ?? conversation.last_message ?? 'Conversation needs review.',
    nextStep: conversation.next_step_hint ?? (
      Number(conversation.open_escalation_count ?? 0) > 0
        ? 'Reply to open escalation'
        : 'Review buyer context'
    ),
    lastMessage: conversation.last_message ?? 'No message preview',
    lastSeen: formatShortTime(conversation.last_message_at ?? conversation.updated_at),
    messageCount: Number(conversation.message_count ?? 0),
    offerCount: Number(conversation.offer_count ?? 0),
    openEscalationCount: Number(conversation.open_escalation_count ?? 0),
    interestLevel: conversation.interest_level,
  }))

  const mappedViewings: ViewingItem[] = viewings.slice(0, 4).map((viewing: any, index: number) => ({
    id: viewing.viewing_id ?? `viewing-${index}`,
    time: formatShortTime(viewing.scheduled_for),
    buyerName: viewing.buyer_phone ?? 'Buyer',
    property: viewing.listing_id ?? 'Property',
    location: viewing.tenant_notice_required ? 'Tenant notice required' : 'Access check',
    status: viewing.status === 'confirmed' ? 'confirmed' : viewing.status === 'completed' ? 'follow_up' : 'pending',
    preparation: viewing.access_notes ?? 'Confirm access and send reminder.',
  }))

  const mappedEscalations: EscalationThreadItem[] = escalationThreads.slice(0, 4).map((thread: any, index: number) => ({
    id: thread.thread_id ?? `escalation-${index}`,
    token: thread.envelope_token,
    category: thread.category ?? 'other',
    state: escalationState(thread.state),
    urgency: escalationUrgency(thread.urgency),
    buyerName: thread.buyer?.name ?? thread.buyer?.phone ?? thread.buyer_phone ?? 'Buyer',
    buyerPhone: thread.buyer?.phone ?? thread.buyer_phone ?? '',
    listingName: thread.listing?.project ?? thread.listing_id ?? 'Listing',
    unitNumber: thread.listing?.unit_number,
    latestQuestion: thread.latest_question ?? thread.questions?.[thread.questions.length - 1]?.question_text ?? 'Agent review needed.',
    questionCount: Number(thread.question_count ?? thread.questions?.length ?? 1),
    lastBuyerMessageAt: formatShortTime(thread.last_buyer_message_at),
    openedAt: formatShortTime(thread.opened_at),
    routeExpiresAt: thread.latest_route_expires_at ? formatShortTime(thread.latest_route_expires_at) : null,
    questions: Array.isArray(thread.questions)
      ? thread.questions.map((question: any, questionIndex: number) => ({
          id: question.question_id ?? `${thread.thread_id ?? index}-q-${questionIndex}`,
          text: question.question_text ?? '',
          addedAt: formatShortTime(question.added_at),
          resolvedAt: question.resolved_at ? formatShortTime(question.resolved_at) : null,
        }))
      : [],
  }))

  return {
    agent: {
      name: payload?.agent?.display_name ?? fallback.agent.name,
      brokerage: payload?.brokerage?.name ?? fallback.agent.brokerage,
      market: fallback.agent.market,
      lastUpdated: payload?.generated_at ? formatShortTime(payload.generated_at) : fallback.agent.lastUpdated,
    },
    hotListRefresh: {
      status: hotListRefresh.status ?? 'not_run',
      trigger: hotListRefresh.trigger ?? null,
      lastRefreshAt: hotListRefresh.last_refresh_at ? formatShortTime(hotListRefresh.last_refresh_at) : null,
      completedAt: hotListRefresh.completed_at ? formatShortTime(hotListRefresh.completed_at) : null,
      assignmentCount: Number(hotListRefresh.assignment_count ?? 0),
      taskCount: Number(hotListRefresh.task_count ?? 0),
      draftCount: Number(hotListRefresh.draft_count ?? 0),
      error: hotListRefresh.error ?? null,
    },
    summary: {
      openTasks: Number(metrics.open_tasks ?? morningQueue.length),
      qualifiedBuyers: Number(metrics.hot_leads ?? buyerDigest.length),
      viewingsToday: Number(metrics.viewings_today ?? mappedViewings.length),
      offersAtRisk: Number(metrics.stale_leads ?? 0),
      openEscalations: Number(metrics.open_escalations ?? mappedEscalations.length),
    },
    performance: mapPerformance(payload?.performance, fallback.performance),
    conversationInbox: mappedConversations.length ? mappedConversations : fallback.conversationInbox,
    morningQueue: morningQueue.length ? morningQueue : fallback.morningQueue,
    escalationInbox: mappedEscalations.length ? mappedEscalations : fallback.escalationInbox,
    campaignSnapshot: {
      headline: mappedCampaigns.length
        ? 'Owner outreach and page activity are ready for review.'
        : fallback.campaignSnapshot.headline,
      activeCampaigns: Number(metrics.active_campaigns ?? mappedCampaigns.length),
      newLeads: Number(metrics.new_owner_leads ?? 0),
      qualifiedLeads: mappedCampaigns.reduce((sum, campaign) => sum + campaign.qualified, 0),
      responseRate: fallback.campaignSnapshot.responseRate,
      costPerQualifiedLead: fallback.campaignSnapshot.costPerQualifiedLead,
      campaigns: mappedCampaigns.length ? mappedCampaigns : fallback.campaignSnapshot.campaigns,
    },
    overnightBuyerDigest: buyerDigest.length ? buyerDigest : fallback.overnightBuyerDigest,
    todaysViewings: mappedViewings.length ? mappedViewings : fallback.todaysViewings,
    personalMomentum: {
      ...fallback.personalMomentum,
      stats: [
        {
          label: 'Replies awaiting review',
          value: String(replyDrafts.length),
          helper: 'Agent approval stays in control',
          trend: replyDrafts.length > 0 ? 'up' : 'flat',
        },
        {
          label: 'Campaign drafts ready',
          value: String(outreachDrafts.length),
          helper: 'Owner outreach opportunities',
          trend: outreachDrafts.length > 0 ? 'up' : 'flat',
        },
        {
          label: 'Page events this week',
          value: String(payload?.marketing?.events_7d ?? 0),
          helper: 'Seller one-pager engagement',
          trend: (payload?.marketing?.events_7d ?? 0) > 0 ? 'up' : 'flat',
        },
      ],
    },
  }
}

function mapPerformance(payload: any, fallback: AgentDashboardData['performance']): AgentDashboardData['performance'] {
  const windows = Array.isArray(payload?.windows)
    ? payload.windows.map((window: any) => mapPerformanceWindow(window)).filter(Boolean)
    : []
  const mappedWindows = windows.length ? windows : fallback.windows
  const primary = payload?.primary ? mapPerformanceWindow(payload.primary) : mappedWindows[0] ?? fallback.primary
  return {
    scope: payload?.scope ?? fallback.scope,
    agentUserId: payload?.agent_user_id ?? fallback.agentUserId ?? null,
    generatedAt: payload?.generated_at ?? fallback.generatedAt ?? null,
    primary,
    windows: mappedWindows,
  }
}

function mapPerformanceWindow(window: any): AgentDashboardData['performance']['primary'] {
  const metrics = window?.metrics ?? {}
  return {
    key: window?.key ?? 'today',
    label: window?.label ?? labelFromKey(window?.key ?? 'today'),
    startAt: window?.start_at ?? null,
    endAt: window?.end_at ?? null,
    metrics: {
      newBuyerConversations: Number(metrics.new_buyer_conversations ?? 0),
      escalationsHandled: Number(metrics.escalations_handled ?? 0),
      avgResponseMinutes: metrics.avg_response_minutes == null ? null : Number(metrics.avg_response_minutes),
      followUpsSent: Number(metrics.follow_ups_sent ?? 0),
      viewingsProposed: Number(metrics.viewings_proposed ?? 0),
      viewingsConfirmed: Number(metrics.viewings_confirmed ?? 0),
      viewingsCompleted: Number(metrics.viewings_completed ?? 0),
      offersDetected: Number(metrics.offers_detected ?? 0),
      hotLeadsActive: Number(metrics.hot_leads_active ?? 0),
      tasksOverdue: Number(metrics.tasks_overdue ?? 0),
    },
  }
}

function priorityFromTask(priority: string | undefined): QueuePriority {
  if (priority === 'critical') return 'critical'
  if (priority === 'high') return 'high'
  return 'normal'
}

function intentFromSignal(signal: string | undefined): BuyerIntent {
  if (signal === 'firm_offer') return 'offer_ready'
  if (signal === 'ready_to_view') return 'viewing_ready'
  if (signal === 'needs_financing') return 'financing'
  return 'researching'
}

function escalationState(state: string | undefined): EscalationState {
  if (state === 'debouncing' || state === 'open' || state === 'updated' || state === 'resolved' || state === 'timed_out' || state === 'opt_out_closed') {
    return state
  }
  return 'open'
}

function escalationUrgency(urgency: string | undefined): EscalationUrgency {
  if (urgency === 'critical' || urgency === 'high' || urgency === 'normal') {
    return urgency
  }
  return 'normal'
}

function labelFromKey(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatShortTime(value: string | null | undefined): string {
  if (!value) return 'Today'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function AgentPerformancePanel({ performance }: { performance: AgentDashboardData['performance'] }) {
  const windows = performance.windows.length ? performance.windows : [performance.primary]
  return (
    <section className="mb-5 rounded-lg border border-neutral-200 bg-white shadow-card-sm">
      <div className="flex flex-col gap-1 border-b border-neutral-200 px-4 py-4 sm:px-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Agent performance</p>
        <h2 className="text-base font-semibold text-neutral-900">Current-agent activity</h2>
      </div>
      <div className="grid divide-y divide-neutral-200 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
        {windows.map((window) => (
          <div key={window.key} className="px-4 py-4 sm:px-5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-neutral-900">{window.label}</p>
              <span className="rounded-full bg-neutral-100 px-2 py-1 text-[11px] font-medium text-neutral-600">
                {window.metrics.avgResponseMinutes == null ? 'No response avg' : `${window.metrics.avgResponseMinutes}m avg`}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <PerformanceValue label="New buyers" value={window.metrics.newBuyerConversations} />
              <PerformanceValue label="Escalations handled" value={window.metrics.escalationsHandled} />
              <PerformanceValue label="Follow-ups sent" value={window.metrics.followUpsSent} />
              <PerformanceValue label="Offers detected" value={window.metrics.offersDetected} />
              <PerformanceValue label="Viewings proposed" value={window.metrics.viewingsProposed} />
              <PerformanceValue label="Viewings confirmed" value={window.metrics.viewingsConfirmed} />
              <PerformanceValue label="Viewings completed" value={window.metrics.viewingsCompleted} />
              <PerformanceValue label="Hot leads active" value={window.metrics.hotLeadsActive} />
              <PerformanceValue label="Tasks overdue" value={window.metrics.tasksOverdue} tone={window.metrics.tasksOverdue > 0 ? 'warning' : 'default'} />
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function PerformanceValue({ label, value, tone = 'default' }: { label: string; value: number; tone?: 'default' | 'warning' }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-neutral-500">{label}</p>
      <p className={tone === 'warning' ? 'mt-1 text-lg font-semibold text-amber-700' : 'mt-1 text-lg font-semibold text-neutral-900'}>
        {Number(value || 0).toLocaleString()}
      </p>
    </div>
  )
}

function SummaryMetric({
  label,
  value,
  tone = 'default',
}: {
  label: string
  value: number
  tone?: 'default' | 'warning'
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-3 shadow-card-sm">
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className={`mt-1 font-mono text-xl font-semibold ${tone === 'warning' ? 'text-warning-700' : 'text-neutral-900'}`}>
        {value}
      </p>
    </div>
  )
}

function Section({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string
  title: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
      <div className="flex items-start justify-between gap-3 border-b border-neutral-200 px-4 py-4 sm:px-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{eyebrow}</p>
          <h2 className="mt-1 text-base font-semibold text-neutral-900">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function MorningQueue({
  items,
  taskActionState,
  actionsEnabled,
  onDone,
  onSnooze,
}: {
  items: QueueItem[]
  taskActionState: Record<string, 'done' | 'snoozed' | 'error' | 'working'>
  actionsEnabled: boolean
  onDone: (taskId: string) => void
  onSnooze: (taskId: string) => void
}) {
  return (
    <Section
      eyebrow="Morning Queue"
      title="What needs agent judgment first"
    >
      <div className="divide-y divide-neutral-200">
        {items.map((item) => (
          <div key={item.id} className="grid gap-4 px-4 py-4 sm:px-5 lg:grid-cols-[minmax(0,1fr)_170px]">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <PriorityPill priority={item.priority} />
                <span className="font-mono text-xs text-neutral-500">{item.due}</span>
              </div>
              <h3 className="mt-2 text-sm font-semibold text-neutral-900">{item.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-neutral-600">{item.context}</p>
              <p className="mt-3 text-xs text-neutral-500">
                <span className="font-medium text-neutral-700">{item.buyerName}</span>
                <span aria-hidden="true"> · </span>
                {item.listingName}
              </p>
            </div>
            <div className="flex items-start justify-between gap-3 lg:block lg:text-right">
              <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Next action</p>
              <p className="mt-1 text-sm font-medium leading-snug text-brand-700">{item.nextAction}</p>
              <div className="mt-3 flex flex-wrap gap-2 lg:justify-end">
                <button
                  type="button"
                  onClick={() => onDone(item.id)}
                  disabled={!actionsEnabled || taskActionState[item.id] === 'working'}
                  className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                    check
                  </span>
                  Done
                </button>
                <button
                  type="button"
                  onClick={() => onSnooze(item.id)}
                  disabled={!actionsEnabled || taskActionState[item.id] === 'working'}
                  className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                    schedule
                  </span>
                  Snooze
                </button>
              </div>
              {taskActionState[item.id] === 'error' && (
                <p className="mt-2 text-xs font-medium text-error-600">Could not update this task.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function ConversationInbox({ items }: { items: ConversationInboxItem[] }) {
  return (
    <Section eyebrow="Conversation Inbox" title="Live buyer threads">
      <div className="divide-y divide-neutral-200">
        {items.length === 0 ? (
          <div className="px-4 py-6 sm:px-5">
            <p className="text-sm font-medium text-neutral-800">No buyer conversations yet.</p>
            <p className="mt-1 text-sm text-neutral-500">Persona and WhatsApp conversations will appear here once buyers engage.</p>
          </div>
        ) : (
          items.map((item) => (
            <Link key={item.id} href={`/agent/conversations/${item.id}`} className="block px-4 py-4 transition-colors hover:bg-neutral-50 sm:px-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate text-sm font-semibold text-neutral-900">{item.buyerName}</h3>
                    {item.openEscalationCount > 0 && (
                      <span className="rounded-full bg-warning-50 px-2 py-0.5 text-[11px] font-semibold text-warning-700">
                        {item.openEscalationCount} escalation{item.openEscalationCount === 1 ? '' : 's'}
                      </span>
                    )}
                    {item.offerCount > 0 && (
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-700">
                        {item.offerCount} offer{item.offerCount === 1 ? '' : 's'}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 truncate text-xs text-neutral-500">
                    {item.listingName}{item.unitNumber ? ` · ${item.unitNumber}` : ''} · {item.lastSeen}
                  </p>
                </div>
                <p className="shrink-0 font-mono text-xs text-neutral-500">{item.messageCount} msgs</p>
              </div>
              <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-neutral-700">{item.summary}</p>
              <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-neutral-500">{item.lastMessage}</p>
              <div className="mt-3 rounded-md bg-neutral-50 px-3 py-2 text-xs font-medium text-neutral-700">
                {item.nextStep}
              </div>
            </Link>
          ))
        )}
      </div>
    </Section>
  )
}

function EscalationInboxPanel({
  items,
  actionState,
  actionsEnabled,
  onResolve,
}: {
  items: EscalationThreadItem[]
  actionState: Record<string, 'resolved' | 'error' | 'working'>
  actionsEnabled: boolean
  onResolve: (threadId: string) => void
}) {
  return (
    <Section
      eyebrow="Escalation Inbox"
      title="Questions waiting for agent judgment"
      action={
        <Link href="/agent/escalations" className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-neutral-300 text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-brand-700" aria-label="Open escalation inbox" title="Open escalation inbox">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">support_agent</span>
        </Link>
      }
    >
      <div className="divide-y divide-neutral-200">
        {items.length === 0 ? (
          <div className="px-4 py-6 sm:px-5">
            <p className="text-sm font-medium text-neutral-800">No open escalations.</p>
            <p className="mt-1 text-sm text-neutral-500">Dalya will surface buyer questions here when agent judgment is needed.</p>
          </div>
        ) : items.map((item) => (
          <div key={item.id} className="grid gap-4 px-4 py-4 sm:px-5 lg:grid-cols-[minmax(0,1fr)_160px]">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <EscalationUrgencyPill urgency={item.urgency} />
                <EscalationStatePill state={item.state} />
                <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
                  {labelFromKey(item.category)}
                </span>
              </div>
              <h3 className="mt-2 text-sm font-semibold text-neutral-900">{item.buyerName}</h3>
              <p className="mt-1 text-xs text-neutral-500">
                {item.listingName}{item.unitNumber ? ` · ${item.unitNumber}` : ''}
              </p>
              <p className="mt-3 text-sm leading-relaxed text-neutral-700">{item.latestQuestion}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-neutral-500">
                <span>{item.questionCount} question{item.questionCount === 1 ? '' : 's'}</span>
                <span aria-hidden="true">·</span>
                <span>Last buyer message {item.lastBuyerMessageAt}</span>
                {item.token && (
                  <>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono">Ref {item.token}</span>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-start justify-between gap-3 lg:block lg:text-right">
              <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Action</p>
              <p className="mt-1 text-sm font-medium leading-snug text-brand-700">Reply from inbox or resolve</p>
              <div className="mt-3 flex flex-wrap gap-2 lg:justify-end">
                <button
                  type="button"
                  onClick={() => onResolve(item.id)}
                  disabled={!actionsEnabled || actionState[item.id] === 'working'}
                  className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]" aria-hidden="true">check_circle</span>
                  Resolve
                </button>
              </div>
              {actionState[item.id] === 'error' && (
                <p className="mt-2 text-xs font-medium text-error-600">Could not resolve this escalation.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function CampaignSnapshot({ snapshot }: { snapshot: CampaignSnapshotType }) {
  return (
    <Section
      eyebrow="Campaign Snapshot"
      title={snapshot.headline}
      action={<IconButton icon="tune" label="Optimize" />}
    >
      <div id="campaigns" className="grid gap-3 border-b border-neutral-200 px-4 py-4 sm:grid-cols-4 sm:px-5">
        <CompactMetric label="Active" value={snapshot.activeCampaigns.toString()} />
        <CompactMetric label="New leads" value={snapshot.newLeads.toString()} />
        <CompactMetric label="Qualified" value={snapshot.qualifiedLeads.toString()} />
        <CompactMetric label="CPQL" value={snapshot.costPerQualifiedLead} />
      </div>
      <div className="divide-y divide-neutral-200">
        {snapshot.campaigns.map((campaign) => (
          <CampaignRow key={campaign.id} campaign={campaign} />
        ))}
      </div>
    </Section>
  )
}

function CampaignRow({ campaign }: { campaign: CampaignItem }) {
  const rate = Math.max(0, Math.min(100, Math.round((campaign.qualified / Math.max(campaign.leads, 1)) * 100)))

  return (
    <div className="px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-neutral-900">{campaign.name}</h3>
            <CampaignStatusPill status={campaign.status} />
          </div>
          <p className="mt-1 text-xs text-neutral-500">{campaign.audience}</p>
        </div>
        <div className="flex gap-4 text-left sm:text-right">
          <MiniStat label="Spend" value={campaign.spend} />
          <MiniStat label="Qualified" value={`${campaign.qualified}/${campaign.leads}`} />
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-neutral-100" aria-label={`${rate}% qualified lead rate`}>
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${rate}%` }} />
      </div>
      <p className="mt-3 text-sm leading-relaxed text-neutral-600">{campaign.insight}</p>
    </div>
  )
}

function OvernightBuyerDigest({ items }: { items: BuyerDigestItem[] }) {
  return (
    <Section
      eyebrow="Overnight Buyer Digest"
      title="Signals that arrived while the desk was offline"
      action={<IconButton icon="mark_chat_unread" label="Open inbox" />}
    >
      <div id="inbox" className="divide-y divide-neutral-200">
        {items.map((item) => (
          <div key={item.id} className="px-4 py-4 sm:px-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-neutral-900">{item.buyerName}</h3>
                <p className="mt-1 text-xs text-neutral-500">{item.target}</p>
              </div>
              <IntentPill intent={item.intent} />
            </div>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">{item.message}</p>
            <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <Fact label="Budget" value={item.budget} />
              <Fact label="Last seen" value={item.lastSeen} />
            </div>
            <p className="mt-3 text-sm font-medium leading-snug text-brand-700">{item.recommendedAction}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}

function TodaysViewings({ items }: { items: ViewingItem[] }) {
  return (
    <Section
      eyebrow="Today's Viewings"
      title="Confirmed and at-risk appointments"
      action={
        <Link href="/agent/viewings" className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-neutral-300 text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-brand-700" aria-label="Open viewing calendar" title="Open viewing calendar">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">calendar_month</span>
        </Link>
      }
    >
      <div id="listings" className="divide-y divide-neutral-200">
        {items.map((item) => (
          <div key={item.id} className="grid grid-cols-[56px_minmax(0,1fr)] gap-3 px-4 py-4 sm:px-5">
            <div className="font-mono text-sm font-semibold text-neutral-900">{item.time}</div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-neutral-900">{item.buyerName}</h3>
                <ViewingStatusPill status={item.status} />
              </div>
              <p className="mt-1 text-sm text-neutral-700">{item.property}</p>
              <p className="mt-1 text-xs text-neutral-500">{item.location}</p>
              <p className="mt-3 text-sm leading-relaxed text-neutral-600">{item.preparation}</p>
              <Link href={`/agent/viewings/${item.id}`} className="mt-3 inline-flex text-sm font-medium text-brand-700 hover:text-brand-800">
                Open viewing detail
              </Link>
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function PersonalMomentum({ momentum }: { momentum: AgentDashboardData['personalMomentum'] }) {
  return (
    <Section
      eyebrow="Personal Momentum"
      title={momentum.weekLabel}
      action={<IconButton icon="insights" label="Details" />}
    >
      <div id="pages" className="grid gap-3 px-4 py-4 sm:px-5">
        {momentum.stats.map((stat) => (
          <MomentumStatRow key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-2 border-y border-neutral-200 bg-neutral-50 px-4 py-4 sm:grid-cols-3 sm:px-5">
        {momentum.streaks.map((streak) => (
          <MomentumStreakTile key={streak.label} streak={streak} />
        ))}
      </div>
      <div id="settings" className="px-4 py-4 sm:px-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Focus</p>
        <p className="mt-2 text-sm leading-relaxed text-neutral-700">{momentum.focus}</p>
      </div>
    </Section>
  )
}

function CompactMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-lg font-semibold text-neutral-900">{value}</p>
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold text-neutral-900">{value}</p>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-neutral-50 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-neutral-800">{value}</p>
    </div>
  )
}

function MomentumStatRow({ stat }: { stat: MomentumStat }) {
  const icon = stat.trend === 'up' ? 'trending_up' : stat.trend === 'down' ? 'trending_down' : 'trending_flat'
  const tone = stat.trend === 'down' ? 'text-warning-700' : stat.trend === 'up' ? 'text-success-700' : 'text-neutral-500'

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-neutral-800">{stat.label}</p>
        <p className="mt-1 text-xs text-neutral-500">{stat.helper}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className={`material-symbols-outlined ${tone}`} aria-hidden="true" style={{ fontSize: 19 }}>
          {icon}
        </span>
        <span className="font-mono text-lg font-semibold text-neutral-900">{stat.value}</span>
      </div>
    </div>
  )
}

function MomentumStreakTile({ streak }: { streak: MomentumStreak }) {
  const toneClass =
    streak.tone === 'success'
      ? 'bg-success-50 text-success-700'
      : streak.tone === 'warning'
        ? 'bg-warning-50 text-warning-700'
        : 'bg-brand-50 text-brand-700'

  return (
    <div className={`rounded-md px-3 py-2 ${toneClass}`}>
      <p className="font-mono text-lg font-semibold">{streak.value}</p>
      <p className="mt-1 text-xs font-medium leading-snug">{streak.label}</p>
    </div>
  )
}

function IconButton({ icon, label }: { icon: string; label: string }) {
  return (
    <button
      type="button"
      className="inline-flex h-9 items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
    >
      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
        {icon}
      </span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}

function PriorityPill({ priority }: { priority: QueuePriority }) {
  const label: Record<QueuePriority, string> = {
    critical: 'Critical',
    high: 'High',
    normal: 'Normal',
  }
  const tone: Record<QueuePriority, string> = {
    critical: 'border-error-100 bg-error-50 text-error-700',
    high: 'border-warning-100 bg-warning-50 text-warning-700',
    normal: 'border-neutral-200 bg-neutral-100 text-neutral-700',
  }

  return <Pill className={tone[priority]}>{label[priority]}</Pill>
}

function CampaignStatusPill({ status }: { status: CampaignStatus }) {
  const label: Record<CampaignStatus, string> = {
    live: 'Live',
    warming: 'Warming',
    needs_action: 'Needs action',
  }
  const tone: Record<CampaignStatus, string> = {
    live: 'border-success-100 bg-success-50 text-success-700',
    warming: 'border-brand-100 bg-brand-50 text-brand-700',
    needs_action: 'border-warning-100 bg-warning-50 text-warning-700',
  }

  return <Pill className={tone[status]}>{label[status]}</Pill>
}

function IntentPill({ intent }: { intent: BuyerIntent }) {
  const label: Record<BuyerIntent, string> = {
    offer_ready: 'Offer-ready',
    viewing_ready: 'Viewing-ready',
    financing: 'Financing',
    researching: 'Researching',
  }
  const tone: Record<BuyerIntent, string> = {
    offer_ready: 'border-success-100 bg-success-50 text-success-700',
    viewing_ready: 'border-brand-100 bg-brand-50 text-brand-700',
    financing: 'border-warning-100 bg-warning-50 text-warning-700',
    researching: 'border-neutral-200 bg-neutral-100 text-neutral-700',
  }

  return <Pill className={tone[intent]}>{label[intent]}</Pill>
}

function ViewingStatusPill({ status }: { status: ViewingStatus }) {
  const label: Record<ViewingStatus, string> = {
    confirmed: 'Confirmed',
    pending: 'Pending',
    follow_up: 'Follow-up',
  }
  const tone: Record<ViewingStatus, string> = {
    confirmed: 'border-success-100 bg-success-50 text-success-700',
    pending: 'border-warning-100 bg-warning-50 text-warning-700',
    follow_up: 'border-brand-100 bg-brand-50 text-brand-700',
  }

  return <Pill className={tone[status]}>{label[status]}</Pill>
}

function EscalationUrgencyPill({ urgency }: { urgency: EscalationUrgency }) {
  const label: Record<EscalationUrgency, string> = {
    critical: 'Critical',
    high: 'High',
    normal: 'Normal',
  }
  const tone: Record<EscalationUrgency, string> = {
    critical: 'border-error-100 bg-error-50 text-error-700',
    high: 'border-warning-100 bg-warning-50 text-warning-700',
    normal: 'border-neutral-200 bg-neutral-100 text-neutral-700',
  }

  return <Pill className={tone[urgency]}>{label[urgency]}</Pill>
}

function EscalationStatePill({ state }: { state: EscalationState }) {
  const label: Record<EscalationState, string> = {
    debouncing: 'Bundling',
    open: 'Open',
    updated: 'Updated',
    resolved: 'Resolved',
    timed_out: 'Timed out',
    opt_out_closed: 'Opt-out closed',
  }
  const tone: Record<EscalationState, string> = {
    debouncing: 'border-brand-100 bg-brand-50 text-brand-700',
    open: 'border-success-100 bg-success-50 text-success-700',
    updated: 'border-warning-100 bg-warning-50 text-warning-700',
    resolved: 'border-neutral-200 bg-neutral-100 text-neutral-700',
    timed_out: 'border-error-100 bg-error-50 text-error-700',
    opt_out_closed: 'border-neutral-200 bg-neutral-100 text-neutral-700',
  }

  return <Pill className={tone[state]}>{label[state]}</Pill>
}

function Pill({ children, className }: { children: ReactNode; className: string }) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}>
      {children}
    </span>
  )
}
