'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error'

interface AgentProfile {
  display_name: string
  phone: string
  rera_number: string
  email: string
}

const EMPTY: AgentProfile = { display_name: '', phone: '', rera_number: '', email: '' }

const FIELDS: { key: keyof AgentProfile; label: string; type: string; placeholder: string; help?: string }[] = [
  { key: 'display_name', label: 'Display name', type: 'text', placeholder: 'e.g. Ahmed Khan', help: 'Shown to buyers and on listings you manage.' },
  { key: 'phone', label: 'WhatsApp number', type: 'tel', placeholder: '+971 50 123 4567' },
  { key: 'rera_number', label: 'RERA / BRN number', type: 'text', placeholder: 'e.g. 12345', help: 'Your RERA broker registration number.' },
  { key: 'email', label: 'Email', type: 'email', placeholder: 'you@brokerage.com' },
]

export function AgentProfileForm() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [profile, setProfile] = useState<AgentProfile>(EMPTY)
  const [saveState, setSaveState] = useState<'idle' | 'working' | 'saved' | 'error'>('idle')

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const response = await apiFetch('/api/v1/agent/profile')
        if (!active) return
        if (!response.ok) {
          setLoadState('error')
          return
        }
        const body = await response.json()
        setProfile({ ...EMPTY, ...body })
        setLoadState('live')
      } catch {
        if (active) setLoadState('error')
      }
    }
    load()
    return () => {
      active = false
    }
  }, [])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setSaveState('working')
    try {
      const response = await apiFetch('/api/v1/agent/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      })
      if (!response.ok) throw new Error(`Profile returned ${response.status}`)
      const body = await response.json()
      setProfile({ ...EMPTY, ...body })
      setSaveState('saved')
    } catch {
      setSaveState('error')
    }
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-card-sm">
      <h2 className="text-sm font-semibold text-neutral-900">Agent profile</h2>
      <p className="mt-1 text-sm text-neutral-600">
        These details autofill when you add new listings, so you don&apos;t re-enter them each time.
      </p>

      {loadState === 'loading' ? (
        <div className="mt-4 h-40 animate-pulse rounded bg-neutral-100" />
      ) : loadState === 'error' ? (
        <p className="mt-4 text-sm font-medium text-error-600">Could not load your profile.</p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-4 grid gap-4 sm:grid-cols-2">
          {FIELDS.map((field) => (
            <label key={field.key} className="flex flex-col gap-1">
              <span className="text-[13px] font-medium text-neutral-800">{field.label}</span>
              <input
                type={field.type}
                value={profile[field.key]}
                placeholder={field.placeholder}
                onChange={(event) => {
                  setProfile((current) => ({ ...current, [field.key]: event.target.value }))
                  setSaveState('idle')
                }}
                className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              />
              {field.help && <span className="text-xs text-neutral-500">{field.help}</span>}
            </label>
          ))}

          <div className="flex items-center gap-3 sm:col-span-2">
            <button
              type="submit"
              disabled={saveState === 'working'}
              className="btn-brand rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60"
            >
              {saveState === 'working' ? 'Saving…' : 'Save profile'}
            </button>
            {saveState === 'saved' && <span className="text-xs font-medium text-success-700">Saved.</span>}
            {saveState === 'error' && <span className="text-xs font-medium text-error-600">Could not save your changes.</span>}
          </div>
        </form>
      )}
    </section>
  )
}
