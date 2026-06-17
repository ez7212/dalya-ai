'use client'

import { use, useState } from 'react'
import { motion } from 'framer-motion'
import { useQueryClient } from '@tanstack/react-query'
import { Badge } from '@/components/ui/Badge'
import { GoldButton } from '@/components/ui/GoldButton'
import { useAuth } from '@/components/providers/AuthProvider'
import { apiFetch } from '@/lib/api'
import { formatMoney } from '@/lib/utils'
import { useBuyerListingMatches, useListingDetail } from '@/lib/queries'
import { StatusRow } from '@/components/sections/SellerUpload'
import {
  InspectionAudioReady,
  InterestedBuyerMatch,
  InterestedBuyersPanel,
  UnitProfileView,
} from '@/components/shared-ui'

const STAGE_ICONS: Record<string, string> = {
  spa_verified: 'check_circle',
  community_research: 'travel_explore',
  listing_review: 'hourglass_top',
  trakheesi_permit: 'verified',
  portal_listings: 'language',
  ai_advisor_live: 'smart_toy',
}

export default function ListingOverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { loading: authLoading } = useAuth()
  const { data: listing, isLoading, error } = useListingDetail(id, !authLoading)
  const { data: buyerMatches, isLoading: matchesLoading, error: matchesError } = useBuyerListingMatches(id, !authLoading)

  const lastActivity = listing?.leads?.[0]?.last_active ?? listing?.leads?.[0]?.last_message_at ?? null

  if (isLoading || authLoading) {
    return <p className="text-n-500 text-sm py-10 text-center">Loading overview...</p>
  }
  if (error) {
    return <p className="text-red-400 text-sm py-10 text-center" role="alert">{error.message}</p>
  }
  if (!listing) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {/* Key stats */}
      <section>
        <h2 className="text-[11px] text-n-500 uppercase tracking-widest font-medium mb-4">Listing Stats</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCell label="Asking Price" value={listing.asking_price != null ? `AED ${formatMoney(listing.asking_price)}` : '—'} gold />
          <StatCell label="Leads" value={listing.lead_count.toString()} />
          <StatCell label="Escalated" value={listing.escalated_count.toString()} />
          <StatCell
            label="Last Activity"
            value={lastActivity ? new Date(lastActivity).toLocaleDateString() : '—'}
            small
          />
        </div>
      </section>

      {/* Listing settings — editable */}
      <ListingSettings listingId={id} listing={listing} />

      <InspectionNotesPanel listingId={id} listing={listing} />

      <BuyerMatchesPanel
        listingId={id}
        matches={buyerMatches?.matches || []}
        isLoading={matchesLoading}
        error={matchesError instanceof Error ? matchesError.message : null}
      />

      {/* SPA summary */}
      <section className="surface-1 rounded-xl p-6 ghost-border">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h2 className="text-sand font-semibold text-base">SPA Summary</h2>
            <p className="text-n-500 text-xs mt-0.5">Extracted from your Sale &amp; Purchase Agreement</p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-5 gap-x-8">
          <DetailCell label="Project" value={listing.property_name} />
          <DetailCell label="Unit" value={listing.unit_number} />
          <DetailCell label="Developer" value={listing.developer} />
          {(listing.bedrooms != null || listing.bathrooms != null) && (
            <DetailCell
              label="Bedrooms"
              value={`${listing.bedrooms ?? '—'} BD / ${listing.bathrooms ?? '—'} BA`}
            />
          )}
          {listing.bua_sqft != null && (
            <DetailCell
              label="BUA"
              value={`${listing.bua_sqft.toLocaleString()} sqft`}
              mono
            />
          )}
          {listing.total_price != null && (
            <DetailCell
              label="Purchase Price"
              value={`AED ${formatMoney(listing.total_price)}`}
              mono
              gold
            />
          )}
        </div>

        {(listing.noc_eligible != null || listing.total_paid_percent != null) && (
          <div className="flex items-center gap-3 mt-6 pt-5 border-t border-gold/8">
            {listing.noc_eligible != null && (
              <Badge variant={listing.noc_eligible ? 'sage' : 'copper'}>
                {listing.noc_eligible ? 'NOC Eligible' : 'NOC Pending'}
              </Badge>
            )}
            {listing.total_paid_percent != null && (
              <span className="text-xs text-n-500 font-mono">
                {listing.total_paid_percent}% paid
              </span>
            )}
          </div>
        )}
      </section>

      {/* Processing stages */}
      {listing.processing_stages && listing.processing_stages.length > 0 && (
        <section className="surface-1 rounded-xl p-6 ghost-border">
          <div className="mb-5">
            <h2 className="text-sand font-semibold text-base">Listing Status</h2>
            <p className="text-n-500 text-xs mt-0.5">Where your listing is in the onboarding pipeline</p>
          </div>
          <div className="space-y-4">
            {listing.processing_stages.map((s) => (
              <StatusRow
                key={s.key}
                icon={STAGE_ICONS[s.key] || 'circle'}
                label={s.label}
                description={s.description}
                status={s.status}
                note={s.note}
              />
            ))}
          </div>
        </section>
      )}
    </motion.div>
  )
}

