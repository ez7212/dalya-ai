'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error'

interface ConversationRow {
  conversation_id: string
  buyer?: { name?: string | null; phone?: string | null } | null
  listing?: { project?: string | null; unit_label?: string | null } | null
  summary?: string | null
  last_message?: string | null
  last_message_role?: string | null
  last_message_at?: string | null
  message_count?: number | null
  open_escalation_count?: number | null
  needs_reply?: boolean
  needs_reply_priority?: string | null
}

const FILTERS = [
  { label: 'All', value: 'all' },
  { label: 'Needs reply', value: 'needs_reply' },
]

export function InboxList() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [conversations, setConversations] = useState<ConversationRow[]>([])
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let active = true
    async function load() {
      setLoadState('loading')
      try {
        const response = await apiFetch('/api/v1/agent/conversations')
        if (!response.ok) throw new Error(`Conversations returned ${response.status}`)
        const payload = await response.json()
        if (!active) return
        setConversations(payload.conversations ?? [])
        setLoadState('live')
      } catch {
        if (active) setLoadState('error')
      }
    }
    load()
    return () => {
      active = false
    }
  }, [])

  const visible = useMemo(
    () => (filter === 'needs_reply' ? conversations.filter((c) => c.needs_reply) : conversations),
    [conversations, filter],
  )
  const needsReplyCount = useMemo(() => conversations.filter((c) => c.needs_reply).length, [conversations])

  return (
    <main className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="mx-auto max-w-[1100px]">
        <header className="mb-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
            <Link href="/agent" className="font-medium text-brand-700 hover:text-brand-800">Agent desk</Link>
            <span aria-hidden="true">/</span>
            <span>Inbox</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">Inbox</h1>
          <p className="mt-1 text-sm text-neutral-500">Every buyer conversation in one place — open any to reply.</p>
        </header>

        <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
          <div className="flex flex-wrap items-center gap-2 border-b border-neutral-200 px-4 py-4 sm:px-5">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setFilter(item.value)}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  filter === item.value
                    ? 'border-brand-300 bg-brand-50 text-brand-700'
                    : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'
                }`}
              >
                {item.label}
                {item.value === 'needs_reply' && needsReplyCount > 0 && (
                  <span className="ms-1.5 rounded-full bg-brand-100 px-1.5 text-[11px] font-semibold text-brand-700">{needsReplyCount}</span>
                )}
              </button>
            ))}
          </div>

          {loadState === 'loading' ? (
            <div className="space-y-3 px-4 py-5 sm:px-5">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-16 animate-pulse rounded-lg bg-neutral-100" />
              ))}
            </div>
          ) : loadState === 'error' ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-error-600">Could not load conversations.</p>
            </div>
          ) : visible.length === 0 ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-neutral-800">No conversations here yet.</p>
              <p className="mt-1 text-sm text-neutral-500">Buyer conversations appear here as they come in.</p>
            </div>
          ) : (
            <div className="divide-y divide-neutral-200">
              {visible.map((conversation) => (
                <Link
                  key={conversation.conversation_id}
                  href={`/agent/conversations/${conversation.conversation_id}`}
                  className="flex items-start gap-3 px-4 py-4 transition-colors hover:bg-neutral-50 sm:px-5"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-neutral-900">
                        {conversation.buyer?.name || conversation.buyer?.phone || 'Buyer'}
                      </p>
                      {conversation.needs_reply && (
                        <span className="rounded-full border border-brand-100 bg-brand-50 px-2 py-0.5 text-[11px] font-medium text-brand-700">
                          Needs reply
                        </span>
                      )}
                      {(conversation.open_escalation_count ?? 0) > 0 && (
                        <span className="rounded-full border border-warning-100 bg-warning-50 px-2 py-0.5 text-[11px] font-medium text-warning-700">
                          Escalation
                        </span>
                      )}
                    </div>
                    {conversation.listing?.project && (
                      <p className="mt-0.5 flex items-center gap-1 text-xs text-neutral-500">
                        <span className="material-symbols-outlined text-[14px] text-neutral-400" aria-hidden="true">apartment</span>
                        <span className="truncate">
                          {conversation.listing.project}
                          {conversation.listing.unit_label ? ` · ${conversation.listing.unit_label}` : ''}
                        </span>
                      </p>
                    )}
                    <p className="mt-1.5 line-clamp-1 text-sm text-neutral-600">
                      {conversation.last_message_role === 'user' ? '' : 'Dalya: '}
                      {conversation.last_message || conversation.summary || 'No messages yet.'}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-xs text-neutral-400">{formatShort(conversation.last_message_at)}</p>
                    <p className="mt-1 text-[11px] text-neutral-400">{conversation.message_count ?? 0} msg</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function formatShort(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}
