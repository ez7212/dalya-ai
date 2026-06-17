'use client'

import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'
import { GoldButton } from '@/components/ui/GoldButton'

const STEPS = [
  {
    step: '01',
    title: 'Upload Your SPA',
    body: 'Dalya parses every payment milestone, floor plan reference, and handover date automatically.',
  },
  {
    step: '02',
    title: 'Live in 30 Minutes',
    body: 'Your listing goes live on Property Finder, Bayut, and Dalya simultaneously. Non-exclusive and RERA-compliant from day one.',
  },
  {
    step: '03',
    title: 'Every Inquiry Answered',
    body: "Dalya responds to buyer questions 24/7 in English, Arabic, Russian, and Hindi. You are escalated only when an offer arrives above your threshold.",
  },
]

export function SellerValue() {
  return (
    <section id="sell" className="py-24 surface-1">
      <div className="max-w-7xl mx-auto px-6 lg:px-10">

        <motion.div
          className="mb-16"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <SectionEyebrow>For Sellers</SectionEyebrow>
          <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight">
            Upload your SPA. Live on every portal.<br />
          </h2>
        </motion.div>

        {/* Step flow — no cards, divided columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gold/10 mb-14">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.step}
              className="py-8 md:py-0 md:px-10 first:md:pl-0 last:md:pr-0"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <div className="font-mono text-[72px] leading-none font-bold text-gold/10 mb-5 select-none">{step.step}</div>
              <h3 className="font-semibold text-sand text-lg mb-3">{step.title}</h3>
              <p className="text-sm text-n-500 leading-relaxed font-light">{step.body}</p>
            </motion.div>
          ))}
        </div>

        {/* Commission callout strip */}
        <motion.div
          className="flex flex-col md:flex-row items-start md:items-center gap-8 p-8 border border-gold/20 rounded-xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="flex-shrink-0">
            <div className="text-[11px] text-n-500 uppercase tracking-widest mb-1">Seller commission</div>
            <div className="font-mono text-5xl font-bold text-gold leading-none">Custom</div>
          </div>
          <div className="hidden md:block w-px self-stretch bg-gold/15" />
          <p className="text-n-500 text-sm font-light leading-relaxed flex-1 max-w-sm">
            Only paid once your property is sold.
          </p>
          <div className="flex items-center gap-4 flex-shrink-0">
            <GoldButton href="/dashboard/listings/new">Upload Your SPA</GoldButton>
            <span className="text-n-500 text-sm font-light hidden lg:block">Free to list · Non-exclusive</span>
          </div>
        </motion.div>

      </div>
    </section>
  )
}
