'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/providers/AuthProvider'
import { useSellerOffers } from '@/lib/queries'
import type { OfferItem } from '@/lib/queries'
import { apiFetch } from '@/lib/api'
import { formatMoney } from '@/lib/utils'

type ListingOffersWorkspaceProps = {
  readonly id: string
}

type OfferTone = 'sage' | 'copper' | 'brick' | 'slate'

export function ListingOffersWorkspace({ id }: ListingOffersWorkspaceProps) {
  const { loading: authLoading } = useAuth()
  const offersQuery = useSellerOffers(id, !authLoading)
  const offers = offersQuery.data?.offers ?? []
  const activeOffers = offers.filter((offer) => isActiveOffer(offer.status))
  const pastOffers = offers.filter((offer) => !isActiveOffer(offer.status))

  if (authLoading || offersQuery.isLoading) {
    return <OffersSkeleton />
  }

  if (offersQuery.error) {
    return (
      <section className="rounded-lg border border-brick/25 bg-white px-4 py-8 text-center" role="alert">
        <p className="text-sm font-semibold text-brick">Offers could not be loaded.</p>
        <p className="mt-2 text-sm text-neutral-600">{errorMessage(offersQuery.error)}</p>
      </section>
    )
  }

  return (
    <div className="space-y-5" data-listing-workspace-route="offers" data-listing-id={id}>
      <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Offer workspace</p>
            <h2 className="mt-1 text-lg font-semibold text-neutral-900">Active and past buyer offers</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-neutral-600">
              Review serious buyer offers, compare against asking price and threshold, and keep negotiation history visible.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <Metric label="Active" value={String(activeOffers.length)} />
            <Metric label="Past" value={String(pastOffers.length)} />
            <ThresholdEditor listingId={id} threshold={offersQuery.data?.threshold ?? null} />
          </div>
        </div>
      </section>

      <OfferSection title="Active offers" empty="No active offers on this listing." offers={activeOffers} />
      <OfferSection title="Past offers" empty="No accepted, rejected, or closed offers yet." offers={pastOffers} />
    </div>
  )
}

function OffersSkeleton() {
  return (
    <div className="space-y-5" aria-label="Loading offers">
      <div className="h-36 animate-pulse rounded-lg border border-neutral-200 bg-white" />
      <div className="h-64 animate-pulse rounded-lg border border-neutral-200 bg-white" />
    </div>
  )
}

