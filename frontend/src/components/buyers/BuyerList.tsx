'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { DealReadinessSummaryLine } from '@/components/readiness/DealReadinessCallout'
import {
  normalizeDealReadiness,
  type DealReadinessMetadata,
} from '@/components/readiness/deal-readiness'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error'

interface BuyerRow {
  profile_id: string
  name?: string | null
  phone_masked: string
  top_conversation_id: string
  top_listing?: string | null
  qualification: {
    budget_max_aed?: number | null
    financing?: string | null
    timeline?: string | null
  }
  deal_readiness?: DealReadinessMetadata | null
  score?: number | null
  last_activity_at?: string | null
  open_offers: number
  next_viewing_at?: string | null
  opted_out: boolean
  stale: boolean
  conversation_count: number
}

const FILTERS = [
  { label: 'All', value: '' },
  { label: 'Open offer', value: 'has_open_offer' },
  { label: 'Viewing scheduled', value: 'viewing_scheduled' },
  { label: 'Stale', value: 'stale' },
]

const SORTS = [
  { label: 'Score', value: 'score' },
  { label: 'Last activity', value: 'last_activity' },
  { label: 'Name', value: 'name' },
]

export function BuyerList() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [buyers, setBuyers] = useState<BuyerRow[]>([])
  const [filter, setFilter] = useState('')
  const [sort, setSort] = useState('score')

  useEffect(() => {
    let active = true
    async function load() {
      setLoadState('loading')
      try {
        const params = new URLSearchParams()
        if (filter) params.set('filter', filter)
        params.set('sort', sort)
        const response = await apiFetch(`/api/v1/agent/buyers?${params.toString()}`)
        if (!response.ok) throw new Error(`Buyers returned ${response.status}`)
        const payload = await response.json()
        if (!active) return
        setBuyers(payload.buyers ?? [])
        setLoadState('live')
      } catch {
        if (active) setLoadState('error')
      }
    }
    load()
    return () => {
      active = false
    }
  }, [filter, sort])

  return (
    <main className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="mx-auto max-w-[1200px]">
        <header className="mb-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
            <Link href="/agent" className="font-medium text-brand-700 hover:text-brand-800">Agent desk</Link>
            <span aria-hidden="true">/</span>
            <span>Buyers</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">Buyers</h1>
        </header>

        <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200 px-4 py-4 sm:px-5">
            <div className="flex flex-wrap gap-2">
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
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-neutral-600">
              Sort
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value)}
                className="h-9 rounded-md border border-neutral-300 bg-white px-2 text-sm text-neutral-800"
              >
                {SORTS.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
          </div>

          {loadState === 'loading' ? (
            <div className="space-y-3 px-4 py-5 sm:px-5">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-16 animate-pulse rounded-lg bg-neutral-100" />
              ))}
            </div>
          ) : loadState === 'error' ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-error-600">Could not load buyers.</p>
            </div>
          ) : buyers.length === 0 ? (
            <div className="px-4 py-8 sm:px-5">
              <p className="text-sm font-medium text-neutral-800">No buyers match this filter.</p>
              <p className="mt-1 text-sm text-neutral-500">Buyer profiles build automatically as conversations come in.</p>
            </div>
          ) : (
            <div className="divide-y divide-neutral-200">
              {buyers.map((buyer) => (
                <Link
                  key={buyer.profile_id}
                  href={`/agent/buyers/${buyer.profile_id}`}
                  className="grid gap-2 px-4 py-4 transition-colors hover:bg-neutral-50 sm:px-5 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1.6fr)_repeat(3,minmax(0,0.8fr))] md:items-center"
                >
                  <div>
                    <p className="text-sm font-semibold text-neutral-900">{buyer.name || buyer.phone_masked}</p>
                    <p className="mt-0.5 text-xs text-neutral-500">
                      {buyer.phone_masked} · {buyer.conversation_count} conversation{buyer.conversation_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <div>
                    <div className="flex flex-wrap gap-1.5">
                      {buyer.qualification.budget_max_aed && (
                        <Chip>≤ AED {Number(buyer.qualification.budget_max_aed).toLocaleString()}</Chip>
                      )}
                      {buyer.qualification.financing && <Chip>{label(buyer.qualification.financing)}</Chip>}
                      {buyer.qualification.timeline && <Chip>{buyer.qualification.timeline}</Chip>}
                      {buyer.opted_out && (
                        <span className="rounded-full border border-error-100 bg-error-50 px-2 py-0.5 text-[11px] font-medium text-error-700">
                          Opted out
                        </span>
                      )}
                    </div>
                    <DealReadinessSummaryLine readiness={normalizeDealReadiness(buyer.deal_readiness)} compact />
                  </div>
                  <Cell label="Score" value={buyer.score != null ? String(buyer.score) : '—'} />
                  <Cell label="Open offers" value={String(buyer.open_offers)} />
                  <Cell
                    label="Next viewing"
                    value={buyer.next_viewing_at ? formatShort(buyer.next_viewing_at) : '—'}
                  />
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-700">
      {children}
    </span>
  )
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500 md:hidden">{label}</p>
      <p className="text-sm font-medium text-neutral-800">{value}</p>
    </div>
  )
}

function label(value: string): string {
  return value.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}

function formatShort(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}
