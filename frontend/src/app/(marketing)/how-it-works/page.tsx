import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Workflow — Dalya',
  description:
    'How Dalya fits into a Dubai brokerage: connect listings and WhatsApp, qualify buyers, brief agents, escalate serious offers, coordinate viewings, and report what changed.',
}

const STEPS: Array<{
  label: string
  title: string
  body: string
  snippet: React.ReactNode
}> = [
  {
    label: '01 · Connect',
    title: 'Connect active listings',
    body: 'We ingest listing details, document-backed facts, asking price, offer threshold, viewing constraints, and the agent responsible for each unit. The platform reads what your brokerage already has: SPA, title deed, Ejari, NOC, service charge.',
    snippet: <SnippetListing />,
  },
  {
    label: '02 · Route',
    title: 'Route WhatsApp inquiries',
    body: 'Buyer messages are answered in the brokerage context, logged against the listing, and classified by intent, urgency, language, and seriousness. EN, AR, RU, HI out of the box. Three-message engagement gate to suppress spam-probe escalations.',
    snippet: <SnippetChat />,
  },
  {
    label: '03 · Brief',
    title: 'Brief the agent',
    body: 'The agent gets buyer context, conversation summary, relevant listing facts, and suggested next action before they follow up. The brief reads in twenty seconds. The call starts already informed.',
    snippet: <SnippetBrief />,
  },
  {
    label: '04 · Escalate',
    title: 'Escalate serious offers',
    body: 'Above-threshold offers and high-intent buyer signals move immediately to the agent and owner view with terms, buyer, and history attached. The escalation is deterministic. The bot promise matches the system action.',
    snippet: <SnippetAlert />,
  },
  {
    label: '05 · Coordinate',
    title: 'Coordinate the operational work',
    body: 'Viewing windows, building access, Ejari notice for tenanted units, post-viewing follow-up, and seller updates stay in the same workflow instead of scattering across WhatsApp threads and notebooks.',
    snippet: <SnippetCalendar />,
  },
  {
    label: '06 · Report',
    title: 'Report what changed',
    body: 'Owners see pipeline quality, response speed, agent activity, offer movement, and revenue-per-agent signals from the same underlying data. Same numbers your team is acting on, in the same shape every Monday.',
    snippet: <SnippetMetric />,
  },
]

