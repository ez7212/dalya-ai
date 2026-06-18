import type { Metadata } from 'next'
import Link from 'next/link'
import { SurfaceCard } from '@/components/marketing/Sections'

export const metadata: Metadata = {
  title: 'For Agents — Dalya',
  description:
    'Dalya gives Dubai real estate agents a ranked hot list, pre-call buyer briefings, viewing logistics, and follow-up support, so the day moves around the deals that matter.',
}

const AGENT_GAINS = [
  {
    title: 'Start with the right calls',
    body: 'A ranked hot list shows which buyers need attention first, sorted by signal, not by the order they messaged.',
  },
  {
    title: 'Walk into calls briefed',
    body: 'Buyer intent, budget signals, prior questions, listing facts, and offer history sit in one view, ready before you dial.',
  },
  {
    title: 'Move viewings faster',
    body: 'Slots, access constraints, tenancy notice, calendar invites, and post-viewing capture stay attached to the buyer thread.',
  },
  {
    title: 'Follow up with better context',
    body: 'Suggested replies and next actions keep you in control while reducing blank-screen work between conversations.',
  },
]

const DAY = [
  {
    time: '08:42',
    label: 'Morning',
    title: 'Open the hot list',
    body: 'Three buyers ready for a real conversation, ranked by signal. The first call has a soft offer floating since Friday.',
    snippet: <DaySnippetHotlist />,
  },
  {
    time: '09:15',
    label: 'Pre-call',
    title: 'Read the buyer briefing',
    body: 'One screen with intent, budget signals, prior questions, listing facts, and the suggested talking points for this call.',
    snippet: <DaySnippetBrief />,
  },
  {
    time: '11:00',
    label: 'Mid-morning',
    title: 'Run the viewing',
    body: 'Building access confirmed. Tenancy notice already sent forty-eight hours ago. Calendar invite shared, follow-up template ready.',
    snippet: <DaySnippetViewing />,
  },
  {
    time: '17:30',
    label: 'Evening',
    title: 'Send the follow-ups',
    body: 'Three drafts prepared from the day, grounded in each buyer’s context. Review, edit, send. The thread updates automatically.',
    snippet: <DaySnippetFollowup />,
  },
]

