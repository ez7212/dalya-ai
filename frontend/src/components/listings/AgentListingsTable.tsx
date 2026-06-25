import Image from 'next/image'
import Link from 'next/link'
import type { ReactNode } from 'react'
import type { AgentListingSummary } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'
import { nextActionForListing } from './listingIndexActions'
import { listingStatusLabel, propertyTypeLabel, readinessStatusLabel } from './listingIndexLabels'

export function ListingsTable({ listings }: { readonly listings: readonly AgentListingSummary[] }) {
  return (
    <div className="overflow-hidden">
      <div className="hidden overflow-x-auto 2xl:block">
        <table className="w-full min-w-[1180px] text-left">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50/70">
              <HeaderCell>Property</HeaderCell>
              <HeaderCell>Status</HeaderCell>
              <HeaderCell>Agent</HeaderCell>
              <HeaderCell>Buyers</HeaderCell>
              <HeaderCell>Readiness</HeaderCell>
              <HeaderCell>Pipeline</HeaderCell>
              <HeaderCell>Last activity</HeaderCell>
              <HeaderCell align="right">Next action</HeaderCell>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {listings.map((listing) => (
              <tr key={listing.id} className="transition-colors hover:bg-neutral-50">
                <td className="min-w-[320px] px-4 py-4">
                  <ListingIdentity listing={listing} />
                </td>
                <td className="px-4 py-4">
                  <StatusStack listing={listing} />
                </td>
                <td className="px-4 py-4">
                  <AgentCell name={listing.assigned_agent_name} />
                </td>
                <td className="px-4 py-4">
                  <CountStack primary={`${listing.buyer_conversation_count} conversations`} secondary={`${listing.escalated_count} escalated`} />
                </td>
                <td className="min-w-[180px] px-4 py-4">
                  <ReadinessStack listing={listing} />
                </td>
                <td className="px-4 py-4">
                  <CountStack primary={`${listing.active_viewing_count} viewings`} secondary={`${listing.open_offer_count} offers`} />
                </td>
                <td className="px-4 py-4">
                  <ActivityCell listing={listing} />
                </td>
                <td className="px-4 py-4 text-right">
                  <ActionStack listing={listing} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="divide-y divide-neutral-200 2xl:hidden">
        {listings.map((listing) => (
          <article key={listing.id} className="p-4 sm:p-5">
            <ListingIdentity listing={listing} />
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <MobileField label="Status">
                <StatusStack listing={listing} />
              </MobileField>
              <MobileField label="Agent">
                <AgentCell name={listing.assigned_agent_name} />
              </MobileField>
              <MobileField label="Buyers">
                <CountStack primary={`${listing.buyer_conversation_count} conversations`} secondary={`${listing.escalated_count} escalated`} />
              </MobileField>
              <MobileField label="Pipeline">
                <CountStack primary={`${listing.active_viewing_count} viewings`} secondary={`${listing.open_offer_count} offers`} />
              </MobileField>
              <MobileField label="Readiness">
                <ReadinessStack listing={listing} />
              </MobileField>
              <MobileField label="Activity">
                <ActivityCell listing={listing} />
              </MobileField>
            </div>
            <div className="mt-4">
              <ActionStack listing={listing} fullWidth />
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}

function HeaderCell({
  children,
  align = 'left',
}: {
  readonly children: ReactNode
  readonly align?: 'left' | 'right'
}) {
  return (
    <th
      className={`px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500 ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
      scope="col"
    >
      {children}
    </th>
  )
}

function MobileField({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  )
}

function ListingIdentity({ listing }: { readonly listing: AgentListingSummary }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="relative h-14 w-20 shrink-0 overflow-hidden rounded-md bg-neutral-100">
        {listing.first_image_url ? (
          <Image src={listing.first_image_url} alt={`${listing.title} preview`} fill sizes="80px" className="object-cover" unoptimized />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-neutral-400">
            <span className="material-symbols-outlined text-[22px]" aria-hidden="true">real_estate_agent</span>
          </div>
        )}
      </div>
      <div className="min-w-0">
        <Link href={`/listings/${listing.id}`} className="block truncate text-sm font-semibold text-neutral-900 transition-colors hover:text-brand-700">
          {listing.title}
        </Link>
        <p className="mt-1 truncate text-sm text-neutral-600">{locationLine(listing)}</p>
        <p className="mt-1 text-xs tabular-nums text-neutral-500">{priceLine(listing)}</p>
        <p className="mt-1 font-mono text-[11px] text-neutral-500">{listing.id}</p>
      </div>
    </div>
  )
}

function StatusStack({ listing }: { readonly listing: AgentListingSummary }) {
  return (
    <div className="space-y-1.5">
      <Badge tone={listing.status === 'live' ? 'sage' : 'copper'}>{listingStatusLabel(listing.status)}</Badge>
      <p className="text-xs text-neutral-600">{propertyTypeLabel(listing.property_type)}</p>
    </div>
  )
}

function AgentCell({ name }: { readonly name: string | null }) {
  return <p className="max-w-[150px] truncate text-sm font-medium text-neutral-800">{name || 'Unassigned'}</p>
}

function CountStack({ primary, secondary }: { readonly primary: string; readonly secondary: string }) {
  return (
    <div>
      <p className="text-sm font-semibold tabular-nums text-neutral-900">{primary}</p>
      <p className="mt-1 text-xs tabular-nums text-neutral-500">{secondary}</p>
    </div>
  )
}

function ReadinessStack({ listing }: { readonly listing: AgentListingSummary }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge tone={listing.missing_fact_count > 0 || listing.knowledge_status !== 'ready' ? 'copper' : 'sage'}>
        Knowledge {readinessStatusLabel(listing.knowledge_status)}
      </Badge>
      <Badge tone={listing.logistics_status === 'needs_attention' ? 'copper' : 'sage'}>Logistics {readinessStatusLabel(listing.logistics_status)}</Badge>
      {listing.missing_fact_count > 0 && <Badge tone="brick">{listing.missing_fact_count} missing facts</Badge>}
    </div>
  )
}

function ActivityCell({ listing }: { readonly listing: AgentListingSummary }) {
  return (
    <div>
      <p className="text-sm font-semibold tabular-nums text-neutral-900">{dateLabel(listing.last_activity_at)}</p>
      <p className="mt-1 text-xs tabular-nums text-neutral-500">Created {dateLabel(listing.created_at)}</p>
    </div>
  )
}

function ActionStack({ listing, fullWidth = false }: { readonly listing: AgentListingSummary; readonly fullWidth?: boolean }) {
  const action = nextActionForListing(listing)
  return (
    <div className={`flex flex-wrap gap-2 ${fullWidth ? '' : 'justify-end'}`}>
      <Link
        href={action.href}
        className={`inline-flex h-9 items-center justify-center gap-1.5 rounded-md bg-brand-700 px-3 text-xs font-semibold text-white transition-colors hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 ${
          fullWidth ? 'min-w-[160px] flex-1' : ''
        }`}
      >
        <span className="material-symbols-outlined text-[16px]" aria-hidden="true">{action.icon}</span>
        {action.label}
      </Link>
      <Link
        href={`/listings/${listing.id}`}
        className={`inline-flex h-9 items-center justify-center rounded-md border border-neutral-300 bg-white px-3 text-xs font-semibold text-neutral-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30 ${
          fullWidth ? 'min-w-[96px]' : ''
        }`}
      >
        Open
      </Link>
    </div>
  )
}

function Badge({ tone, children }: { readonly tone: 'brand' | 'sage' | 'copper' | 'brick'; readonly children: ReactNode }) {
  const className = {
    brand: 'bg-brand-50 text-brand-700',
    sage: 'bg-sage/15 text-sage',
    copper: 'bg-copper/15 text-copper',
    brick: 'bg-brick/15 text-brick',
  }[tone]
  return <span className={`inline-flex rounded-sm px-2 py-1 text-[11px] font-semibold ${className}`}>{children}</span>
}

function locationLine(listing: AgentListingSummary): string {
  const parts = [listing.community, listing.subcommunity, listing.unit_number ? `Unit ${listing.unit_number}` : null].filter((part): part is string => Boolean(part))
  return parts.length > 0 ? parts.join(' / ') : 'Location not set'
}

function priceLine(listing: AgentListingSummary): string {
  const price = listing.asking_price_aed != null ? `AED ${formatMoney(listing.asking_price_aed)}` : 'Price not set'
  const area = listing.size_sqft != null ? `${formatMoney(listing.size_sqft)} sqft` : 'Area not set'
  return `${price} / ${area}`
}

function dateLabel(value: string | null): string {
  if (!value) return 'No activity'
  const timestamp = Date.parse(value)
  if (!timestamp) return 'No activity'
  return new Intl.DateTimeFormat('en-AE', { day: '2-digit', month: 'short' }).format(new Date(timestamp))
}