function InspectionNotesPanel({
  listingId,
  listing,
}: {
  listingId: string
  listing: {
    unit_profile?: Record<string, string[] | string | null>
    unit_profile_history?: Array<Record<string, unknown>>
  }
}) {
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)

  const submitAudio = async (audio: InspectionAudioReady) => {
    setSaving(true)
    setError(null)
    try {
      const audioBase64 = await blobToBase64(audio.file)
      await saveInspectionNotes({
        audio_base64: audioBase64,
        content_type: audio.contentType,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Inspection note upload failed')
    } finally {
      setSaving(false)
    }
  }

  const submitTranscript = async () => {
    if (!transcript.trim()) return
    setSaving(true)
    setError(null)
    try {
      await saveInspectionNotes({ transcript_text: transcript.trim() })
      setTranscript('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Inspection notes failed')
    } finally {
      setSaving(false)
    }
  }

  const saveInspectionNotes = async (body: Record<string, string>) => {
    const res = await apiFetch(`/api/v1/agent/listings/${listingId}/inspection-notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, mode: 'append' }),
    })
    if (!res.ok) {
      const payload = await res.json().catch(() => null)
      throw new Error(payload?.detail ?? `Save failed (${res.status})`)
    }
    await queryClient.invalidateQueries({ queryKey: ['listing', listingId] })
  }

  return (
    <div className="space-y-3">
      <UnitProfileView
        profile={listing.unit_profile || {}}
        history={listing.unit_profile_history || []}
        onAudioReady={submitAudio}
        renderTypedFallback={
          <div className="rounded border border-neutral-200 bg-white p-4">
            <label className="block text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
              Typed fallback
            </label>
            <textarea
              rows={4}
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
              placeholder="Type or paste inspection notes if you are not recording."
              className="mt-2 w-full rounded border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
            />
            <button
              onClick={submitTranscript}
              disabled={saving || !transcript.trim()}
              className="mt-3 inline-flex min-h-11 items-center justify-center rounded bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {saving ? 'Saving notes...' : 'Save typed notes'}
            </button>
          </div>
        }
      />
      {error && <p className="rounded border border-error-100 bg-error-50 px-3 py-2 text-sm text-error-700" role="alert">{error}</p>}
    </div>
  )
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const value = String(reader.result || '')
      resolve(value.includes(',') ? value.split(',')[1] : value)
    }
    reader.onerror = () => reject(new Error('Could not read recorded audio'))
    reader.readAsDataURL(blob)
  })
}

function BuyerMatchesPanel({
  listingId,
  matches,
  isLoading,
  error,
}: {
  listingId: string
  matches: Array<{
    match_id: string
    buyer_id: string
    match_score: number
    aligned_preferences: string[]
    traced_inquiry_listing_ids: string[]
    outreach_draft: string
    status: 'draft' | 'copied' | 'dismissed' | 'sent_external'
  }>
  isLoading: boolean
  error: string | null
}) {
  const queryClient = useQueryClient()
  const mapped: InterestedBuyerMatch[] = matches.map((match, index) => ({
    id: match.match_id,
    buyerLabel: match.buyer_id || `Buyer ${index + 1}`,
    matchScore: match.match_score,
    matchReasons: match.aligned_preferences,
    tracedInquiries: match.traced_inquiry_listing_ids,
    outreachDraft: match.outreach_draft,
    status: match.status,
  }))

  return (
    <InterestedBuyersPanel
      matches={mapped}
      loading={isLoading}
      error={error}
      onCopyDraft={async (matchId) => {
        await apiFetch(`/api/v1/agent/listings/${listingId}/buyer-matches/${matchId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'copied' }),
        }).catch(() => null)
        await queryClient.invalidateQueries({ queryKey: ['buyer-listing-matches', listingId] })
      }}
    />
  )
}

