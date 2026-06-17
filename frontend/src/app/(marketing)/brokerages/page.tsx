import type { Metadata } from 'next'
import Link from 'next/link'
import { SurfaceCard } from '@/components/marketing/Sections'

export const metadata: Metadata = {
  title: 'For Brokerages — Dalya',
  description:
    'Dalya gives Dubai brokerage owners visibility into agent workflow, buyer response speed, listing activity, and serious offer movement, without manual weekly spreadsheets.',
}

const OWNER_METRICS = [
  { label: 'Revenue per agent', kind: 'currency' as const, note: 'tracked against your operating baseline' },
  { label: 'Speed to first useful response', kind: 'duration' as const, note: 'measured per inbound buyer message' },
  { label: 'Offers above threshold', kind: 'count' as const, note: 'broken down by listing and agent' },
  { label: 'Active buyer conversations', kind: 'count' as const, note: 'segmented by listing and seriousness' },
  { label: 'Viewing pipeline', kind: 'count' as const, note: 'scheduled, completed, no-shows, follow-up due' },
  { label: 'Listing acquisition signal', kind: 'currency' as const, note: 'owners worth a tailored outreach this week' },
]

const SILOED = [
  'Listing details and document-backed facts',
  'Buyer identities, contact numbers, and conversation history',
  'Agent-level performance and rep activity',
  'Per-listing offer history and seller communication',
]

const AGGREGATED = [
  'Anonymized buyer language patterns that improve qualification accuracy',
  'Anonymized response-quality signals that improve the working surface',
  'Aggregate operating benchmarks across the design partnership cohort',
]

