'use client'

import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'
import { ListingCard } from '@/components/cards/ListingCard'
import { LISTINGS } from '@/lib/constants'

export function ListingGallery() {
  const handleAskDalya = (_id: string) => {
    // TODO: open WhatsApp deep link for this listing
  }

  return (
    <section id="listings" className="py-28 bg-deep">
      <div className="max-w-7xl mx-auto px-6 lg:px-10">

        <div className="flex items-end justify-between mb-14">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>Verified Listings</SectionEyebrow>
            <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight">
              Off-Plan Resale.<br />Every SPA verified.
            </h2>
          </motion.div>
          <motion.a
            href="#"
            className="hidden md:flex items-center gap-2 text-gold text-sm font-medium hover:gap-3 transition-all"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            View all listings
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>arrow_forward</span>
          </motion.a>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {LISTINGS.map((listing, i) => (
            <motion.div
              key={listing.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <ListingCard listing={listing} onAskDalya={handleAskDalya} />
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  )
}
