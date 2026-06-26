'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error'
type ActionState = 'saving' | 'sending' | 'rejecting' | 'snoozing' | 'error'

interface ReplyDraft {
  draft_id: string
  conversation_id: string
  listing_id?: string | null
  buyer_phone?: string | null
  buyer_name?: string | null
  listing_name: string
  unit_number?: string | null
  intent: string
  category: string
  body: string
  source: string
  status: string
  snoozed_until?: string | null
  created_at?: string | null
  updated_at?: string | null
}

interface DraftPayload {
  drafts: ReplyDraft[]
  counts?: {
    total?: number
    categories?: Record<string, number>
  }
  generated_at?: string
}

const CATEGORY_ORDER = [
  'urgent',
  'today',
  'stale_buyer',
  'viewing_follow_up',
  'offer_follow_up',
  'financing_follow_up',
  'general_nurture',
]

export function DraftQueue() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [payload, setPayload] = useState<DraftPayload>({ drafts: [] })
  const [category, setCategory] = useState('')
  const [includeSnoozed, setIncludeSnoozed] = useState(false)
  const [draftBodies, setDraftBodies] = useState<Record<string, string>>({})
  const [actionState, setActionState] = useState<Record<string, ActionState>>({})

  useEffect(() => {
    let active = true

    async function loadDrafts() {
      setLoadState('loading')
      try {
        const params = new URLSearchParams()
        if (includeSnoozed) params.set('include_snoozed', 'true')
        const response = await apiFetch(`/api/v1/agent/drafts?${params.toString()}`)
        if (!response.ok) throw new Error(`Draft queue returned ${response.status}`)
        const body = await response.json()
        if (!active) return
        setPayload(body)
        setDraftBodies(
          Object.fromEntries((body.drafts ?? []).map((draft: ReplyDraft) => [draft.draft_id, draft.body ?? ''])),
        )
        setLoadState('live')
      } catch {
        if (!active) return
        setLoadState('error')
      }
    }

    loadDrafts()
    return () => {
      active = false
    }
  }, [includeSnoozed])

  const categories = useMemo(() => {
    const present = new Set(payload.drafts.map((draft) => draft.category))
    return CATEGORY_ORDER.filter((item) => present.has(item))
  }, [payload.drafts])

  const visibleDrafts = useMemo(() => {
    if (!category) return payload.drafts
    return payload.drafts.filter((draft) => draft.category === category)
  }, [category, payload.drafts])

  async function updateDraft(draftId: string) {
    const body = (draftBodies[draftId] ?? '').trim()
    if (!body) {
      setActionState((current) => ({ ...current, [draftId]: 'error' }))
      return
    }
    setActionState((current) => ({ ...current, [draftId]: 'saving' }))
    try {
      const response = await apiFetch(`/api/v1/agent/drafts/${draftId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body }),
      })
      if (!response.ok) throw new Error(`Update returned ${response.status}`)
      const updated = await response.json()
      setPayload((current) => ({
        ...current,
        drafts: current.drafts.map((draft) => (draft.draft_id === draftId ? updated : draft)),
      }))
      setActionState((current) => {
        const next = { ...current }
        delete next[draftId]
        return next
      })
    } catch {
      setActionState((current) => ({ ...current, [draftId]: 'error' }))
    }
  }

  async function sendDraft(draftId: string) {
    const body = (draftBodies[draftId] ?? '').trim()
    if (!body) {
      setActionState((current) => ({ ...current, [draftId]: 'error' }))
      return
    }
    await mutateDraft(draftId, 'sending', `/api/v1/agent/drafts/${draftId}/send`, { body })
  }

  async function rejectDraft(draftId: string) {
    await mutateDraft(draftId, 'rejecting', `/api/v1/agent/drafts/${draftId}/reject`, { reason: 'Rejected from draft queue.' })
  }

  async function snoozeDraft(draftId: string) {
    await mutateDraft(draftId, 'snoozing', `/api/v1/agent/drafts/${draftId}/snooze`, { minutes: 120, reason: 'Snoozed from draft queue.' })
  }

  async function mutateDraft(draftId: string, state: ActionState, path: string, body: Record<string, unknown>) {
    setActionState((current) => ({ ...current, [draftId]: state }))
    try {
      const response = await apiFetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) throw new Error(`Draft action returned ${response.status}`)
      setPayload((current) => ({
        ...current,
        drafts: current.drafts.filter((draft) => draft.draft_id !== draftId),
      }))
      setActionState((current) => {
        const next = { ...current }
        delete next[draftId]
        return next
      })
    } catch {
      setActionState((current) => ({ ...current, [draftId]: 'error' }))
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
              <span>Drafts</span>
              {payload.generated_at && (
                <>
                  <span aria-hidden="true">/</span>
                  <span>Updated {formatShortTime(payload.generated_at)}</span>
                </>
              )}
            </div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
              Draft approval queue
            </h1>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:min-w-[320px]">
            <Metric label="Ready" value={String(payload.counts?.total ?? visibleDrafts.length)} />
            <Metric label="Categories" value={String(Object.keys(payload.counts?.categories ?? {}).length)} />
          </div>
        </header>

        <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
          <div className="grid gap-3 border-b border-neutral-200 px-4 py-4 lg:grid-cols-[minmax(0,1fr)_180px] sm:px-5">
            <div className="flex flex-wrap gap-2">
              <FilterButton active={!category} onClick={() => setCategory('')}>All</FilterButton>
              {categories.map((item) => (
                <FilterButton key={item} active={category === item} onClick={() => setCategory(item)}>
                  {labelFromKey(item)}
                </FilterButton>
              ))}
            </div>
            <label className="inline-flex items-center justify-start gap-2 text-sm font-medium text-neutral-700 lg:justify-end">
              <input
                type="checkbox"
                checked={includeSnoozed}
                onChange={(event) => setIncludeSnoozed(event.target.checked)}
                className="h-4 w-4 rounded border-neutral-300 text-brand-700"
              />
              Snoozed
            </label>
          </div>

          {loadState === 'loading' ? (
            <div className="space-y-3 px-4 py-5 sm:px-5">
              {[0, 1, 2].map((item) => (
                <div key={item} className="rounded-lg border border-neutral-200 p-4">
                  <div className="h-4 w-56 animate-pulse rounded bg-neutral-200" />
                  <div className="mt-3 h-20 animate-pulse rounded bg-neutral-100" />
                </div>
              ))}
            </div>
          ) : loadState === 'error' ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-error-600">Could not load draft replies.</p>
            </div>
          ) : visibleDrafts.length === 0 ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-neutral-800">No drafts in this queue.</p>
              <p className="mt-1 text-sm text-neutral-500">
                Dalya queues a reply draft here whenever a buyer message needs your review before sending.
                Drafts ready for review also surface on the matching Today Queue task.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-neutral-200">
              {visibleDrafts.map((draft) => (
                <DraftRow
                  key={draft.draft_id}
                  draft={draft}
                  body={draftBodies[draft.draft_id] ?? draft.body}
                  state={actionState[draft.draft_id]}
                  onBodyChange={(value) => setDraftBodies((current) => ({ ...current, [draft.draft_id]: value }))}
                  onSave={() => updateDraft(draft.draft_id)}
                  onSend={() => sendDraft(draft.draft_id)}
                  onReject={() => rejectDraft(draft.draft_id)}
                  onSnooze={() => snoozeDraft(draft.draft_id)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function DraftRow({
  draft,
  body,
  state,
  onBodyChange,
  onSave,
  onSend,
  onReject,
  onSnooze,
}: {
  draft: ReplyDraft
  body: string
  state?: ActionState
  onBodyChange: (value: string) => void
  onSave: () => void
  onSend: () => void
  onReject: () => void
  onSnooze: () => void
}) {
  const busy = Boolean(state && state !== 'error')
  const changed = body.trim() !== (draft.body ?? '').trim()
  const canSend = !busy && body.trim().length > 0

  return (
    <article className="grid gap-5 px-4 py-5 sm:px-5 xl:grid-cols-[minmax(0,1fr)_220px]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-brand-100 bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700">
            {labelFromKey(draft.category)}
          </span>
          <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
            {labelFromKey(draft.source)}
          </span>
          {draft.snoozed_until && (
            <span className="rounded-full border border-warning-100 bg-warning-50 px-2 py-0.5 text-[11px] font-medium text-warning-700">
              {formatShortTime(draft.snoozed_until)}
            </span>
          )}
        </div>
        <div className="mt-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-neutral-900">{draft.buyer_name || draft.buyer_phone || 'Buyer'}</h2>
            <p className="mt-1 text-xs text-neutral-500">{draft.buyer_phone}</p>
          </div>
          <p className="text-sm font-medium text-neutral-700">
            {draft.listing_name}{draft.unit_number ? ` · ${draft.unit_number}` : ''}
          </p>
        </div>
        <label className="mt-4 block">
          <span className="sr-only">Draft body</span>
          <textarea
            value={body}
            onChange={(event) => onBodyChange(event.target.value)}
            rows={5}
            className="w-full resize-none rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm leading-relaxed text-neutral-900 outline-none transition-colors focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
          />
        </label>
        {state === 'error' && <p className="mt-2 text-xs font-medium text-error-600">Draft action failed.</p>}
      </div>
      <aside className="rounded-lg border border-neutral-200 bg-white p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Actions</p>
        <div className="mt-3 grid gap-2">
          <Link
            href={`/agent/conversations/${draft.conversation_id}`}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">forum</span>
            Conversation
          </Link>
          <button
            type="button"
            onClick={onSend}
            disabled={!canSend}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">send</span>
            {state === 'sending' ? 'Sending' : 'Send'}
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={busy || !changed || body.trim().length === 0}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">save</span>
            {state === 'saving' ? 'Saving' : 'Save edit'}
          </button>
          <button
            type="button"
            onClick={onSnooze}
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">schedule</span>
            {state === 'snoozing' ? 'Snoozing' : 'Snooze'}
          </button>
          <button
            type="button"
            onClick={onReject}
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">block</span>
            {state === 'rejecting' ? 'Rejecting' : 'Reject'}
          </button>
        </div>
        <dl className="mt-4 grid gap-3 text-sm">
          <Fact label="Intent" value={labelFromKey(draft.intent)} />
          <Fact label="Updated" value={formatShortTime(draft.updated_at)} />
        </dl>
      </aside>
    </article>
  )
}

function FilterButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? 'border-brand-300 bg-brand-50 text-brand-700'
          : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'
      }`}
    >
      {children}
    </button>
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

function labelFromKey(value: string | null | undefined): string {
  return String(value || 'general')
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
