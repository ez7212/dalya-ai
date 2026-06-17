'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'
import { useAuth } from '@/components/providers/AuthProvider'
import { apiFetch } from '@/lib/api'
import { formatMoney } from '@/lib/utils'

interface AdminListing {
  id: string
  property_name: string
  unit_number: string
  seller_email: string
  seller_id: string
  asking_price: number
  status: 'active' | 'draft'
  conversations: number
  escalated: number
  last_activity: string | null
}

interface AdminData {
  listings: AdminListing[]
  total_listings: number
  total_sellers: number
  total_conversations: number
  total_escalated: number
}

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth()
  const [data, setData] = useState<AdminData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isAdmin = user?.id === process.env.NEXT_PUBLIC_ADMIN_USER_ID

  useEffect(() => {
    if (authLoading) return

    async function fetchAdmin() {
      try {
        const res = await apiFetch('/api/v1/listings')
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail ?? `Failed to load admin data (${res.status})`)
        }
        const json: AdminData = await res.json()
        setData(json)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Something went wrong')
      } finally {
        setLoading(false)
      }
    }

    fetchAdmin()
  }, [authLoading])

  const listings = data?.listings ?? []

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <SectionEyebrow>Admin Dashboard</SectionEyebrow>
      <h1 className="editorial text-3xl md:text-4xl font-bold text-sand tracking-tight mb-10">
        Platform Overview
      </h1>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard label="Total Listings" value={data?.total_listings ?? 0} />
        <StatCard label="Total Sellers" value={data?.total_sellers ?? 0} />
        <StatCard label="Conversations" value={data?.total_conversations ?? 0} />
        <StatCard label="Escalated" value={data?.total_escalated ?? 0} />
      </div>

      {/* Content */}
      {loading || authLoading ? (
        <div className="text-center py-20">
          <p className="text-n-500 text-sm">Loading admin data...</p>
        </div>
      ) : error ? (
        <div className="text-center py-20">
          <p className="text-red-400 text-sm" role="alert">{error}</p>
        </div>
      ) : listings.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-n-500 text-sm">No listings on the platform yet.</p>
        </div>
      ) : (
        <div className="surface-1 rounded-xl ghost-border shadow-ambient overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="border-b border-gold/10">
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold">Project</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold">Unit</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold">Seller</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold text-right">Asking Price</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold text-center">Status</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold text-right">Convos</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold text-right">Escalated</th>
                  <th className="px-5 py-4 text-[11px] text-gold uppercase tracking-widest font-semibold text-right">Last Activity</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing, i) => (
                  <motion.tr
                    key={listing.id}
                    className="border-b border-gold/5 hover:bg-gold/3 transition-colors"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: i * 0.03 }}
                  >
                    <td className="px-5 py-3.5 text-sm text-sand font-medium">{listing.property_name}</td>
                    <td className="px-5 py-3.5 text-sm text-n-300">{listing.unit_number}</td>
                    <td className="px-5 py-3.5 text-sm text-n-300 max-w-[200px] truncate">{listing.seller_email}</td>
                    <td className="px-5 py-3.5 text-sm font-mono text-gold text-right">
                      AED {formatMoney(listing.asking_price)}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${listing.status === 'active' ? 'bg-sage' : 'bg-n-500'}`} />
                    </td>
                    <td className="px-5 py-3.5 text-sm font-mono text-n-300 text-right">{listing.conversations}</td>
                    <td className="px-5 py-3.5 text-sm font-mono text-right">
                      <span className={listing.escalated > 0 ? 'text-sage-lt' : 'text-n-500'}>
                        {listing.escalated}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-n-500 text-right">
                      {listing.last_activity
                        ? new Date(listing.last_activity).toLocaleDateString()
                        : '--'}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
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
