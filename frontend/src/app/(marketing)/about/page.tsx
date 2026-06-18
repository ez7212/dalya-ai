import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'About Dalya',
  description:
    'Dalya is the agent operating layer for Dubai brokerages, built inside a working RERA-licensed firm and now running as a B2B design partnership programme.',
}

const TIMELINE = [
  {
    year: '2024',
    label: 'Founded',
    title: 'Founded inside a working Dubai brokerage',
    body: 'A working RERA-licensed brokerage becomes the operating foundation. Every later product decision is shaped by what actually happens inside a Dubai brokerage day.',
  },
  {
    year: '2025',
    label: 'Built',
    title: 'Consumer-direct marketplace',
    body: 'Dalya launches as an off-plan resale marketplace. Buyers get a multilingual responder. Sellers get a fast SPA-to-listing pipeline.',
  },
  {
    year: '2026 · May',
    label: 'Pivoted',
    title: 'B2B agent infrastructure',
    body: 'After watching the workflow patterns, the product pivots from selling buyer-side to giving the same agent-side tools to other brokerages. The platform becomes the product.',
  },
  {
    year: '2026 · today',
    label: 'Now',
    title: 'Design partnerships',
    body: 'We are running hands-on pilots with a small number of Dubai brokerages. Pricing waits until the agent day is measurably sharper.',
  },
]

const PRINCIPLES = [
  {
    title: 'Built for Dubai brokerage work',
    body: 'Dalya is shaped around WhatsApp-heavy buyer conversations, RERA-aware workflows, off-plan and resale documents, viewing coordination, and fast-moving agent follow-up.',
  },
  {
    title: 'Agents remain the centre',
    body: 'The product makes buyer context, listing data, and next actions easier to use. The relationship, judgment, negotiation, and close still belong to the agent.',
  },
  {
    title: 'Owners get a faster team',
    body: 'The brokerage owner buys Dalya because every agent handles buyers faster, escalates serious offers to the right person, and keeps follow-up tight — a sharper team without adding headcount.',
  },
  {
    title: 'Regulatory awareness from day one',
    body: 'Every listing on the platform is operated by a RERA-licensed Dubai brokerage. Dalya is designed with PDPL, audit trails, and brokerage-specific data boundaries in mind.',
  },
]

const ATTRIBUTES = [
  {
    word: 'Trustworthy',
    body: 'Specific numbers, named sources, no exaggeration. We default to under-claiming and over-delivering on the operating metrics that brokerage owners actually check.',
  },
  {
    word: 'Calm',
    body: 'Quiet by omission. The product surface gives agents what they need and steps back. No notification theatre, no growth-loop manipulation, no fake urgency.',
  },
  {
    word: 'Sharp',
    body: 'Specific, precise, and useful at the moment a decision is being made. The brief is twenty seconds long because that is how long an agent has before the call.',
  },
]

