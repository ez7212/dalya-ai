'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'
import { useAuth } from '@/components/providers/AuthProvider'
import { useAgentListings, useListingDetail } from '@/lib/queries'
import type { AgentListingSummary, ListingDetail, ProcessingStage } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'
import { nextActionForListing } from './listingIndexActions'

type WorkspaceTab = {
  readonly label: string
  readonly href: (id: string) => string
  readonly match: (pathname: string, id: string) => boolean
}

type ListingWorkspaceShellProps = {
  readonly id: string
  readonly children: ReactNode
}

type NextAction = {
  readonly label: string
  readonly href: string
  readonly icon: string
}

const WORKSPACE_TABS: readonly WorkspaceTab[] = [
  { label: 'Overview', href: (id) => `/listings/${id}`, match: (pathname, id) => pathname === `/listings/${id}` },
  { label: 'Knowledge', href: (id) => `/listings/${id}/knowledge`, match: (pathname, id) => pathname.startsWith(`/listings/${id}/knowledge`) },
  { label: 'Community Data', href: (id) => `/listings/${id}/community`, match: (pathname, id) => pathname.startsWith(`/listings/${id}/community`) },
  { label: 'Logistics', href: (id) => `/listings/${id}/logistics`, match: (pathname, id) => pathname.startsWith(`/listings/${id}/logistics`) },
  { label: 'Offers', href: (id) => `/listings/${id}/offers`, match: (pathname, id) => pathname.startsWith(`/listings/${id}/offers`) },
  { label: 'Documents', href: (id) => `/listings/${id}/documents`, match: (pathname, id) => pathname.startsWith(`/listings/${id}/documents`) },
]

export function ListingWorkspaceShell({ id, children }: ListingWorkspaceShellProps) {
  const pathname = usePathname()
  const { loading: authLoading } = useAuth()
  const detailQuery = useListingDetail(id, !authLoading)
  const listingsQuery = useAgentListings(!authLoading)
  const summary = listingsQuery.data?.listings.find((listing) => listing.id === id)
  const title = listingTitle(detailQuery.data, summary)

  if (authLoading || detailQuery.isLoading) {
    return <ListingWorkspaceFrame>{loadingHeader(id)}</ListingWorkspaceFrame>
  }

  if (detailQuery.error) {
    return (
      <ListingWorkspaceFrame>
        <div className="rounded-lg border border-brick/25 bg-white px-4 py-10 text-center" role="alert">
          <p className="text-sm font-semibold text-brick">Listing could not be loaded.</p>
          <p className="mt-2 text-sm text-neutral-600">
            {detailQuery.error instanceof Error ? detailQuery.error.message : 'Open the listing again from the inventory workspace.'}
          </p>
          <Link
            href="/listings"
            className="mt-5 inline-flex items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
          >
            Return to listings
          </Link>
        </div>
      </ListingWorkspaceFrame>
    )
  }

  return (
    <ListingWorkspaceFrame>
      <header className="rounded-lg border border-neutral-200 bg-white">
        <div className="border-b border-neutral-200 px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <nav aria-label={`Listings / ${title}`} className="text-sm text-neutral-500">
                <Link href="/listings" className="font-medium text-brand-700 transition-colors hover:text-brand-800">
                  Listings
                </Link>
                <span className="mx-2 text-neutral-400">/</span>
                <span className="text-neutral-700">{title}</span>
              </nav>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">{title}</h1>
                <StatusBadge status={detailQuery.data?.status ?? summary?.status ?? 'unknown'} />
              </div>
              <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-neutral-600">
                <MetaItem label="Agent" value={summary?.assigned_agent_name ?? 'Unassigned'} />
                <MetaItem label="Price" value={priceLabel(detailQuery.data, summary)} strong />
                <MetaItem label="Community" value={communityLabel(detailQuery.data, summary)} />
                <MetaItem label="Type" value={propertyTypeLabel(detailQuery.data?.property_type ?? summary?.property_type)} />
              </dl>
            </div>
            <PrimaryAction action={nextAction(id, summary, detailQuery.data)} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {healthBadges(detailQuery.data, summary).map((badge) => (
              <HealthBadge key={badge.label} label={badge.label} tone={badge.tone} />
            ))}
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3" aria-label="Listing workspace">
          {WORKSPACE_TABS.map((tab) => {
            const active = tab.match(pathname, id)
            return (
              <Link
                key={tab.label}
                href={tab.href(id)}
                aria-current={active ? 'page' : undefined}
                className={`relative whitespace-nowrap px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 ${
                  active ? 'text-brand-700' : 'text-neutral-600 hover:text-neutral-900'
                }`}
              >
                {tab.label}
                {active && <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-sm bg-brand-600" aria-hidden="true" />}
              </Link>
            )
          })}
        </nav>
      </header>
      <main className="mt-5">{children}</main>
    </ListingWorkspaceFrame>
  )
}

function ListingWorkspaceFrame({ children }: { readonly children: ReactNode }) {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-5 text-neutral-800 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1500px]">{children}</div>
    </div>
  )
}

function loadingHeader(id: string) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-5 sm:px-5" aria-label="Loading listing workspace">
      <div className="h-4 w-56 animate-pulse rounded bg-neutral-100" />
      <div className="mt-4 h-8 w-80 max-w-full animate-pulse rounded bg-neutral-100" />
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        {[`${id}-agent`, `${id}-price`, `${id}-community`, `${id}-type`].map((key) => (
          <div key={key} className="h-10 animate-pulse rounded-md bg-neutral-100" />
        ))}
      </div>
      <div className="mt-5 h-11 animate-pulse rounded-md bg-neutral-100" />
    </div>
  )
}

