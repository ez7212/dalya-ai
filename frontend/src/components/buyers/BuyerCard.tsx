'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { DealReadinessPanel } from '@/components/readiness/DealReadinessCallout'
import {
  normalizeDealReadiness,
  type DealReadinessMetadata,
} from '@/components/readiness/deal-readiness'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error'

interface FieldEntry {
  value: unknown
  provenance: string
  confidence?: number | null
  source_message_id?: number | null
  confirmed_by?: string | null
  updated_at?: string | null
  suggestion?: { value: unknown; confidence?: number | null } | null
}

interface CardPayload {
  profile_id: string
  identity: {
    name?: string | null
    phone: string
    language?: string | null
    source?: string | null
    opted_out: boolean
  }
  qualification: Record<string, FieldEntry>
  deal_readiness?: DealReadinessMetadata | null
  conversations: { conversation_id: string; listing?: string | null; updated_at?: string | null }[]
  viewings: {
    viewing_id: string
    scheduled_for?: string | null
    status: string
    feedback?: { score?: number | null; summary?: string | null; sentiment?: string | null } | null
  }[]
  offers: {
    offer_id: string
    amount?: number | null
    direction: string
    status: string
    created_at?: string | null
  }[]
  escalation_count: number
}

const FIELD_LABELS: Record<string, string> = {
  budget_min_aed: 'Budget min (AED)',
  budget_max_aed: 'Budget max (AED)',
  financing: 'Financing',
  preapproval_amount_aed: 'Pre-approval (AED)',
  preapproval_bank: 'Pre-approval bank',
  timeline: 'Timeline',
  target_areas: 'Target areas',
  property_type: 'Property type',
  bedrooms: 'Bedrooms',
  must_haves: 'Must-haves',
  deal_breakers: 'Deal-breakers',
}