export default function AgentsPage() {
  return (
    <>
      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 pt-20 pb-16 lg:pt-28 lg:pb-24">
          <div className="grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-12 lg:gap-16 items-center">
            <div>
              <div className="t-eyebrow mb-4">For agents</div>
              <h1 className="t-display max-w-[640px] mb-5">A cleaner day for serious agents.</h1>
              <p className="t-large max-w-[620px] mb-7">
                Dalya gives you the buyer context, listing facts, and next action before the
                follow-up happens. Less hunting through chats. More time on the conversations
                that can turn into deals.
              </p>
              <div className="flex flex-wrap gap-3 items-center">
                <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
                  Apply for design partnership
                </Link>
                <Link
                  href="/brand-mockups/agent-desktop.html"
                  target="_blank"
                  rel="noreferrer"
                  className="btn-outline rounded-lg px-5 py-2.5 text-sm"
                >
                  Open the agent mockup
                </Link>
              </div>
            </div>

            {/* Floating agent-view cards */}
            <div className="relative h-[480px] hidden lg:block">
              {/* Hot list card */}
              <FloatingCard top="0px" left="40px" width="340px" rotate="-2deg" z={2}>
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
                      background: 'var(--color-brand-50)',
                      color: 'var(--color-brand-700)',
                    }}
                  >
                    Hot list · 08:42
                  </span>
                  <span
                    className="ml-auto text-[10px] uppercase tracking-widest font-semibold"
                    style={{ color: 'var(--color-text-3)' }}
                  >
                    Mon
                  </span>
                </div>
                <div className="p-3 flex flex-col gap-1.5" style={{ background: 'var(--color-surface-0)' }}>
                  <HotRow name="Sara Mohammed" note="Soft offer · AED 17M" kind="hot" isTop />
                  <HotRow name="Tom Henderson" note="Viewing scheduled · 11:00" kind="warm" />
                  <HotRow name="Anya Volkov" note="Document re-share due" kind="warm" />
                </div>
              </FloatingCard>

              {/* Buyer briefing card */}
              <FloatingCard top="170px" left="290px" width="360px" rotate="2deg" z={3}>
                <div
                  className="px-4 py-2.5 flex items-center gap-2 border-b"
                  style={{
                    background: 'var(--color-surface-1)',
                    borderColor: 'var(--color-border-hairline)',
                  }}
                >
                  <span
                    className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
                    style={{
                      background: 'var(--color-brand-100)',
                      color: 'var(--color-brand-700)',
                    }}
                  >
                    SM
                  </span>
                  <span className="text-xs font-semibold" style={{ color: 'var(--color-text-1)' }}>
                    Sara Mohammed
                  </span>
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
                <div className="p-3.5" style={{ background: 'var(--color-surface-0)' }}>
                  <div className="t-eyebrow mb-2">Pre-call briefing</div>
                  <BriefRow k="Budget" v="AED 16 – 18M" />
                  <BriefRow k="Listing" v="Palace Villas Ostra" />
                  <BriefRow k="Soft offer" v="AED 17.0M · Friday" mono />
                  <BriefRow k="Next step" v="Confirm 30-day close terms" />
                </div>
              </FloatingCard>

              {/* Suggested reply card */}
              <FloatingCard top="350px" left="120px" width="300px" rotate="-1deg" z={1}>
                <div className="p-3.5" style={{ background: 'var(--color-surface-0)' }}>
                  <div className="t-eyebrow mb-1.5">Suggested reply · ready to send</div>
                  <p
                    className="text-[12px] leading-snug"
                    style={{ color: 'var(--color-text-1)' }}
                  >
                    Confirming your AED 17M offer with the seller this morning. Will circle
                    back on the 30-day close timeline once reviewed.
                  </p>
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
              The relationship, the negotiation, the close still belong to the agent. Dalya
              organises everything that surrounds those moments so the agent stops losing
              time to context-hunting and starts every conversation already briefed.
            </p>
          </div>
        </div>
      </div>

      {/* ── DAY IN THE LIFE ──────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
          <div className="t-eyebrow mb-2.5">A day with Dalya</div>
          <h2 className="t-section mb-3 max-w-[760px]">The agent day, in four moments.</h2>
          <p className="t-large max-w-[680px] mb-12">
            From the morning hot list to the evening follow-up sweep. Same agent, same book,
            different operating surface around them.
          </p>

          <div className="flex flex-col gap-4">
            {DAY.map((moment, i) => (
              <article
                key={moment.time}
                className="rounded-xl overflow-hidden grid grid-cols-1 lg:grid-cols-[180px_1fr_1fr]"
                style={{
                  background: 'var(--color-surface-0)',
                  border: '1px solid var(--color-border-hairline)',
                }}
              >
                <div
                  className="px-5 py-5 flex flex-col justify-center gap-1 border-b lg:border-b-0 lg:border-r"
                  style={{
                    borderColor: 'var(--color-border-hairline)',
                    background: 'var(--color-surface-1)',
                  }}
                >
                  <div
                    className="text-[28px] font-bold tabular-aed leading-none"
                    style={{ color: 'var(--color-brand-500)', letterSpacing: '-0.02em' }}
                  >
                    {moment.time}
                  </div>
                  <div
                    className="text-[10px] uppercase tracking-widest font-bold"
                    style={{ color: 'var(--color-text-3)' }}
                  >
                    {moment.label}
                  </div>
                  <div
                    className="text-[10px] tabular-aed mt-1"
                    style={{ color: 'var(--color-text-3)' }}
                  >
                    {String(i + 1).padStart(2, '0')} / 04
                  </div>
                </div>

                <div className="px-5 py-5 flex flex-col justify-center gap-2">
                  <h3
                    className="text-lg font-semibold"
                    style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
                  >
                    {moment.title}
                  </h3>
                  <p className="text-[14px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                    {moment.body}
                  </p>
                </div>

                <div
                  className="px-5 py-5 border-t lg:border-t-0 lg:border-l flex items-center"
                  style={{
                    borderColor: 'var(--color-border-hairline)',
                    background: 'var(--color-surface-1)',
                  }}
                >
                  <div
                    className="w-full rounded-lg p-3 flex flex-col gap-1.5"
                    style={{
                      background: 'var(--color-surface-0)',
                      border: '1px solid var(--color-border-hairline)',
                    }}
                  >
                    {moment.snippet}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── EMBEDDED AGENT MOCKUP ────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
        <div className="t-eyebrow mb-2.5">Working surface</div>
        <h2 className="t-section mb-3 max-w-[760px]">The agent surface, live.</h2>
        <p className="t-large max-w-[680px] mb-10">
          Hot list, buyer briefing, conversation thread, and viewing logistics in one
          working surface. Mobile when the agent is on the move. Desktop when there is real
          paperwork on the table.
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

      {/* ── GAINS GRID ──────────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
          <div className="t-eyebrow mb-2.5">What changes for the agent</div>
          <h2 className="t-section mb-3 max-w-[760px]">Faster, better briefed, fewer dropped balls.</h2>
          <p className="t-large max-w-[680px] mb-10">
            The volume of conversations does not change. The work that happens around each
            conversation does.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {AGENT_GAINS.map((g, i) => (
              <article
                key={g.title}
                className="rounded-xl p-6"
                style={{
                  background: 'var(--color-surface-0)',
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
                  className="text-base font-semibold mb-2"
                  style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
                >
                  {g.title}
                </h3>
                <p className="text-[14px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                  {g.body}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── CLOSING CTA ──────────────────────────────────── */}
      <section className="text-center max-w-[720px] mx-auto px-6 py-24">
        <div className="t-eyebrow mb-4">Want this for your team?</div>
        <h2 className="t-section mb-4">Run a 60-day pilot with us.</h2>
        <p className="t-large mb-6 max-w-[540px] mx-auto">
          We work with one brokerage at a time, deep, for sixty to ninety days. Your agents
          get the platform. We get the feedback that tells us where to build next.
        </p>
        <Link href="/contact" className="btn-brand rounded-lg px-5 py-2.5 text-sm">
          Apply for design partnership
        </Link>
      </section>
    </>
  )
}

