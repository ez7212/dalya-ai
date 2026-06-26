'use client'

import Link from 'next/link'
import { useAuth } from '@/components/providers/AuthProvider'
import { InterestedBuyersPanel } from '@/components/shared-ui/InterestedBuyersPanel'
import type { InterestedBuyerMatch } from '@/components/shared-ui/InterestedBuyersPanel'
import { UnitProfileView } from '@/components/shared-ui/UnitProfileView'
import type { UnitProfile, UnitProfileHistoryItem } from '@/components/shared-ui/UnitProfileView'
import { useAgentListings, useBuyerListingMatches, useListingDetail } from '@/lib/queries'
import type { BuyerListingMatch, ListingDetail, ProcessingStage } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'

type StatItem = { readonly label: string; readonly value: string; readonly detail: string; readonly tone: 'brand' | 'sage' | 'copper' | 'brick' | 'neutral' }

export function ListingOverviewWorkspace({ id }: { readonly id: string }) {
  const { loading: authLoading } = useAuth()
  const detailQuery = useListingDetail(id, !authLoading)
  const listingsQuery = useAgentListings(!authLoading)
  const matchesQuery = useBuyerListingMatches(id, !authLoading)
  const detail = detailQuery.data
  const summary = listingsQuery.data?.listings.find((listing) => listing.id === id)
  const matches = toInterestedBuyerMatches(matchesQuery.data?.matches ?? [])

  if (authLoading || detailQuery.isLoading) {
    return <OverviewSkeleton />
  }

  if (detailQuery.error) {
    return (
      <section className="rounded-lg border border-brick/25 bg-white px-4 py-8 text-center" role="alert">
        <p className="text-sm font-semibold text-brick">Overview could not be loaded.</p>
        <p className="mt-2 text-sm text-neutral-600">{errorMessage(detailQuery.error)}</p>
      </section>
    )
  }

  const stages = detail?.processing_stages ?? []
  const profile = detail?.unit_profile ?? {}
  const history = toUnitProfileHistory(detail?.unit_profile_history ?? [])
  const hasProfile = hasUnitProfile(profile) || history.length > 0

  return (
    <div className="space-y-5" data-listing-workspace-route="overview" data-listing-id={id}>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {overviewStats(detail, summary).map((item) => (
          <article key={item.label} className="rounded-lg border border-neutral-200 bg-white p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{item.label}</p>
            <p className={`mt-2 text-2xl font-semibold tabular-nums ${toneText(item.tone)}`}>{item.value}</p>
            <p className="mt-1 text-xs leading-relaxed text-neutral-500">{item.detail}</p>
          </article>
        ))}
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <ProcessingPanel stages={stages} />
          <ListingSettingsPanel detail={detail} />
          {hasProfile && <UnitProfileView profile={profile} history={history} />}
          {(matches.length > 0 || matchesQuery.isLoading || matchesQuery.error) && (
            <InterestedBuyersPanel
              matches={matches}
              loading={matchesQuery.isLoading}
              error={matchesQuery.error ? errorMessage(matchesQuery.error) : null}
              defaultLimit={3}
            />
          )}
        </div>
        <aside className="space-y-5">
          <NextStepsPanel id={id} detail={detail} />
          <NotesPanel notes={detail?.seller_notes} />
        </aside>
      </div>
    </div>
  )
}

function OverviewSkeleton() {
  return (
    <div className="space-y-5" aria-label="Loading overview">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {['price', 'buyers', 'documents', 'health'].map((key) => (
          <div key={key} className="h-28 animate-pulse rounded-lg border border-neutral-200 bg-white" />
        ))}
      </div>
      <div className="h-72 animate-pulse rounded-lg border border-neutral-200 bg-white" />
    </div>
  )
}

