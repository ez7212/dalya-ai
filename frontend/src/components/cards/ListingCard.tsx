'use client'

import Image from 'next/image'
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { GoldButton } from '@/components/ui/GoldButton'
import type { Listing } from '@/types/listing'
import { formatMoney } from '@/lib/utils'

interface Props { listing: Listing; onAskDalya?: (id: string) => void }

export function ListingCard({ listing, onAskDalya }: Props) {
  const noc =
    listing.nocStatus === 'ready'
      ? { v: 'sage' as const, label: 'NOC Ready' }
      : listing.nocStatus === 'at40'
      ? { v: 'copper' as const, label: 'NOC at 40%' }
      : { v: 'copper' as const, label: 'NOC Pending' }

  return (
    <motion.article
      className="surface-1 rounded-xl overflow-hidden ghost-border shadow-ambient flex flex-col h-full"
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
    >
      {/* Image */}
      <div className="relative overflow-hidden flex-shrink-0" style={{ aspectRatio: '16/9' }}>
        <Image
          src={listing.imageUrl}
          alt={listing.imageAlt}
          fill
          className="object-cover"
          loading="lazy"
          sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink/70 to-transparent" />
        <div className="absolute top-3 right-3">
          <Badge variant="verified" icon="verified">SPA Verified</Badge>
        </div>
      </div>

      {/* Content */}
      <div className="p-5 flex flex-col flex-1 gap-4">

        {/* Tier 1: identity + price */}
        <div>
          <h3 className="font-semibold text-sand text-base leading-snug">{listing.title}</h3>
          <p className="text-[12px] text-n-500 mt-0.5">{listing.location}</p>
          <p className="font-mono text-2xl font-bold text-gold mt-3">AED {formatMoney(listing.priceAed)}</p>
        </div>

        {/* Tier 2: key specs — inline, equal weight */}
        <div className="flex items-center gap-2.5 text-[12px] text-n-300 font-medium flex-wrap">
          <span>{listing.bedrooms} bed</span>
          <span className="text-gold/25">·</span>
          <span>{listing.buaSqft.toLocaleString()} sqft</span>
          <span className="text-gold/25">·</span>
          <span>{listing.handoverQuarter}</span>
        </div>

        {/* Tier 3: investment signals — quiet, at the bottom */}
        <div className="mt-auto space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-n-500">{listing.paymentPercent}% paid</span>
            <Badge variant={noc.v} className="text-[10px]">{noc.label}</Badge>
          </div>
          <ProgressBar percent={listing.paymentPercent} variant={listing.nocStatus === 'at40' ? 'copper' : 'gold'} />
        </div>

        <GoldButton className="w-full text-center block" onClick={() => onAskDalya?.(listing.id)} size="sm">
          Ask Dalya
        </GoldButton>
      </div>
    </motion.article>
  )
}
