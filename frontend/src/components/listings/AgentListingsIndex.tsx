'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/components/providers/AuthProvider'
import { useAgentListings, type AgentListingSummary } from '@/lib/queries'
import {
  AgentListingsControls,
  type AttentionFilter,
  type InventoryDisplayMode,
  type InventorySort,
  type StatusFilter,
} from './AgentListingsControls'
import { ListingsGrid } from './AgentListingsGrid'
import { ListingsTable } from './AgentListingsTable'

const VIEW_STORAGE_KEY = 'dalya:listings-view'

const EMPTY_LISTINGS: readonly AgentListingSummary[] = []

export function AgentListingsIndex() {
  const { loading: authLoading } = useAuth()
  const { data, isLoading, error } = useAgentListings(!authLoading)
  const listings = data?.listings ?? EMPTY_LISTINGS
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [attentionFilter, setAttentionFilter] = useState<AttentionFilter>('all')
  const [sort, setSort] = useState<InventorySort>('last_activity')
  const [view, setView] = useState<InventoryDisplayMode>('grid')

  useEffect(() => {
    // Read persisted view after mount so server and first client render agree (avoids hydration mismatch).
    const stored = window.localStorage.getItem(VIEW_STORAGE_KEY)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time hydration-safe restore of persisted preference
    if (stored === 'grid' || stored === 'table') setView(stored)
  }, [])

  function handleViewChange(next: InventoryDisplayMode) {
    setView(next)
    window.localStorage.setItem(VIEW_STORAGE_KEY, next)
  }

  const visibleListings = useMemo(
    () => applyInventoryView(listings, { search, statusFilter, attentionFilter, sort }),
    [listings, search, statusFilter, attentionFilter, sort],
  )
  const stats = buildStats(listings, data?.total_conversations ?? 0)

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-800">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Inventory command center</p>
              <h1 className="mt-1 text-2xl font-semibold text-neutral-900">Listings</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
                Active inventory, buyer pressure, readiness gaps, and next work for each property.
              </p>
            </div>
            <AddListingLink />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8">
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Listing summary">
          <Metric label="Needs attention" value={stats.attention.toString()} tone={stats.attention > 0 ? 'warning' : 'neutral'} />
          <Metric label="Buyer conversations" value={stats.conversations.toString()} />
          <Metric label="Active viewings" value={stats.viewings.toString()} />
          <Metric label="Open offers" value={stats.offers.toString()} />
        </section>

        <section className="mt-5 rounded-lg border border-neutral-200 bg-white shadow-card-sm" aria-label="Listings">
          <AgentListingsControls
            totalCount={listings.length}
            visibleCount={visibleListings.length}
            search={search}
            statusFilter={statusFilter}
            attentionFilter={attentionFilter}
            sort={sort}
            view={view}
            onSearchChange={setSearch}
            onStatusFilterChange={setStatusFilter}
            onAttentionFilterChange={setAttentionFilter}
            onSortChange={setSort}
            onViewChange={handleViewChange}
          />

          {isLoading || authLoading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error instanceof Error ? error.message : 'Listings could not be loaded.'} />
          ) : listings.length === 0 ? (
            <EmptyState />
          ) : visibleListings.length === 0 ? (
            <NoResultsState />
          ) : view === 'grid' ? (
            <ListingsGrid listings={visibleListings} />
          ) : (
            <ListingsTable listings={visibleListings} />
          )}
        </section>
      </main>
    </div>
  )
}

interface InventoryView {
  readonly search: string
  readonly statusFilter: StatusFilter
  readonly attentionFilter: AttentionFilter
  readonly sort: InventorySort
}

function applyInventoryView(listings: readonly AgentListingSummary[], view: InventoryView): readonly AgentListingSummary[] {
  const needle = view.search.trim().toLowerCase()
  return [...listings]
    .filter((listing) => matchesSearch(listing, needle))
    .filter((listing) => matchesStatus(listing, view.statusFilter))
    .filter((listing) => matchesAttention(listing, view.attentionFilter))
    .sort((left, right) => compareListings(left, right, view.sort))
}

function matchesSearch(listing: AgentListingSummary, needle: string): boolean {
  if (!needle) return true
  return [
    listing.title,
    listing.community,
    listing.subcommunity,
    listing.building_or_project,
    listing.unit_number,
    listing.id,
  ].some((value) => value?.toLowerCase().includes(needle))
}