function OfferSection({ title, empty, offers }: { readonly title: string; readonly empty: string; readonly offers: readonly OfferItem[] }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-neutral-900">{title}</h2>
        <span className="rounded-sm bg-neutral-100 px-2 py-1 text-[11px] font-medium text-neutral-700">{offers.length} offers</span>
      </div>

      {offers.length === 0 ? (
        <p className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-600">{empty}</p>
      ) : (
        <div className="mt-4 divide-y divide-neutral-200">
          {offers.map((offer) => (
            <article key={`${offer.buyer_label}-${offer.received_at ?? offer.amount_aed}`} className="py-4 first:pt-0 last:pb-0">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-neutral-900">{offer.buyer_label}</p>
                  <p className="mt-1 text-2xl font-semibold text-neutral-900 tabular-nums">{moneyLabel(offer.amount_aed)}</p>
                </div>
                <span className={`w-fit rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${statusTone(statusToneName(offer.status))}`}>
                  {statusLabel(offer.status)}
                </span>
              </div>
              <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Fact label="Against asking" value={offer.vs_asking ?? 'Not recorded'} />
                <Fact label="Received" value={dateLabel(offer.received_at)} />
                <Fact label="Next step" value={nextStepLabel(offer.status)} />
              </dl>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function ThresholdEditor({ listingId, threshold }: { readonly listingId: string; readonly threshold: number | null }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState<string>(threshold == null ? '' : String(threshold))

  const save = useMutation({
    mutationFn: async () => {
      const trimmed = value.trim()
      const parsed = trimmed === '' ? null : Number(trimmed)
      if (parsed != null && (Number.isNaN(parsed) || parsed < 0)) throw new Error('Enter a valid amount.')
      const res = await apiFetch(`/api/v1/listings/${listingId}/offer-threshold`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold_aed: parsed }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Update failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess: async () => {
      setEditing(false)
      await queryClient.invalidateQueries({ queryKey: ['seller-offers', listingId] })
    },
  })

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => { setValue(threshold == null ? '' : String(threshold)); setEditing(true) }}
        title="Edit the offer escalation threshold"
        className="min-w-20 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-left transition-colors hover:border-brand-300 hover:bg-brand-50"
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Threshold</p>
        <p className="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{moneyLabel(threshold)}</p>
      </button>
    )
  }

  return (
    <div className="min-w-20 rounded-md border border-brand-200 bg-brand-50 px-3 py-2 text-left">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Threshold (AED)</p>
      <input
        type="number"
        min={0}
        value={value}
        autoFocus
        onChange={(event) => setValue(event.target.value)}
        className="mt-1 w-full rounded border border-neutral-300 px-1.5 py-0.5 text-sm tabular-nums outline-none focus:border-brand-500"
      />
      <div className="mt-2 flex items-center gap-2">
        <button type="button" onClick={() => save.mutate()} disabled={save.isPending} className="rounded bg-brand-700 px-2 py-1 text-xs font-semibold text-white disabled:opacity-60">
          {save.isPending ? 'Saving' : 'Save'}
        </button>
        <button type="button" onClick={() => { setEditing(false); setValue(threshold == null ? '' : String(threshold)) }} className="text-xs font-medium text-neutral-500 hover:text-neutral-700">
          Cancel
        </button>
      </div>
      {save.error && <p className="mt-1 text-[11px] font-medium text-brick">{errorMessage(save.error)}</p>}
    </div>
  )
}

function errorDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  return typeof (body as { detail: unknown }).detail === 'string' ? (body as { detail: string }).detail : null
}

function Metric({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="min-w-20 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{value}</p>
    </div>
  )
}

function Fact({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-neutral-900 tabular-nums">{value}</dd>
    </div>
  )
}

// NOTE: the offers API (`build_listing_offers_payload`) currently emits status="pending" for
// every offer, so today only the "pending" branches below are exercised. The richer status
// handling (accepted/rejected/countered/etc.) is kept ahead of the backend emitting real
// offer lifecycle states; the "Past offers" section stays empty until then.
function isActiveOffer(status: string): boolean {
  return !['accepted', 'rejected', 'declined', 'discarded', 'expired', 'withdrawn'].includes(status)
}

function statusToneName(status: string): OfferTone {
  if (status === 'accepted') return 'sage'
  if (['rejected', 'declined', 'discarded', 'expired', 'withdrawn'].includes(status)) return 'brick'
  if (['pending', 'submitted', 'countered', 'draft_pending_confirm'].includes(status)) return 'copper'
  return 'slate'
}

function statusTone(tone: OfferTone): string {
  const classes: Record<OfferTone, string> = {
    sage: 'bg-sage/15 text-sage',
    copper: 'bg-copper/15 text-copper',
    brick: 'bg-brick/15 text-brick',
    slate: 'bg-brand-50 text-brand-700',
  }
  return classes[tone]
}

function nextStepLabel(status: string): string {
  if (status === 'accepted') return 'Prepare conveyancing handoff'
  if (['rejected', 'declined', 'discarded'].includes(status)) return 'Closed'
  if (status === 'countered') return 'Await buyer response'
  return 'Agent review'
}

function moneyLabel(value?: number | null): string {
  return value == null ? 'Not set' : `AED ${formatMoney(value)}`
}

function dateLabel(value?: string | null): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function statusLabel(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Open the listing again from the inventory workspace.'
}