function ProcessingPanel({ stages }: { readonly stages: readonly ProcessingStage[] }) {
  if (stages.length === 0) {
    return (
      <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
        <PanelHeader label="Processing health" title="No processing stages reported" />
        <p className="mt-3 text-sm leading-relaxed text-neutral-600">
          Dalya has not received a processing timeline for this listing yet. Uploaded documents and knowledge checks will appear here as they run.
        </p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <PanelHeader label="Processing health" title="Workspace readiness" />
      <div className="mt-4 divide-y divide-neutral-200">
        {stages.map((stage) => (
          <div key={stage.key} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-900">{stage.label}</p>
              <p className="mt-1 text-sm leading-relaxed text-neutral-600">{stage.note || stage.description}</p>
            </div>
            <span className={`w-fit rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${stageTone(stage.status)}`}>
              {stage.key === 'ai_advisor_live' && stage.status === 'complete' ? 'Live' : statusLabel(stage.status)}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}

function ListingSettingsPanel({ detail }: { readonly detail?: ListingDetail }) {
  const rows = [
    ['Asking price', moneyLabel(detail?.asking_price ?? detail?.total_price)],
    ['Offer threshold', moneyLabel(detail?.negotiation_threshold)],
    ['NOC eligible', detail?.noc_eligible == null ? 'Not recorded' : detail.noc_eligible ? 'Yes' : 'No'],
    ['Handover', dateLabel(detail?.handover_date)],
    ['Bedrooms', numberLabel(detail?.bedrooms)],
    ['Bathrooms', numberLabel(detail?.bathrooms)],
    ['BUA', sqftLabel(detail?.bua_sqft)],
    ['Plot', sqftLabel(detail?.plot_sqft)],
  ] satisfies readonly (readonly [string, string])[]

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <PanelHeader label="Listing settings" title="Agent-facing facts" />
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
            <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</dt>
            <dd className="mt-1 text-sm font-medium text-neutral-900 tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function NextStepsPanel({ id, detail }: { readonly id: string; readonly detail?: ListingDetail }) {
  const blocked = detail?.processing_stages?.find((stage) => stage.status === 'blocked')
  const items = [
    { href: `/listings/${id}/documents`, icon: 'description', label: 'Review documents' },
    { href: `/listings/${id}/knowledge`, icon: 'fact_check', label: blocked ? `Resolve ${blocked.label}` : 'Check knowledge' },
    { href: `/listings/${id}/logistics`, icon: 'event_available', label: 'Prepare viewings' },
  ] satisfies readonly { readonly href: string; readonly icon: string; readonly label: string }[]

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4">
      <PanelHeader label="Next actions" title="Keep this listing moving" />
      <div className="mt-4 space-y-2">
        {items.map((item) => (
          <Link key={item.href} href={item.href} className="flex items-center justify-between gap-3 rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-800 transition-colors hover:border-brand-200 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30">
            <span className="inline-flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-brand-700" aria-hidden="true">{item.icon}</span>
              {item.label}
            </span>
            <span className="material-symbols-outlined text-[18px] text-neutral-400" aria-hidden="true">arrow_forward</span>
          </Link>
        ))}
      </div>
    </section>
  )
}

function NotesPanel({ notes }: { readonly notes?: string | null }) {
  if (!notes?.trim()) return null
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4">
      <PanelHeader label="Agent notes" title="Seller context" />
      <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-neutral-700">{notes}</p>
    </section>
  )
}

function PanelHeader({ label, title }: { readonly label: string; readonly title: string }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <h2 className="mt-1 text-base font-semibold text-neutral-900">{title}</h2>
    </div>
  )
}

function overviewStats(detail?: ListingDetail, summary?: { readonly reference_document_count: number; readonly buyer_conversation_count: number; readonly active_viewing_count: number; readonly open_offer_count: number; readonly missing_fact_count: number }): readonly StatItem[] {
  return [
    { label: 'Asking price', value: moneyLabel(detail?.asking_price ?? detail?.total_price), detail: 'Shown to agents with Inter tabular numerals.', tone: 'brand' },
    { label: 'Buyer conversations', value: String(summary?.buyer_conversation_count ?? detail?.lead_count ?? 0), detail: `${detail?.escalated_count ?? 0} escalated`, tone: (detail?.escalated_count ?? 0) > 0 ? 'copper' : 'neutral' },
    { label: 'Documents', value: String(summary?.reference_document_count ?? 0), detail: 'Reference files attached to listing context.', tone: (summary?.reference_document_count ?? 0) > 0 ? 'sage' : 'neutral' },
    { label: 'Open work', value: String((summary?.active_viewing_count ?? 0) + (summary?.open_offer_count ?? 0) + (summary?.missing_fact_count ?? 0)), detail: 'Viewings, offers, and missing facts.', tone: (summary?.missing_fact_count ?? 0) > 0 ? 'brick' : 'brand' },
  ]
}

function toInterestedBuyerMatches(matches: readonly BuyerListingMatch[]): InterestedBuyerMatch[] {
  return matches.map((match) => ({
    id: match.match_id,
    buyerLabel: `Buyer ${match.buyer_id.slice(0, 8)}`,
    matchScore: match.match_score,
    matchReasons: match.aligned_preferences,
    tracedInquiries: match.traced_inquiry_listing_ids,
    outreachDraft: match.outreach_draft,
    status: statusLabel(match.status),
  }))
}

function hasUnitProfile(profile: UnitProfile): boolean {
  return Object.values(profile).some((value) => Array.isArray(value) ? value.length > 0 : Boolean(value))
}

function toUnitProfileHistory(items: readonly Record<string, unknown>[]): UnitProfileHistoryItem[] {
  return items.map((item) => ({
    timestamp: stringOrNull(item.timestamp),
    source: stringOrNull(item.source),
    agent_user_id: stringOrNull(item.agent_user_id),
    transcript: stringOrNull(item.transcript),
    provenance: stringOrNull(item.provenance),
  }))
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}

function moneyLabel(value?: number | null): string {
  return value == null ? 'Not set' : `AED ${formatMoney(value)}`
}

function sqftLabel(value?: number | null): string {
  return value == null ? 'Not recorded' : `${formatMoney(value)} sqft`
}

function numberLabel(value?: number | null): string {
  return value == null ? 'Not recorded' : String(value)
}

function dateLabel(value?: string | null): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Try reopening this listing from the inventory workspace.'
}

function statusLabel(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function toneText(tone: StatItem['tone']): string {
  const classes: Record<StatItem['tone'], string> = {
    brand: 'text-brand-700',
    sage: 'text-sage',
    copper: 'text-copper',
    brick: 'text-brick',
    neutral: 'text-neutral-900',
  }
  return classes[tone]
}

function stageTone(status: ProcessingStage['status']): string {
  const classes: Record<ProcessingStage['status'], string> = {
    pending: 'bg-neutral-100 text-neutral-700',
    in_progress: 'bg-brand-50 text-brand-700',
    complete: 'bg-sage/15 text-sage',
    blocked: 'bg-brick/15 text-brick',
  }
  return classes[status]
}
