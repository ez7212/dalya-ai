'use client'

import Image from 'next/image'
import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'

export function MarketIntelligence() {
  return (
    <section id="insights" className="py-20 bg-deep">
      <div className="max-w-7xl mx-auto px-6 lg:px-10">

        <motion.div
          className="mb-14"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <SectionEyebrow>Market Intelligence</SectionEyebrow>
          <h2 className="editorial text-4xl font-bold text-sand tracking-tight">UAE Off-Plan Resale.<br />Live data.</h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 md:h-[560px]">

          {/* Featured insight — tall left */}
          <motion.div
            className="md:col-span-2 md:row-span-2 surface-1 rounded-xl p-8 flex flex-col justify-end relative overflow-hidden group ghost-border"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <div className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-transparent z-10 pointer-events-none" />
            <motion.div
              className="absolute inset-0"
              whileHover={{ scale: 1.05 }}
              transition={{ duration: 0.7 }}
            >
              <Image
                src="https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800&q=70"
                alt="Dubai real estate architecture"
                fill
                className="object-cover opacity-25"
                sizes="(max-width: 768px) 100vw, 50vw"
              />
            </motion.div>
            <div className="relative z-20">
              <span className="bg-gold text-ink px-2.5 py-1 text-[10px] font-bold tracking-widest uppercase rounded mb-4 inline-block">
                Featured Analysis
              </span>
              <h4 className="text-2xl font-bold text-sand mb-3 editorial">
                Off-Plan Resale Volume Up 34% in Q1 2026
              </h4>
              <p className="text-n-500 text-sm leading-relaxed mb-5 font-light">
                SPA-sourced data reveals accelerating secondary market activity across Dubai South and MBR City as investor confidence strengthens.
              </p>
              <button className="text-gold font-semibold text-xs tracking-widest uppercase flex items-center gap-2 group/btn">
                Read Analysis
                <span className="material-symbols-outlined group-hover/btn:translate-x-1 transition-transform" style={{ fontSize: '16px' }}>
                  arrow_forward
                </span>
              </button>
            </div>
          </motion.div>

          {/* Stat: Marina growth */}
          <motion.div
            className="md:col-span-2 surface-1 rounded-xl p-6 ghost-border flex items-center justify-between"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div>
              <h4 className="font-semibold text-sand text-base mb-1">Dubai Marina Resale</h4>
              <p className="text-n-500 text-[11px] uppercase tracking-widest font-semibold">Avg. Days on Market</p>
            </div>
            <div className="text-right">
              <div className="font-mono text-3xl font-bold text-gold">14</div>
              <div className="text-[10px] text-n-500 uppercase tracking-widest">Days</div>
            </div>
          </motion.div>

          {/* Stat: Foreign investment */}
          <motion.div
            className="surface-2 rounded-xl p-6 ghost-border flex flex-col justify-between"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <span className="material-symbols-outlined text-sage">public</span>
            <div>
              <div className="font-mono text-2xl font-bold text-sand">42%</div>
              <div className="text-[10px] text-n-500 uppercase tracking-widest font-semibold mt-1">Foreign Buyer Share</div>
            </div>
          </motion.div>

          {/* Stat: NOC threshold */}
          <motion.div
            className="surface-2 rounded-xl p-6 ghost-border flex flex-col justify-between"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <span className="material-symbols-outlined text-gold">gavel</span>
            <div>
              <div className="font-mono text-2xl font-bold text-sand">40%</div>
              <div className="text-[10px] text-n-500 uppercase tracking-widest font-semibold mt-1">Avg. NOC Threshold</div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  )
}
