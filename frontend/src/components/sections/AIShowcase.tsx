'use client'

import { motion } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'

export function AIShowcase() {
  return (
    <section className="py-20 bg-deep relative overflow-hidden">

      <div className="max-w-7xl mx-auto px-6 lg:px-10">

        {/* Section header */}
        <motion.div
          className="mb-16 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <SectionEyebrow>In Practice</SectionEyebrow>
          <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight mb-4">
            Your SPA does the work.<br />You stay in control.
          </h2>
          <p className="text-n-500 text-lg font-light leading-relaxed">
            Upload once. Dalya&apos;s property advisor answers every buyer question in English, Arabic, Russian, or Hindi — while you watch from your dashboard.
          </p>
        </motion.div>

        <div className="grid grid-cols-12 gap-8 items-center">

          {/* Seller Dashboard Mockup */}
          <motion.div
            className="col-span-12 lg:col-span-7 relative z-10"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <div className="surface-1 rounded-xl ghost-border shadow-ambient overflow-hidden">

              {/* Dashboard topbar */}
              <div className="px-6 py-4 border-b border-gold/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-md bg-gold/15 flex items-center justify-center">
                    <span className="material-symbols-outlined text-gold" style={{ fontSize: '18px' }}>monitoring</span>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-sand">Seller Dashboard</div>
                    <div className="text-[10px] text-n-500 uppercase tracking-widest">Active session — Rania Al-Mazrouei</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <span className="badge-sage text-[10px] font-semibold uppercase tracking-widest px-2.5 py-1 rounded-full">Live</span>
                  <span className="badge-verified text-[10px] font-semibold uppercase tracking-widest px-2.5 py-1 rounded-full">Verified SPA</span>
                </div>
              </div>

              {/* Metrics row */}
              <div className="p-6 grid grid-cols-3 gap-4">
                <div className="surface-2 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="material-symbols-outlined text-gold" style={{ fontSize: '20px' }}>home_work</span>
                    <span className="text-[10px] text-sage-lt font-semibold uppercase">Active</span>
                  </div>
                  <div className="text-[11px] text-n-300 mb-1">Your Listings</div>
                  <div className="font-mono text-2xl font-bold text-sand">3</div>
                  <div className="text-[10px] text-gold mt-1">+1 this week</div>
                </div>
                <div className="surface-2 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="material-symbols-outlined text-sage" style={{ fontSize: '20px' }}>mark_chat_read</span>
                    <div className="w-2 h-2 rounded-full bg-sage" />
                  </div>
                  <div className="text-[11px] text-n-300 mb-1">Inquiries (7d)</div>
                  <div className="font-mono text-2xl font-bold text-sand">24</div>
                  <div className="text-[10px] text-sage mt-1 font-mono">100% answered</div>
                </div>
                <div className="rounded-xl p-5 bg-gold/10 border border-gold/20">
                  <div className="flex items-center justify-between mb-3">
                    <span className="material-symbols-outlined text-gold" style={{ fontSize: '20px' }}>savings</span>
                  </div>
                  <div className="text-[11px] text-n-300 mb-1">Buyer Saves</div>
                  <div className="font-mono text-xl font-bold text-gold">AED 17k</div>
                  <div className="text-[10px] text-n-300 mt-1">vs. standard 2%</div>
                </div>
              </div>

              {/* Live activity */}
              <div className="px-6 pb-6 space-y-3">
                <div className="text-[10px] text-n-500 uppercase tracking-widest font-semibold mb-3">Recent Activity</div>

                <div className="surface-2 rounded-xl p-4 flex items-start gap-4">
                  <div className="w-8 h-8 rounded-md bg-sage/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="material-symbols-outlined text-sage" style={{ fontSize: '16px' }}>chat_bubble</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-sand">Buyer inquiry answered</div>
                    <div className="text-[11px] text-n-300 mt-0.5 truncate">
                      &ldquo;What&apos;s the remaining payment schedule?&rdquo; — DAMAC Hills 2, Unit 4B
                    </div>
                    <div className="text-[10px] text-sage mt-1">Answered in 4 seconds · Arabic</div>
                  </div>
                  <span className="text-[10px] text-n-500 flex-shrink-0">3m ago</span>
                </div>

                <div className="surface-2 rounded-xl p-4 flex items-start gap-4">
                  <div className="w-8 h-8 rounded-md bg-gold/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="material-symbols-outlined text-gold" style={{ fontSize: '16px' }}>person_raised_hand</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-sand">Offer received — action needed</div>
                    <div className="text-[11px] text-n-300 mt-0.5 truncate">
                      AED 1,870,000 on Emaar Beachfront Unit 12C · Above threshold
                    </div>
                    <div className="text-[10px] text-gold mt-1">Escalated to you · Awaiting response</div>
                  </div>
                  <span className="text-[10px] text-n-500 flex-shrink-0">18m ago</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* WhatsApp phone mockup */}
          <motion.div
            className="col-span-12 lg:col-span-5 flex justify-center lg:justify-end"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="relative">
              {/* Phone shell */}
              <div
                className="w-[280px] h-[600px] rounded-[3rem] p-2.5 shadow-ambient relative"
                style={{
                  background: '#111',
                  border: '6px solid #1a1a1a',
                }}
              >
                <div className="w-full h-full bg-white rounded-[2.5rem] overflow-hidden flex flex-col">

                  {/* WA Header */}
                  <div className="px-4 pt-10 pb-3 flex items-center gap-3" style={{ background: '#075E54' }}>
                    <div className="w-9 h-9 rounded-full bg-gold/20 border border-gold/30 flex items-center justify-center flex-shrink-0">
                      <span className="text-gold text-xs font-bold">D</span>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-white">Dalya</div>
                      <div className="text-[10px] text-white/75">online</div>
                    </div>
                  </div>

                  {/* WA Chat */}
                  <div className="flex-1 whatsapp-bg p-3 pb-4 space-y-3 overflow-y-auto">

                    {/* Buyer message — right, green (sender) */}
                    <div
                      className="max-w-[85%] rounded-lg rounded-tr-none p-2.5 shadow-sm ml-auto flex flex-col"
                      style={{ background: '#DCF8C6' }}
                    >
                      <p className="text-[11px] text-gray-800">How much is left to pay on unit 12C?</p>
                      <div className="flex items-center justify-end gap-1 mt-1">
                        <span className="text-[9px] text-gray-400">9:14 AM</span>
                        <span className="material-symbols-outlined text-sky-500" style={{ fontSize: '10px' }}>done_all</span>
                      </div>
                    </div>

                    {/* Dalya response — left, white (recipient) */}
                    <div className="max-w-[90%] bg-white rounded-lg rounded-tl-none p-2.5 shadow-sm flex flex-col">
                      <p className="text-[11px] text-gray-800">
                        Unit 12C — Emaar Beachfront.<br />
                        <strong>63% paid</strong> (AED 1,181,000).<br />
                        Remaining: <strong>AED 693,000</strong> — due at 70% and handover.<br />
                        NOC eligible at 40% ✓
                      </p>
                      <span className="text-[9px] text-gray-400 self-end mt-1">9:14 AM</span>
                    </div>

                    {/* Buyer follow-up — right, green (sender) */}
                    <div
                      className="max-w-[85%] rounded-lg rounded-tr-none p-2.5 shadow-sm ml-auto flex flex-col"
                      style={{ background: '#DCF8C6' }}
                    >
                      <p className="text-[11px] text-gray-800">I&apos;d like to submit an offer of 1.8M AED.</p>
                      <div className="flex items-center justify-end gap-1 mt-1">
                        <span className="text-[9px] text-gray-400">9:15 AM</span>
                        <span className="material-symbols-outlined text-sky-500" style={{ fontSize: '10px' }}>done_all</span>
                      </div>
                    </div>

                    {/* Dalya — left, white (recipient) */}
                    <div className="max-w-[90%] bg-white rounded-lg rounded-tl-none p-2.5 shadow-sm flex flex-col">
                      <p className="text-[11px] text-gray-800">
                        Received! Passing along to the seller. I&apos;ll let you know about the next steps once I hear back.
                      </p>
                      <span className="text-[9px] text-gray-400 self-end mt-1">9:15 AM</span>
                    </div>
                  </div>

                  {/* WA input */}
                  <div className="p-2 flex items-center gap-2" style={{ background: '#F0F0F0' }}>
                    <div className="flex-1 bg-white rounded-full px-3 py-1.5 text-[10px] text-gray-400">Type a message</div>
                    <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: '#075E54' }}>
                      <span className="material-symbols-outlined text-white" style={{ fontSize: '16px' }}>mic</span>
                    </div>
                  </div>
                </div>
                {/* Notch */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-5 rounded-b-2xl z-10" style={{ background: '#111' }} />
              </div>

              {/* Legend */}
              <div className="mt-5 flex items-center justify-center gap-5">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#DCF8C6' }} />
                  <span className="text-[10px] text-n-500">Buyer</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm bg-white/80 flex-shrink-0" />
                  <span className="text-[10px] text-n-500">Dalya</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
