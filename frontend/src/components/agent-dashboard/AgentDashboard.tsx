'use client'

import { useEffect, useState, type ReactNode } from 'react'
import {
  normalizeDealReadiness,
  type DealReadinessMetadata,
} from '@/components/readiness/deal-readiness'
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
  OutreachDraftItem,
  QueueItem,
  QueuePriority,
  ReplyDraftItem,
  ViewingItem,
} from './types'
import { TodayQueue } from './TodayQueue'
import { buildTodayQueue } from './today-queue'

interface AgentDashboardProps {
  data: AgentDashboardData
}

export function AgentDashboard({ data }: AgentDashboardProps) {
  const [dashboardData, setDashboardData] = useState<AgentDashboardData | null>(null)
  const [dataState, setDataState] = useState<'loading' | 'live' | 'error'>('loading')
  const [taskActionState, setTaskActionState] = useState<Record<string, 'done' | 'snoozed' | 'error' | 'working'>>({})
  const [escalationActionState, setEscalationActionState] = useState<Record<string, 'resolved' | 'error' | 'working'>>({})
  const [refreshState, setRefreshState] = useState<'idle' | 'working' | 'error'>('idle')
  const [reloadKey, setReloadKey] = useState(0)
  const [showMore, setShowMore] = useState(false)

  useEffect(() => {
    let active = true

    async function loadDashboard() {
      if (reloadKey > 0) {
        // Retry: drop back to the loading skeleton instead of stale sample data.
        setDashboardData(null)
        setDataState('loading')
      }
      try {
        const res = await apiFetch('/api/v1/agent/dashboard')
        if (!res.ok) {
          throw new Error(`Dashboard API returned ${res.status}`)
        }
        const body = await res.json()
        if (!active) return
        setDashboardData(mapApiDashboard(body, data))
        setDataState('live')
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
  }, [data, reloadKey])

  const sourceLabel = dataState === 'live'
    ? 'Live workspace'
    : dataState === 'loading'
      ? 'Loading workspace'
      : 'Connection error'

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
      setDataState('live')
      setRefreshState('idle')
    } catch {
      setRefreshState('error')
    }
  }

  const actionsEnabled = dataState === 'live'
  const needsReply = sortNeedsReply(dashboardData.conversationInbox)
  const todayQueue = buildTodayQueue({ data: dashboardData, needsReply })

  const dayIsClear = todayQueue.length === 0

  function retry() {
    setReloadKey((key) => key + 1)
  }

  return (
    <div id="dashboard" className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
      <div className="mx-auto max-w-[1600px]">
        <main className="min-w-0 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <header className="mb-4 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
                <span>{dashboardData.agent.market}</span>
                <span aria-hidden="true">/</span>
                <span className={dataState === 'error' ? 'font-medium text-error-700' : undefined}>{sourceLabel}</span>
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
                  disabled={!actionsEnabled || refreshState === 'working'}
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

          {dataState === 'error' && (
            <div className="mb-4 flex flex-col gap-3 rounded-lg border border-error-100 bg-error-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-2">
                <span className="material-symbols-outlined text-[20px] text-error-600" aria-hidden="true">cloud_off</span>
                <div>
                  <p className="text-sm font-semibold text-error-700">Couldn&apos;t load your live workspace</p>
                  <p className="mt-0.5 text-sm text-error-700/80">Showing the local dashboard fallback. Actions are paused until we reconnect.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={retry}
                className="inline-flex shrink-0 items-center gap-2 self-start rounded-md border border-error-200 bg-white px-3 py-2 text-sm font-medium text-error-700 transition-colors hover:bg-error-50 sm:self-auto"
              >
                <span className="material-symbols-outlined text-[18px]" aria-hidden="true">refresh</span>
                Retry
              </button>
            </div>
          )}

          <div className="mx-auto max-w-4xl space-y-5">
            {dayIsClear ? (
              <DayIsClear sourceLabel={sourceLabel} emptyState={dashboardData.emptyState} />
            ) : (
              <TodayQueue
                items={todayQueue}
                actionsEnabled={actionsEnabled}
                taskActionState={taskActionState}
                escalationActionState={escalationActionState}
                refreshState={refreshState}
                onTaskDone={(taskId) => updateTask(taskId, 'done')}
                onTaskSnooze={(taskId) => updateTask(taskId, 'snoozed')}
                onResolveEscalation={resolveEscalation}
                onRefreshHotList={refreshHotList}
              />
            )}
          </div>

          {/* Analytics — demoted below the fold behind a compact toggle. */}
          <div className="mx-auto mt-8 max-w-4xl">
            <button
              type="button"
              onClick={() => setShowMore((value) => !value)}
              aria-expanded={showMore}
              className="flex w-full items-center justify-between rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
            >
              <span className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-neutral-500" aria-hidden="true">bar_chart</span>
                More — performance, campaigns &amp; momentum
              </span>
              <span className="material-symbols-outlined text-[20px] text-neutral-500" aria-hidden="true">
                {showMore ? 'expand_less' : 'expand_more'}
              </span>
            </button>
            {showMore && (
              <div className="mt-5 space-y-5">
                <AgentPerformancePanel performance={dashboardData.performance} />
                <div className="grid gap-5 xl:grid-cols-2">
                  <CampaignSnapshot snapshot={dashboardData.campaignSnapshot} />
                  <OvernightBuyerDigest items={dashboardData.overnightBuyerDigest} />
                  <PersonalMomentum momentum={dashboardData.personalMomentum} />
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

function sortNeedsReply(items: ConversationInboxItem[]): ConversationInboxItem[] {
  // The server now provides an authoritative `needs_reply` signal (DAL-170E5),
  // derived from last buyer-vs-agent message timestamps and opt-out state, and
  // already ranks needs_reply threads first. We re-assert that ordering here so
  // it survives any client-side reshuffling, then fall back to a lightweight
  // urgency heuristic (open escalations > offers > high interest) as a tiebreak.
  function score(item: ConversationInboxItem): number {
    let value = item.needsReply ? 1000 : 0
    if (item.openEscalationCount > 0) value += 100 + item.openEscalationCount
    if (item.offerCount > 0) value += 40 + item.offerCount
    if ((item.interestLevel ?? '').toLowerCase() === 'high') value += 10
    return value
  }
  return [...items].sort((a, b) => score(b) - score(a))
}

function DayIsClear({
  sourceLabel,
  emptyState,
}: {
  sourceLabel: string
  emptyState?: AgentDashboardData['emptyState']
}) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white px-6 py-12 text-center shadow-card-sm">
      <span className="material-symbols-outlined text-[40px] text-success-600" aria-hidden="true">task_alt</span>
      <h2 className="mt-3 text-lg font-semibold text-neutral-900">
        {emptyState ? 'Workspace is ready' : 'Your day is clear'}
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-neutral-600">
        {emptyState?.message ?? (
          <>
            No buyers waiting on a reply, no hot signals, no drafts to review, and no viewings or escalations open right now.
            New activity lands here the moment a buyer engages.
          </>
        )}
      </p>
      <p className="mt-3 text-xs text-neutral-400">{sourceLabel}</p>
    </section>
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

interface ApiBuyer {
  readonly name?: string | null
  readonly phone?: string | null
  readonly budget_aed?: number | null
  readonly stage?: string | null
}

interface ApiListing {
  readonly listing_id?: string | null
  readonly project?: string | null
  readonly unit_number?: string | null
  readonly asking_price_aed?: number | null
}

interface ApiTask {
  readonly task_id?: string | null
  readonly task_type?: string | null
  readonly title?: string | null
  readonly description?: string | null
  readonly priority?: string | null
  readonly listing_id?: string | null
  readonly buyer_phone?: string | null
  readonly due_at?: string | null
  readonly created_at?: string | null
  readonly metadata?: {
    readonly reason?: string | null
    readonly entity_label?: string | null
  } | null
}

interface ApiReadinessShadow {
  readonly deal_readiness?: DealReadinessMetadata | null
}

interface ApiHotLead {
  readonly id?: string | null
  readonly buyer?: ApiBuyer | null
  readonly listing?: ApiListing | null
  readonly signal?: string | null
  readonly signal_key?: string | null
  readonly next_action?: string | null
  readonly reason?: string | null
  readonly urgency_score?: number | null
  readonly last_message?: string | null
  readonly last_message_at?: string | null
  readonly due_at?: string | null
  readonly readiness_shadow?: ApiReadinessShadow | null
}

interface ApiCampaign {
  readonly campaign_id?: string | null
  readonly name?: string | null
  readonly campaign_type?: string | null
  readonly status?: string | null
  readonly audience?: {
    readonly project?: string | null
  } | null
  readonly offer?: {
    readonly cta?: string | null
  } | null
  readonly metrics?: {
    readonly spend?: string | null
    readonly uploaded?: number | string | null
    readonly sent?: number | string | null
    readonly qualified?: number | string | null
    readonly replies?: number | string | null
  } | null
}

interface ApiMarketingPage {
  readonly page_id?: string | null
  readonly title?: string | null
  readonly slug?: string | null
  readonly status?: string | null
}

interface ApiConversation {
  readonly conversation_id?: string | null
  readonly buyer?: ApiBuyer | null
  readonly listing?: ApiListing | null
  readonly listing_id?: string | null
  readonly summary?: string | null
  readonly last_message?: string | null
  readonly next_step_hint?: string | null
  readonly interest_level?: string | null
  readonly last_message_at?: string | null
  readonly updated_at?: string | null
  readonly message_count?: number | null
  readonly offer_count?: number | null
  readonly open_escalation_count?: number | null
  readonly needs_reply?: boolean | null
  readonly needs_reply_reason?: string | null
  readonly has_pending_draft?: boolean | null
  readonly last_buyer_message_at?: string | null
  readonly last_agent_response_at?: string | null
  readonly deal_readiness?: DealReadinessMetadata | null
}

interface ApiViewing {
  readonly viewing_id?: string | null
  readonly scheduled_for?: string | null
  readonly buyer_phone?: string | null
  readonly listing_id?: string | null
  readonly tenant_notice_required?: boolean | null
  readonly status?: string | null
  readonly access_notes?: string | null
}

interface ApiEscalationQuestion {
  readonly question_id?: string | null
  readonly question_text?: string | null
  readonly added_at?: string | null
  readonly resolved_at?: string | null
}

interface ApiEscalationThread {
  readonly thread_id?: string | null
  readonly envelope_token?: string | null
  readonly category?: string | null
  readonly state?: string | null
  readonly urgency?: string | null
  readonly buyer?: ApiBuyer | null
  readonly buyer_phone?: string | null
  readonly listing?: ApiListing | null
  readonly listing_id?: string | null
  readonly latest_question?: string | null
  readonly question_count?: number | null
  readonly last_buyer_message_at?: string | null
  readonly opened_at?: string | null
  readonly latest_route_expires_at?: string | null
  readonly questions?: readonly ApiEscalationQuestion[] | null
}

interface ApiReplyDraft {
  readonly reply_draft_id?: string | null
  readonly draft_id?: string | null
  readonly conversation_id?: string | null
  readonly buyer_name?: string | null
  readonly buyer_phone?: string | null
  readonly listing_name?: string | null
  readonly listing?: ApiListing | null
  readonly listing_id?: string | null
  readonly unit_number?: string | null
  readonly category?: string | null
  readonly intent?: string | null
  readonly body?: string | null
  readonly created_at?: string | null
}

interface ApiOutreachDraft {
  readonly outreach_draft_id?: string | null
  readonly draft_id?: string | null
  readonly subject?: string | null
  readonly audience?: {
    readonly project?: string | null
  } | null
  readonly audience_label?: string | null
  readonly body?: string | null
}

interface ApiDrafts {
  readonly reply_drafts?: readonly ApiReplyDraft[] | null
  readonly outreach_drafts?: readonly ApiOutreachDraft[] | null
}

interface ApiPerformanceMetrics {
  readonly new_buyer_conversations?: number | null
  readonly escalations_handled?: number | null
  readonly avg_response_minutes?: number | null
  readonly follow_ups_sent?: number | null
  readonly viewings_proposed?: number | null
  readonly viewings_confirmed?: number | null
  readonly viewings_completed?: number | null
  readonly offers_detected?: number | null
  readonly hot_leads_active?: number | null
  readonly tasks_overdue?: number | null
}

interface ApiPerformanceWindow {
  readonly key?: string | null
  readonly label?: string | null
  readonly start_at?: string | null
  readonly end_at?: string | null
  readonly metrics?: ApiPerformanceMetrics | null
}

interface ApiPerformance {
  readonly scope?: string | null
  readonly agent_user_id?: string | null
  readonly generated_at?: string | null
  readonly primary?: ApiPerformanceWindow | null
  readonly windows?: readonly ApiPerformanceWindow[] | null
}

interface ApiDashboardPayload {
  readonly generated_at?: string | null
  readonly agent?: {
    readonly display_name?: string | null
  } | null
  readonly brokerage?: {
    readonly name?: string | null
  } | null
  readonly hot_list_refresh?: {
    readonly status?: string | null
    readonly trigger?: string | null
    readonly last_refresh_at?: string | null
    readonly completed_at?: string | null
    readonly assignment_count?: number | null
    readonly task_count?: number | null
    readonly draft_count?: number | null
    readonly error?: string | null
  } | null
  readonly empty_state?: {
    readonly reason?: string | null
    readonly message?: string | null
  } | null
  readonly metrics?: Record<string, number | null | undefined> | null
  readonly hot_leads?: readonly ApiHotLead[] | null
  readonly conversations?: readonly ApiConversation[] | null
  readonly tasks?: readonly ApiTask[] | null
  readonly campaigns?: readonly ApiCampaign[] | null
  readonly viewings?: readonly ApiViewing[] | null
  readonly escalation_threads?: readonly ApiEscalationThread[] | null
  readonly drafts?: ApiDrafts | null
  readonly marketing?: {
    readonly pages?: readonly ApiMarketingPage[] | null
    readonly events_7d?: number | null
  } | null
  readonly performance?: ApiPerformance | null
}

function mapApiDashboard(payload: ApiDashboardPayload, fallback: AgentDashboardData): AgentDashboardData {
  const metrics = payload?.metrics ?? {}
  const hotListRefresh = payload?.hot_list_refresh ?? {}
  const emptyState = payload?.empty_state
  const hotLeads: readonly ApiHotLead[] = Array.isArray(payload?.hot_leads) ? payload.hot_leads : []
  const conversations: readonly ApiConversation[] = Array.isArray(payload?.conversations) ? payload.conversations : []
  const tasks: readonly ApiTask[] = Array.isArray(payload?.tasks) ? payload.tasks : []
  const campaigns: readonly ApiCampaign[] = Array.isArray(payload?.campaigns) ? payload.campaigns : []
  const viewings: readonly ApiViewing[] = Array.isArray(payload?.viewings) ? payload.viewings : []
  const escalationThreads: readonly ApiEscalationThread[] = Array.isArray(payload?.escalation_threads) ? payload.escalation_threads : []
  const replyDrafts: readonly ApiReplyDraft[] = Array.isArray(payload?.drafts?.reply_drafts) ? payload.drafts.reply_drafts : []
  const outreachDrafts: readonly ApiOutreachDraft[] = Array.isArray(payload?.drafts?.outreach_drafts) ? payload.drafts.outreach_drafts : []
  const pages: readonly ApiMarketingPage[] = Array.isArray(payload?.marketing?.pages) ? payload.marketing.pages : []

  const morningQueue: QueueItem[] = [
    ...tasks.slice(0, 4).map((task, index) => ({
      id: task.task_id ?? `task-${index}`,
      source: 'task' as const,
      priority: priorityFromTask(task.priority),
      title: task.title ?? 'Review task',
      context: task.description ?? task.metadata?.reason ?? 'Review the next action and update the workspace.',
      buyerName: task.buyer_phone ?? 'Workspace',
      listingName: task.metadata?.entity_label ?? task.listing_id ?? 'Agent task',
      nextAction: task.task_type ? labelFromKey(task.task_type) : 'Open task',
      due: formatShortTime(task.due_at),
      dueAt: task.due_at ?? null,
      createdAt: task.created_at ?? null,
    })),
    ...hotLeads.slice(0, Math.max(0, 4 - tasks.length)).map((lead, index) => ({
      id: lead.id ?? `lead-${index}`,
      source: 'hot_lead' as const,
      priority: priorityFromScore(lead.urgency_score),
      title: lead.signal ? `Hot buyer: ${lead.listing?.project ?? 'Property'}` : 'Buyer needs follow-up',
      context: lead.reason ?? lead.last_message ?? 'Buyer activity needs agent review.',
      buyerName: lead.buyer?.name ?? lead.buyer?.phone ?? 'Buyer',
      listingName: lead.listing?.project ?? 'Listing',
      nextAction: lead.next_action ?? 'Open brief',
      due: formatShortTime(lead.due_at),
      dueAt: lead.due_at ?? null,
      readiness: normalizeDealReadiness(lead.readiness_shadow?.deal_readiness),
    })),
    ...outreachDrafts.slice(0, 1).map((draft, index) => ({
      id: draft.outreach_draft_id ?? `outreach-${index}`,
      source: 'outreach' as const,
      priority: 'high' as const,
      title: 'Review owner outreach draft',
      context: draft.body ?? 'Campaign draft is ready for review.',
      buyerName: 'Owner campaign',
      listingName: draft.subject ?? 'Outreach',
      nextAction: 'Review draft',
      due: 'Today',
    })),
    ...pages.filter((page) => page.status !== 'published').slice(0, 1).map((page, index) => ({
      id: page.page_id ?? `page-${index}`,
      source: 'page' as const,
      priority: 'normal' as const,
      title: `One-pager ready: ${page.title ?? 'Marketing page'}`,
      context: 'Review the seller acquisition page before publishing.',
      buyerName: 'Marketing page',
      listingName: page.slug ?? 'Page',
      nextAction: 'Preview page',
      due: 'Today',
    })),
  ].slice(0, 4)

  const mappedCampaigns: CampaignItem[] = campaigns.slice(0, 4).map((campaign, index) => ({
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

  const buyerDigest: BuyerDigestItem[] = hotLeads.slice(0, 3).map((lead, index) => ({
    id: lead.id ?? `digest-${index}`,
    buyerName: lead.buyer?.name ?? lead.buyer?.phone ?? 'Buyer',
    intent: intentFromSignal(lead.signal_key),
    message: lead.last_message ?? lead.reason ?? 'Buyer activity needs review.',
    budget: lead.buyer?.budget_aed ? `AED ${Number(lead.buyer.budget_aed).toLocaleString()}` : 'Budget not confirmed',
    target: lead.listing?.project ?? 'Listing',
    recommendedAction: lead.next_action ?? 'Open brief',
    lastSeen: formatShortTime(lead.last_message_at),
    urgencyScore: lead.urgency_score ?? null,
    dueAt: lead.due_at ?? null,
    lastMessageAt: lead.last_message_at ?? null,
    readiness: normalizeDealReadiness(lead.readiness_shadow?.deal_readiness),
  }))

  const mappedConversations: ConversationInboxItem[] = conversations.slice(0, 8).map((conversation, index) => ({
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
    needsReply: Boolean(conversation.needs_reply),
    needsReplyReason: conversation.needs_reply_reason ?? null,
    hasPendingDraft: Boolean(conversation.has_pending_draft),
    lastBuyerMessageAt: formatShortTime(conversation.last_buyer_message_at),
    lastBuyerMessageAtRaw: conversation.last_buyer_message_at ?? null,
    lastAgentResponseAt: conversation.last_agent_response_at ? formatShortTime(conversation.last_agent_response_at) : null,
    readiness: normalizeDealReadiness(conversation.deal_readiness),
  }))

  const mappedViewings: ViewingItem[] = viewings.slice(0, 4).map((viewing, index) => ({
    id: viewing.viewing_id ?? `viewing-${index}`,
    time: formatShortTime(viewing.scheduled_for),
    scheduledFor: viewing.scheduled_for ?? null,
    buyerName: viewing.buyer_phone ?? 'Buyer',
    property: viewing.listing_id ?? 'Property',
    location: viewing.tenant_notice_required ? 'Tenant notice required' : 'Access check',
    status: viewing.status === 'confirmed' ? 'confirmed' : viewing.status === 'completed' ? 'follow_up' : 'pending',
    preparation: viewing.access_notes ?? 'Confirm access and send reminder.',
  }))

  const mappedEscalations: EscalationThreadItem[] = escalationThreads.slice(0, 4).map((thread, index) => ({
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
    lastBuyerMessageAtRaw: thread.last_buyer_message_at ?? null,
    openedAt: formatShortTime(thread.opened_at),
    openedAtRaw: thread.opened_at ?? null,
    routeExpiresAt: thread.latest_route_expires_at ? formatShortTime(thread.latest_route_expires_at) : null,
    routeExpiresAtRaw: thread.latest_route_expires_at ?? null,
    questions: Array.isArray(thread.questions)
      ? thread.questions.map((question, questionIndex) => ({
          id: question.question_id ?? `${thread.thread_id ?? index}-q-${questionIndex}`,
          text: question.question_text ?? '',
          addedAt: formatShortTime(question.added_at),
          resolvedAt: question.resolved_at ? formatShortTime(question.resolved_at) : null,
        }))
      : [],
  }))

  const mappedReplyDrafts: ReplyDraftItem[] = replyDrafts.slice(0, 6).map((draft, index) => ({
    id: draft.reply_draft_id ?? draft.draft_id ?? `reply-draft-${index}`,
    conversationId: draft.conversation_id ?? null,
    buyerName: draft.buyer_name ?? draft.buyer_phone ?? 'Buyer',
    buyerPhone: draft.buyer_phone ?? null,
    listingName: draft.listing_name ?? draft.listing?.project ?? draft.listing_id ?? 'Listing',
    unitNumber: draft.unit_number ?? draft.listing?.unit_number ?? null,
    category: draft.category ?? 'general_nurture',
    intent: draft.intent ?? null,
    body: draft.body ?? 'Draft reply is ready for review.',
    createdAt: draft.created_at ?? null,
  }))

  const mappedOutreachDrafts: OutreachDraftItem[] = outreachDrafts.slice(0, 4).map((draft, index) => ({
    id: draft.outreach_draft_id ?? draft.draft_id ?? `outreach-draft-${index}`,
    subject: draft.subject ?? 'Owner outreach draft',
    audience: draft.audience?.project
      ? `${draft.audience.project} owners`
      : draft.audience_label ?? 'Owner acquisition',
    body: draft.body ?? 'Campaign draft is ready for review.',
  }))

  const hasVisibleActivity = mappedConversations.length > 0
    || morningQueue.length > 0
    || mappedEscalations.length > 0
    || buyerDigest.length > 0
    || mappedViewings.length > 0

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
    emptyState: typeof emptyState?.reason === 'string' && typeof emptyState?.message === 'string'
      ? {
          reason: emptyState.reason,
          message: emptyState.message,
        }
      : undefined,
    summary: {
      openTasks: Number(metrics.open_tasks ?? morningQueue.length),
      qualifiedBuyers: Number(metrics.hot_leads ?? buyerDigest.length),
      viewingsToday: Number(metrics.viewings_today ?? mappedViewings.length),
      offersAtRisk: Number(metrics.stale_leads ?? 0),
      openEscalations: Number(metrics.open_escalations ?? mappedEscalations.length),
    },
    performance: mapPerformance(payload?.performance),
    conversationInbox: mappedConversations,
    morningQueue,
    escalationInbox: mappedEscalations,
    drafts: {
      replyDrafts: mappedReplyDrafts,
      outreachDrafts: mappedOutreachDrafts,
    },
    campaignSnapshot: {
      headline: mappedCampaigns.length
        ? 'Owner outreach and page activity are ready for review.'
        : 'No owner outreach campaigns are active yet.',
      activeCampaigns: Number(metrics.active_campaigns ?? mappedCampaigns.length),
      newLeads: Number(metrics.new_owner_leads ?? 0),
      qualifiedLeads: mappedCampaigns.reduce((sum, campaign) => sum + campaign.qualified, 0),
      responseRate: mappedCampaigns.length ? fallback.campaignSnapshot.responseRate : '0%',
      costPerQualifiedLead: mappedCampaigns.length ? fallback.campaignSnapshot.costPerQualifiedLead : 'AED 0',
      campaigns: mappedCampaigns,
    },
    overnightBuyerDigest: buyerDigest,
    todaysViewings: mappedViewings,
    personalMomentum: {
      ...fallback.personalMomentum,
      focus: emptyState?.message ?? fallback.personalMomentum.focus,
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
      streaks: hasVisibleActivity
        ? fallback.personalMomentum.streaks
        : [],
    },
  }
}

function mapPerformance(payload: ApiPerformance | null | undefined): AgentDashboardData['performance'] {
  const windows = Array.isArray(payload?.windows)
    ? payload.windows.map((window) => mapPerformanceWindow(window))
    : []
  const primary = payload?.primary ? mapPerformanceWindow(payload.primary) : windows[0] ?? emptyPerformanceWindow()
  return {
    scope: payload?.scope ?? 'agent',
    agentUserId: payload?.agent_user_id ?? null,
    generatedAt: payload?.generated_at ?? null,
    primary,
    windows,
  }
}

function emptyPerformanceWindow(): AgentDashboardData['performance']['primary'] {
  return {
    key: 'today',
    label: 'Today',
    startAt: null,
    endAt: null,
    metrics: {
      newBuyerConversations: 0,
      escalationsHandled: 0,
      avgResponseMinutes: null,
      followUpsSent: 0,
      viewingsProposed: 0,
      viewingsConfirmed: 0,
      viewingsCompleted: 0,
      offersDetected: 0,
      hotLeadsActive: 0,
      tasksOverdue: 0,
    },
  }
}

function mapPerformanceWindow(window: ApiPerformanceWindow): AgentDashboardData['performance']['primary'] {
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

function priorityFromTask(priority: string | null | undefined): QueuePriority {
  if (priority === 'critical') return 'critical'
  if (priority === 'high') return 'high'
  return 'normal'
}

function priorityFromScore(score: number | null | undefined): QueuePriority {
  const normalizedScore = Number(score ?? 0)
  if (normalizedScore >= 90) return 'critical'
  if (normalizedScore >= 70) return 'high'
  return 'normal'
}

function intentFromSignal(signal: string | null | undefined): BuyerIntent {
  if (signal === 'firm_offer') return 'offer_ready'
  if (signal === 'ready_to_view') return 'viewing_ready'
  if (signal === 'needs_financing') return 'financing'
  return 'researching'
}

function escalationState(state: string | null | undefined): EscalationState {
  if (state === 'debouncing' || state === 'open' || state === 'updated' || state === 'resolved' || state === 'timed_out' || state === 'opt_out_closed') {
    return state
  }
  return 'open'
}

function escalationUrgency(urgency: string | null | undefined): EscalationUrgency {
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
  id,
  eyebrow,
  title,
  children,
  action,
}: {
  id?: string
  eyebrow: string
  title: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-28 rounded-lg border border-neutral-200 bg-white shadow-card-sm">
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

function Pill({ children, className }: { children: ReactNode; className: string }) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}>
      {children}
    </span>
  )
}