function StatCell({
  label,
  value,
  gold,
  small,
}: {
  label: string
  value: string
  gold?: boolean
  small?: boolean
}) {
  return (
    <div className="surface-1 rounded-xl p-5 ghost-border">
      <p className="text-n-500 text-[10px] uppercase tracking-widest mb-1.5">{label}</p>
      <p
        className={`font-mono font-bold ${gold ? 'text-gold' : 'text-sand'} ${
          small ? 'text-sm' : 'text-lg'
        }`}
      >
        {value}
      </p>
    </div>
  )
}

function DetailCell({
  label,
  value,
  mono,
  gold,
}: {
  label: string
  value: string
  mono?: boolean
  gold?: boolean
}) {
  return (
    <div>
      <span className="text-n-500 text-[11px] block mb-1">{label}</span>
      <p
        className={`text-sm font-medium ${gold ? 'text-gold' : 'text-sand'} ${mono ? 'font-mono' : ''}`}
      >
        {value}
      </p>
    </div>
  )
}

/* ---------- Listing Settings (editable) ---------- */

function formatNumericInput(raw: string): string {
  const cleaned = raw.replace(/[^\d.]/g, '')
  const parts = cleaned.split('.')
  const intPart = parts[0] || ''
  const decPart = parts.length > 1 ? '.' + parts.slice(1).join('').slice(0, 2) : ''
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return withCommas + decPart
}

function parseNumericInput(formatted: string): string {
  return formatted.replace(/,/g, '')
}

interface ListingSettingsProps {
  listingId: string
  listing: {
    asking_price?: number | null
    negotiation_threshold?: number | null
    seller_notes?: string | null
  }
}

