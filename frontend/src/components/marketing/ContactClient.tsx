'use client'

import { useState } from 'react'
import Link from 'next/link'

type Focus =
  | 'Buyer response speed'
  | 'Viewing coordination'
  | 'Listing acquisition'
  | 'Follow-up discipline'
  | 'All of the above'

const FOCUS_OPTIONS: Focus[] = [
  'Buyer response speed',
  'Viewing coordination',
  'Listing acquisition',
  'Follow-up discipline',
  'All of the above',
]

const TIMELINE = [
  {
    label: 'Week 0',
    title: 'Application review',
    body: 'We read your application within two working days. If we are a fit, we schedule a thirty-minute call with you and one of your senior agents.',
  },
  {
    label: 'Week 1',
    title: 'Listing and workflow setup',
    body: 'Active listings, documents, and your WhatsApp inquiry surface are connected. We brief your agents on what the working surface does and does not do.',
  },
  {
    label: 'Week 2 – 8',
    title: 'Live partnership',
    body: 'Your team uses the product daily. We sit weekly with your owners and top agents. Every gap goes into the build queue. Every win is measured.',
  },
  {
    label: 'Week 9',
    title: 'Operating review and pricing',
    body: 'We compare the operating baseline against the pilot scorecard, then negotiate pricing if your team wants to keep the platform.',
  },
]

const GOOD_FIT = [
  'You operate a Dubai real estate brokerage or sales team.',
  'You have active listings and WhatsApp inquiry flow.',
  'Your agents will use the product during the pilot.',
  'You can give weekly feedback on what is sharper or slower.',
]

const NOT_A_FIT = [
  'Pure investor introducer with no active brokerage book.',
  'Looking for a lead-generation channel rather than a working surface.',
  'Cannot commit an owner or team lead to a weekly review call.',
]

