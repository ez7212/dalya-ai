'use client'

import { use } from 'react'
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/Badge'
import { useAuth } from '@/components/providers/AuthProvider'
import { formatMoney } from '@/lib/utils'
import { useListingDetail } from '@/lib/queries'

export default function ListingSpaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { loading: authLoading } = useAuth()
  const { data, isLoading, error } = useListingDetail(id, !authLoading)

  if (isLoading || authLoading) {
    return <p className="text-n-500 text-sm py-10 text-center">Loading SPA data...</p>
  }
  if (error) {
    return <p className="text-red-400 text-sm py-10 text-center" role="alert">{error.message}</p>
  }
  if (!data) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="surface-1 rounded-xl ghost-border p-6 sm:p-7"
    >
      {data.noc_eligible != null && (
        <div className="flex items-center justify-between mb-5 pb-5 border-b border-gold/8">
          <div className="flex items-center gap-3">
            <Badge variant={data.noc_eligible ? 'sage' : 'copper'}>
              {data.noc_eligible ? 'NOC Eligible' : 'NOC Pending'}
            </Badge>
            {data.total_paid_percent != null && (
              <span className="text-xs text-n-500 font-mono">
                {data.total_paid_percent}% paid
              </span>
            )}
          </div>
          {data.property_status && (
            <span className="text-[11px] text-n-500 uppercase tracking-widest">
              {data.property_status}
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-6 gap-x-8">
        <DetailCell label="Project" value={data.property_name} />
        {data.sub_community && <DetailCell label="Sub-community" value={data.sub_community} />}
        <DetailCell label="Developer" value={data.developer} />
        <DetailCell label="Unit" value={data.unit_number} />
        {data.property_type && <DetailCell label="Type" value={data.property_type} />}
        {(data.bedrooms != null || data.bathrooms != null) && (
          <DetailCell label="Bedrooms" value={`${data.bedrooms ?? '—'} BD / ${data.bathrooms ?? '—'} BA`} />
        )}
        {data.bua_sqft != null && (
          <DetailCell label="BUA" value={`${data.bua_sqft.toLocaleString()} sqft`} mono />
        )}
        {data.plot_sqft != null && (
          <DetailCell label="Plot" value={`${data.plot_sqft.toLocaleString()} sqft`} mono />
        )}
        {data.total_price != null && (
          <DetailCell
            label="Purchase Price"
            value={`AED ${formatMoney(data.total_price)}`}
            mono
            gold
          />
        )}
        {data.handover_date && (
          <DetailCell
            label="Handover"
            value={data.handover_date}
            mono={/^\d{4}-\d{2}-\d{2}$/.test(data.handover_date)}
          />
        )}
      </div>

      <p className="text-n-500 text-xs mt-7 pt-5 border-t border-gold/8 leading-relaxed">
        This is the data Dalya extracted from your Sale &amp; Purchase Agreement.
        Contact support if any field looks incorrect.
      </p>
    </motion.div>
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
