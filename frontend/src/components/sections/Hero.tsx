'use client'

import Image from 'next/image'
import { motion } from 'framer-motion'
import { GoldButton } from '@/components/ui/GoldButton'
import { GhostButton } from '@/components/ui/GhostButton'

export function Hero() {
  return (
    <section className="relative h-screen min-h-[700px] flex items-center pt-24">
      {/* Background image */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <Image
          src="https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1800&q=80"
          alt="UAE architecture — modern Dubai tower at dusk"
          fill
          className="object-cover object-center"
          priority
          sizes="100vw"
        />
        <div className="hero-overlay absolute inset-0" />
        <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-deep to-transparent" />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-10 w-full">
        <div className="max-w-3xl">

          {/* Eyebrow badge */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="badge-verified inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-8 text-[11px] font-semibold tracking-widest uppercase">
              <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>verified</span>
              UAE Off-Plan Resale Marketplace
            </div>
          </motion.div>

          {/* Headline */}
          <motion.h1
            className="editorial text-5xl md:text-7xl font-extrabold leading-[0.95] text-sand mb-6"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            The most intelligent<br />
            <span className="text-gold font-medium italic">offplan resale experience.</span>
          </motion.h1>

          {/* Sub-copy */}
          <motion.p
            className="text-n-300 text-lg md:text-xl font-light leading-relaxed max-w-xl mb-10"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            Verified off-plan resale listings. Ask anything, in any language — answered instantly.
          </motion.p>

          {/* CTAs */}
          <motion.div
            className="flex flex-wrap gap-4 mb-16"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <GoldButton href="#sell">List Your Offplan</GoldButton>
            <GhostButton href="#listings">View Listings</GhostButton>
          </motion.div>

          {/* Stats row */}
          <motion.div
            className="flex flex-wrap gap-10"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div>
              <div className="font-mono text-2xl font-bold text-gold">Custom</div>
              <div className="text-[11px] text-n-500 uppercase tracking-widest mt-1">Commission</div>
            </div>
            <div className="w-px bg-gold/15 self-stretch" />
            <div>
              <div className="font-mono text-2xl font-bold text-sand">30 min</div>
              <div className="text-[11px] text-n-500 uppercase tracking-widest mt-1">Listing on All Platforms</div>
            </div>
            <div className="w-px bg-gold/15 self-stretch" />
            <div>
              <div className="font-mono text-2xl font-bold text-sand">24 / 7</div>
              <div className="text-[11px] text-n-500 uppercase tracking-widest mt-1">Buyer Inquiries Answered</div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  )
}