export default function AboutPage() {
  return (
    <>
      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 pt-20 pb-12 lg:pt-28">
        <div className="t-eyebrow mb-4">About Dalya</div>
        <h1 className="t-display max-w-[820px] mb-5">
          Agent infrastructure for Dubai brokerages.
        </h1>
        <p className="t-large max-w-[720px]">
          Dalya started inside a working brokerage. The product now helps brokerages make
          every agent faster and better briefed across buyer conversations, serious-offer
          escalation, follow-up, and viewings.
        </p>
      </section>

      {/* ── TIMELINE ────────────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1180px] mx-auto px-6 lg:px-8 py-20 lg:py-24">
          <div className="t-eyebrow mb-2.5">How we got here</div>
          <h2 className="t-section mb-3 max-w-[720px]">
            From operating brokerage to platform.
          </h2>
          <p className="t-large max-w-[680px] mb-12">
            Every product decision started from inside an actual Dubai brokerage day. The
            consumer-direct work in 2025 taught us what was load-bearing for agents. The
            pivot in May 2026 made that the product.
          </p>

          <ol className="relative flex flex-col gap-0">
            {TIMELINE.map((step, i) => (
              <li key={step.year} className="grid grid-cols-[120px_1fr] lg:grid-cols-[180px_1fr] gap-6">
                {/* Left rail */}
                <div className="relative flex flex-col items-start pt-1">
                  <span
                    className="text-[13px] uppercase tracking-widest font-bold"
                    style={{ color: 'var(--color-brand-500)' }}
                  >
                    {step.year}
                  </span>
                  <span
                    className="text-[11px] uppercase tracking-widest font-semibold mt-0.5"
                    style={{ color: 'var(--color-text-3)' }}
                  >
                    {step.label}
                  </span>
                </div>

                {/* Right content with bullet + line */}
                <div className="relative pb-10 pl-8">
                  <span
                    className="absolute left-0 top-2 w-2.5 h-2.5 rounded-full"
                    style={{
                      background: 'var(--color-brand-500)',
                      boxShadow: '0 0 0 4px var(--color-surface-1)',
                    }}
                  />
                  {i < TIMELINE.length - 1 && (
                    <span
                      className="absolute left-[5px] top-5 bottom-0 w-px"
                      style={{ background: 'var(--color-border-default)' }}
                    />
                  )}
                  <h3
                    className="text-xl font-semibold mb-2"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
                  >
                    {step.title}
                  </h3>
                  <p
                    className="text-[15px] leading-relaxed max-w-[580px]"
                    style={{ color: 'var(--color-text-2)' }}
                  >
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── PRINCIPLES ──────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 py-24">
        <div className="t-eyebrow mb-2.5">How we operate</div>
        <h2 className="t-section mb-3 max-w-[720px]">Four principles that shape the build.</h2>
        <p className="t-large max-w-[680px] mb-12">
          They are not marketing principles. Each one rules out a class of decisions on the
          build queue every week.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {PRINCIPLES.map((p, i) => (
            <article
              key={p.title}
              className="rounded-xl p-6"
              style={{
                background: 'var(--color-surface-1)',
                border: '1px solid var(--color-border-hairline)',
              }}
            >
              <div
                className="text-[11px] font-mono mb-3"
                style={{ color: 'var(--color-brand-500)' }}
              >
                0{i + 1}
              </div>
              <h3
                className="text-lg font-semibold mb-2"
                style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
              >
                {p.title}
              </h3>
              <p className="text-[14px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                {p.body}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* ── BRAND ATTRIBUTES ──────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1180px] mx-auto px-6 lg:px-8 py-24">
          <div className="grid grid-cols-1 lg:grid-cols-[0.85fr_1.15fr] gap-10 lg:gap-16">
            <div>
              <div className="t-eyebrow mb-2.5">What we believe</div>
              <h2 className="t-section mb-4">
                Three words we hold ourselves to.
              </h2>
              <p
                className="text-[16px] leading-relaxed max-w-[440px]"
                style={{ color: 'var(--color-text-2)' }}
              >
                The brand reads in three words because the product reads that way. Specific
                where it matters, quiet where it does not, useful at the moment of decision.
              </p>
            </div>

            <div className="flex flex-col gap-4">
              {ATTRIBUTES.map((a, i) => (
                <div
                  key={a.word}
                  className="rounded-xl p-5 lg:p-6 grid grid-cols-1 md:grid-cols-[200px_1fr] gap-4 md:gap-6"
                  style={{
                    background: 'var(--color-surface-0)',
                    border: '1px solid var(--color-border-hairline)',
                  }}
                >
                  <div className="flex items-baseline gap-3">
                    <span
                      className="text-[12px] font-mono"
                      style={{ color: 'var(--color-brand-500)' }}
                    >
                      0{i + 1}
                    </span>
                    <span
                      className="text-2xl font-bold"
                      style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
                    >
                      {a.word}
                    </span>
                  </div>
                  <p className="text-[14px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                    {a.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── TRUST SIGNALS ─────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 py-20">
        <div className="t-eyebrow mb-2.5">Operating context</div>
        <h2 className="t-section mb-3 max-w-[720px]">Licensed, regulated, Dubai-based.</h2>
        <p className="t-large max-w-[680px] mb-10">
          Every listing on the platform is operated by a RERA-licensed Dubai brokerage.
          Regulatory posture and data boundaries are baked into the product rather than
          retrofitted later.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <TrustCard
            label="RERA"
            value="Per listing"
            note="Every listing on the platform is operated by a RERA-licensed Dubai brokerage."
          />
          <TrustCard
            label="UAE PDPL"
            value="Compliant"
            note="Per-brokerage data isolation, audit trail, and contractual data boundaries."
          />
          <TrustCard
            label="Languages"
            value="EN · AR · RU · HI"
            note="Buyer-facing responder operates natively in four languages out of the box."
          />
          <TrustCard
            label="Base"
            value="Dubai"
            note="Working with Dubai brokerages on Dubai listings. Not a remote SaaS team."
          />
        </div>
      </section>

      {/* ── CLOSING CTA ─────────────────────────────────── */}
      <section className="text-center max-w-[720px] mx-auto px-6 py-24">
        <div className="t-eyebrow mb-4">Currently in design partnership</div>
        <h2 className="t-section mb-4">Run a 60-day pilot with us.</h2>
        <p className="t-large mb-6 max-w-[540px] mx-auto">
          We are running design partnerships with small-to-medium Dubai brokerages before
          publishing pricing. The goal is simple: prove the agent day gets sharper.
        </p>
        <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
          Apply for pilot
        </Link>
      </section>
    </>
  )
}

function TrustCard({
  label,
  value,
  note,
}: {
  label: string
  value: string
  note: string
}) {
  return (
    <article
      className="rounded-xl p-5 flex flex-col gap-2"
      style={{
        background: 'var(--color-surface-1)',
        border: '1px solid var(--color-border-hairline)',
      }}
    >
      <div
        className="text-[11px] uppercase tracking-widest font-bold"
        style={{ color: 'var(--color-text-3)' }}
      >
        {label}
      </div>
      <div
        className="text-xl font-bold"
        style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
      >
        {value}
      </div>
      <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
        {note}
      </p>
    </article>
  )
}