/* ─────── Floating card primitive ─────── */

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

function HotRow({
  name,
  note,
  kind,
  isTop,
}: {
  name: string
  note: string
  kind: 'hot' | 'warm'
  isTop?: boolean
}) {
  return (
    <div
      className="flex items-center gap-2 px-2 py-1.5 rounded"
      style={isTop ? { background: 'var(--color-surface-2)' } : undefined}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: kind === 'hot' ? 'var(--color-error-500)' : 'var(--color-brand-500)' }}
      />
      <span className="flex-1 text-[11px] leading-tight">
        <span className="font-semibold" style={{ color: 'var(--color-text-1)' }}>
          {name}
        </span>
        <br />
        <span style={{ color: 'var(--color-text-3)' }}>{note}</span>
      </span>
    </div>
  )
}

function BriefRow({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 mb-1 text-[12px]">
      <span
        className="w-[64px] text-[10px] uppercase tracking-wide font-semibold shrink-0"
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

/* ─────── Day-in-the-life snippets ─────── */

function DaySnippetHotlist() {
  return (
    <>
      <div className="flex items-center gap-2 text-[11px]">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: 'var(--color-error-500)' }}
        />
        <span className="font-semibold flex-1" style={{ color: 'var(--color-text-1)' }}>
          Sara Mohammed
        </span>
        <span className="tabular-aed text-[10px]" style={{ color: 'var(--color-text-3)' }}>
          14:23
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: 'var(--color-brand-500)' }}
        />
        <span className="font-semibold flex-1" style={{ color: 'var(--color-text-1)' }}>
          Tom Henderson
        </span>
        <span className="tabular-aed text-[10px]" style={{ color: 'var(--color-text-3)' }}>
          13:51
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: 'var(--color-brand-500)' }}
        />
        <span className="font-semibold flex-1" style={{ color: 'var(--color-text-1)' }}>
          Anya Volkov
        </span>
        <span className="tabular-aed text-[10px]" style={{ color: 'var(--color-text-3)' }}>
          12:04
        </span>
      </div>
    </>
  )
}

function DaySnippetBrief() {
  return (
    <>
      <KeyVal k="Intent" v="Investment buyer" />
      <KeyVal k="Budget" v="AED 16 – 18M" mono />
      <KeyVal k="Listing" v="Palace Villas Ostra" />
      <KeyVal k="Last" v="Soft offer at AED 17M" />
    </>
  )
}

function DaySnippetViewing() {
  return (
    <>
      <KeyVal k="Slot" v="Wed · 14:00" mono />
      <KeyVal k="Access" v="Concierge confirmed" />
      <KeyVal k="Notice" v="Ejari · 48h sent" />
      <KeyVal k="After" v="Follow-up template ready" />
    </>
  )
}

function DaySnippetFollowup() {
  return (
    <>
      <div
        className="text-[11px] px-2 py-1.5 rounded-md leading-snug"
        style={{
          background: 'var(--color-surface-1)',
          color: 'var(--color-text-1)',
          border: '1px solid var(--color-border-hairline)',
          borderLeft: '2px solid var(--color-brand-500)',
        }}
      >
        Confirming the AED 17M offer with the seller this morning. Will circle back today.
      </div>
      <div className="flex gap-2 text-[10px]">
        <span
          className="px-2 py-0.5 rounded font-bold"
          style={{
            background: 'var(--color-brand-500)',
            color: 'white',
          }}
        >
          Send
        </span>
        <span
          className="px-2 py-0.5 rounded font-bold"
          style={{
            background: 'var(--color-surface-2)',
            color: 'var(--color-text-2)',
          }}
        >
          Edit
        </span>
      </div>
    </>
  )
}

function KeyVal({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 text-[11px]">
      <span
        className="w-[54px] text-[10px] uppercase tracking-wide font-semibold shrink-0"
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
