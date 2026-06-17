'use client'

import { motion } from 'framer-motion'
import Image from 'next/image'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'

const COMPLIANCE_ITEMS = [
  {
    label: 'RERA Licensed',
    icon: 'gavel',
    detail: 'Mahoroba Realty holds a valid Real Estate Regulatory Agency licence issued by the Dubai Land Department. All Dalya listings and transactions operate under this licence.',
  },
  {
    label: 'Trakheesi Partner',
    icon: 'fact_check',
    detail: 'Every listing on Dalya carries a Trakheesi permit number issued by DLD. No listing goes live without a valid permit — this is verified automatically at upload.',
  },
  {
    label: 'DLD Registered',
    icon: 'account_balance',
    detail: 'All completed transactions are recorded with the Dubai Land Department. Buyers and sellers receive full documentation trail at every stage.',
  },
  {
    label: 'SPA-Sourced Data',
    icon: 'description',
    detail: 'Property data is parsed from original Sale and Purchase Agreements, not manually entered. Every figure on the platform is legally traceable to a signed document.',
  },
]

export function About() {
  return (
    <section className="py-28 bg-deep relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-10">
        <div className="grid grid-cols-12 gap-12 lg:gap-20 items-start">

          {/* Left: narrative */}
          <motion.div
            className="col-span-12 lg:col-span-5"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <SectionEyebrow>About Dalya</SectionEyebrow>
            <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight mb-6">
              Built on a real<br />RERA licence.
            </h2>
            <div className="space-y-5 text-n-500 font-light leading-relaxed">
              <p>
                Dalya is the intelligence layer built on top of{' '}
                <span className="text-sand font-medium">Mahoroba Realty</span>, a fully licensed UAE real estate brokerage. Every listing, transaction, and advisory interaction operates under Mahoroba&apos;s RERA registration — not a grey-area technology exemption.
              </p>
              <p>
                The UAE&apos;s off-plan resale market is the fastest-growing segment of Dubai property — and the least served. Sellers with valid SPAs have no efficient way to reach buyers. Buyers have no reliable way to verify what they&apos;re actually purchasing. Dalya was built to close both gaps.
              </p>
              <p>
                Dalya is the interface, not the authority. When a deal requires human judgment, a qualified broker is escalated — not an automated bot.
              </p>
            </div>

            <motion.div
              className="mt-10 flex flex-wrap gap-3"
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              {['RERA Licensed', 'Trakheesi Partner', 'DLD Registered'].map(tag => (
                <span
                  key={tag}
                  className="badge-verified text-[11px] font-semibold uppercase tracking-widest px-3 py-1.5 rounded-full"
                >
                  {tag}
                </span>
              ))}
            </motion.div>

            <motion.div
              className="mt-10 pt-8 border-t border-gold/8 flex items-center gap-3"
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: 0.3 }}
            >
              <span className="text-[11px] text-n-500 uppercase tracking-widest font-medium">Licensed under</span>
              <Image src="/logo-mahoroba.png" alt="Mahoroba Realty" height={28} width={941} style={{ width: 'auto', maxHeight: '42px' }} className="object-contain opacity-70" />
            </motion.div>
          </motion.div>

          {/* Right: compliance list — label + detail rows, no cards */}
          <div className="col-span-12 lg:col-span-7">
            <div className="divide-y divide-gold/8">
              {COMPLIANCE_ITEMS.map((item, i) => (
                <motion.div
                  key={item.label}
                  className="py-7 flex gap-8 items-start first:pt-0"
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.07 }}
                >
                  <div className="w-8 h-8 rounded-md bg-sage/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="material-symbols-outlined text-sage-lt" style={{ fontSize: '16px' }}>{item.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sand text-sm mb-1.5">{item.label}</div>
                    <p className="text-sm text-n-500 leading-relaxed font-light">{item.detail}</p>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Legal note */}
            <motion.div
              className="mt-8 pt-8 border-t border-gold/8"
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: 0.3 }}
            >
              <p className="text-n-500 text-xs font-light leading-relaxed">
                Mahoroba Realty is registered with the Real Estate Regulatory Agency (RERA) under the Dubai Land Department. All brokerage activities are conducted in compliance with UAE Federal Law No. 26 of 2007 and its amendments. Commission rates are disclosed in full before any transaction proceeds.
              </p>
            </motion.div>
          </div>

        </div>
      </div>
    </section>
  )
}
