import Link from 'next/link'
import Image from 'next/image'

/* ════════════════════════════════════════════════════════════════════
 * STATS — three big-number stat cards
 * ════════════════════════════════════════════════════════════════════ */

export function StatsRow() {
  return (
    <section style={{ background: 'var(--color-surface-1)' }}>
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-16">
        <div className="t-eyebrow mb-2.5">Always on</div>
        <h2 className="t-section mb-3 max-w-[760px]">The intelligent system that never sleeps.</h2>
        <p className="t-large max-w-[680px] mb-10">
          It answers the 2am inquiry, qualifies the buyer, and flags the serious ones. It drafts
          the follow-up before the trail goes cold and escalates the offer the moment it matters.
          Every agent walks in already briefed — working like your sharpest one.
        </p>

        <div
          className="grid grid-cols-1 md:grid-cols-3 md:gap-px overflow-hidden md:border md:rounded-xl"
          style={{ borderColor: 'var(--color-border-hairline)', background: 'var(--color-border-hairline)' }}
        >
          <StatCard
            measure="First response"
            value="Under 60s"
            body="Every buyer message is answered, qualified, and logged while the lead is still warm — day or night."
          />
          <StatCard
            measure="Morning hot list"
            value="Ranked & ready"
            body="Each agent opens to a ranked queue of who to call, the conversation summary, and the next action already drafted."
          />
          <StatCard
            measure="Viewing logistics"
            value="Booked & confirmed"
            body="Slots proposed, tenant and buyer confirmed, calendar invite sent — the back-and-forth handled before the agent arrives."
          />
        </div>
      </div>
    </section>
  )
}

