'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error' | 'unavailable'

interface PreferencesPayload {
  events: Record<string, boolean>
  quiet_hours: { start: string; end: string }
  catalog?: Record<string, { urgency: string; sends_in_quiet_hours: boolean }>
}

const EVENT_LABELS: Record<string, string> = {
  escalation_alert: 'Escalations',
  lead_first_touch: 'New portal leads',
  hot_buyer_reply: 'Hot buyer replies',
  viewing_buyer_update: 'Buyer viewing updates',
  tenant_confirmation: 'Tenant confirmations',
  viewing_reminder: 'Viewing reminders',
  feedback_received: 'Post-viewing feedback',
  drafts_pending: 'AI drafts pending (digest)',
  buyer_opt_out: 'Buyer opt-outs',
  ai_failure: 'AI failures',
  calendar_error: 'Calendar errors',
  takeover_stale: 'Stale takeovers (digest)',
  hot_list_ready: 'Morning hot list',
}

export function NotificationPreferences() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [prefs, setPrefs] = useState<PreferencesPayload | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'working' | 'saved' | 'error'>('idle')

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const response = await apiFetch('/api/v1/agent/notification-preferences')
        if (!active) return
        if (!response.ok) {
          setLoadState(response.status === 403 || response.status === 404 ? 'unavailable' : 'error')
          return
        }
        setPrefs(await response.json())
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

  async function save(update: { events?: Record<string, boolean>; quiet_hours?: { start: string; end: string } }) {
    setSaveState('working')
    try {
      const response = await apiFetch('/api/v1/agent/notification-preferences', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update),
      })
      if (!response.ok) throw new Error(`Preferences returned ${response.status}`)
      const body = await response.json()
      setPrefs((current) => (current ? { ...current, events: body.events, quiet_hours: body.quiet_hours } : current))
      setSaveState('saved')
    } catch {
      setSaveState('error')
    }
  }

  if (loadState === 'unavailable') return null

  return (
    <section className="mx-auto mt-6 max-w-[760px] rounded-lg border border-neutral-200 bg-white p-5 shadow-card-sm">
      <h2 className="text-sm font-semibold text-neutral-900">WhatsApp notifications</h2>
      <p className="mt-1 text-sm text-neutral-600">
        Time-sensitive events push to your WhatsApp with a link to the right screen. Digest-class events
        ride along with the morning hot list.
      </p>

      {loadState === 'loading' ? (
        <div className="mt-4 h-24 animate-pulse rounded bg-neutral-100" />
      ) : loadState === 'error' || !prefs ? (
        <p className="mt-4 text-sm font-medium text-error-600">Could not load notification preferences.</p>
      ) : (
        <>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {Object.entries(prefs.events).map(([eventType, enabled]) => (
              <label key={eventType} className="flex items-center justify-between gap-3 rounded-md border border-neutral-200 px-3 py-2 text-sm text-neutral-800">
                <span>{EVENT_LABELS[eventType] ?? eventType}</span>
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(event) => save({ events: { [eventType]: event.target.checked } })}
                  className="h-4 w-4 rounded border-neutral-300"
                />
              </label>
            ))}
          </div>

          <div className="mt-5 border-t border-neutral-200 pt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Quiet hours (GST)</p>
            <p className="mt-1 text-xs text-neutral-500">
              Non-urgent pushes queue for the morning digest during quiet hours. Escalations, new leads,
              viewing changes, opt-outs, and AI failures still come through.
            </p>
            <div className="mt-3 flex items-center gap-3 text-sm">
              <input
                type="time"
                value={prefs.quiet_hours.start}
                onChange={(event) => save({ quiet_hours: { ...prefs.quiet_hours, start: event.target.value } })}
                className="rounded-md border border-neutral-300 px-2 py-1.5 text-sm"
              />
              <span className="text-neutral-500">to</span>
              <input
                type="time"
                value={prefs.quiet_hours.end}
                onChange={(event) => save({ quiet_hours: { ...prefs.quiet_hours, end: event.target.value } })}
                className="rounded-md border border-neutral-300 px-2 py-1.5 text-sm"
              />
            </div>
          </div>

          {saveState === 'saved' && <p className="mt-3 text-xs font-medium text-success-700">Saved.</p>}
          {saveState === 'error' && <p className="mt-3 text-xs font-medium text-error-600">Could not save your changes.</p>}
        </>
      )}
    </section>
  )
}
