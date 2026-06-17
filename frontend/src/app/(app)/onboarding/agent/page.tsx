'use client'

import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'

interface OnboardingState {
  has_profile: boolean
  member_status: string | null
  can_access_agent_workspace: boolean
  brokerage: { name: string } | null
  profile: {
    display_name: string
    verification_status: string
    onboarding_status: string
  } | null
}

interface BrokerageLookup {
  brokerage_id: string
  name: string
  slug: string
  real_estate_number?: string
}

interface ReraAgentLookup {
  card_number: string
  full_name_en: string | null
  full_name_ar: string | null
  card_expiry_date: string | null
  mobile: string | null
  email: string | null
  license_number: string | null
  real_estate_number: string | null
  office_name_en: string | null
  office_name_ar: string | null
  office_expiry_date: string | null
  card_holder_photo: string | null
  office_logo: string | null
  office_rank: string | null
  card_rank: string | null
}

const inputCls =
  'w-full rounded-md border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-800 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

export default function AgentOnboardingPage() {
  const [status, setStatus] = useState<OnboardingState | null>(null)
  const [brokerage, setBrokerage] = useState<BrokerageLookup | null>(null)
  const [reraLookup, setReraLookup] = useState<ReraAgentLookup | null>(null)
  const [fullName, setFullName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [whatsappPhone, setWhatsappPhone] = useState('')
  const [reraNumber, setReraNumber] = useState('')
  const [reraExpiry, setReraExpiry] = useState('')
  const [languages, setLanguages] = useState<string[]>(['English'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    apiFetch('/api/v1/onboarding/me')
      .then(async (res) => {
        if (!res.ok) return null
        return res.json()
      })
      .then((body) => {
        if (!body) return
        setStatus(body)
        if (body.profile) {
          setFullName(body.profile.display_name)
          setDisplayName(body.profile.display_name)
        }
      })
      .catch(() => undefined)
  }, [])

  async function lookupReraCard() {
    setError(null)
    setSuccess(null)
    setReraLookup(null)
    if (!reraNumber.trim()) {
      setError('Enter your RERA broker card number.')
      return
    }
    setLoading(true)
    try {
      const res = await apiFetch('/api/v1/onboarding/rera-brokerage-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rera_broker_card_number: reraNumber }),
      })
      const body = await res.json().catch(() => null)
      if (!res.ok) throw new Error(body?.detail ?? 'Could not find RERA card')
      const agent = body.agent as ReraAgentLookup
      setBrokerage(body.brokerage)
      setReraLookup(agent)
      setFullName(agent.full_name_en ?? '')
      setDisplayName(formatDisplayName(agent.full_name_en ?? ''))
      setWhatsappPhone(agent.mobile ?? '')
      setReraExpiry((agent.card_expiry_date ?? '').slice(0, 10))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not find RERA card')
    } finally {
      setLoading(false)
    }
  }

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)
    try {
      const res = await apiFetch('/api/v1/onboarding/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName,
          display_name: displayName || fullName,
          whatsapp_phone: whatsappPhone,
          rera_broker_card_number: reraNumber,
          rera_card_expiry: reraExpiry || null,
          languages,
          service_areas: [],
          rera_lookup_payload: reraLookup ?? {},
        }),
      })
      const body = await res.json().catch(() => null)
      if (!res.ok) throw new Error(body?.detail ?? 'Could not submit profile')
      setSuccess(body?.message ?? 'Agent profile active.')
      const refreshed = await apiFetch('/api/v1/onboarding/me')
      if (refreshed.ok) setStatus(await refreshed.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-700">
      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:px-8">
        <section className="rounded-lg border border-neutral-200 bg-white p-5 sm:p-6">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
            Agent onboarding
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-800">
            Join your brokerage workspace
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-neutral-600">
            Enter your RERA broker card number. Dalya checks your registered brokerage
            from DLD records and only continues if that brokerage is active on Dalya.
          </p>

          {status?.has_profile && (
            <div className="mt-5 rounded-md border border-warning-500/30 bg-warning-50 p-4">
              <p className="text-sm font-semibold text-warning-700">
                Profile active
              </p>
              <p className="mt-1 text-sm text-neutral-700">
                {status.brokerage?.name} has your profile as <span className="font-medium">{status.member_status}</span>.
                Your agent Property Advisor handoff is configured for this brokerage.
              </p>
              {status.can_access_agent_workspace && (
                <Link
                  href="/agent"
                  className="mt-3 inline-flex rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  Open agent workspace
                </Link>
              )}
            </div>
          )}

          <div className="mt-6 rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <label htmlFor="rera-card" className="block text-sm font-medium text-neutral-800">
              RERA broker card number
            </label>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                id="rera-card"
                className={inputCls}
                value={reraNumber}
                onChange={(event) => setReraNumber(event.target.value)}
                placeholder="Example: 92913"
              />
              <button
                type="button"
                onClick={lookupReraCard}
                disabled={loading}
                className="shrink-0 rounded-md border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-800 hover:bg-white disabled:opacity-50"
              >
                Look up RERA card
              </button>
            </div>
            {reraLookup && (
              <div className="mt-3 flex gap-3 rounded-md border border-success-500/30 bg-success-50 p-3">
                {reraLookup.card_holder_photo && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={reraLookup.card_holder_photo}
                    alt=""
                    className="h-14 w-14 rounded-md object-cover"
                  />
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-success-700">
                    {reraLookup.full_name_en}
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-neutral-700">
                    {reraLookup.office_name_en} · Card {reraLookup.card_number}
                  </p>
                  {brokerage && (
                    <p className="mt-0.5 text-xs leading-relaxed text-success-700">
                      Registered brokerage matched: {brokerage.name}
                      {brokerage.real_estate_number ? ` (${brokerage.real_estate_number})` : ''}
                    </p>
                  )}
                  <p className="mt-0.5 text-xs text-neutral-500">
                    Expires {(reraLookup.card_expiry_date ?? '').slice(0, 10) || 'not returned'}
                  </p>
                </div>
              </div>
            )}
          </div>

          <form onSubmit={submitProfile} className="mt-6 grid gap-4 sm:grid-cols-2">
            <Field label="Full legal name" value={fullName} setValue={setFullName} required />
            <Field label="Display name" value={displayName} setValue={setDisplayName} placeholder="Shown in agent handoff" />
            <Field label="WhatsApp phone number" value={whatsappPhone} setValue={setWhatsappPhone} required placeholder="+971..." />
            <Field label="RERA card expiry" value={reraExpiry} setValue={setReraExpiry} type="date" />
            <div className="sm:col-span-2">
              <LanguageSelect selected={languages} setSelected={setLanguages} />
            </div>

            {error && (
              <p className="sm:col-span-2 rounded-md border border-error-500/30 bg-error-50 p-3 text-sm text-error-700">
                {error}
              </p>
            )}
            {success && (
              <p className="sm:col-span-2 rounded-md border border-success-500/30 bg-success-50 p-3 text-sm text-success-700">
                {success}
              </p>
            )}

            <div className="sm:col-span-2 flex flex-col gap-3 sm:flex-row sm:items-center">
              <button
                type="submit"
                disabled={loading}
                className="rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Submit agent profile
              </button>
              <p className="text-xs leading-relaxed text-neutral-500">
                If DLD matches your RERA card to a registered Dalya brokerage, handoff activates immediately.
              </p>
            </div>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">Brokerage not registered?</h2>
            <p className="mt-2 text-sm leading-relaxed text-neutral-600">
              Agents cannot create a brokerage workspace directly during the first rollout.
              Ask the brokerage owner or team lead to contact Dalya.
            </p>
            <Link
              href="/contact"
              className="mt-4 inline-flex rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-50"
            >
              Contact Dalya
            </Link>
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">What this creates</h2>
            <ul className="mt-3 space-y-2 text-sm leading-relaxed text-neutral-600">
              <li>Agent profile under the registered brokerage.</li>
              <li>DLD/RERA card verification record.</li>
              <li>Agent-specific Property Advisor handoff config.</li>
              <li>WhatsApp escalation destination for serious buyer conversations.</li>
              <li>Service areas can be added later from the agent profile.</li>
            </ul>
          </section>
        </aside>
      </main>
    </div>
  )
}

