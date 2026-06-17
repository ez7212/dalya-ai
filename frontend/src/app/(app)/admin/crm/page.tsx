'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { useAuth } from '@/components/providers/AuthProvider'
import { useAdminBuyers, useAdminBuyerStats } from '@/lib/queries'
import type { BuyerSummary } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'

const STAGES = [
  { key: 'all', label: 'All' },
  { key: 'new', label: 'New' },
  { key: 'engaged', label: 'Engaged' },
  { key: 'qualified', label: 'Qualified' },
  { key: 'offer', label: 'Offer' },
  { key: 'negotiation', label: 'Negotiation' },
  { key: 'closed_won', label: 'Won' },
  { key: 'closed_lost', label: 'Lost' },
] as const

function StagePill({ stage }: { stage: string }) {
  const styles: Record<string, string> = {
    new: 'border border-n-500/30 text-n-500',
    engaged: 'border border-gold/30 text-gold bg-gold/10',
    qualified: 'badge-sage',
    offer: 'text-gold bg-gold/15',
    negotiation: 'text-gold bg-gold/20 font-bold',
    closed_won: 'badge-sage',
    closed_lost: 'border border-red-400/30 text-red-400',
  }
  return (
    <span
      className={`inline-flex items-center text-[10px] font-semibold px-2.5 py-1 rounded ${styles[stage] ?? styles.new}`}
    >
      {stage.replace('_', ' ')}
    </span>
  )
}

export default function CrmBuyerListPage() {
  const { loading: authLoading } = useAuth()
  const { data: buyersData, isLoading, error } = useAdminBuyers(!authLoading)
  const { data: stats } = useAdminBuyerStats(!authLoading)

  const [activeStage, setActiveStage] = useState('all')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce search input
  const searchTimeout = useState<ReturnType<typeof setTimeout> | null>(null)
  const handleSearch = (value: string) => {
    setSearch(value)
    if (searchTimeout[0]) clearTimeout(searchTimeout[0])
    searchTimeout[1](
      setTimeout(() => setDebouncedSearch(value), 300),
    )
  }

  const buyers = buyersData?.buyers ?? []

  const filtered = useMemo(() => {
    let result = buyers
    if (activeStage !== 'all') {
      result = result.filter((b) => b.lead_stage === activeStage)
    }
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase()
      result = result.filter(
        (b) =>
          (b.name && b.name.toLowerCase().includes(q)) ||
          b.phone.includes(q),
      )
    }
    return result
  }, [buyers, activeStage, debouncedSearch])

  const loading = isLoading || authLoading

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <h1 className="editorial text-3xl md:text-4xl font-bold text-sand tracking-tight mb-8">
        Buyer CRM
      </h1>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Buyers" value={stats?.total_buyers ?? 0} />
        <StatCard label="New This Week" value={stats?.new_this_week ?? 0} />
        <StatCard label="Qualified" value={stats?.qualified ?? 0} />
        <StatCard label="Offers Made" value={stats?.offers_made ?? 0} />
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
        <div className="flex flex-wrap gap-2">
          {STAGES.map((s) => (
            <button
              key={s.key}
              onClick={() => setActiveStage(s.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                activeStage === s.key
                  ? 'bg-gold/15 text-gold'
                  : 'bg-white/5 text-n-500 hover:text-sand hover:bg-white/10'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="sm:ml-auto">
          <input
            type="text"
            placeholder="Search name or phone..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full sm:w-64 rounded-lg bg-deep border border-gold/10 px-4 py-2 text-sm text-sand placeholder:text-n-500 focus:outline-none focus:border-gold/30 transition-colors"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-20">
          <p className="text-n-500 text-sm">Loading buyers...</p>
        </div>
      ) : error ? (
        <div className="text-center py-20">
          <p className="text-red-400 text-sm" role="alert">{error.message}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-n-500 text-sm">No buyers found.</p>
        </div>
      ) : (
        <div className="surface-1 rounded-xl ghost-border shadow-ambient overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="border-b border-gold/10">
                  <Th>Name</Th>
                  <Th>Phone</Th>
                  <Th>Stage</Th>
                  <Th align="right">Budget</Th>
                  <Th align="center">Beds</Th>
                  <Th align="right">Listings</Th>
                  <Th align="right">Last Active</Th>
                  <Th>Source</Th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((buyer, i) => (
                  <BuyerRow key={buyer.phone} buyer={buyer} index={i} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </motion.div>
  )
}

function Th({
  children,
  align = 'left',
}: {
  children: React.ReactNode
  align?: 'left' | 'right' | 'center'
}) {
  return (
    <th
      className={`px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold text-${align}`}
    >
      {children}
    </th>
  )
}

function BuyerRow({ buyer, index }: { buyer: BuyerSummary; index: number }) {
  const encodedPhone = encodeURIComponent(buyer.phone)
  return (
    <motion.tr
      className="border-b border-gold/5 hover:bg-gold/3 transition-colors"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.02 }}
    >
      <td className="px-5 py-3.5">
        <Link
          href={`/admin/crm/${encodedPhone}`}
          className="text-sm text-sand font-medium hover:text-gold transition-colors"
        >
          {buyer.name || 'Unknown'}
        </Link>
      </td>
      <td className="px-5 py-3.5 text-sm font-mono text-n-500">{buyer.phone}</td>
      <td className="px-5 py-3.5">
        <StagePill stage={buyer.lead_stage} />
      </td>
      <td className="px-5 py-3.5 text-sm font-mono text-gold text-right">
        {buyer.budget_aed != null ? `AED ${formatMoney(buyer.budget_aed)}` : '—'}
      </td>
      <td className="px-5 py-3.5 text-sm text-n-500 text-center">
        {buyer.bedroom_preferences ?? '—'}
      </td>
      <td className="px-5 py-3.5 text-sm font-mono text-n-500 text-right">
        {buyer.listings_inquired}
      </td>
      <td className="px-5 py-3.5 text-xs text-n-500 text-right">
        {buyer.last_active
          ? new Date(buyer.last_active).toLocaleDateString()
          : '—'}
      </td>
      <td className="px-5 py-3.5 text-xs text-n-500">
        {buyer.lead_source ?? '—'}
      </td>
    </motion.tr>
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