function matchesStatus(listing: AgentListingSummary, filter: StatusFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'ready' || filter === 'off_plan') return listing.property_type === filter
  return listing.status === filter
}

function matchesAttention(listing: AgentListingSummary, filter: AttentionFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'attention') return needsAttention(listing)
  if (filter === 'buyers') return listing.buyer_conversation_count > 0
  if (filter === 'offers') return listing.open_offer_count > 0
  if (filter === 'viewings') return listing.active_viewing_count > 0
  return isRecent(listing.last_activity_at)
}

function compareListings(left: AgentListingSummary, right: AgentListingSummary, sort: InventorySort): number {
  if (sort === 'created') return dateValue(right.created_at) - dateValue(left.created_at)
  if (sort === 'buyers') return right.buyer_conversation_count - left.buyer_conversation_count
  if (sort === 'offers') return right.open_offer_count - left.open_offer_count
  if (sort === 'viewings') return right.active_viewing_count - left.active_viewing_count
  if (sort === 'price') return (right.asking_price_aed ?? 0) - (left.asking_price_aed ?? 0)
  return dateValue(right.last_activity_at) - dateValue(left.last_activity_at)
}

function buildStats(listings: readonly AgentListingSummary[], conversations: number) {
  return {
    attention: listings.filter(needsAttention).length,
    conversations,
    viewings: listings.reduce((total, listing) => total + listing.active_viewing_count, 0),
    offers: listings.reduce((total, listing) => total + listing.open_offer_count, 0),
  }
}

function needsAttention(listing: AgentListingSummary): boolean {
  return (
    listing.missing_fact_count > 0 ||
    listing.knowledge_status !== 'ready' ||
    listing.logistics_status === 'needs_attention' ||
    listing.primary_next_action !== 'open_listing'
  )
}

function isRecent(value: string | null): boolean {
  if (!value) return false
  const fourteenDaysMs = 14 * 24 * 60 * 60 * 1000
  return Date.now() - dateValue(value) <= fourteenDaysMs
}

function dateValue(value: string | null): number {
  return value ? Date.parse(value) || 0 : 0
}

function Metric({
  label,
  value,
  tone = 'neutral',
}: {
  readonly label: string
  readonly value: string
  readonly tone?: 'neutral' | 'warning'
}) {
  const valueClass = tone === 'warning' ? 'text-warning-700' : 'text-neutral-900'
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${valueClass}`}>{value}</p>
    </div>
  )
}

function AddListingLink() {
  return (
    <Link
      href="/listings/new"
      className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
    >
      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">add</span>
      Add listing
    </Link>
  )
}

function LoadingState() {
  return (
    <div className="space-y-3 p-4" aria-label="Loading listings">
      {[0, 1, 2].map((item) => (
        <div key={item} className="grid animate-pulse gap-3 rounded-md border border-neutral-200 p-3 md:grid-cols-[minmax(280px,1fr)_140px_160px_140px]">
          <div className="h-14 rounded-md bg-neutral-100" />
          <div className="h-14 rounded-md bg-neutral-100" />
          <div className="h-14 rounded-md bg-neutral-100" />
          <div className="h-14 rounded-md bg-neutral-100" />
        </div>
      ))}
    </div>
  )
}

function ErrorState({ message }: { readonly message: string }) {
  return (
    <div className="px-4 py-12 text-center" role="alert">
      <p className="text-sm font-medium text-brick">Listings could not be loaded.</p>
      <p className="mt-2 text-sm text-neutral-600">{message}</p>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="px-4 py-14 text-center">
      <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-brand-50 text-brand-700">
        <span className="material-symbols-outlined text-[22px]" aria-hidden="true">real_estate_agent</span>
      </div>
      <h2 className="mt-4 text-base font-semibold text-neutral-900">No listings added yet</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-600">
        Add a ready property from a portal link or enter an off-plan listing manually, then it will appear here.
      </p>
      <div className="mt-5">
        <AddListingLink />
      </div>
    </div>
  )
}

function NoResultsState() {
  return (
    <div className="px-4 py-12 text-center">
      <p className="text-sm font-semibold text-neutral-900">No listings match these filters.</p>
      <p className="mt-2 text-sm text-neutral-600">Adjust search, status, attention, or activity filters.</p>
    </div>
  )
}
