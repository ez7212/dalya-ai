'use client'

import { useState } from 'react'
import Link from 'next/link'

const TIMELINE = [
  {
    label: 'Step 1',
    title: 'You reach out',
    body: 'Tell us about your brokerage and where your agents lose the most time. We reply within two working days.',
  },
  {
    label: 'Step 2',
    title: 'A demo on your listings',
    body: 'A thirty-minute walkthrough on your own listings and a real WhatsApp thread, so you see exactly what your agents would wake up to.',
  },
  {
    label: 'Step 3',
    title: 'Setup',
    body: 'We connect your active listings, documents, and WhatsApp inquiry surface, and brief your agents on the working surface.',
  },
  {
    label: 'Step 4',
    title: 'Live with your team',
    body: 'Your agents run their day on Dalya — hot list, escalations, follow-ups, and viewings — with us close by as you roll it out across the team.',
  },
]

const GOOD_FIT = [
  'You operate a Dubai real estate brokerage or sales team.',
  'You have active listings and WhatsApp inquiry flow.',
  'Your agents will use the product day to day.',
]

type Status = 'idle' | 'sending' | 'ok' | 'error'

export function ContactClient() {
  const [brokerage, setBrokerage] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [notes, setNotes] = useState('')
  const [company, setCompany] = useState('') // honeypot — must stay empty
  const [status, setStatus] = useState<Status>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (status === 'sending' || status === 'ok') return
    setStatus('sending')
    setErrorMsg('')
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, brokerage, notes, company }),
      })
      if (!res.ok) {
        const data = (await res.json().catch(() => ({}))) as { error?: string }
        setErrorMsg(data.error || 'Something went wrong. Please try again.')
        setStatus('error')
        return
      }
      setStatus('ok')
    } catch {
      setErrorMsg('Network error — please try again, or email us directly.')
      setStatus('error')
    }
  }

  return (
    <>
      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 pt-20 pb-10 lg:pt-28 lg:pb-14">
        <div className="t-eyebrow mb-4">Book a demo</div>
        <h1 className="t-display max-w-[820px] mb-5">
          See Dalya run a day of buyer work on your listings.
        </h1>
        <p className="t-large max-w-[720px]">
          Tell us about your brokerage and we&apos;ll show you the working surface your agents
          wake up to — the hot list, the escalations, and the follow-ups already drafted before
          anyone arrives.
        </p>
      </section>

      {/* ── FORM + SIDEBAR ─────────────────────────────────── */}
      <section className="max-w-[1180px] mx-auto px-6 lg:px-8 pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_0.95fr] gap-6">
          {/* Form column */}
          <form
            onSubmit={handleSubmit}
            className="relative rounded-xl p-6 lg:p-8 shadow-card-sm"
            style={{
              background: 'var(--color-surface-0)',
              border: '1px solid var(--color-border-hairline)',
            }}
          >
            <div className="t-eyebrow mb-2">Demo request</div>
            <h2
              className="text-xl font-semibold mb-6"
              style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
            >
              Tell us about your brokerage.
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <Field label="Your name" required>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your Name"
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

            <div className="mb-4">
              <Field label="Brokerage name" required>
                <input
                  type="text"
                  required
                  value={brokerage}
                  onChange={(e) => setBrokerage(e.target.value)}
                  placeholder="Your brokerage's name"
                  className="input"
                />
              </Field>
            </div>

            <div className="mb-6">
              <Field label="Anything else (optional)">
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  placeholder="The workflow you most want to fix, your team size, or anything unusual about your book."
                  className="input"
                />
              </Field>
            </div>

            {/* Honeypot — hidden from people, catches bots. */}
            <div aria-hidden="true" className="absolute -left-[9999px] top-auto h-0 w-0 overflow-hidden">
              <label>
                Company
                <input
                  type="text"
                  tabIndex={-1}
                  autoComplete="off"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                />
              </label>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <button
                type="submit"
                disabled={status === 'sending' || status === 'ok'}
                className="btn-brand rounded-lg px-5 py-2.5 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {status === 'sending' ? 'Sending…' : status === 'ok' ? 'Sent ✓' : 'Book a demo'}
              </button>
              <span className="text-[12px]" style={{ color: 'var(--color-text-3)' }}>
                We respond within two working days.
              </span>
            </div>

            {status === 'ok' && (
              <div
                className="mt-4 flex items-start gap-2 rounded-lg px-3.5 py-3 text-[13px] leading-snug"
                style={{ background: 'var(--color-success-100)', color: 'var(--color-success-700)' }}
                role="status"
                aria-live="polite"
              >
                <span className="font-bold mt-px">✓</span>
                <span>
                  Thanks — your request is in. We&apos;ll reply within two working days.
                </span>
              </div>
            )}

            {status === 'error' && (
              <div
                className="mt-4 flex items-start gap-2 rounded-lg px-3.5 py-3 text-[13px] leading-snug"
                style={{ background: 'var(--color-error-100)', color: 'var(--color-error-700)' }}
                role="alert"
                aria-live="assertive"
              >
                <span className="font-bold mt-px">!</span>
                <span>
                  {errorMsg} You can also email us at{' '}
                  <a href="mailto:eric@dalya.ae" className="underline">eric@dalya.ae</a>.
                </span>
              </div>
            )}
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
                background: 'var(--color-surface-0)',
                border: '1px solid var(--color-border-hairline)',
              }}
            >
              <div className="t-eyebrow mb-2">Pricing</div>
              <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
                Pricing scales with your team. We&apos;ll walk through it on the demo, once
                you&apos;ve seen what Dalya does for your agents day to day.
              </p>
            </div>
          </aside>
        </div>
      </section>

      {/* ── TIMELINE ────────────────────────────────────────── */}
      <section style={{ background: 'var(--color-surface-1)' }}>
        <div className="max-w-[1180px] mx-auto px-6 lg:px-8 py-20">
          <div className="t-eyebrow mb-2.5">What happens after you reach out</div>
          <h2 className="t-section mb-3 max-w-[720px]">From first message to live in four steps.</h2>
          <p className="t-large max-w-[660px] mb-10">
            No procurement theatre, no slide deck cadence. You see Dalya on your own listings
            first, then decide.
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
              Send the same details directly. We treat an email and the form the same.
            </p>
          </div>
          <Link
            href="mailto:eric@dalya.ae?subject=Dalya%20demo%20request"
            className="btn-outline rounded-lg px-5 py-2.5 text-sm whitespace-nowrap"
          >
            eric@dalya.ae
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
