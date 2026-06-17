'use client'

import { use } from 'react'
import { motion } from 'framer-motion'
import { ListingLogisticsForm } from '@/components/viewings/ListingLogisticsForm'

export default function ListingLogisticsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <section>
        <h2 className="text-[11px] font-medium uppercase tracking-widest text-n-500">Viewing logistics</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-n-500">
          Configure access, keys, tenant coordination, and owner restrictions once. New listings in the same building can reuse confirmed building defaults.
        </p>
      </section>
      <ListingLogisticsForm listingId={id} />
    </motion.div>
  )
}
