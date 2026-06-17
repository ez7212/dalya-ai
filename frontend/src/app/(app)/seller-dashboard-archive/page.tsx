'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { GoldButton } from '@/components/ui/GoldButton'
import { useAuth } from '@/components/providers/AuthProvider'
import { useSellerListings } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'

type ListingStatus = 'active' | 'draft' | 'pending_review' | 'sold' | 'blocked'

export default function SellerDashboardArchivePage() {
  const { user, loading: authLoading } = useAuth()
  const { data, isLoading: loading, error } = useSellerListings(!authLoading && !!user)

  const listings = data?.listings ?? []
  const totalListings = listings.length
  const totalConversations = data?.total_conversations ?? 0
  const totalEscalated = data?.total_escalated ?? 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="max-w-6xl mx-auto"
    >
      <div className="mb-8 rounded-xl border border-copper/30 bg-copper/10 px-5 py-4">
        <p className="text-copper text-xs font-semibold uppercase tracking-widest mb-1">
          Archived seller dashboard
        </p>
        <p className="text-n-300 text-sm leading-relaxed">
          This surface is preserved for reference while Dalya shifts active product work to
          the brokerage agent dashboard.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-10">
        <div>
          <h1 className="editorial text-3xl md:text-4xl font-bold text-sand tracking-tight">
            My Listings
          </h1>
        </div>
        <GoldButton href="/dashboard/listings/new" size="sm">Upload New SPA</GoldButton>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-10">
        <StatCard label="Total Listings" value={totalListings} />
        <StatCard label="Conversations" value={totalConversations} />
        <StatCard label="Escalated Leads" value={totalEscalated} />
      </div>

      {loading || authLoading ? (
        <div className="text-center py-20">
          <p className="text-n-500 text-sm">Loading your listings...</p>
        </div>
      ) : error ? (
        <div className="text-center py-20">
          <p className="text-red-400 text-sm" role="alert">{error.message}</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="text-center py-20">
          <span className="material-symbols-outlined text-gold/30 block mb-4" style={{ fontSize: '48px' }}>
            home_work
          </span>
          <p className="text-sand text-lg font-semibold mb-2">No listings yet</p>
          <p className="text-n-500 text-sm mb-8">Upload your SPA to create your first listing.</p>
          <GoldButton href="/dashboard/listings/new">Upload Your SPA</GoldButton>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {listings.map((listing, i) => (
            <motion.div
              key={listing.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
            >
              <Link
                href={`/dashboard/listings/${listing.id}`}
                className="block surface-1 rounded-xl p-6 ghost-border shadow-ambient hover:border-gold/25 transition-colors group"
              >
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-sand font-semibold text-base group-hover:text-gold transition-colors">
                      {listing.property_name}
                    </h3>
                    <p className="text-n-500 text-xs mt-0.5">Unit {listing.unit_number}</p>
                  </div>
                  {listing.status !== 'pending_review' && (
                    <StatusPill status={listing.status as ListingStatus} />
                  )}
                </div>

                <p className="font-mono text-xl font-bold text-gold mb-4">
                  {listing.asking_price != null ? `AED ${formatMoney(listing.asking_price)}` : 'Price pending'}
                </p>

                <div className="flex items-center gap-5 text-xs text-n-500">
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>chat</span>
                    {listing.lead_count} leads
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>priority_high</span>
                    {listing.escalated_count} escalated
                  </span>
                  {listing.last_activity && (
                    <span className="ml-auto text-n-500">
                      Last activity: {new Date(listing.last_activity).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="surface-1 rounded-xl p-5 ghost-border">
      <p className="text-n-500 text-xs uppercase tracking-widest mb-1">{label}</p>
      <p className="font-mono text-2xl font-bold text-gold">{value}</p>
    </div>
  )
}

function StatusPill({ status }: { status: ListingStatus }) {
  const variants: Record<ListingStatus, { label: string; cls: string }> = {
    active: { label: 'Live', cls: 'badge-sage' },
    pending_review: { label: 'Pending Review', cls: 'border border-copper/40 text-copper bg-copper/10' },
    sold: { label: 'Sold', cls: 'border border-n-500/30 text-n-500 bg-n-500/5' },
    draft: { label: 'Draft', cls: 'border border-n-500/30 text-n-500 bg-transparent' },
    blocked: { label: 'Blocked', cls: 'border border-red-400/40 text-red-400 bg-red-400/10' },
  }
  const v = variants[status] ?? variants.draft
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded ${v.cls}`}>
      {v.label}
    </span>
  )
}
