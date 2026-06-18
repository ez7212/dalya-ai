import type { Metadata } from 'next'
import Link from 'next/link'
import { SurfaceCard } from '@/components/marketing/Sections'

export const metadata: Metadata = {
  title: 'For Brokerages — Dalya',
  description:
    'Dalya gives every agent in your Dubai brokerage the same operating layer: a 24/7 buyer concierge, smart escalation of serious offers, a ranked morning hot list, and viewing logistics — a faster team without adding headcount.',
}

const WORKFLOWS = [
  { label: '24/7 inquiry concierge', note: 'Every buyer message answered, qualified, and logged in EN · AR · RU · HI — day or night, grounded in the listing documents.' },
  { label: 'Smart escalation', note: 'Serious questions and above-threshold offers reach the right agent on WhatsApp or the dashboard. The reply relays straight back to the buyer.' },
  { label: 'Morning hot list & follow-ups', note: 'Each agent opens to a ranked queue and review-only follow-up drafts. Nothing sends without the agent.' },
  { label: 'Viewing logistics', note: 'Slot proposals, tenant and buyer confirmation, calendar invites, pre-viewing briefs, and post-viewing capture — handled before the viewing.' },
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
                The sharpest version of every agent you have.
              </h1>
              <p className="t-large max-w-[620px] mb-7">
                Dalya gives every agent on your team the same operating layer — a 24/7 buyer
                concierge, serious offers escalated to the right person, a ranked morning hot
                list, and viewings that organise themselves. A faster team, without adding
                headcount.
              </p>
              <div className="flex flex-wrap gap-3 items-center">
                <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
                  Apply for design partnership
                </Link>
                <Link href="/agents" className="btn-outline rounded-lg px-5 py-2.5 text-sm">
                  See the agent workflow
                </Link>
              </div>
            </div>

            {/* Floating agent-workflow cards */}
            <div className="relative h-[480px] hidden lg:block">
              {/* First response */}
              <FloatingCard top="0px" left="60px" width="300px" rotate="-2deg" z={2}>
                <div className="p-4" style={{ background: 'var(--color-surface-0)' }}>
                  <div className="t-eyebrow mb-1">First response</div>
                  <div
                    className="text-[34px] font-bold tabular-aed leading-none mb-2"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
                  >
                    Under 60s
                  </div>
                  <div className="text-[11px]" style={{ color: 'var(--color-text-3)' }}>
                    every buyer message · EN · AR · RU · HI
                  </div>
                </div>
              </FloatingCard>

              {/* Escalation envelope */}
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
                    Escalated
                  </span>
                  <span
                    className="text-[11px] uppercase tracking-widest font-semibold"
                    style={{ color: 'var(--color-text-3)' }}
                  >
                    Offer above threshold
                  </span>
                </div>
                <div className="p-3.5" style={{ background: 'var(--color-surface-0)' }}>
                  <div
                    className="text-2xl font-bold tabular-aed mb-1"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
                  >
                    AED 17,000,000
                  </div>
                  <div className="text-[11px]" style={{ color: 'var(--color-text-2)' }}>
                    Sara Mohammed · Palace Villas Ostra · routed to Eric
                  </div>
                </div>
              </FloatingCard>

              {/* Morning hot list */}
              <FloatingCard top="330px" left="120px" width="300px" rotate="-1deg" z={1}>
                <div className="p-4" style={{ background: 'var(--color-surface-0)' }}>
                  <div className="t-eyebrow mb-1">Morning hot list</div>
                  <div
                    className="text-[34px] font-bold tabular-aed leading-none mb-2"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
                  >
                    6 to call
                  </div>
                  <div className="text-[11px]" style={{ color: 'var(--color-text-3)' }}>
                    ranked, with buyer context attached
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
              Your best agents shouldn&apos;t be your bottleneck. Dalya does the repetitive work
              around every deal — the midnight replies, the qualification, the follow-up
              chasing — so the people you hired to close can spend their time closing.
            </p>
          </div>
        </div>
      </div>

      {/* ── EMBEDDED AGENT SURFACE ───────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
        <div className="t-eyebrow mb-2.5">What your team uses</div>
        <h2 className="t-section mb-3 max-w-[760px]">One working surface for every agent.</h2>
        <p className="t-large max-w-[680px] mb-10">
          Every agent opens to the same place: who to call this morning, the briefing for
          each buyer, the live conversation, and the reply ready to review and send. Built
          for hours of daily use, mobile and desktop.
        </p>

        <div className="max-w-[820px]">
          <SurfaceCard
            eyebrow="For agents · mobile + desktop"
            title="The agent day."
            desc="Hot list of who to call this morning. Pre-call buyer briefing one tap away. Conversation history and suggested reply ready before the agent follows up."
            img="/brand-mockups/agent-desktop.png"
            src="/brand-mockups/agent-desktop.html"
          />
        </div>
      </section>

      {/* ── WHAT YOU MEASURE ─────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
          <div className="t-eyebrow mb-2.5">What changes for your team</div>
          <h2 className="t-section mb-3 max-w-[760px]">Four workflows, every agent.</h2>
          <p className="t-large max-w-[680px] mb-10">
            The repetitive work around every deal, handled the same way for everyone on the
            team. No manual roll-up. No retrofitted CRM hygiene project.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {WORKFLOWS.map((m, i) => (
              <article
                key={m.label}
                className="rounded-xl p-5 flex flex-col gap-2"
                style={{
                  background: 'var(--color-surface-0)',
                  border: '1px solid var(--color-border-hairline)',
                }}
              >
                <span
                  className="text-[11px] font-mono"
                  style={{ color: 'var(--color-brand-500)' }}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
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