function StatCard({
  measure,
  value,
  body,
}: {
  measure: string
  value: string
  body: string
}) {
  return (
    <div
      className="px-7 py-8 flex flex-col"
      style={{ background: 'var(--color-surface-0)' }}
    >
      <div
        className="text-[11px] uppercase tracking-widest font-bold mb-2"
        style={{ color: 'var(--color-brand-500)' }}
      >
        {measure}
      </div>
      <div
        className="text-[26px] font-semibold tabular-aed leading-tight mb-2"
        style={{ color: 'var(--color-text-1)', letterSpacing: '-0.02em' }}
      >
        {value}
      </div>
      <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
        {body}
      </p>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * SURFACES — crisp product screenshots (was: scaled iframes)
 * ════════════════════════════════════════════════════════════════════ */

export function Surfaces() {
  return (
    <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
      <div className="t-eyebrow mb-2.5">The platform</div>
      <h2 className="t-section mb-3 max-w-[760px]">The agent&apos;s entire day, on one screen.</h2>
      <p className="t-large max-w-[680px]">
        One dashboard that encompasses every facet of an agent&apos;s daily workflow — the
        morning hot list, today&apos;s viewings, live conversations, drafts awaiting review, and
        every listing they manage. They open it and start working.
      </p>

      <div className="mt-10">
        <SurfaceCard
          eyebrow="For agents · mobile + desktop"
          title="The agent dashboard."
          desc="Who to call this morning, ranked by buying signal. Today's viewings and confirmations. Drafts waiting for one-tap approval. Every page an agent needs, one click away."
          img="/brand-mockups/agent-dashboard.png"

          mobileImg="/brand-mockups/agent-mobile.png"
          src="/brand-mockups/agent-dashboard.html"
        />
      </div>
    </section>
  )
}

export function SurfaceCard({
  eyebrow,
  title,
  desc,
  img,
  mobileImg,
  src,
}: {
  eyebrow: string
  title: string
  desc: string
  img: string
  mobileImg?: string
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
      {/* Desktop: full landscape surface. Hidden on mobile when a portrait
          mobile mockup is available (a shrunk desktop dashboard is illegible). */}
      <div
        className={`relative border-t overflow-hidden ${mobileImg ? 'hidden md:block' : ''}`}
        style={{
          background: 'var(--color-surface-1)',
          borderColor: 'var(--color-border-hairline)',
          aspectRatio: '1280 / 600',
        }}
      >
        <Image
          src={img}
          alt={`${title} — Dalya product preview`}
          fill
          sizes="(max-width: 1024px) 100vw, 1232px"
          quality={95}
          unoptimized
          className="object-cover object-top"
        />
      </div>
      {mobileImg && (
        <div
          className="md:hidden flex justify-center px-6 py-7 border-t"
          style={{
            background: 'var(--color-surface-1)',
            borderColor: 'var(--color-border-hairline)',
          }}
        >
          <div
            className="relative w-[260px] rounded-xl overflow-hidden shadow-card-md"
            style={{ aspectRatio: '390 / 760', border: '1px solid var(--color-border-hairline)' }}
          >
            <Image
              src={mobileImg}
              alt={`${title} — Dalya on mobile`}
              fill
              sizes="260px"
              unoptimized
              className="object-cover object-top"
            />
          </div>
        </div>
      )}
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
        <div className="t-eyebrow mb-2.5">What Dalya does today</div>
        <h2 className="t-section mb-3 max-w-[760px]">Four workflows, working right now.</h2>
        <p className="t-large max-w-[680px]">
          Each one maps to a job your agents already do. Dalya makes the inputs visible,
          the next action obvious, and the follow-up easier to complete.
        </p>

        {/* Bento: wide cards (text beside snippet) alternate L/R against
            narrow stacked cards, breaking the uniform grid rhythm. */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-10">

          <Pillar
            wide
            num="01 / Buyers"
            title="24/7 inquiry concierge"
            desc="A multilingual responder grounded in the actual listing documents. Routine questions are answered, voice notes are transcribed, serious signals are tagged, and agents wake up to an organized queue."
            snippet={<SnippetChat />}
          />
          <Pillar
            num="02 / Escalation"
            title="Smart escalation"
            desc="Serious or unanswerable questions and above-threshold offers route to the right agent — on WhatsApp or the dashboard. The agent replies, and it relays straight back to the buyer."
            snippet={<SnippetEscalation />}
          />
          <Pillar
            num="03 / Workflow"
            title="Hot list & follow-ups"
            desc="A morning hot list ranking who to call. Review-only follow-up drafts when a buyer goes quiet. The agent edits and sends in one tap — Dalya never sends on its own."
            snippet={<SnippetHotlist />}
          />
          <Pillar
            wide
            num="04 / Viewings"
            title="Viewing logistics"
            desc="Slot proposals, Ejari notice for tenanted units, building access, tenant and buyer confirmation, calendar invites, pre-viewing briefs, and post-viewing capture — organized before the agent steps into the viewing."
            snippet={<SnippetCalendar />}
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
  wide = false,
}: {
  num: string
  title: string
  desc: string
  snippet: React.ReactNode
  wide?: boolean
}) {
  const heading = (
    <div>
      <div
        className="text-[11px] font-medium font-mono tracking-wide mb-3"
        style={{ color: 'var(--color-brand-500)' }}
      >
        {num}
      </div>
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
  )

  const snippetBox = (
    <div
      className="rounded-lg p-3 min-h-[100px] flex flex-col justify-center gap-1.5"
      style={{
        background: 'var(--color-surface-1)',
        border: '1px solid var(--color-border-hairline)',
      }}
    >
      {snippet}
    </div>
  )

  // Wide cards span two columns and read horizontally (text │ snippet),
  // giving the section a different beat from the stacked narrow cards.
  if (wide) {
    return (
      <div
        className="rounded-xl p-5 lg:p-6 lg:col-span-2 flex flex-col gap-4 lg:grid lg:grid-cols-2 lg:gap-6 lg:items-stretch"
        style={{
          background: 'var(--color-surface-0)',
          border: '1px solid var(--color-border-hairline)',
        }}
      >
        {heading}
        {snippetBox}
      </div>
    )
  }

  return (
    <div
      className="rounded-xl p-5 flex flex-col gap-4"
      style={{
        background: 'var(--color-surface-0)',
        border: '1px solid var(--color-border-hairline)',
      }}
    >
      {heading}
      <div className="mt-auto">{snippetBox}</div>
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
        Yes, 5BD Palace Villas Ostra. Asking AED 17,253,444. Would you like to schedule a viewing?
      </div>
    </>
  )
}

function SnippetCalendar() {
  return (
    <>
      <div className="text-[10px] uppercase tracking-widest font-semibold" style={{ color: 'var(--color-text-3)' }}>Wed · proposed slots</div>
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
      <div
        className="flex items-center gap-1.5 mt-1 text-[10px] px-2 py-1.5 rounded-md leading-snug"
        style={{ background: 'var(--color-success-100)', color: 'var(--color-success-700)' }}
      >
        <span className="font-bold">✓</span>
        <span>Confirmed · Sara, Wed 14:00 — calendar invite &amp; tenant notice sent</span>
      </div>
    </>
  )
}

function SnippetEscalation() {
  return (
    <>
      <SnippetRow label="Question" value="Close in 30 days?" pillText="Escalated" pillKind="brand" />
      <SnippetRow label="Offer" value="AED 17.0M" pillText="Above threshold" pillKind="success" />
      <SnippetRow label="Routed to" value="Alice · Lead Broker" />
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
 * NEVER MISSES — always-on escalation + sample alert mockup
 * ════════════════════════════════════════════════════════════════════ */

export function HowWeShip() {
  return (
    <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">
        <div>
          <div className="t-eyebrow mb-2.5">Never misses the moment</div>
          <h2 className="t-section mb-5">The work happens whether you&apos;re watching or not.</h2>
          <div
            className="text-[17px] leading-relaxed flex flex-col gap-4"
            style={{ color: 'var(--color-text-2)' }}
          >
            <p>
              A serious offer lands at midnight. Dalya surfaces it instantly with a negotiation
              draft, and the right agent&apos;s phone lights up — listing, buyer, terms, and
              context already attached.
            </p>
            <p>
              The buyer who went quiet for six days gets a follow-up drafted before the trail
              goes cold. The 2am question gets a grounded answer. Nothing waits for morning.
            </p>
            <p>
              <strong style={{ color: 'var(--color-text-1)' }}>Your agents stay in control.</strong>{' '}
              Dalya does the work around the deal and hands it over ready to send. The
              relationship, the judgment, and the close still belong to the agent.
            </p>
          </div>
        </div>

        {/* Escalated-message mockup */}
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
              style={{ background: 'var(--color-warning-500)' }}
            />
            <span
              className="text-[11px] uppercase tracking-widest font-semibold"
              style={{ color: 'var(--color-text-3)' }}
            >
              Escalation · 6 minutes ago
            </span>
            <span
              className="ml-auto text-[11px] tabular-aed"
              style={{ color: 'var(--color-text-3)' }}
            >
              14:23 GST
            </span>
          </div>
          <div className="p-5">
            <div className="t-eyebrow mb-1">New question from Mark</div>
            <div className="text-[12px] mb-3" style={{ color: 'var(--color-text-3)' }}>
              Address Residences Sky View · 2-bed apartment
            </div>
            <div
              className="text-[13px] px-3 py-2 rounded-lg leading-snug mb-4"
              style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-1)' }}
            >
              &ldquo;Are there tenants living there? We&apos;d like to move in at the beginning of next month.&rdquo;
            </div>
            <div className="t-eyebrow mb-1.5">Draft response</div>
            <div
              className="text-[13px] px-3 py-2 rounded-lg leading-snug"
              style={{
                background: 'var(--color-surface-1)',
                color: 'var(--color-text-1)',
                border: '1px solid var(--color-border-hairline)',
                borderLeft: '2px solid var(--color-brand-500)',
              }}
            >
              &ldquo;Available for move-in ASAP. Can arrange a viewing tomorrow — what time works?&rdquo;
            </div>
          </div>
          <div
            className="px-5 py-3 flex items-center gap-2 border-t"
            style={{
              background: 'var(--color-surface-1)',
              borderColor: 'var(--color-border-hairline)',
            }}
            aria-hidden="true"
          >
            <span className="btn-brand text-xs rounded-md px-3 py-1.5">Accept</span>
            <span
              className="text-xs px-3 py-1.5 font-medium"
              style={{ color: 'var(--color-text-2)' }}
            >
              Edit
            </span>
            <span
              className="text-xs px-3 py-1.5 font-medium"
              style={{ color: 'var(--color-text-2)' }}
            >
              Re-draft
            </span>
            <span
              className="ml-auto text-[9px] uppercase tracking-widest font-semibold"
              style={{ color: 'var(--color-text-3)' }}
            >
              Preview
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * WHATSAPP BRIDGE — keep your number; Dalya drafts, you one-tap send
 * ════════════════════════════════════════════════════════════════════ */

export function WhatsAppBridge() {
  return (
    <section style={{ background: 'var(--color-surface-1)' }}>
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">

          {/* WhatsApp chat mock */}
          <div className="order-2 lg:order-1">
            <div
              className="rounded-xl overflow-hidden shadow-card-md mx-auto max-w-[380px]"
              style={{
                background: 'var(--color-surface-0)',
                border: '1px solid var(--color-border-hairline)',
              }}
            >
              <div
                className="px-4 py-3 flex items-center gap-2.5 border-b"
                style={{
                  background: 'var(--color-surface-1)',
                  borderColor: 'var(--color-border-hairline)',
                }}
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold"
                  style={{ background: 'var(--color-brand-100)', color: 'var(--color-brand-700)' }}
                >
                  MK
                </div>
                <div>
                  <div className="text-xs font-semibold" style={{ color: 'var(--color-text-1)' }}>Mark</div>
                  <div className="text-[10px] tabular-aed" style={{ color: 'var(--color-text-3)' }}>+971 50 412 0098 · WhatsApp</div>
                </div>
                <span
                  className="ml-auto text-[9px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
                  style={{ background: 'var(--color-success-100)', color: 'var(--color-success-700)' }}
                >
                  Your number
                </span>
              </div>

              <div className="p-3.5 flex flex-col gap-2.5" style={{ background: 'var(--color-surface-0)' }}>
                <div
                  className="text-[12px] px-2.5 py-1.5 rounded-lg leading-snug max-w-[85%]"
                  style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-1)' }}
                >
                  Have a buyer looking for a 4 bedroom villa - have anything I can show him?
                </div>
                <div className="self-end max-w-[88%]">
                  <div
                    className="text-[9px] uppercase tracking-widest font-bold mb-1 text-right"
                    style={{ color: 'var(--color-brand-500)' }}
                  >
                    Dalya draft
                  </div>
                  <div
                    className="text-[12px] px-2.5 py-1.5 rounded-lg leading-snug"
                    style={{
                      background: 'var(--color-brand-50)',
                      color: 'var(--color-text-1)',
                      border: '1px solid var(--color-brand-100)',
                    }}
                  >
                    I have one in Dubai Hills and two in Arabian Ranches. Which area does he prefer?
                  </div>
                </div>
              </div>

              <div
                className="px-3.5 py-2.5 flex items-center gap-2 border-t"
                style={{
                  background: 'var(--color-surface-1)',
                  borderColor: 'var(--color-border-hairline)',
                }}
                aria-hidden="true"
              >
                <span className="flex-1 text-[11px]" style={{ color: 'var(--color-text-3)' }}>
                  Edit, or send as-is…
                </span>
                <span className="btn-brand text-xs rounded-full px-4 py-1.5">Send</span>
              </div>
            </div>
          </div>

          {/* Copy */}
          <div className="order-1 lg:order-2">
            <div className="t-eyebrow mb-2.5">Works on your number</div>
            <h2 className="t-section mb-5">Keep your WhatsApp. Keep your contacts.</h2>
            <div
              className="text-[17px] leading-relaxed flex flex-col gap-4"
              style={{ color: 'var(--color-text-2)' }}
            >
              <p>
                Link your existing WhatsApp number, conversations, and contacts. Nothing moves.
                Your buyers and other agents keep messaging the number they already have.
              </p>
              <p>
                Dalya watches every incoming message, prepares a ready-to-send draft grounded in
                the listing, and surfaces it the moment it lands.
              </p>
              <p>
                <strong style={{ color: 'var(--color-text-1)' }}>One tap to send</strong> — straight
                through the WhatsApp app, in your voice, from your number.
              </p>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}

/* ════════════════════════════════════════════════════════════════════
 * CLOSING CTA
 * ════════════════════════════════════════════════════════════════════ */

export function ClosingCTA() {
  return (
    <section className="section-rule relative overflow-hidden">
      <div aria-hidden className="dot-grid absolute inset-0" style={{ zIndex: 0 }} />
      <div className="relative text-center max-w-[720px] mx-auto px-6 py-24" style={{ zIndex: 1 }}>
        <div className="t-eyebrow mb-4">See it on your listings</div>
        <h2 className="t-section mb-4">Put Dalya to work on your listings.</h2>
        <p className="t-large mb-6 max-w-[540px] mx-auto">
          Bring your listings and your toughest buyer conversations. We&apos;ll show you the
          working surface your agents wake up to — and how much of the day it handles before
          they arrive.
        </p>
        <Link
          href="/contact"
          className="btn-brand rounded-lg px-5 py-2.5 text-sm"
        >
          Book a demo
        </Link>
      </div>
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