function formatDisplayName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

const LANGUAGE_OPTIONS = [
  'English',
  'Arabic',
  'Hindi',
  'Urdu',
  'Russian',
  'Mandarin',
  'French',
  'Spanish',
  'Persian',
  'Tagalog',
]

function LanguageSelect({
  selected,
  setSelected,
}: {
  selected: string[]
  setSelected: (value: string[]) => void
}) {
  const available = LANGUAGE_OPTIONS.filter((language) => !selected.includes(language))

  function addLanguage(value: string) {
    if (!value || selected.includes(value)) return
    setSelected([...selected, value])
  }

  function removeLanguage(value: string) {
    setSelected(selected.filter((language) => language !== value))
  }

  return (
    <div>
      <label htmlFor="languages" className="block text-sm font-medium text-neutral-800">
        Languages
      </label>
      <div className="mt-2 rounded-md border border-neutral-300 bg-white p-2">
        <div className="flex min-h-9 flex-wrap gap-2">
          {selected.map((language) => (
            <span
              key={language}
              className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-sm font-medium text-brand-700"
            >
              {language}
              <button
                type="button"
                onClick={() => removeLanguage(language)}
                className="rounded-full text-brand-600 hover:text-brand-800"
                aria-label={`Remove ${language}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <select
          id="languages"
          value=""
          onChange={(event) => addLanguage(event.target.value)}
          className="mt-2 w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-800 outline-none focus:border-brand-500"
        >
          <option value="">Add a language</option>
          {available.map((language) => (
            <option key={language} value={language}>
              {language}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  setValue,
  required = false,
  placeholder,
  type = 'text',
}: {
  label: string
  value: string
  setValue: (value: string) => void
  required?: boolean
  placeholder?: string
  type?: string
}) {
  const id = label.toLowerCase().replace(/[^a-z0-9]+/g, '-')
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-neutral-800">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required={required}
        className={`${inputCls} mt-2`}
        value={value}
        placeholder={placeholder}
        onChange={(event) => setValue(event.target.value)}
      />
    </div>
  )
}