export function BuyerCard({ profileId }: { profileId: string }) {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [card, setCard] = useState<CardPayload | null>(null)
  const [editField, setEditField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saveError, setSaveError] = useState('')

  async function load() {
    try {
      const response = await apiFetch(`/api/v1/agent/buyers/${profileId}`)
      if (!response.ok) throw new Error(`Buyer returned ${response.status}`)
      setCard(await response.json())
      setLoadState('live')
    } catch {
      setLoadState('error')
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId])

  async function confirmField(field: string, value: unknown) {
    setSaveError('')
    try {
      const response = await apiFetch(`/api/v1/agent/buyers/${profileId}/fields`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field, value }),
      })
      if (!response.ok) throw new Error(`Field update returned ${response.status}`)
      const payload = await response.json()
      setCard((current) => (current ? { ...current, qualification: payload.qualification } : current))
      setEditField(null)
    } catch {
      setSaveError('Could not save the field.')
    }
  }

  return (
    <main className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="mx-auto max-w-[1100px]">
        <header className="mb-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
            <Link href="/agent" className="font-medium text-brand-700 hover:text-brand-800">Agent desk</Link>
            <span aria-hidden="true">/</span>
            <Link href="/agent/buyers" className="font-medium text-brand-700 hover:text-brand-800">Buyers</Link>
            <span aria-hidden="true">/</span>
            <span>Card</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
            {card?.identity.name || card?.identity.phone || 'Buyer'}
          </h1>
          {card?.identity.opted_out && (
            <p className="mt-2 inline-flex items-center gap-2 rounded-md border border-error-100 bg-error-50 px-3 py-1.5 text-sm font-medium text-error-700">
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">block</span>
              Opted out — all sends are blocked for this buyer.
            </p>
          )}
        </header>

        {loadState === 'loading' ? (
          <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-card-sm">
            <div className="h-5 w-64 animate-pulse rounded bg-neutral-200" />
            <div className="mt-4 h-32 animate-pulse rounded bg-neutral-100" />
          </div>
        ) : loadState === 'error' || !card ? (
          <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-card-sm">
            <p className="text-sm font-medium text-error-600">Could not load this buyer.</p>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-5">
              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm sm:p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Qualification</p>
                {Object.keys(card.qualification).length === 0 ? (
                  <p className="mt-3 text-sm text-neutral-600">
                    Nothing captured yet — values appear here as Dalya infers them and you confirm them.
                  </p>
                ) : (
                  <div className="mt-3 divide-y divide-neutral-100">
                    {Object.entries(card.qualification).map(([field, entry]) => {
                      const suggestion = entry.suggestion
                      return (
                        <div key={field} className="flex flex-wrap items-start justify-between gap-2 py-2.5">
                          <div className="min-w-0">
                            <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">
                              {FIELD_LABELS[field] ?? field}
                            </p>
                            {editField === field ? (
                              <div className="mt-1 flex items-center gap-2">
                                <input
                                  value={editValue}
                                  onChange={(event) => setEditValue(event.target.value)}
                                  className="rounded-md border border-neutral-300 px-2 py-1 text-sm"
                                />
                                <button
                                  type="button"
                                  onClick={() => confirmField(field, coerce(editValue))}
                                  className="rounded-md bg-brand-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-800"
                                >
                                  Confirm
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setEditField(null)}
                                  className="text-xs font-medium text-neutral-500 hover:text-neutral-700"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <p className="mt-1 text-sm font-medium text-neutral-900">{display(entry.value)}</p>
                            )}
                            {suggestion && (
                              <button
                                type="button"
                                onClick={() => confirmField(field, suggestion.value)}
                                className="mt-1.5 inline-flex items-center gap-1.5 rounded-full border border-warning-100 bg-warning-50 px-2.5 py-1 text-[11px] font-medium text-warning-700 hover:bg-warning-100"
                              >
                                <span className="material-symbols-outlined text-[14px]" aria-hidden="true">tips_and_updates</span>
                                Buyer mentioned {display(suggestion.value)} — update?
                              </button>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                              entry.provenance === 'agent_confirmed'
                                ? 'border-success-100 bg-success-50 text-success-700'
                                : 'border-neutral-200 bg-neutral-50 text-neutral-600'
                            }`}>
                              {entry.provenance === 'agent_confirmed' ? 'Confirmed' : 'AI inferred'}
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                setEditField(field)
                                setEditValue(String(entry.value ?? ''))
                              }}
                              className="text-xs font-medium text-brand-700 hover:text-brand-800"
                            >
                              Edit
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
                {saveError && <p className="mt-2 text-xs font-medium text-error-600">{saveError}</p>}
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm sm:p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Offer history</p>
                {card.offers.length === 0 ? (
                  <p className="mt-3 text-sm text-neutral-600">No offers logged yet.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {card.offers.map((offer) => (
                      <div key={offer.offer_id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-neutral-200 px-3 py-2">
                        <div>
                          <p className="text-sm font-semibold text-neutral-900">
                            {offer.amount ? `AED ${Number(offer.amount).toLocaleString()}` : 'Amount TBC'}
                          </p>
                          <p className="text-xs text-neutral-500">
                            {offer.direction === 'seller_counter' ? 'Seller counter' : 'Buyer offer'}
                            {offer.created_at ? ` · ${new Date(offer.created_at).toLocaleDateString()}` : ''}
                          </p>
                        </div>
                        <OfferStatusPill status={offer.status} />
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm sm:p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Viewing history</p>
                {card.viewings.length === 0 ? (
                  <p className="mt-3 text-sm text-neutral-600">No viewings yet.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {card.viewings.map((viewing) => (
                      <div key={viewing.viewing_id} className="rounded-md border border-neutral-200 px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-medium text-neutral-800">
                            {viewing.scheduled_for ? new Date(viewing.scheduled_for).toLocaleString() : 'Unscheduled'}
                          </p>
                          <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
                            {viewing.status}
                          </span>
                        </div>
                        {viewing.feedback?.summary && (
                          <p className="mt-1 text-xs text-neutral-600">
                            Feedback{viewing.feedback.score != null ? ` (${viewing.feedback.score}/10)` : ''}: {viewing.feedback.summary}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <aside className="space-y-5">
              <DealReadinessPanel readiness={normalizeDealReadiness(card.deal_readiness)} />

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Identity</p>
                <dl className="mt-3 grid gap-3 text-sm">
                  <Fact label="Phone" value={card.identity.phone} />
                  <Fact label="Language" value={card.identity.language || '—'} />
                  <Fact label="Source" value={card.identity.source === 'portal' ? 'Portal lead' : 'WhatsApp direct'} />
                  <Fact label="Escalations" value={String(card.escalation_count)} />
                </dl>
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Conversations</p>
                <div className="mt-3 space-y-2">
                  {card.conversations.map((conversation) => (
                    <Link
                      key={conversation.conversation_id}
                      href={`/agent/conversations/${conversation.conversation_id}`}
                      className="block rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-800 transition-colors hover:bg-neutral-50"
                    >
                      {conversation.listing || 'Conversation'}
                      <span className="mt-0.5 block text-xs font-normal text-neutral-500">
                        {conversation.updated_at ? new Date(conversation.updated_at).toLocaleString() : ''}
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            </aside>
          </div>
        )}
      </div>
    </main>
  )
}

function OfferStatusPill({ status }: { status: string }) {
  const className =
    status === 'accepted'
      ? 'border-success-100 bg-success-50 text-success-700'
      : status === 'submitted' || status === 'countered'
        ? 'border-warning-100 bg-warning-50 text-warning-700'
        : status === 'draft_pending_confirm'
          ? 'border-brand-100 bg-brand-50 text-brand-700'
          : 'border-neutral-200 bg-neutral-100 text-neutral-600'
  const label = status === 'draft_pending_confirm' ? 'Pending confirm' : status.charAt(0).toUpperCase() + status.slice(1)
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${className}`}>{label}</span>
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

function display(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'number') return value.toLocaleString()
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}

function coerce(raw: string): unknown {
  const trimmed = raw.trim()
  if (trimmed === '') return null
  const numeric = Number(trimmed.replace(/,/g, ''))
  if (!Number.isNaN(numeric) && /^[\d.,]+$/.test(trimmed)) return numeric
  return trimmed
}
