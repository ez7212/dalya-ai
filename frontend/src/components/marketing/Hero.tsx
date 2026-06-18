import Link from 'next/link'

export function Hero() {
  return (
    <section className="relative">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 pt-20 pb-16 lg:pt-28 lg:pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-12 lg:gap-16 items-center">

          {/* Copy column */}
          <div>
            <div className="t-eyebrow mb-4">Built for Dubai brokerages</div>
            <h1 className="t-display max-w-xl mb-5">
              Give every agent a sharper operating system.
            </h1>
            <p className="t-large max-w-xl mb-7">
              Dalya helps your team qualify buyers faster, prioritize the right follow-ups,
              coordinate viewings, and surface serious offers the moment they arrive.
              Your agents stay focused on the conversations that move deals forward.
            </p>
            <div className="flex flex-wrap gap-3 items-center">
              <Link
                href="/contact"
                className="btn-brand rounded-lg px-5 py-2.5 text-sm"
              >
                Book a demo
              </Link>
              <Link
                href="/how-it-works"
                className="btn-outline rounded-lg px-5 py-2.5 text-sm"
              >
                See the workflow
              </Link>
            </div>
          </div>

          {/* Floating product visual */}
          <div className="relative h-[480px] hidden lg:block">

            {/* Card: conversation */}
            <FloatingCard
              top="0px"
              left="0px"
              width="340px"
              rotate="-2deg"
              z={2}
            >
              <MiniChatHead name="Sara Mohammed" initial="SM" time="14:21" />
              <div
                className="p-3 flex flex-col gap-1.5"
                style={{ background: 'var(--color-surface-0)' }}
              >
                <MiniBubble variant="them">
                  My offer is AED 17M cash. Can we close in 30 days?
                </MiniBubble>
                <MiniBubble variant="dalya">
                  AED 17,000,000 noted. Passing this to the seller now and circling back once they&apos;ve reviewed.
                </MiniBubble>
              </div>
            </FloatingCard>

            {/* Card: alert */}
            <FloatingCard
              top="140px"
              left="280px"
              width="360px"
              rotate="2.5deg"
              z={3}
            >
              <div
                className="flex items-center gap-2 px-3.5 py-2.5 border-b"
                style={{ borderColor: 'var(--color-border-hairline)' }}
              >
                <span
                  className="text-[10px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
                  style={{
                    color: 'var(--color-success-700)',
                    background: 'var(--color-success-100)',
                  }}
                >
                  Offer · above threshold
                </span>
                <span
                  className="ml-auto text-[11px] tabular-aed"
                  style={{ color: 'var(--color-text-3)' }}
                >
                  14:23
                </span>
              </div>
              <div className="p-3.5" style={{ background: 'var(--color-surface-0)' }}>
                <div className="t-eyebrow mb-1">Offer received</div>
                <div
                  className="text-2xl font-bold tabular-aed mb-1.5"
                  style={{
                    color: 'var(--color-text-1)',
                    letterSpacing: '-0.01em',
                  }}
                >
                  AED 17,000,000
                </div>
                <div
                  className="text-[11px]"
                  style={{ color: 'var(--color-text-2)' }}
                >
                  Sara Mohammed · Palace Villas Ostra · Cash · 30-day close
                </div>
              </div>
            </FloatingCard>

            {/* Card: morning hot list */}
            <FloatingCard
              top="320px"
              left="60px"
              width="290px"
              rotate="-1.5deg"
              z={1}
            >
              <div className="p-3.5" style={{ background: 'var(--color-surface-0)' }}>
                <div className="t-eyebrow mb-2.5">Morning hot list</div>
                <div className="flex flex-col gap-2">
                  <HotItem n="3" label="to call" />
                  <HotItem n="2" label="escalated questions · approve drafts" />
                  <HotItem n="4" label="additions to buyer contacts" />
                </div>
              </div>
            </FloatingCard>
          </div>

        </div>
      </div>
    </section>
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

function MiniChatHead({
  name,
  initial,
  time,
}: {
  name: string
  initial: string
  time: string
}) {
  return (
    <div
      className="flex items-center gap-2 px-3 py-2.5 border-b"
      style={{
        background: 'var(--color-surface-1)',
        borderColor: 'var(--color-border-hairline)',
      }}
    >
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
        style={{
          background: 'var(--color-brand-100)',
          color: 'var(--color-brand-700)',
        }}
      >
        {initial}
      </div>
      <span className="text-xs font-semibold" style={{ color: 'var(--color-text-1)' }}>
        {name}
      </span>
      <span
        className="ml-auto text-[10px] tabular-aed"
        style={{ color: 'var(--color-text-3)' }}
      >
        {time}
      </span>
    </div>
  )
}

function MiniBubble({
  children,
  variant,
}: {
  children: React.ReactNode
  variant: 'them' | 'dalya'
}) {
  const styles =
    variant === 'them'
      ? { background: 'var(--color-surface-2)', color: 'var(--color-text-1)', borderLeft: 'none' }
      : {
          background: 'var(--color-surface-1)',
          color: 'var(--color-text-1)',
          border: '1px solid var(--color-border-hairline)',
          borderLeft: '2px solid var(--color-brand-500)',
        }
  return (
    <div
      className="text-xs px-2.5 py-1.5 rounded-md max-w-[88%] leading-snug"
      style={styles}
    >
      {children}
    </div>
  )
}

function HotItem({ n, label }: { n: string; label: string }) {
  return (
    <div className="flex items-baseline gap-2">
      <span
        className="text-[16px] font-bold tabular-aed leading-none"
        style={{ color: 'var(--color-brand-600)' }}
      >
        {n}
      </span>
      <span
        className="text-[11px] leading-snug"
        style={{ color: 'var(--color-text-2)' }}
      >
        {label}
      </span>
    </div>
  )
}
