import Image from 'next/image'
import Link from 'next/link'
import type { ReactNode } from 'react'
import type { AgentListingSummary } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'
import { nextActionForListing } from './listingIndexActions'
import { listingStatusLabel, propertyTypeLabel, readinessStatusLabel } from './listingIndexLabels'

export function ListingsGrid({ listings }: { readonly listings: readonly AgentListingSummary[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 sm:p-5 xl:grid-cols-3">
      {listings.map((listing) => (
        <ListingCard key={listing.id} listing={listing} />
      ))}
    </div>
  )
}

function ListingCard({ listing }: { readonly listing: AgentListingSummary }) {
  const action = nextActionForListing(listing)
  return (
    <article className="group flex flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-card-sm transition-shadow hover:shadow-card-md">
      <Link
        href={`/listings/${listing.id}`}
        className="relative block aspect-[16/10] overflow-hidden bg-neutral-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500/40"
      >
        {listing.first_image_url ? (
          <Image
            src={listing.first_image_url}
            alt={`${listing.title} preview`}
            fill
            sizes="(min-width: 1280px) 33vw, (min-width: 640px) 50vw, 100vw"
            className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
            unoptimized
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-neutral-300">
            <span className="material-symbols-outlined text-[44px]" aria-hidden="true">real_estate_agent</span>
          </div>
        )}
        <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 p-2.5">
          <OverlayBadge tone={listing.status === 'live' ? 'sage' : 'copper'}>{listingStatusLabel(listing.status)}</OverlayBadge>
          <OverlayBadge tone="neutral">{propertyTypeLabel(listing.property_type)}</OverlayBadge>
        </div>
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <Link href={`/listings/${listing.id}`} className="block">
          <h3 className="truncate text-sm font-semibold text-neutral-900 transition-colors group-hover:text-brand-700">{listing.title}</h3>
        </Link>
        <p className="mt-1 truncate text-sm text-neutral-600">{locationLine(listing)}</p>

        <div className="mt-3 flex items-baseline justify-between gap-2">
          <p className="text-lg font-semibold tabular-nums text-neutral-900">{priceLabel(listing)}</p>
          <p className="text-xs tabular-nums text-neutral-500">{pricePerSqftLabel(listing)}</p>
        </div>

        <p className="mt-2 text-xs tabular-nums text-neutral-500">{specLine(listing)}</p>

        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge tone={listing.missing_fact_count > 0 || listing.knowledge_status !== 'ready' ? 'copper' : 'sage'}>
            Knowledge {readinessStatusLabel(listing.knowledge_status)}
          </Badge>
          <Badge tone={listing.logistics_status === 'ready' ? 'sage' : listing.logistics_status === 'not_required' ? 'neutral' : 'copper'}>
            Logistics {readinessStatusLabel(listing.logistics_status)}
          </Badge>
          {listing.missing_fact_count > 0 && <Badge tone="brick">{listing.missing_fact_count} missing facts</Badge>}
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 border-t border-neutral-100 pt-3">
          <Stat label="Buyers" value={listing.buyer_conversation_count} />
          <Stat label="Viewings" value={listing.active_viewing_count} />
          <Stat label="Offers" value={listing.open_offer_count} />
        </div>

        <div className="mt-4 flex items-center gap-2">
          <Link
            href={action.href}
            className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md bg-brand-700 px-3 text-xs font-semibold text-white transition-colors hover:bg-brand-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
          >
            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">{action.icon}</span>
            {action.label}
          </Link>
          <Link
            href={`/listings/${listing.id}`}
            className="inline-flex h-9 items-center justify-center rounded-md border border-neutral-300 bg-white px-3 text-xs font-semibold text-neutral-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"
          >
            Open
          </Link>
        </div>

        <p className="mt-3 flex items-center justify-between text-[11px] tabular-nums text-neutral-400">
          <span className="truncate">{listing.assigned_agent_name || 'Unassigned'}</span>
          <span>{activityLabel(listing.last_activity_at)}</span>
        </p>
      </div>
    </article>
  )
}

function Stat({ label, value }: { readonly label: string; readonly value: number }) {
  return (
    <div className="min-w-0">
      <p className="text-base font-semibold tabular-nums text-neutral-900">{value}</p>
      <p className="truncate text-[11px] font-medium uppercase tracking-[0.08em] text-neutral-500">{label}</p>
    </div>
  )
}

function OverlayBadge({ tone, children }: { readonly tone: 'sage' | 'copper' | 'neutral'; readonly children: ReactNode }) {
  const className = {
    sage: 'bg-sage/90 text-white',
    copper: 'bg-copper/90 text-white',
    neutral: 'bg-neutral-900/70 text-white',
  }[tone]
  return <span className={`inline-flex rounded-sm px-2 py-1 text-[11px] font-semibold backdrop-blur-sm ${className}`}>{children}</span>
}

function Badge({ tone, children }: { readonly tone: 'sage' | 'copper' | 'brick' | 'neutral'; readonly children: ReactNode }) {
  const className = {
    sage: 'bg-sage/15 text-sage',
    copper: 'bg-copper/15 text-copper',
    brick: 'bg-brick/15 text-brick',
    neutral: 'bg-neutral-100 text-neutral-600',
  }[tone]
  return <span className={`inline-flex rounded-sm px-2 py-1 text-[11px] font-semibold ${className}`}>{children}</span>
}

function locationLine(listing: AgentListingSummary): string {
  const parts = [listing.community, listing.subcommunity, listing.unit_number ? `Unit ${listing.unit_number}` : null].filter(
    (part): part is string => Boolean(part),
  )
  return parts.length > 0 ? parts.join(' / ') : 'Location not set'
}

function priceLabel(listing: AgentListingSummary): string {
  return listing.asking_price_aed != null ? `AED ${formatMoney(listing.asking_price_aed)}` : 'Price not set'
}

function pricePerSqftLabel(listing: AgentListingSummary): string {
  return listing.price_per_sqft_aed != null ? `AED ${formatMoney(listing.price_per_sqft_aed)}/sqft` : ''
}

function specLine(listing: AgentListingSummary): string {
  const parts = [
    listing.bedrooms != null ? `${listing.bedrooms} bed` : null,
    listing.bathrooms != null ? `${listing.bathrooms} bath` : null,
    listing.size_sqft != null ? `${formatMoney(listing.size_sqft)} sqft` : null,
  ].filter((part): part is string => Boolean(part))
  return parts.length > 0 ? parts.join(' · ') : 'Specs not set'
}

function activityLabel(value: string | null): string {
  if (!value) return 'No activity'
  const timestamp = Date.parse(value)
  if (!timestamp) return 'No activity'
  return new Intl.DateTimeFormat('en-AE', { day: '2-digit', month: 'short' }).format(new Date(timestamp))
}