export function ContactClient() {
  const [brokerage, setBrokerage] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [teamSize, setTeamSize] = useState('')
  const [listings, setListings] = useState('')
  const [focus, setFocus] = useState<Focus>('All of the above')
  const [notes, setNotes] = useState('')

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const subject = `Dalya design partnership: ${brokerage || 'application'}`
    const body = [
      `Brokerage: ${brokerage}`,
      `Contact: ${name}${role ? ' · ' + role : ''}`,
      `Email: ${email}`,
      phone ? `Phone: ${phone}` : null,
      `Team size: ${teamSize}`,
      `Active listings: ${listings}`,
      `Primary focus: ${focus}`,
      notes ? `\nNotes:\n${notes}` : null,
    ]
      .filter(Boolean)
      .join('\n')
    const url = `mailto:hello@dalya.ai?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    window.location.href = url
  }

  return (
    <>
      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 pt-20 pb-10 lg:pt-28 lg:pb-14">
        <div className="t-eyebrow mb-4">Design partnership</div>
        <h1 className="t-display max-w-[820px] mb-5">
          Run Dalya with your brokerage for 60 days.
        </h1>
        <p className="t-large max-w-[720px]">
          We are taking a small number of Dubai brokerages through hands-on pilots.
          Pricing waits until the product is used daily and the operating metrics are clear.
        </p>
      </section>

      {/* ── FORM + SIDEBAR ─────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_0.95fr] gap-6">
          {/* Form column */}
          <form
            onSubmit={handleSubmit}
            className="rounded-xl p-6 lg:p-8 shadow-card-sm"
            style={{
              background: 'var(--color-surface-0)',
              border: '1px solid var(--color-border-hairline)',
            }}
          >
            <div className="t-eyebrow mb-2">Application</div>
            <h2
              className="text-xl font-semibold mb-6"
              style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
            >
              Tell us about your brokerage.
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <Field label="Brokerage name" required>
                <input
                  type="text"
                  required
                  value={brokerage}
                  onChange={(e) => setBrokerage(e.target.value)}
                  placeholder="Mahoroba Realty"
                  className="input"
                />
              </Field>
              <Field label="Your name" required>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Luqman Al-Mansouri"
                  className="input"
                />
              </Field>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <Field label="Your role">
                <input
                  type="text"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="Owner · Team lead · Senior broker"
                  className="input"
                />
              </Field>
              <Field label="Work email" required>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@brokerage.ae"
                  className="input"
                />
              </Field>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <Field label="WhatsApp">
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+971 50 ..."
                  className="input"
                />
              </Field>
              <Field label="Team size">
                <input
                  type="text"
                  value={teamSize}
                  onChange={(e) => setTeamSize(e.target.value)}
                  placeholder="12 agents"
                  className="input"
                />
              </Field>
              <Field label="Active listings">
                <input
                  type="text"
                  value={listings}
                  onChange={(e) => setListings(e.target.value)}
                  placeholder="80 secondary · 40 off-plan"
                  className="input"
                />
              </Field>
            </div>

            <Field label="Primary focus during the pilot">
              <div className="flex flex-wrap gap-2 mt-1">
                {FOCUS_OPTIONS.map((opt) => {
                  const active = focus === opt
                  return (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setFocus(opt)}
                      className="text-[12px] font-medium rounded-md px-3 py-1.5 transition-colors"
                      style={{
                        background: active ? 'var(--color-brand-500)' : 'var(--color-surface-1)',
                        color: active ? 'white' : 'var(--color-text-2)',
                        border: `1px solid ${active ? 'var(--color-brand-500)' : 'var(--color-border-hairline)'}`,
                      }}
                    >
                      {opt}
                    </button>
                  )
                })}
              </div>
            </Field>

            <div className="mt-4 mb-6">
              <Field label="Anything else">
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  placeholder="The workflow you most want to fix. Anything unusual about your book. Your timeline."
                  className="input"
                />
              </Field>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <button
                type="submit"
                className="btn-brand rounded-lg px-5 py-2.5 text-sm"
              >
                Submit application
              </button>
              <span className="text-[12px]" style={{ color: 'var(--color-text-3)' }}>
                We respond within two working days.
              </span>
            </div>
          </form>

          {/* Sidebar */}
          <aside className="flex flex-col gap-4">
            <div
              className="rounded-xl p-5"
              style={{
                background: 'var(--color-surface-1)',
                border: '1px solid var(--color-border-hairline)',
              }}
            >
              <div className="t-eyebrow mb-3">Good fit</div>
              <ul className="flex flex-col gap-2.5">
                {GOOD_FIT.map((item) => (
                  <li key={item} className="flex gap-2 text-[13px] leading-snug" style={{ color: 'var(--color-text-2)' }}>
                    <span
                      className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: 'var(--color-success-500)' }}
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div
              className="rounded-xl p-5"
              style={{
                background: 'var(--color-surface-1)',
                border: '1px solid var(--color-border-hairline)',
              }}
            >
              <div className="t-eyebrow mb-3">Not a fit yet</div>
              <ul className="flex flex-col gap-2.5">
                {NOT_A_FIT.map((item) => (
                  <li key={item} className="flex gap-2 text-[13px] leading-snug" style={{ color: 'var(--color-text-2)' }}>
                    <span
                      className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: 'var(--color-warning-500)' }}
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div
              className="rounded-xl p-5"
              style={{
                background: 'var(--color-surface-0)',
                border: '1px solid var(--color-border-hairline)',
              }}
            >
              <div className="t-eyebrow mb-2">Pricing</div>
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                We do not charge during the design partnership. Pricing is negotiated once your
                agents use it daily and the operating picture is clearer. The only thing we
                optimise for is whether your team wants to keep it.
              </p>
            </div>
          </aside>
        </div>
      </section>

      {/* ── TIMELINE ────────────────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1180px] mx-auto px-6 lg:px-8 py-20">
          <div className="t-eyebrow mb-2.5">What happens after you apply</div>
          <h2 className="t-section mb-3 max-w-[720px]">A clear sixty-day arc.</h2>
          <p className="t-large max-w-[660px] mb-10">
            No procurement theatre, no slide deck cadence. The pilot is structured so we know
            within nine weeks whether the agent day got sharper.
          </p>

          <ol
            className="relative grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px overflow-hidden rounded-xl border"
            style={{
              background: 'var(--color-border-hairline)',
              borderColor: 'var(--color-border-hairline)',
            }}
          >
            {TIMELINE.map((step, i) => (
              <li
                key={step.label}
                className="px-6 py-7 flex flex-col gap-3"
                style={{ background: 'var(--color-surface-0)' }}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="text-[11px] uppercase tracking-widest font-bold"
                    style={{ color: 'var(--color-brand-500)' }}
                  >
                    {step.label}
                  </span>
                  <span
                    className="text-[10px] tabular-aed font-medium px-1.5 py-0.5 rounded"
                    style={{
                      background: 'var(--color-surface-1)',
                      color: 'var(--color-text-3)',
                    }}
                  >
                    {String(i + 1).padStart(2, '0')} / 04
                  </span>
                </div>
                <h3
                  className="text-base font-semibold leading-snug"
                  style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
                >
                  {step.title}
                </h3>
                <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── FALLBACK / DIRECT EMAIL ─────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 py-16">
        <div
          className="rounded-xl p-6 lg:p-8 flex flex-col md:flex-row md:items-center md:justify-between gap-5"
          style={{
            background: 'var(--color-surface-1)',
            border: '1px solid var(--color-border-hairline)',
          }}
        >
          <div className="max-w-[640px]">
            <div className="t-eyebrow mb-2">Prefer email</div>
            <p className="text-[15px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
              Send the same details directly. We treat the inbox application and the form
              application the same.
            </p>
          </div>
          <Link
            href="mailto:hello@dalya.ai?subject=Dalya%20design%20partnership"
            className="btn-outline rounded-lg px-5 py-2.5 text-sm whitespace-nowrap"
          >
            hello@dalya.ai
          </Link>
        </div>
      </section>
    </>
  )
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className="text-[11px] uppercase tracking-widest font-semibold"
        style={{ color: 'var(--color-text-3)' }}
      >
        {label}
        {required && (
          <span style={{ color: 'var(--color-brand-500)' }} className="ml-1">
            *
          </span>
        )}
      </span>
      {children}
    </label>
  )
}
