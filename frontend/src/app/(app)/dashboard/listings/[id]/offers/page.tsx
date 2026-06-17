'use client'

import { use } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '@/components/providers/AuthProvider'
import { useSellerOffers } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'
import type { OfferItem } from '@/lib/queries'

const LABEL_COLORS = [
  '#C9A96E', '#4A7C6F', '#6BA898', '#8A8078', '#7B9EC7',
  '#B07BAC', '#CC8866', '#6B8E7B', '#9B8A6E', '#7A8FA6',
]

function avatarColor(label: string): string {
  let hash = 0
  for (let i = 0; i < label.length; i++) {
    hash = label.charCodeAt(i) + ((hash << 5) - hash)
  }
  return LABEL_COLORS[Math.abs(hash) % LABEL_COLORS.length]
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-gold/15 border-gold/30 text-gold',
  accepted: 'bg-sage/20 border-sage/35 text-sage',
  rejected: 'bg-ink/60 border-gold/10 text-n-500',
}

function OfferCard({ offer, askingPrice, index }: { offer: OfferItem; askingPrice: number; index: number }) {
  const color = avatarColor(offer.buyer_label)
  const pctText = offer.vs_asking
  const isAbove = pctText.startsWith('+')

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index * 0.04, 0.3) }}
      className="surface-1 rounded-xl p-5 ghost-border hover:border-gold/25 transition-colors"
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div
          className="w-9 h-9 rounded-full shrink-0 flex items-center justify-center text-xs font-bold text-deep"
          style={{ backgroundColor: color }}
          aria-hidden="true"
        >
          {offer.buyer_label.replace('Buyer ', 'B')}
        </div>

        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className="text-sand text-sm font-semibold">{offer.buyer_label}</span>
            <span
              className={`inline-flex items-center text-[10px] font-semibold px-2.5 py-0.5 rounded border capitalize ${
                STATUS_STYLES[offer.status] ?? STATUS_STYLES.pending
              }`}
            >
              {offer.status}
            </span>
          </div>

          {/* Amount row */}
          <div className="flex items-baseline gap-3 flex-wrap mb-2">
            <span className="font-mono text-gold text-lg font-bold">
              AED {formatMoney(offer.amount_aed)}
            </span>
            <span className={`font-mono text-xs font-medium ${isAbove ? 'text-sage' : 'text-n-500'}`}>
              {pctText} vs asking
            </span>
          </div>

          {/* Date */}
          <p className="text-[11px] text-n-500">
            Received {formatDate(offer.received_at)}
          </p>
        </div>
      </div>
    </motion.div>
  )
}

export default function ListingOffersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { loading: authLoading } = useAuth()
  const { data, isLoading, error } = useSellerOffers(id, !authLoading)

  if (isLoading || authLoading) {
    return <p className="text-n-500 text-sm py-10 text-center">Loading offers...</p>
  }

  if (error) {
    return <p className="text-red-400 text-sm py-10 text-center" role="alert">{error.message}</p>
  }

  const offers = data?.offers ?? []
  const askingPrice = data?.asking_price ?? 0
  const threshold = data?.threshold

  if (offers.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="surface-1 rounded-xl ghost-border py-20 px-6 text-center"
      >
        <span
          className="material-symbols-outlined text-gold/30 block mb-4"
          aria-hidden="true"
          style={{ fontSize: '40px' }}
        >
          request_quote
        </span>
        <p className="text-sand text-base font-semibold mb-2">No offers yet</p>
        <p className="text-n-500 text-sm max-w-sm mx-auto leading-relaxed">
          When a buyer submits an offer above your minimum threshold, it will appear here.
        </p>
      </motion.div>
    )
  }

  const sorted = [...offers].sort(
    (a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime(),
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Context bar */}
      <div className="surface-1 rounded-xl p-4 ghost-border mb-4 flex items-center gap-6 flex-wrap text-xs">
        <div>
          <span className="text-n-500">Asking price</span>
          <span className="ml-2 font-mono text-gold font-semibold">
            AED {formatMoney(askingPrice)}
          </span>
        </div>
        {threshold != null && (
          <div>
            <span className="text-n-500">Alert threshold</span>
            <span className="ml-2 font-mono text-sand font-semibold">
              AED {formatMoney(threshold)}
            </span>
          </div>
        )}
        <div className="text-n-500">
          {sorted.length} offer{sorted.length !== 1 ? 's' : ''} received
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {sorted.map((offer, i) => (
          <OfferCard key={`${offer.buyer_label}-${offer.received_at}`} offer={offer} askingPrice={askingPrice} index={i} />
        ))}
      </div>
    </motion.div>
  )
}
