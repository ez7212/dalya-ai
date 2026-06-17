'use client'

import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'
import { GoldButton } from '@/components/ui/GoldButton'
import { SAVINGS_TABLE } from '@/lib/constants'

export function BuyerSavings() {
  return (
    <section className="py-24 surface-1 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

          {/* Left: copy */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>For Buyers</SectionEyebrow>
            <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight mb-6">
              Clear brokerage fees.<br />No hidden layers.
            </h2>
            <p className="text-n-500 text-lg font-light leading-relaxed mb-8">
              Each brokerage sets its own commission. Dalya keeps the fee structure visible
              so buyers understand the full transaction cost before they move.
            </p>
            <GoldButton href="#listings">Browse Listings</GoldButton>
          </motion.div>

          {/* Right: savings table */}
          <motion.div
            className="surface-2 rounded-xl p-5 md:p-8 ghost-border shadow-ambient"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
            <div className="text-[11px] text-n-500 uppercase tracking-widest font-semibold mb-6">Commission Context</div>

            {/* ── Desktop: 4-column grid (md+) ── */}
            <div className="hidden md:block">
              <div className="grid grid-cols-4 gap-4 pb-3 border-b border-gold/10 text-[10px] text-n-500 uppercase tracking-widest">
                <div>Property Value</div>
                <div className="text-right">Standard 2%</div>
                <div className="text-right text-gold">Brokerage Fee</div>
                <div className="text-right text-sage-lt">Difference</div>
              </div>
              {SAVINGS_TABLE.map((row, i) => (
                <div
                  key={row.value}
                  className={`grid grid-cols-4 gap-4 py-4 ${i < SAVINGS_TABLE.length - 1 ? 'border-b border-gold/8' : ''} ${i === 1 ? 'bg-gold/5 -mx-8 px-8' : ''}`}
                >
                  <div className="font-mono text-sm font-medium text-n-300">{row.value}</div>
                  <div className="text-right font-mono text-sm text-n-500">{row.standard}</div>
                  <div className="text-right font-mono text-sm font-semibold text-gold">{row.withDalya}</div>
                  <div className="text-right font-mono text-sm font-bold text-sage-lt">{row.saves}</div>
                </div>
              ))}
            </div>

            {/* ── Mobile: stacked comparison blocks (< md) ── */}
            <div className="space-y-3 md:hidden">
              {SAVINGS_TABLE.map((row, i) => (
                <div
                  key={row.value}
                  className={`rounded-lg p-4 ${i === 1 ? 'border border-gold/25 bg-gold/5' : 'border border-gold/10'}`}
                >
                  <div className="font-mono text-base font-bold text-sand mb-3">{row.value}</div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-n-500 uppercase tracking-widest">Standard 2%</span>
                      <span className="font-mono text-sm text-n-500">{row.standard}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-gold/60 uppercase tracking-widest">Brokerage fee</span>
                      <span className="font-mono text-sm font-semibold text-gold">{row.withDalya}</span>
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-gold/10">
                      <span className="text-[11px] text-sage-lt/70 uppercase tracking-widest">You Save</span>
                      <span className="font-mono text-sm font-bold text-sage-lt">{row.saves}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 pt-4 border-t border-gold/10 text-[10px] text-n-500 leading-relaxed">
              Commission is set per brokerage/listing and should be confirmed before publishing.
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  )
}
