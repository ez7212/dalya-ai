'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { EscalationHandoffPanel } from '@/components/agent-dashboard/QueueHandoffCard'
import { apiFetch } from '@/lib/api'
import type { EscalationState, EscalationThreadItem, EscalationUrgency } from '@/components/agent-dashboard/types'
import type { RefObject } from 'react'

type LoadState = 'loading' | 'live' | 'error'

interface InboxPayload {
  threads: any[]
  counts?: Record<string, any>
  generated_at?: string
}

interface EscalationInboxProps {
  readonly selectedThreadId?: string | null
}

const STATE_FILTERS = [
  { label: 'Active', value: 'active' },
  { label: 'Updated', value: 'updated' },
  { label: 'Bundling', value: 'debouncing' },
  { label: 'Timed out', value: 'timed_out' },
  { label: 'Closed', value: 'closed' },
]

export function EscalationInbox({ selectedThreadId = null }: EscalationInboxProps) {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [payload, setPayload] = useState<InboxPayload>({ threads: [] })
  const [stateFilter, setStateFilter] = useState('active')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [actionState, setActionState] = useState<Record<string, 'working' | 'resolved' | 'error'>>({})
  const [replyState, setReplyState] = useState<Record<string, 'working' | 'sent' | 'error'>>({})
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({})
  const [aiModeBusy, setAiModeBusy] = useState<Record<string, boolean>>({})
  const [replyFiles, setReplyFiles] = useState<Record<string, File[]>>({})
  const selectedThreadRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    let active = true

    async function loadInbox() {
      setLoadState('loading')
      const params = new URLSearchParams()
      if (stateFilter) params.set('state', stateFilter)
      if (categoryFilter) params.set('category', categoryFilter)
      params.set('limit', '100')
      try {
        const response = await apiFetch(`/api/v1/agent/escalations?${params.toString()}`)
        if (!response.ok) {
          throw new Error(`Escalation inbox returned ${response.status}`)
        }
        const body = await response.json()
        if (!active) return
        setPayload(body)
        setLoadState('live')
      } catch {
        if (!active) return
        setLoadState('error')
      }
    }

    loadInbox()
    return () => {
      active = false
    }
  }, [stateFilter, categoryFilter])

  const threads = useMemo(() => payload.threads.map(mapThread), [payload.threads])
  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const thread of payload.threads) {
      if (thread.category) set.add(thread.category)
    }
    return Array.from(set).sort()
  }, [payload.threads])

  useEffect(() => {
    if (loadState !== 'live' || !selectedThreadId) return
    const selectedThread = selectedThreadRef.current
    if (!selectedThread) return
    selectedThread.scrollIntoView({ block: 'center', behavior: 'smooth' })
    selectedThread.focus({ preventScroll: true })
  }, [loadState, selectedThreadId, threads])

  async function resolveThread(threadId: string) {
    setActionState((current) => ({ ...current, [threadId]: 'working' }))
    try {
      const response = await apiFetch(`/api/v1/agent/escalations/${threadId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'manual', note: 'Resolved from escalation inbox.' }),
      })
      if (!response.ok) {
        throw new Error(`Resolve returned ${response.status}`)
      }
      setPayload((current) => ({
        ...current,
        threads: current.threads.filter((thread) => thread.thread_id !== threadId),
      }))
      setActionState((current) => ({ ...current, [threadId]: 'resolved' }))
    } catch {
      setActionState((current) => ({ ...current, [threadId]: 'error' }))
    }
  }

  async function toggleAiMode(conversationId: string, currentMode: string | undefined) {
    const paused = currentMode === 'agent_controlled'
    // Pausing is one-tap; resuming is the dangerous direction and confirms.
    if (paused && !window.confirm('Resume Dalya for this buyer? It will answer their next message.')) {
      return
    }
    setAiModeBusy((current) => ({ ...current, [conversationId]: true }))
    try {
      const response = await apiFetch(`/api/v1/agent/leads/${conversationId}/ai-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: paused ? 'active' : 'agent_controlled' }),
      })
      if (!response.ok) {
        throw new Error(`AI mode returned ${response.status}`)
      }
      const body = await response.json()
      setPayload((current) => ({
        ...current,
        threads: current.threads.map((thread) =>
          thread.conversation_id === conversationId ? { ...thread, ai_mode: body.ai_mode } : thread,
        ),
      }))
    } catch {
      // Leave the row unchanged — the chip keeps showing the persisted state.
    } finally {
      setAiModeBusy((current) => ({ ...current, [conversationId]: false }))
    }
  }

  async function sendReply(threadId: string, conversationId?: string | null) {
    const body = (replyDrafts[threadId] ?? '').trim()
    if (!body) {
      setReplyState((current) => ({ ...current, [threadId]: 'error' }))
      return
    }
    setReplyState((current) => ({ ...current, [threadId]: 'working' }))
    try {
      // Attachments first (DAL-160): media rides the conversation media
      // endpoint; the text reply then resolves the escalation as today.
      const files = replyFiles[threadId] ?? []
      if (files.length > 0 && conversationId) {
        const form = new FormData()
        for (const file of files) form.append('files', file)
        form.append('caption', '')
        const mediaResponse = await apiFetch(`/api/v1/agent/leads/${conversationId}/media`, {
          method: 'POST',
          body: form,
        })
        if (!mediaResponse.ok) {
          throw new Error(`Media upload returned ${mediaResponse.status}`)
        }
      }
      const response = await apiFetch(`/api/v1/agent/escalations/${threadId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body, send_to_buyer: true }),
      })
      if (!response.ok) {
        throw new Error(`Reply returned ${response.status}`)
      }
      setReplyFiles((current) => {
        const next = { ...current }
        delete next[threadId]
        return next
      })
      setPayload((current) => ({
        ...current,
        threads: current.threads.filter((thread) => thread.thread_id !== threadId),
      }))
      setReplyDrafts((current) => {
        const next = { ...current }
        delete next[threadId]
        return next
      })
      setReplyState((current) => ({ ...current, [threadId]: 'sent' }))
    } catch {
      setReplyState((current) => ({ ...current, [threadId]: 'error' }))
    }
  }

  return (
    <main className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
              <Link href="/agent" className="font-medium text-brand-700 hover:text-brand-800">Agent desk</Link>
              <span aria-hidden="true">/</span>
              <span>Escalation inbox</span>
              {payload.generated_at && (
                <>
                  <span aria-hidden="true">/</span>
                  <span>Updated {formatShortTime(payload.generated_at)}</span>
                </>
              )}
            </div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
              Escalation inbox
            </h1>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:min-w-[420px]">
            <Metric label="Threads" value={String(payload.counts?.total ?? threads.length)} />
            <Metric label="Critical" value={String(payload.counts?.critical ?? threads.filter((thread) => thread.urgency === 'critical').length)} />
            <Metric label="High" value={String(payload.counts?.high ?? threads.filter((thread) => thread.urgency === 'high').length)} />
          </div>
        </header>

        <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
          <div className="grid gap-3 border-b border-neutral-200 px-4 py-4 sm:grid-cols-[minmax(0,1fr)_220px] sm:px-5">
            <div className="flex flex-wrap gap-2">
              {STATE_FILTERS.map((filter) => (
                <button
                  key={filter.value}
                  type="button"
                  onClick={() => setStateFilter(filter.value)}
                  className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                    stateFilter === filter.value
                      ? 'border-brand-300 bg-brand-50 text-brand-700'
                      : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
            <label className="block">
              <span className="sr-only">Filter by category</span>
              <select
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value)}
                className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-800"
              >
                <option value="">All categories</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{labelFromKey(category)}</option>
                ))}
              </select>
            </label>
          </div>

          {loadState === 'loading' ? (
            <div className="space-y-3 px-4 py-5 sm:px-5">
              {[0, 1, 2].map((item) => (
                <div key={item} className="rounded-lg border border-neutral-200 p-4">
                  <div className="h-4 w-52 animate-pulse rounded bg-neutral-200" />
                  <div className="mt-3 h-3 w-3/4 animate-pulse rounded bg-neutral-100" />
                  <div className="mt-2 h-3 w-1/2 animate-pulse rounded bg-neutral-100" />
                </div>
              ))}
            </div>
          ) : loadState === 'error' ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-error-600">Could not load escalation threads.</p>
            </div>
          ) : threads.length === 0 ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-neutral-800">No threads match this filter.</p>
              <p className="mt-1 text-sm text-neutral-500">Open buyer questions will appear here after Dalya escalates them.</p>
            </div>
          ) : (
            <div className="divide-y divide-neutral-200">
              {threads.map((thread) => (
                <EscalationThreadRow
                  key={thread.id}
                  thread={thread}
                  isSelected={selectedThreadId === thread.id}
                  selectedThreadRef={selectedThreadRef}
                  actionState={actionState[thread.id]}
                  replyState={replyState[thread.id]}
                  replyValue={replyDrafts[thread.id] ?? ''}
                  aiModeBusy={thread.conversationId ? Boolean(aiModeBusy[thread.conversationId]) : false}
                  replyFileCount={(replyFiles[thread.id] ?? []).length}
                  onReplyChange={(value) => setReplyDrafts((current) => ({ ...current, [thread.id]: value }))}
                  onReplyFilesChange={(files) => setReplyFiles((current) => ({ ...current, [thread.id]: files }))}
                  onSendReply={() => sendReply(thread.id, thread.conversationId)}
                  onResolve={() => resolveThread(thread.id)}
                  onToggleAiMode={() => thread.conversationId && toggleAiMode(thread.conversationId, thread.aiMode)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function EscalationThreadRow({
  thread,
  isSelected,
  selectedThreadRef,
  actionState,
  replyState,
  replyValue,
  aiModeBusy,
  replyFileCount,
  onReplyChange,
  onReplyFilesChange,
  onSendReply,
  onResolve,
  onToggleAiMode,
}: {
  thread: EscalationThreadItem
  isSelected: boolean
  selectedThreadRef: RefObject<HTMLElement | null>
  actionState?: 'working' | 'resolved' | 'error'
  replyState?: 'working' | 'sent' | 'error'
  replyValue: string
  aiModeBusy: boolean
  replyFileCount: number
  onReplyChange: (value: string) => void
  onReplyFilesChange: (files: File[]) => void
  onSendReply: () => void
  onResolve: () => void
  onToggleAiMode: () => void
}) {
  const canAct = !['resolved', 'timed_out', 'opt_out_closed'].includes(thread.state)
  const canSendReply = canAct && replyState !== 'working' && replyValue.trim().length > 0
  const aiPaused = thread.aiMode === 'agent_controlled'

  return (
    <article
      ref={isSelected ? selectedThreadRef : undefined}
      tabIndex={isSelected ? -1 : undefined}
      aria-current={isSelected ? 'true' : undefined}
      data-thread-id={thread.id}
      data-selected-thread={isSelected ? 'true' : undefined}
      className={`scroll-mt-24 grid gap-5 px-4 py-5 outline-none transition-colors sm:px-5 xl:grid-cols-[minmax(0,1fr)_260px] ${
        isSelected ? 'bg-brand-50/70 ring-2 ring-inset ring-brand-100' : 'bg-white'
      }`}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <UrgencyPill urgency={thread.urgency} />
          <StatePill state={thread.state} />
          <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
            {labelFromKey(thread.category)}
          </span>
          {aiPaused && (
            <span className="rounded-full border border-warning-100 bg-warning-50 px-2 py-0.5 text-[11px] font-medium text-warning-700">
              Dalya paused
            </span>
          )}
          {thread.token && <span className="font-mono text-xs text-neutral-500">Ref {thread.token}</span>}
        </div>
        <div className="mt-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-neutral-900">{thread.buyerName}</h2>
            <p className="mt-1 text-xs text-neutral-500">{thread.buyerPhone}</p>
          </div>
          <p className="text-sm font-medium text-neutral-700">
            {thread.listingName}{thread.unitNumber ? ` · ${thread.unitNumber}` : ''}
          </p>
        </div>
        <div className="mt-4 rounded-lg border border-neutral-200 bg-neutral-50">
          {thread.questions.map((question, index) => (
            <div key={question.id} className="border-b border-neutral-200 px-3 py-3 last:border-b-0">
              <div className="flex items-center justify-between gap-3">
                <p className="font-mono text-[11px] text-neutral-500">Q{index + 1} · {question.addedAt}</p>
                {question.resolvedAt && <p className="text-[11px] font-medium text-success-700">Resolved {question.resolvedAt}</p>}
              </div>
              <p dir="auto" className="mt-1 text-sm leading-relaxed text-neutral-800">{question.text}</p>
            </div>
          ))}
        </div>
      </div>

      <aside className="rounded-lg border border-neutral-200 bg-white p-4">
        <EscalationHandoffPanel thread={thread} />
        <div className="mt-4 border-t border-neutral-200 pt-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Thread status</p>
          <dl className="mt-3 grid gap-3 text-sm">
            <Fact label="Questions" value={String(thread.questionCount)} />
            <Fact label="Opened" value={thread.openedAt} />
            <Fact label="Last buyer message" value={thread.lastBuyerMessageAt} />
            <Fact label="Route expires" value={thread.routeExpiresAt ?? 'No active route'} />
          </dl>
        </div>
        {canAct && (
          <div className="mt-4 border-t border-neutral-200 pt-4">
            <label className="block text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500" htmlFor={`reply-${thread.id}`}>
              Reply to buyer
            </label>
            <textarea
              id={`reply-${thread.id}`}
              value={replyValue}
              onChange={(event) => onReplyChange(event.target.value)}
              rows={5}
              placeholder="Write the buyer-safe answer. Dalya sends it through Brokerage AI and closes this escalation."
              className="mt-2 w-full resize-none rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm leading-relaxed text-neutral-900 outline-none transition-colors placeholder:text-neutral-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
            {thread.conversationId && (
              <label className="mt-2 block">
                <span className="sr-only">Attachments</span>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                  onChange={(event) => onReplyFilesChange(Array.from(event.target.files ?? []))}
                  className="block w-full text-xs text-neutral-600 file:mr-3 file:rounded-md file:border file:border-neutral-300 file:bg-white file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-neutral-800 hover:file:bg-neutral-50"
                />
                {replyFileCount > 0 && (
                  <span className="mt-1 block text-xs text-neutral-500">{replyFileCount} attachment{replyFileCount !== 1 ? 's' : ''} will send with this reply.</span>
                )}
              </label>
            )}
            <button
              type="button"
              onClick={onSendReply}
              disabled={!canSendReply}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">send</span>
              {replyState === 'working' ? 'Sending' : 'Send to buyer'}
            </button>
            {replyState === 'error' && <p className="mt-2 text-xs font-medium text-error-600">Could not send this reply.</p>}
          </div>
        )}
        {canAct && (
          <button
            type="button"
            onClick={onResolve}
            disabled={actionState === 'working'}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">check_circle</span>
            Resolve thread
          </button>
        )}
        {thread.conversationId && (
          <button
            type="button"
            onClick={onToggleAiMode}
            disabled={aiModeBusy}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
              {aiPaused ? 'play_arrow' : 'pause'}
            </span>
            {aiModeBusy ? 'Updating' : aiPaused ? 'Resume Dalya' : 'Pause Dalya'}
          </button>
        )}
        {actionState === 'error' && <p className="mt-2 text-xs font-medium text-error-600">Could not resolve this thread.</p>}
      </aside>
    </article>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-3 shadow-card-sm">
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-xl font-semibold text-neutral-900">{value}</p>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</dt>
      <dd className="mt-1 font-medium text-neutral-800">{value}</dd>
    </div>
  )
}

function UrgencyPill({ urgency }: { urgency: EscalationUrgency }) {
  const className = urgency === 'critical'
    ? 'border-error-100 bg-error-50 text-error-700'
    : urgency === 'high'
      ? 'border-warning-100 bg-warning-50 text-warning-700'
      : 'border-neutral-200 bg-neutral-100 text-neutral-700'
  return <Pill className={className}>{labelFromKey(urgency)}</Pill>
}

function StatePill({ state }: { state: EscalationState }) {
  const className = state === 'updated'
    ? 'border-warning-100 bg-warning-50 text-warning-700'
    : state === 'debouncing'
      ? 'border-brand-100 bg-brand-50 text-brand-700'
      : state === 'timed_out'
        ? 'border-error-100 bg-error-50 text-error-700'
        : 'border-success-100 bg-success-50 text-success-700'
  return <Pill className={className}>{labelFromKey(state)}</Pill>
}

function Pill({ children, className }: { children: string; className: string }) {
  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}>
      {children}
    </span>
  )
}

function mapThread(thread: any, index: number): EscalationThreadItem {
  return {
    id: thread.thread_id ?? `thread-${index}`,
    token: thread.envelope_token,
    conversationId: thread.conversation_id ?? null,
    aiMode: thread.ai_mode ?? 'active',
    category: thread.category ?? 'other',
    state: normalizeState(thread.state),
    urgency: normalizeUrgency(thread.urgency),
    buyerName: thread.buyer?.name ?? thread.buyer?.phone ?? thread.buyer_phone ?? 'Buyer',
    buyerPhone: thread.buyer?.phone ?? thread.buyer_phone ?? '',
    listingName: thread.listing?.project ?? thread.listing_id ?? 'Listing',
    unitNumber: thread.listing?.unit_number,
    latestQuestion: thread.latest_question ?? 'Agent review needed.',
    questionCount: Number(thread.question_count ?? thread.questions?.length ?? 1),
    lastBuyerMessageAt: formatShortTime(thread.last_buyer_message_at),
    openedAt: formatShortTime(thread.opened_at),
    routeExpiresAt: thread.latest_route_expires_at ? formatShortTime(thread.latest_route_expires_at) : null,
    questions: Array.isArray(thread.questions)
      ? thread.questions.map((question: any, questionIndex: number) => ({
          id: question.question_id ?? `${thread.thread_id ?? index}-${questionIndex}`,
          text: question.question_text ?? '',
          addedAt: formatShortTime(question.added_at),
          resolvedAt: question.resolved_at ? formatShortTime(question.resolved_at) : null,
        }))
      : [],
  }
}

function normalizeState(state: string | undefined): EscalationState {
  if (state === 'debouncing' || state === 'open' || state === 'updated' || state === 'resolved' || state === 'timed_out' || state === 'opt_out_closed') {
    return state
  }
  return 'open'
}

function normalizeUrgency(urgency: string | undefined): EscalationUrgency {
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