export default function WorkflowPage() {
  return (
    <>
      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 pt-20 pb-12 lg:pt-28">
        <div className="t-eyebrow mb-4">Workflow</div>
        <h1 className="t-display max-w-[820px] mb-5">
          From inbound buyer message to a sharper agent day.
        </h1>
        <p className="t-large max-w-[720px]">
          Dalya sits around the brokerage workflow your team already runs. It captures the
          buyer signal, gives the agent useful context, and gives owners a clean view of
          what is happening across the book.
        </p>
      </section>

      {/* ── FRAME STRIP ─────────────────────────────────── */}
      <div className="border-t border-b" style={{ borderColor: 'var(--color-border-hairline)' }}>
        <div className="max-w-[1180px] mx-auto px-6 lg:px-8 py-10">
          <div className="flex flex-wrap items-center gap-3 text-[13px]">
            {['Connect', 'Route', 'Brief', 'Escalate', 'Coordinate', 'Report'].map((s, i) => (
              <span key={s} className="flex items-center gap-3">
                <span
                  className="px-2.5 py-1 rounded-md text-[11px] uppercase tracking-widest font-bold"
                  style={{
                    background: 'var(--color-surface-1)',
                    color: 'var(--color-text-1)',
                    border: '1px solid var(--color-border-hairline)',
                  }}
                >
                  {String(i + 1).padStart(2, '0')} · {s}
                </span>
                {i < 5 && (
                  <span style={{ color: 'var(--color-text-3)' }}>→</span>
                )}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── ALTERNATING STEPS ───────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 py-24">
        <div className="flex flex-col gap-16 lg:gap-24">
          {STEPS.map((step, i) => {
            const flipped = i % 2 === 1
            return (
              <article
                key={step.label}
                className={`grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center`}
              >
                <div className={flipped ? 'lg:order-2' : ''}>
                  <div
                    className="text-[11px] uppercase tracking-widest font-bold mb-3"
                    style={{ color: 'var(--color-brand-500)' }}
                  >
                    {step.label}
                  </div>
                  <h2
                    className="text-3xl lg:text-4xl font-bold mb-4 leading-tight"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
                  >
                    {step.title}
                  </h2>
                  <p
                    className="text-[16px] leading-relaxed max-w-[520px]"
                    style={{ color: 'var(--color-text-2)' }}
                  >
                    {step.body}
                  </p>
                </div>

                <div className={flipped ? 'lg:order-1' : ''}>
                  <div
                    className="rounded-xl shadow-card-lg overflow-hidden"
                    style={{
                      background: 'var(--color-surface-0)',
                      border: '1px solid var(--color-border-hairline)',
                    }}
                  >
                    {step.snippet}
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      {/* ── TRUST STRIP ────────────────────────────────── */}
      <div
        className="border-t"
        style={{
          background: 'var(--color-surface-0)',
          borderColor: 'var(--color-border-hairline)',
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6 py-7 flex flex-wrap gap-6 justify-center items-center">
          {[
            'Listings operated by RERA-licensed brokerages',
            'UAE PDPL compliant',
            'EN · AR · RU · HI',
            'Dubai-based',
          ].map((item, i) => (
            <span
              key={item}
              className="text-[11px] uppercase tracking-widest font-semibold flex items-center"
              style={{ color: 'var(--color-text-3)' }}
            >
              {i > 0 && (
                <span
                  className="mr-2 font-bold"
                  style={{ color: 'var(--color-success-500)' }}
                >
                  ·
                </span>
              )}
              {item}
            </span>
          ))}
        </div>
      </div>

      {/* ── CLOSING CTA ─────────────────────────────────── */}
      <section className="text-center max-w-[720px] mx-auto px-6 py-24">
        <div className="t-eyebrow mb-4">Ready to see it on your book?</div>
        <h2 className="t-section mb-4">Run a 60-day pilot with us.</h2>
        <p className="t-large mb-6 max-w-[540px] mx-auto">
          Your team is the design partner. Your listings and your inquiry flow shape what
          gets built next.
        </p>
        <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
          Apply for design partnership
        </Link>
      </section>
    </>
  )
}

/* ─────── Step snippets ─────── */

function SnippetListing() {
  return (
    <>
      <div
        className="px-5 py-3 flex items-center gap-2 border-b"
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
          SPA verified
        </span>
        <span
          className="text-[11px] uppercase tracking-widest font-semibold"
          style={{ color: 'var(--color-text-3)' }}
        >
          Palace Villas Ostra · 5BD · Unit 2805
        </span>
      </div>
      <div className="p-5 grid grid-cols-2 gap-y-3 gap-x-6" style={{ background: 'var(--color-surface-0)' }}>
        <FactRow k="Asking" v="AED 17,253,444" mono />
        <FactRow k="Threshold" v="AED 16,894,000" mono />
        <FactRow k="Handover" v="2029-09-30" mono />
        <FactRow k="Tenure" v="Off-plan resale" />
        <FactRow k="Agent" v="Eric Lead Broker" />
        <FactRow k="DLD reg." v="In progress" />
      </div>
    </>
  )
}

function SnippetChat() {
  return (
    <div className="p-5 flex flex-col gap-2" style={{ background: 'var(--color-surface-0)' }}>
      <ChatBubble side="them">
        Salam, is the 5BD Palace Villas Ostra still available?
      </ChatBubble>
      <ChatBubble side="dalya">
        Yes. Asking AED 17,253,444. Off-plan resale, handover September 2029. What is drawing you to it?
      </ChatBubble>
      <ChatBubble side="them">
        Investment. Cash buyer, can move in 30 days. What is the minimum you would consider?
      </ChatBubble>
      <div className="flex gap-2 mt-2">
        <Tag text="Intent · investor" kind="brand" />
        <Tag text="Cash · 30-day close" kind="success" />
        <Tag text="Language · EN" kind="muted" />
      </div>
    </div>
  )
}

function SnippetBrief() {
  return (
    <>
      <div
        className="px-5 py-3 flex items-center gap-2 border-b"
        style={{
          background: 'var(--color-surface-1)',
          borderColor: 'var(--color-border-hairline)',
        }}
      >
        <span
          className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold"
          style={{
            background: 'var(--color-brand-100)',
            color: 'var(--color-brand-700)',
          }}
        >
          SM
        </span>
        <div className="flex flex-col leading-tight">
          <span className="text-[13px] font-semibold" style={{ color: 'var(--color-text-1)' }}>
            Sara Mohammed
          </span>
          <span className="text-[10px]" style={{ color: 'var(--color-text-3)' }}>
            Pre-call briefing · ready in 20s
          </span>
        </div>
        <span
          className="ml-auto text-[10px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
          style={{
            background: 'var(--color-success-100)',
            color: 'var(--color-success-700)',
          }}
        >
          Serious
        </span>
      </div>
      <div className="p-5 flex flex-col gap-2.5" style={{ background: 'var(--color-surface-0)' }}>
        <FactRow k="Intent" v="Investment · ready to move" />
        <FactRow k="Budget" v="AED 16 – 18M" mono />
        <FactRow k="Listing" v="Palace Villas Ostra · 5BD" />
        <FactRow k="Soft offer" v="AED 17.0M · Friday" mono />
        <FactRow k="Next step" v="Confirm 30-day close terms" />
      </div>
    </>
  )
}

function SnippetAlert() {
  return (
    <>
      <div
        className="px-5 py-3 flex items-center gap-2 border-b"
        style={{
          background: 'var(--color-surface-1)',
          borderColor: 'var(--color-border-hairline)',
        }}
      >
        <span
          className="w-2 h-2 rounded-full animate-pulse-dot"
          style={{ background: 'var(--color-success-500)' }}
        />
        <span
          className="text-[11px] uppercase tracking-widest font-semibold"
          style={{ color: 'var(--color-text-3)' }}
        >
          Live · Telegram alert
        </span>
        <span className="ml-auto text-[11px] tabular-aed" style={{ color: 'var(--color-text-3)' }}>
          14:23 GST
        </span>
      </div>
      <div className="p-5" style={{ background: 'var(--color-surface-0)' }}>
        <div className="t-eyebrow mb-2">Offer received · above threshold</div>
        <div
          className="text-3xl font-bold tabular-aed mb-3"
          style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
        >
          AED 17,000,000
        </div>
        <FactRow k="Buyer" v="Sara Mohammed" />
        <FactRow k="Listing" v="Palace Villas Ostra · 2805" />
        <FactRow k="Threshold" v="AED 16,894,000" mono />
        <FactRow k="Terms" v="Cash · 30-day close requested" />
      </div>
      <div
        className="px-5 py-3 flex gap-2 border-t"
        style={{
          background: 'var(--color-surface-1)',
          borderColor: 'var(--color-border-hairline)',
        }}
      >
        <span className="btn-brand text-xs rounded-md px-3 py-1.5">Accept</span>
        <span className="text-xs px-3 py-1.5 font-medium" style={{ color: 'var(--color-text-2)' }}>
          Counter
        </span>
        <span className="text-xs px-3 py-1.5 font-medium" style={{ color: 'var(--color-text-2)' }}>
          Decline
        </span>
      </div>
    </>
  )
}

function SnippetCalendar() {
  return (
    <div className="p-5" style={{ background: 'var(--color-surface-0)' }}>
      <div className="t-eyebrow mb-3">Wednesday · viewing slots</div>
      <div className="grid grid-cols-4 gap-2 mb-4">
        {[
          { label: '10:00', kind: 'empty' as const },
          { label: '11:30', kind: 'booked' as const },
          { label: '14:00', kind: 'suggested' as const },
          { label: '15:30', kind: 'empty' as const },
        ].map((s) => (
          <div
            key={s.label}
            className="text-[12px] py-2 text-center rounded-md font-semibold tabular-aed"
            style={
              s.kind === 'booked'
                ? {
                    background: 'var(--color-brand-500)',
                    color: 'white',
                    border: '1px solid var(--color-brand-500)',
                  }
                : s.kind === 'suggested'
                ? {
                    background: 'var(--color-brand-50)',
                    color: 'var(--color-brand-700)',
                    border: '1px solid var(--color-brand-100)',
                  }
                : {
                    background: 'var(--color-surface-1)',
                    color: 'var(--color-text-3)',
                    border: '1px solid var(--color-border-hairline)',
                  }
            }
          >
            {s.label}
          </div>
        ))}
      </div>
      <FactRow k="Access" v="Concierge notified · approved" />
      <FactRow k="Tenancy" v="Ejari · 48h notice sent" />
      <FactRow k="Invite" v="Calendar shared with Sara" />
      <FactRow k="After" v="Follow-up template ready" />
    </div>
  )
}

function SnippetMetric() {
  return (
    <div className="p-5 grid grid-cols-2 gap-5" style={{ background: 'var(--color-surface-0)' }}>
      <div>
        <div className="t-eyebrow mb-2">Revenue / agent · 30d</div>
        <div
          className="text-[32px] font-bold tabular-aed leading-none mb-2"
          style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
        >
          AED 187k
        </div>
        <span
          className="text-[11px] px-1.5 py-0.5 rounded font-bold tabular-aed"
          style={{
            background: 'var(--color-success-100)',
            color: 'var(--color-success-700)',
          }}
        >
          +12% vs baseline
        </span>
      </div>
      <div>
        <div className="t-eyebrow mb-2">Speed to response</div>
        <div
          className="text-[32px] font-bold tabular-aed leading-none mb-2"
          style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
        >
          47s
        </div>
        <span
          className="text-[11px] px-1.5 py-0.5 rounded font-bold tabular-aed"
          style={{
            background: 'var(--color-brand-50)',
            color: 'var(--color-brand-700)',
          }}
        >
          across 12 agents
        </span>
      </div>
    </div>
  )
}

/* ─────── Primitives ─────── */

function FactRow({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-3 text-[13px]">
      <span
        className="w-[88px] text-[11px] uppercase tracking-wide font-semibold shrink-0"
        style={{ color: 'var(--color-text-3)' }}
      >
        {k}
      </span>
      <span
        className="font-medium"
        style={{
          color: 'var(--color-text-1)',
          fontFamily: mono ? 'var(--font-mono)' : undefined,
          fontFeatureSettings: mono ? '"tnum", "ss01"' : undefined,
        }}
      >
        {v}
      </span>
    </div>
  )
}

function ChatBubble({
  children,
  side,
}: {
  children: React.ReactNode
  side: 'them' | 'dalya'
}) {
  const styles =
    side === 'them'
      ? {
          background: 'var(--color-surface-1)',
          color: 'var(--color-text-1)',
        }
      : {
          background: 'var(--color-surface-0)',
          color: 'var(--color-text-1)',
          border: '1px solid var(--color-border-hairline)',
          borderLeft: '2px solid var(--color-brand-500)',
        }
  return (
    <div
      className={`text-[13px] px-3 py-2 rounded-md max-w-[88%] leading-snug ${
        side === 'dalya' ? 'ml-auto' : ''
      }`}
      style={styles}
    >
      {children}
    </div>
  )
}

function Tag({
  text,
  kind,
}: {
  text: string
  kind: 'brand' | 'success' | 'muted'
}) {
  const styles =
    kind === 'success'
      ? { background: 'var(--color-success-100)', color: 'var(--color-success-700)' }
      : kind === 'brand'
        ? { background: 'var(--color-brand-50)', color: 'var(--color-brand-700)' }
        : { background: 'var(--color-surface-1)', color: 'var(--color-text-3)' }
  return (
    <span
      className="text-[10px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
      style={styles}
    >
      {text}
    </span>
  )
}