function MetaItem({ label, value, strong = false }: { readonly label: string; readonly value: string; readonly strong?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</dt>
      <dd className={`mt-1 tabular-nums ${strong ? 'font-semibold text-neutral-900' : 'text-neutral-700'}`}>{value}</dd>
    </div>
  )
}

function PrimaryAction({ action }: { readonly action: NextAction }) {
  return (
    <Link
      href={action.href}
      aria-label={`Primary next action: ${action.label}`}
      className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-brand-700 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
    >
      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{action.icon}</span>
      {action.label}
    </Link>
  )
}

function StatusBadge({ status }: { readonly status: string }) {
  const live = status.toLowerCase() === 'live'
  const tone = live ? 'bg-sage/15 text-sage' : 'bg-copper/15 text-copper'
  return <span className={`rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${tone}`}>{live ? 'Live' : statusLabel(status)}</span>
}

function HealthBadge({ label, tone }: { readonly label: string; readonly tone: 'brand' | 'sage' | 'copper' | 'brick' | 'neutral' }) {
  const classes: Record<typeof tone, string> = {
    brand: 'bg-brand-50 text-brand-700',
    sage: 'bg-sage/15 text-sage',
    copper: 'bg-copper/15 text-copper',
    brick: 'bg-brick/15 text-brick',
    neutral: 'bg-neutral-100 text-neutral-700',
  }
  return <span className={`rounded-sm px-2 py-1 text-[11px] font-medium ${classes[tone]}`}>{label}</span>
}

function listingTitle(detail?: ListingDetail, summary?: AgentListingSummary): string {
  if (summary?.title) return summary.title
  const name = detail?.property_name?.trim()
  const unit = detail?.unit_number?.trim()
  if (name && unit) return `${name} / Unit ${unit}`
  return name || unit || 'Unknown listing'
}

function priceLabel(detail?: ListingDetail, summary?: AgentListingSummary): string {
  const price = summary?.asking_price_aed ?? detail?.asking_price ?? detail?.total_price
  return price != null ? `AED ${formatMoney(price)}` : 'Price not set'
}

function communityLabel(detail?: ListingDetail, summary?: AgentListingSummary): string {
  return summary?.community ?? detail?.sub_community ?? detail?.developer ?? 'Community not set'
}

function propertyTypeLabel(value?: string | null): string {
  if (value === 'ready') return 'Ready'
  if (value === 'off_plan') return 'Off-plan'
  return value ? statusLabel(value) : 'Type not set'
}

function statusLabel(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function healthBadges(detail?: ListingDetail, summary?: AgentListingSummary) {
  const missingFacts = summary?.missing_fact_count ?? 0
  const activeViewings = summary?.active_viewing_count ?? 0
  const openOffers = summary?.open_offer_count ?? 0
  const documentCount = summary?.reference_document_count ?? 0
  const stages = detail?.processing_stages ?? []
  const blockedStage = stages.find((stage) => stage.status === 'blocked')
  return [
    { label: summary ? `Knowledge ${statusLabel(summary.knowledge_status)}` : stageLabel(stages), tone: missingFacts > 0 ? 'copper' : 'sage' },
    { label: summary ? `Logistics ${statusLabel(summary.logistics_status)}` : 'Logistics unknown', tone: logisticsBadgeTone(summary?.logistics_status) },
    { label: `${missingFacts} missing facts`, tone: missingFacts > 0 ? 'brick' : 'neutral' },
    { label: `${activeViewings} active viewings`, tone: activeViewings > 0 ? 'brand' : 'neutral' },
    { label: `${openOffers} open offers`, tone: openOffers > 0 ? 'brand' : 'neutral' },
    { label: `${documentCount} documents`, tone: documentCount > 0 ? 'sage' : 'neutral' },
    ...(blockedStage ? [{ label: `${blockedStage.label} blocked`, tone: 'brick' as const }] : []),
  ] satisfies ReadonlyArray<{ readonly label: string; readonly tone: 'brand' | 'sage' | 'copper' | 'brick' | 'neutral' }>
}

function logisticsBadgeTone(status?: AgentListingSummary['logistics_status']): 'sage' | 'copper' | 'neutral' {
  if (status === 'needs_attention') return 'copper'
  if (status === 'not_required') return 'neutral'
  return 'sage'
}

function stageLabel(stages: readonly ProcessingStage[]): string {
  const active = stages.find((stage) => stage.status === 'blocked' || stage.status === 'in_progress')
  return active ? `${active.label} ${statusLabel(active.status)}` : 'Knowledge unknown'
}

function nextAction(id: string, summary?: AgentListingSummary, detail?: ListingDetail): NextAction {
  // Prefer the shared inventory action so labels/icons/routes match the listings index exactly.
  if (summary) return nextActionForListing(summary)
  const blockedStage = detail?.processing_stages?.find((stage) => stage.status === 'blocked')
  if (blockedStage) return { label: `Review ${blockedStage.label}`, href: `/listings/${id}/knowledge`, icon: 'priority_high' }
  return { label: 'Review overview', href: `/listings/${id}`, icon: 'arrow_forward' }
}
