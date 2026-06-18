import Link from 'next/link'

/* ════════════════════════════════════════════════════════════════════
 * FRAME — the agent-improvement statement
 * ════════════════════════════════════════════════════════════════════ */

export function Frame() {
  return (
    <div
      className="border-t border-b"
      style={{ borderColor: 'var(--color-border-hairline)' }}
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-14">
        <div className="max-w-[880px]">
          <div className="t-eyebrow mb-2.5">The frame</div>
          <p
            className="text-[22px] sm:text-2xl font-normal leading-snug"
            style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
          >
            Dalya is the operating layer around your agents&apos; day. It organizes repetitive
            questions, late-night WhatsApp replies, viewing coordination, and follow-up nudges
            into one working surface, so every agent starts the day knowing who to call,
            what changed, and where the next serious conversation is.
          </p>
        </div>
      </div>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * STATS — three big-number stat cards
 * ════════════════════════════════════════════════════════════════════ */

export function StatsRow() {
  return (
    <section style={{ background: 'var(--color-surface-1)' }}>
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-16">
        <div className="t-eyebrow mb-2.5">The pilot scorecard</div>
        <h2 className="t-section mb-3 max-w-[760px]">Measure whether agents get sharper.</h2>
        <p className="t-large max-w-[680px] mb-10">
          The first sixty days are not about software adoption theatre. We track the operating
          metrics brokerage owners already care about: speed to response, serious conversations,
          and revenue per agent.
        </p>

        <div
          className="grid grid-cols-1 md:grid-cols-3 md:gap-px overflow-hidden md:border md:rounded-xl"
          style={{ borderColor: 'var(--color-border-hairline)', background: 'var(--color-border-hairline)' }}
        >
          <StatCard
            num="<60s"
            headline="Faster first response."
            body="WhatsApp inquiries are answered, qualified, and logged while the lead is still warm."
            footnote="Pilot target · measured from inbound inquiry to first useful response"
          />
          <StatCard
            num="1 list"
            headline="Clear morning priority."
            body="Each agent starts with a ranked hot list, buyer context, and recommended next action."
            footnote="Daily workflow metric · measured by active follow-ups completed"
          />
          <StatCard
            num="Live"
            headline="Offer escalation."
            body="Above-threshold offers are surfaced immediately with listing, buyer, terms, and context."
            footnote="Operational metric · measured across every active listing"
          />
        </div>
      </div>
    </section>
  )
}

function StatCard({
  num,
  headline,
  body,
  footnote,
}: {
  num: string
  headline: string
  body: string
  footnote: string
}) {
  return (
    <div
      className="px-7 py-8"
      style={{ background: 'var(--color-surface-0)' }}
    >
      <div
        className="text-5xl font-bold tabular-aed leading-none mb-3"
        style={{ color: 'var(--color-brand-500)', letterSpacing: '-0.025em' }}
      >
        {num}
      </div>
      <div
        className="text-lg font-semibold mb-1.5"
        style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
      >
        {headline}
      </div>
      <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
        {body}
      </p>
      <p
        className="text-[11px] mt-3 italic"
        style={{ color: 'var(--color-text-3)' }}
      >
        {footnote}
      </p>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * SURFACES — two iframes showing the actual product
 * ════════════════════════════════════════════════════════════════════ */

export function Surfaces() {
  return (
    <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
      <div className="t-eyebrow mb-2.5">The platform</div>
        <h2 className="t-section mb-3 max-w-[760px]">Agents work faster. Owners see why.</h2>
        <p className="t-large max-w-[680px]">
        The agent surface turns buyer conversations into a practical work queue. The owner
        dashboard shows pipeline health, response speed, and revenue per agent from the same
        listing, conversation, and offer data.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-10">
        <SurfaceCard
          eyebrow="For agents · mobile + desktop"
          title="The agent day."
          desc="Hot list of who to call this morning. Pre-call buyer briefing one tap away. Conversation history and suggested reply ready before the agent follows up."
          src="/brand-mockups/agent-desktop.html"
        />
        <SurfaceCard
          eyebrow="For owners · desktop"
          title="The brokerage view."
          desc="Revenue per agent. Listings in flight. Offers above threshold. Buyer engagement velocity. The dashboard makes the operating picture visible."
          src="/brand-mockups/owner-dashboard.html"
        />
      </div>
    </section>
  )
}

export function SurfaceCard({
  eyebrow,
  title,
  desc,
  src,
}: {
  eyebrow: string
  title: string
  desc: string
  src: string
}) {
  return (
    <article
      className="rounded-xl overflow-hidden shadow-card-md"
      style={{
        background: 'var(--color-surface-0)',
        border: '1px solid var(--color-border-hairline)',
      }}
    >
      <div
        className="px-5 py-4 border-b"
        style={{ borderColor: 'var(--color-border-hairline)' }}
      >
        <div
          className="text-[11px] uppercase tracking-widest font-bold mb-1"
          style={{ color: 'var(--color-brand-500)' }}
        >
          {eyebrow}
        </div>
        <div
          className="text-lg font-semibold mb-1"
          style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
        >
          {title}
        </div>
        <p className="text-[13px] leading-snug" style={{ color: 'var(--color-text-2)' }}>
          {desc}
        </p>
      </div>
      <div
        className="relative h-[360px] overflow-hidden border-t"
        style={{
          background: 'var(--color-surface-1)',
          borderColor: 'var(--color-border-hairline)',
        }}
      >
        <iframe
          src={src}
          loading="lazy"
          title={title}
          className="absolute top-0 left-0 border-0"
          style={{
            width: '1440px',
            height: '720px',
            transform: 'scale(0.5)',
            transformOrigin: 'top left',
            pointerEvents: 'none',
          }}
        />
      </div>
      <div
        className="px-5 py-3 border-t"
        style={{
          background: 'var(--color-surface-1)',
          borderColor: 'var(--color-border-hairline)',
        }}
      >
        <a
          href={src}
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium"
          style={{ color: 'var(--color-brand-500)' }}
        >
          Open the live mockup →
        </a>
      </div>
    </article>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * PILLARS — six pillar cards each with a mini product snippet
 * ════════════════════════════════════════════════════════════════════ */

export function Pillars() {
  return (
    <section style={{ background: 'var(--color-surface-1)' }}>
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
        <div className="t-eyebrow mb-2.5">What Dalya improves</div>
        <h2 className="t-section mb-3 max-w-[760px]">The workflows around every deal.</h2>
        <p className="t-large max-w-[680px]">
          Every pillar maps to a job your agents already do. Dalya makes the inputs visible,
          the next action obvious, and the follow-up easier to complete.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-10">

          <Pillar
            num="01 / Buyers"
            title="Buyer engagement"
            desc="A 24/7 multilingual responder grounded in the actual documents. Routine questions are answered, serious signals are tagged, and agents wake up to an organized queue."
            snippet={<SnippetChat />}
          />
          <Pillar
            num="02 / Viewings"
            title="Viewing logistics"
            desc="Time slots, Ejari notice for tenanted units, building access, calendar invites, and post-viewing capture, organized before the agent steps into the viewing."
            snippet={<SnippetCalendar />}
          />
          <Pillar
            num="03 / Listings"
            title="Listing acquisition"
            desc="DLD ownership tenure, capital-gain signal, building velocity, comparable transactions. Per-owner outreach drafts grounded in that owner's specific unit."
            snippet={<SnippetListings />}
          />
          <Pillar
            num="04 / Workflow"
            title="Daily agent workflow"
            desc="A morning hot list ranking who to call. Draft-and-send when the agent is in the loop. Follow-up nudges when a buyer goes quiet."
            snippet={<SnippetHotlist />}
          />
          <Pillar
            num="05 / Negotiation"
            title="Negotiation support"
            desc="Comparables on demand. Seller flexibility signals. Suggested counters. Your agent decides. Dalya surfaces the inputs."
            snippet={<SnippetNegotiation />}
          />
          <Pillar
            num="06 / Sellers"
            title="Seller-side workflow"
            desc="Weekly seller updates auto-drafted with seven days of context. The agent reviews and sends with one tap. Friday afternoons stop disappearing."
            snippet={<SnippetSeller />}
          />

        </div>
      </div>
    </section>
  )
}

function Pillar({
  num,
  title,
  desc,
  snippet,
}: {
  num: string
  title: string
  desc: string
  snippet: React.ReactNode
}) {
  return (
    <div
      className="rounded-xl p-5 flex flex-col gap-4"
      style={{
        background: 'var(--color-surface-0)',
        border: '1px solid var(--color-border-hairline)',
      }}
    >
      <div
        className="text-[11px] font-medium font-mono tracking-wide"
        style={{ color: 'var(--color-brand-500)' }}
      >
        {num}
      </div>
      <div>
        <h3
          className="text-base font-semibold mb-1"
          style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
        >
          {title}
        </h3>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
          {desc}
        </p>
      </div>
      <div
        className="mt-auto rounded-lg p-3 min-h-[100px] flex flex-col justify-center gap-1.5"
        style={{
          background: 'var(--color-surface-1)',
          border: '1px solid var(--color-border-hairline)',
        }}
      >
        {snippet}
      </div>
    </div>
  )
}

/* Pillar snippet primitives ───────────────── */

function SnippetChat() {
  return (
    <>
      <div
        className="text-[11px] px-2 py-1.5 rounded-md leading-snug max-w-[92%]"
        style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-1)' }}
      >
        Is this villa still available?
      </div>
      <div
        className="text-[11px] px-2 py-1.5 rounded-md leading-snug max-w-[92%]"
        style={{
          background: 'var(--color-surface-0)',
          color: 'var(--color-text-1)',
          border: '1px solid var(--color-border-hairline)',
          borderLeft: '2px solid var(--color-brand-500)',
        }}
      >
        Yes, 5BD Palace Villas Ostra. Asking AED 17,253,444. What&apos;s drawing you to it?
      </div>
    </>
  )
}

function SnippetCalendar() {
  return (
    <>
      <div className="text-[10px] uppercase tracking-widest font-semibold" style={{ color: 'var(--color-text-3)' }}>Wed</div>
      <div className="grid grid-cols-4 gap-1">
        {[
          { label: '10:00', kind: 'empty' as const },
          { label: '11:30', kind: 'booked' as const },
          { label: '14:00', kind: 'suggested' as const },
          { label: '15:30', kind: 'empty' as const },
        ].map(s => (
          <div
            key={s.label}
            className="text-[9px] px-1 py-1 text-center rounded font-medium tabular-aed"
            style={
              s.kind === 'booked'
                ? { background: 'var(--color-brand-500)', color: 'white', border: '1px solid var(--color-brand-500)' }
                : s.kind === 'suggested'
                  ? { background: 'var(--color-brand-50)', color: 'var(--color-brand-700)', border: '1px solid var(--color-brand-100)' }
                  : { background: 'var(--color-surface-0)', color: 'var(--color-text-3)', border: '1px solid var(--color-border-hairline)' }
            }
          >
            {s.label}
          </div>
        ))}
      </div>
    </>
  )
}

function SnippetListings() {
  return (
    <>
      <SnippetRow label="Owner since" value="2019" />
      <SnippetRow label="Bought at" value="AED 1.8M" />
      <SnippetRow label="Comparable" value="AED 2.3M" pillText="+28%" pillKind="success" />
    </>
  )
}

function SnippetHotlist() {
  return (
    <>
      <HotlistRow name="Sara Mohammed" time="14:23" kind="hot" isTop />
      <HotlistRow name="Tom Henderson" time="13:51" kind="warm" />
      <HotlistRow name="+971 50 101 0012" time="12:04" kind="warm" />
    </>
  )
}

function SnippetNegotiation() {
  return (
    <>
      <SnippetRow label="Offer" value="AED 16.5M" pillText="−4.4%" pillKind="warning" />
      <SnippetRow label="3 comps" value="AED 17.1M avg" />
      <SnippetRow label="Suggest" value="Counter 17.0M" />
    </>
  )
}

function SnippetSeller() {
  return (
    <>
      <div className="text-[10px] uppercase tracking-widest font-semibold" style={{ color: 'var(--color-text-3)' }}>This week</div>
      <div className="flex items-center gap-2 text-[11px]">
        <span style={{ color: 'var(--color-text-3)' }} className="text-[10px] uppercase tracking-widest font-semibold">Views</span>
        <span className="tabular-aed font-semibold" style={{ color: 'var(--color-text-1)' }}>14</span>
        <span style={{ color: 'var(--color-text-3)' }} className="ml-auto text-[10px] uppercase tracking-widest font-semibold">Offers</span>
        <span className="tabular-aed font-semibold" style={{ color: 'var(--color-text-1)' }}>2</span>
      </div>
      <SnippetRow label="Top" value="AED 17.0M" pillText="Above ask" pillKind="brand" />
    </>
  )
}

function SnippetRow({
  label,
  value,
  pillText,
  pillKind,
}: {
  label: string
  value: string
  pillText?: string
  pillKind?: 'success' | 'warning' | 'brand'
}) {
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span
        className="text-[10px] uppercase tracking-widest font-semibold"
        style={{ color: 'var(--color-text-3)' }}
      >
        {label}
      </span>
      <span className="tabular-aed font-semibold" style={{ color: 'var(--color-text-1)' }}>
        {value}
      </span>
      {pillText && pillKind && <Pill text={pillText} kind={pillKind} />}
    </div>
  )
}

function Pill({ text, kind }: { text: string; kind: 'success' | 'warning' | 'brand' }) {
  const styles =
    kind === 'success'
      ? { background: 'var(--color-success-100)', color: 'var(--color-success-700)' }
      : kind === 'warning'
        ? { background: 'var(--color-warning-100)', color: 'var(--color-warning-700)' }
        : { background: 'var(--color-brand-50)', color: 'var(--color-brand-700)' }
  return (
    <span
      className="text-[9px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded ml-auto"
      style={styles}
    >
      {text}
    </span>
  )
}

function HotlistRow({
  name,
  time,
  kind,
  isTop,
}: {
  name: string
  time: string
  kind: 'hot' | 'warm'
  isTop?: boolean
}) {
  return (
    <div
      className="flex items-center gap-1.5 px-1.5 py-1 rounded text-[11px]"
      style={isTop ? { background: 'var(--color-surface-2)' } : undefined}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: kind === 'hot' ? 'var(--color-error-500)' : 'var(--color-brand-500)' }}
      />
      <span className="font-medium flex-1" style={{ color: 'var(--color-text-1)' }}>
        {name}
      </span>
      <span className="text-[10px] tabular-aed" style={{ color: 'var(--color-text-3)' }}>
        {time}
      </span>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * HOW WE SHIP — design partnerships + sample alert mockup
 * ════════════════════════════════════════════════════════════════════ */

export function HowWeShip() {
  return (
    <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">
        <div>
          <div className="t-eyebrow mb-2.5">How we ship</div>
          <h2 className="t-section mb-5">Design partnerships, not enterprise sales.</h2>
          <div
            className="text-[17px] leading-relaxed flex flex-col gap-4"
            style={{ color: 'var(--color-text-2)' }}
          >
            <p>
              We work with one brokerage at a time, deep, for sixty to ninety days.
              Every listing your team signs in that window runs through Dalya.
              Every WhatsApp inquiry is captured, qualified, and routed into the agent workflow.
            </p>
            <p>
              We sit on weekly calls with your owners and your top agents.
              You get the platform. We get the feedback that tells us where to build next.
            </p>
            <p>
              <strong style={{ color: 'var(--color-text-1)' }}>Pricing is deferred.</strong>{' '}
              We don&apos;t charge during the design partnership. Once your agents use it daily
              and the owner dashboard shows a clearer operating picture, we negotiate. Until
              then, the only thing we&apos;re optimising for is whether the team wants to keep it.
            </p>
          </div>
        </div>

        {/* Sample Telegram alert mockup */}
        <div
          className="rounded-xl overflow-hidden shadow-card-md"
          style={{
            background: 'var(--color-surface-0)',
            border: '1px solid var(--color-border-hairline)',
          }}
        >
          <div
            className="px-4 py-3 flex items-center gap-2 border-b"
            style={{
              background: 'var(--color-surface-1)',
              borderColor: 'var(--color-border-hairline)',
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse-dot"
              style={{ background: 'var(--color-success-500)' }}
            />
            <span
              className="text-[11px] uppercase tracking-widest font-semibold"
              style={{ color: 'var(--color-text-3)' }}
            >
              Live · Telegram alert
            </span>
            <span
              className="ml-auto text-[11px] tabular-aed"
              style={{ color: 'var(--color-text-3)' }}
            >
              14:23 GST
            </span>
          </div>
          <div className="p-5">
            <div className="t-eyebrow mb-2">Offer received · above threshold</div>
            <div
              className="text-2xl font-bold tabular-aed mb-3"
              style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
            >
              AED 17,000,000
            </div>
            <KeyValRow k="Buyer" v="Sara Mohammed" />
            <KeyValRow k="Listing" v="Palace Villas Ostra · 2805" />
            <KeyValRow k="Asking" v="AED 17,253,444" mono />
            <KeyValRow k="Threshold" v="AED 16,894,000" mono />
            <KeyValRow k="Terms" v="Cash · 30-day close requested" />
          </div>
          <div
            className="px-5 py-3 flex gap-2 border-t"
            style={{
              background: 'var(--color-surface-1)',
              borderColor: 'var(--color-border-hairline)',
            }}
          >
            <span className="btn-brand text-xs rounded-md px-3 py-1.5">Accept</span>
            <span
              className="text-xs px-3 py-1.5 font-medium"
              style={{ color: 'var(--color-text-2)' }}
            >
              Counter
            </span>
            <span
              className="text-xs px-3 py-1.5 font-medium"
              style={{ color: 'var(--color-text-2)' }}
            >
              Decline
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}

function KeyValRow({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 mb-1.5 text-[13px]">
      <span
        className="w-[90px] text-[11px] uppercase tracking-wide font-semibold"
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

/* ════════════════════════════════════════════════════════════════════
 * TRUST STRIP
 * ════════════════════════════════════════════════════════════════════ */

export function TrustStrip() {
  const items = [
    'Listings operated by RERA-licensed brokerages',
    'UAE PDPL compliant',
    'EN · AR · RU · HI',
    'Dubai-based',
  ]
  return (
    <div
      className="border-t"
      style={{
        background: 'var(--color-surface-0)',
        borderColor: 'var(--color-border-hairline)',
      }}
    >
      <div className="max-w-[1280px] mx-auto px-6 py-7 flex flex-wrap gap-6 justify-center items-center">
        {items.map((item, i) => (
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
  )
}

/* ════════════════════════════════════════════════════════════════════
 * CLOSING CTA
 * ════════════════════════════════════════════════════════════════════ */

export function ClosingCTA() {
  return (
    <section className="text-center max-w-[720px] mx-auto px-6 py-24">
      <div className="t-eyebrow mb-4">Currently in design partnership</div>
      <h2 className="t-section mb-4">Run a 60-day pilot with us.</h2>
      <p className="t-large mb-6 max-w-[540px] mx-auto">
        You give us active listings, agent feedback, and the operating baseline. We give your
        team the platform and measure whether the day gets sharper.
      </p>
      <Link
        href="/contact"
        className="btn-brand rounded-lg px-5 py-2.5 text-sm"
      >
        Apply for design partnership
      </Link>
    </section>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * MARKETING FOOTER
 * ════════════════════════════════════════════════════════════════════ */

export function MarketingFooter() {
  return (
    <footer
      className="border-t"
      style={{
        background: 'var(--color-surface-1)',
        borderColor: 'var(--color-border-hairline)',
      }}
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-6 flex flex-wrap gap-4 justify-between text-[11px]" style={{ color: 'var(--color-text-3)' }}>
        <span>© 2026 Dalya · AI infrastructure for Dubai brokerages</span>
        <div className="flex gap-4">
          <Link href="/contact" style={{ color: 'var(--color-text-3)' }}>Contact</Link>
        </div>
      </div>
    </footer>
  )
}