export default function BrokeragesPage() {
  return (
    <>
      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 pt-20 pb-16 lg:pt-28 lg:pb-24">
          <div className="grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-12 lg:gap-16 items-center">
            <div>
              <div className="t-eyebrow mb-4">For brokerages</div>
              <h1 className="t-display max-w-[640px] mb-5">
                See the work that moves your brokerage.
              </h1>
              <p className="t-large max-w-[620px] mb-7">
                One operating view across listings, buyer conversations, agent follow-up,
                viewings, and offers. The goal is not more software to manage. It is a
                clearer agent day and a cleaner brokerage pipeline.
              </p>
              <div className="flex flex-wrap gap-3 items-center">
                <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
                  Apply for design partnership
                </Link>
                <Link
                  href="/brand-mockups/owner-dashboard.html"
                  target="_blank"
                  rel="noreferrer"
                  className="btn-outline rounded-lg px-5 py-2.5 text-sm"
                >
                  Open the dashboard mockup
                </Link>
              </div>
            </div>

            {/* Floating owner-view cards */}
            <div className="relative h-[480px] hidden lg:block">
              {/* Revenue per agent tile */}
              <FloatingCard top="0px" left="60px" width="320px" rotate="-2deg" z={2}>
                <div className="p-4" style={{ background: 'var(--color-surface-0)' }}>
                  <div className="t-eyebrow mb-1">Revenue / agent · 30d</div>
                  <div
                    className="text-[34px] font-bold tabular-aed leading-none mb-2"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
                  >
                    AED 187k
                  </div>
                  <div className="flex items-center gap-2 text-[11px]">
                    <span
                      className="px-1.5 py-0.5 rounded font-bold tabular-aed"
                      style={{
                        background: 'var(--color-success-100)',
                        color: 'var(--color-success-700)',
                      }}
                    >
                      +12% vs baseline
                    </span>
                    <span style={{ color: 'var(--color-text-3)' }}>
                      across 12 agents
                    </span>
                  </div>
                </div>
              </FloatingCard>

              {/* Offers above threshold list */}
              <FloatingCard top="150px" left="0px" width="360px" rotate="1.5deg" z={3}>
                <div
                  className="px-4 py-2.5 flex items-center gap-2 border-b"
                  style={{
                    background: 'var(--color-surface-1)',
                    borderColor: 'var(--color-border-hairline)',
                  }}
                >
                  <span
                    className="text-[10px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
                    style={{
                      background: 'var(--color-success-100)',
                      color: 'var(--color-success-700)',
                    }}
                  >
                    Live
                  </span>
                  <span
                    className="text-[11px] uppercase tracking-widest font-semibold"
                    style={{ color: 'var(--color-text-3)' }}
                  >
                    Offers above threshold
                  </span>
                </div>
                <div className="p-3 flex flex-col gap-2" style={{ background: 'var(--color-surface-0)' }}>
                  <OfferRow buyer="Sara Mohammed" listing="Palace Villas Ostra" amount="AED 17.0M" />
                  <OfferRow buyer="Yusuf Khalil" listing="Seahaven Tower B" amount="AED 9.4M" />
                  <OfferRow buyer="Anya Volkov" listing="Address Residences" amount="AED 6.1M" />
                </div>
              </FloatingCard>

              {/* Listing activity sparkline */}
              <FloatingCard top="330px" left="120px" width="300px" rotate="-1deg" z={1}>
                <div className="p-4" style={{ background: 'var(--color-surface-0)' }}>
                  <div className="t-eyebrow mb-2">Listing activity · this week</div>
                  <div className="flex items-end gap-1.5 h-12 mb-2">
                    {[14, 22, 18, 31, 27, 38, 33].map((h, i) => (
                      <div
                        key={i}
                        className="flex-1 rounded-t-sm"
                        style={{
                          height: `${(h / 38) * 100}%`,
                          background: i === 6 ? 'var(--color-brand-500)' : 'var(--color-brand-200)',
                        }}
                      />
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-[10px]" style={{ color: 'var(--color-text-3)' }}>
                    <span className="uppercase tracking-widest font-semibold">Mon</span>
                    <span className="uppercase tracking-widest font-semibold">Today</span>
                  </div>
                </div>
              </FloatingCard>
            </div>
          </div>
        </div>
      </section>

      {/* ── FRAME STRIP ───────────────────────────────────── */}
      <div className="border-t border-b" style={{ borderColor: 'var(--color-border-hairline)' }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-14">
          <div className="max-w-[880px]">
            <div className="t-eyebrow mb-2.5">The frame</div>
            <p
              className="text-[22px] sm:text-2xl font-normal leading-snug"
              style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
            >
              You should not have to ask your top agents what is happening in their pipeline.
              The dashboard shows you, in the same shape every Monday, with the same numbers
              your team is acting on.
            </p>
          </div>
        </div>
      </div>

      {/* ── EMBEDDED OWNER MOCKUP ────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
        <div className="t-eyebrow mb-2.5">Owner dashboard</div>
        <h2 className="t-section mb-3 max-w-[760px]">Your operating picture, in one view.</h2>
        <p className="t-large max-w-[680px] mb-10">
          Pipeline quality, response speed, offers above threshold, viewing logistics,
          listing acquisition, and revenue per agent come from the same listing,
          conversation, and offer data your team is already creating.
        </p>

        <div className="max-w-[820px]">
          <SurfaceCard
            eyebrow="For owners · desktop"
            title="The brokerage view."
            desc="Revenue per agent. Offers above threshold. Listings in flight. Buyer engagement velocity. The dashboard makes the operating picture visible without a manual weekly spreadsheet."
            src="/brand-mockups/owner-dashboard.html"
          />
        </div>
      </section>

      {/* ── WHAT YOU MEASURE ─────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
          <div className="t-eyebrow mb-2.5">What you measure</div>
          <h2 className="t-section mb-3 max-w-[760px]">The metrics you check every Monday.</h2>
          <p className="t-large max-w-[680px] mb-10">
            Six numbers, named in language your team already uses. They run off live listing,
            conversation, and offer data. No manual roll-up. No retrofitted CRM hygiene project.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {OWNER_METRICS.map((m, i) => (
              <article
                key={m.label}
                className="rounded-xl p-5 flex flex-col gap-2"
                style={{
                  background: 'var(--color-surface-0)',
                  border: '1px solid var(--color-border-hairline)',
                }}
              >
                <div className="flex items-baseline gap-2">
                  <span
                    className="text-[11px] font-mono"
                    style={{ color: 'var(--color-brand-500)' }}
                  >
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <MetricIcon kind={m.kind} />
                </div>
                <h3
                  className="text-base font-semibold"
                  style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
                >
                  {m.label}
                </h3>
                <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                  {m.note}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── DATA BOUNDARIES ──────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
        <div className="t-eyebrow mb-2.5">Your data, your brokerage</div>
        <h2 className="t-section mb-3 max-w-[760px]">What stays siloed. What gets aggregated.</h2>
        <p className="t-large max-w-[680px] mb-10">
          The platform improves over time by reading anonymized signal across the cohort.
          The specifics that name your business stay inside your account, by contract.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div
            className="rounded-xl p-6"
            style={{
              background: 'var(--color-surface-0)',
              border: '1px solid var(--color-border-hairline)',
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: 'var(--color-success-500)' }}
              />
              <span
                className="text-[11px] uppercase tracking-widest font-bold"
                style={{ color: 'var(--color-text-1)' }}
              >
                Stays siloed in your brokerage
              </span>
            </div>
            <ul className="flex flex-col gap-2.5">
              {SILOED.map((item) => (
                <li
                  key={item}
                  className="flex gap-2 text-[14px] leading-snug"
                  style={{ color: 'var(--color-text-2)' }}
                >
                  <span
                    className="mt-1.5 w-1 h-1 rounded-full shrink-0"
                    style={{ background: 'var(--color-text-3)' }}
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div
            className="rounded-xl p-6"
            style={{
              background: 'var(--color-surface-0)',
              border: '1px solid var(--color-border-hairline)',
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: 'var(--color-brand-500)' }}
              />
              <span
                className="text-[11px] uppercase tracking-widest font-bold"
                style={{ color: 'var(--color-text-1)' }}
              >
                Anonymized signal across the cohort
              </span>
            </div>
            <ul className="flex flex-col gap-2.5">
              {AGGREGATED.map((item) => (
                <li
                  key={item}
                  className="flex gap-2 text-[14px] leading-snug"
                  style={{ color: 'var(--color-text-2)' }}
                >
                  <span
                    className="mt-1.5 w-1 h-1 rounded-full shrink-0"
                    style={{ background: 'var(--color-text-3)' }}
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ── CLOSING CTA ──────────────────────────────────── */}
      <section className="text-center max-w-[720px] mx-auto px-6 py-24">
        <div className="t-eyebrow mb-4">Currently in design partnership</div>
        <h2 className="t-section mb-4">Run a 60-day pilot with us.</h2>
        <p className="t-large mb-6 max-w-[540px] mx-auto">
          You give us active listings, agent feedback, and the operating baseline. We give your
          team the platform and measure whether the day gets sharper.
        </p>
        <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
          Apply for design partnership
        </Link>
      </section>
    </>
  )
}

/* ─────── Internal subcomponents ─────── */

function FloatingCard({
  children,
  top,
  left,
  width,
  rotate,
  z,
}: {
  children: React.ReactNode
  top: string
  left: string
  width: string
  rotate: string
  z: number
}) {
  return (
    <div
      className="absolute rounded-xl overflow-hidden shadow-card-lg"
      style={{
        top,
        left,
        width,
        transform: `rotate(${rotate})`,
        zIndex: z,
        background: 'var(--color-surface-0)',
        border: '1px solid var(--color-border-hairline)',
      }}
    >
      {children}
    </div>
  )
}

function OfferRow({
  buyer,
  listing,
  amount,
}: {
  buyer: string
  listing: string
  amount: string
}) {
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="font-semibold flex-1 leading-tight" style={{ color: 'var(--color-text-1)' }}>
        {buyer}
        <br />
        <span className="font-normal text-[10px]" style={{ color: 'var(--color-text-3)' }}>
          {listing}
        </span>
      </span>
      <span className="tabular-aed font-bold" style={{ color: 'var(--color-text-1)' }}>
        {amount}
      </span>
    </div>
  )
}

function MetricIcon({ kind }: { kind: 'currency' | 'duration' | 'count' }) {
  const symbol = kind === 'currency' ? 'د.إ' : kind === 'duration' ? 't' : '#'
  return (
    <span
      className="text-[10px] tabular-aed font-bold px-1.5 py-0.5 rounded"
      style={{
        background: 'var(--color-brand-50)',
        color: 'var(--color-brand-700)',
      }}
    >
      {symbol}
    </span>
  )
}