function ListingSettings({ listingId, listing }: ListingSettingsProps) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [askingPrice, setAskingPrice] = useState(
    listing.asking_price != null ? formatNumericInput(String(listing.asking_price)) : ''
  )
  const [threshold, setThreshold] = useState(
    listing.negotiation_threshold != null ? formatNumericInput(String(listing.negotiation_threshold)) : ''
  )
  const [notes, setNotes] = useState(listing.seller_notes || '')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [justSaved, setJustSaved] = useState(false)

  const startEdit = () => {
    setAskingPrice(listing.asking_price != null ? formatNumericInput(String(listing.asking_price)) : '')
    setThreshold(listing.negotiation_threshold != null ? formatNumericInput(String(listing.negotiation_threshold)) : '')
    setNotes(listing.seller_notes || '')
    setSaveError(null)
    setEditing(true)
  }

  const cancel = () => {
    setEditing(false)
    setSaveError(null)
  }

  const save = async () => {
    if (askingPrice && threshold) {
      const askNum = Number(parseNumericInput(askingPrice))
      const thrNum = Number(parseNumericInput(threshold))
      if (thrNum >= askNum) {
        setSaveError('Minimum offer to alert must be less than the asking price.')
        return
      }
    }
    setSaving(true)
    setSaveError(null)
    try {
      const body: Record<string, string | number | null> = {}
      if (askingPrice) body.seller_asking_price = Number(parseNumericInput(askingPrice))
      body.negotiation_threshold_aed = threshold ? Number(parseNumericInput(threshold)) : null
      body.seller_notes = notes || null

      const res = await apiFetch(`/api/v1/seller/listings/${listingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Save failed (${res.status})`)
      }
      // Refresh the cached listing data
      await queryClient.invalidateQueries({ queryKey: ['listing', listingId] })
      setEditing(false)
      setJustSaved(true)
      setTimeout(() => setJustSaved(false), 2400)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const inputCls =
    'w-full rounded-lg bg-deep border border-gold/10 px-4 py-2.5 text-sand text-sm placeholder:text-n-500 focus:outline-none focus:border-gold/30 transition-colors'

  if (!editing) {
    return (
      <section className="surface-1 rounded-xl p-6 ghost-border">
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h2 className="text-sand font-semibold text-base">Listing Settings</h2>
            <p className="text-n-500 text-xs mt-0.5">Asking price, alert threshold, and seller notes</p>
          </div>
          <button
            onClick={startEdit}
            className="text-sm text-n-500 hover:text-gold transition-colors font-medium"
          >
            Edit
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-5 gap-x-8">
          <DetailCell
            label="Asking Price"
            value={listing.asking_price != null ? `AED ${formatMoney(listing.asking_price)}` : '—'}
            mono
            gold
          />
          <DetailCell
            label="Contact Threshold"
            value={
              listing.negotiation_threshold != null
                ? `AED ${formatMoney(listing.negotiation_threshold)}`
                : 'Not set — all offers alert'
            }
            mono={listing.negotiation_threshold != null}
          />
        </div>
        {listing.seller_notes && (
          <div className="mt-5 pt-5 border-t border-gold/8">
            <span className="text-n-500 text-[11px] block mb-2">Notes for the AI</span>
            <p className="text-sand text-sm leading-relaxed">{listing.seller_notes}</p>
          </div>
        )}
        {justSaved && (
          <p className="mt-4 text-xs text-sage">Settings saved.</p>
        )}
      </section>
    )
  }

  return (
    <section className="surface-1 rounded-xl p-6 ghost-border">
      <div className="mb-5">
        <h2 className="text-sand font-semibold text-base">Listing Settings</h2>
        <p className="text-n-500 text-xs mt-0.5">Update your asking price, alert threshold, and notes</p>
      </div>

      <div className="space-y-5">
        <div>
          <label className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Asking Price (AED)
          </label>
          <input
            type="text"
            inputMode="decimal"
            className={`${inputCls} font-mono`}
            placeholder="e.g. 1,850,000"
            value={askingPrice}
            onChange={(e) => setAskingPrice(formatNumericInput(e.target.value))}
          />
        </div>

        <div>
          <label className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Contact Threshold (AED)
          </label>
          <input
            type="text"
            inputMode="decimal"
            className={`${inputCls} font-mono`}
            placeholder="Leave empty to alert on all offers"
            value={threshold}
            onChange={(e) => setThreshold(formatNumericInput(e.target.value))}
          />
          <p className="text-[11px] text-n-500 mt-1.5">
            We&apos;ll only notify you about offers at or above this amount.
          </p>
        </div>

        <div>
          <label className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Notes for the AI
          </label>
          <textarea
            rows={3}
            className={inputCls}
            placeholder="e.g. Pool view, willing to negotiate on payment timing"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
      </div>

      {saveError && (
        <p className="mt-4 text-sm text-red-400" role="alert">{saveError}</p>
      )}

      <div className="mt-6 flex items-center gap-4">
        <GoldButton
          onClick={save}
          size="sm"
          className={saving ? 'opacity-50 pointer-events-none' : ''}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </GoldButton>
        <button
          onClick={cancel}
          disabled={saving}
          className="text-sm text-n-500 hover:text-sand transition-colors"
        >
          Cancel
        </button>
      </div>
    </section>
  )
}
