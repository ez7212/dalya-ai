'use client'

import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'
import { GoldButton } from '@/components/ui/GoldButton'
import { GhostButton } from '@/components/ui/GhostButton'

const SELLER_STEPS = [
  {
    step: '01',
    title: 'Upload your SPA',
    body: 'Send us your SPA (Sale and Purchase Agreement) — one PDF. Dalya parses every payment milestone, floor plan reference, handover date, and NOC threshold automatically. No manual entry, no back-and-forth.',
  },
  {
    step: '02',
    title: 'Live on every portal in 30 minutes',
    body: 'Your verified listing goes live on Property Finder, Bayut, and Dalya simultaneously. Non-exclusive — list with as many brokers as you like. RERA-compliant from day one.',
  },
  {
    step: '03',
    title: 'Dalya answers every inquiry',
    body: "Dalya responds to buyer questions 24/7 in English, Arabic, Russian, and Hindi — payment schedules, payment history, NOC status, handover dates. You are never interrupted by a question your SPA already answers.",
  },
  {
    step: '04',
    title: 'You get the offer, not the noise',
    body: 'Set your floor price and commission terms. Dalya filters everything below the threshold and escalates serious offers with full buyer context.',
  },
]

const BUYER_STEPS = [
  {
    step: '01',
    icon: 'verified',
    title: 'Every listing sourced from the actual SPA',
    body: "No manually entered figures. Every price, payment percentage, and handover date on Dalya is parsed directly from the seller's original Sale and Purchase Agreement and cross-referenced against DLD records.",
  },
  {
    step: '02',
    icon: 'chat_bubble',
    title: 'Ask anything, get answered instantly',
    body: "What's the remaining payment schedule? Is the NOC eligible? What did the developer last update? Ask Dalya on WhatsApp — answered in your language within 60 seconds, any time of day.",
  },
  {
    step: '03',
    icon: 'handshake',
    title: 'Make an offer without pressure',
    body: "Submit your offer directly through Dalya. No agent middlemen, no follow-up calls. Offers above the seller's threshold get an instant response. Offers below are held with the seller's knowledge — no chasing, no silence.",
  },
  {
    step: '04',
    icon: 'savings',
    title: 'See the fee structure before you move',
    body: 'Each brokerage sets its own commission. Dalya keeps the fee visible alongside DLD and other transaction costs so buyers can compare the real outlay.',
  },
]

export function HowItWorks() {
  return (
    <section className="py-28 surface-1 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-10">

        {/* Section header */}
        <motion.div
          className="mb-20 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <SectionEyebrow>How It Works</SectionEyebrow>
          <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight mb-4">
            Built for both sides<br />of the transaction.
          </h2>
          <p className="text-n-500 text-lg font-light leading-relaxed">
            Dalya removes friction for sellers and opacity for buyers. Every feature serves one of those two goals.
          </p>
        </motion.div>

        {/* ── Seller track ── 2×2 accent-left columns */}
        <div className="mb-20">
          <motion.div
            className="flex items-center gap-4 mb-10"
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
          >
            <span className="text-sm font-semibold uppercase tracking-widest text-gold">For Sellers</span>
            <div className="flex-1 h-px bg-gold/10" />
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-16 gap-y-12 mb-10">
            {SELLER_STEPS.map((step, i) => (
              <motion.div
                key={step.step}
                className="border-l-2 border-gold/25 pl-7"
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <div className="font-mono text-xs text-gold/50 uppercase tracking-widest mb-3">{step.step}</div>
                <h3 className="font-semibold text-sand mb-2 leading-snug">{step.title}</h3>
                <p className="text-sm text-n-500 leading-relaxed font-light">{step.body}</p>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="flex items-center gap-4"
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            <GoldButton href="/#sell">List Your Offplan</GoldButton>
            <span className="text-n-500 text-sm font-light">Free to list · Non-exclusive · Brokerage-set commission</span>
          </motion.div>
        </div>

        {/* Divider */}
        <div className="border-t border-gold/10 mb-20" />

        {/* ── Buyer track ── stacked horizontal rows */}
        <div>
          <motion.div
            className="flex items-center gap-4 mb-10"
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
          >
            <span className="text-sm font-semibold uppercase tracking-widest text-sage-lt">For Buyers</span>
            <div className="flex-1 h-px bg-sage/10" />
          </motion.div>

          <div className="space-y-0 mb-10">
            {BUYER_STEPS.map((step, i) => (
              <motion.div
                key={step.step}
                className="flex items-start gap-8 py-7 border-b border-gold/8 last:border-0"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
              >
                <div className="font-mono text-4xl font-bold text-sage/25 w-14 flex-shrink-0 leading-none pt-1 select-none">
                  {step.step}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-sand mb-2 leading-snug">{step.title}</h3>
                  <p className="text-sm text-n-500 leading-relaxed font-light max-w-2xl">{step.body}</p>
                </div>
                <div className="w-9 h-9 rounded-lg bg-sage/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="material-symbols-outlined text-sage-lt" style={{ fontSize: '18px' }}>{step.icon}</span>
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div
            className="flex items-center gap-4"
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            <GhostButton href="/#listings">View Listings</GhostButton>
            <span className="text-n-500 text-sm font-light">Transparent commission · SPA-verified data</span>
          </motion.div>
        </div>

      </div>
    </section>
  )
}
