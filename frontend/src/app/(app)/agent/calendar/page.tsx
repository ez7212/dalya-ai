'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '@/lib/api'

interface CalendarConnection {
  provider: string
  status: string
  selected_calendar_ids: string[]
  sync_direction: string
  token_ref?: string | null
  scopes: string[]
  last_sync_at?: string | null
  settings: Record<string, unknown>
}

const inputCls =
  'w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/15'

export default function AgentCalendarPage() {
  const [connection, setConnection] = useState<CalendarConnection | null>(null)
  const [calendarIds, setCalendarIds] = useState('primary')
  const [tokenRef, setTokenRef] = useState('')
  const [redirectUri, setRedirectUri] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const connected = connection?.status === 'connected'
  const lastSync = useMemo(() => {
    if (!connection?.last_sync_at) return 'Never'
    return new Date(connection.last_sync_at).toLocaleString()
  }, [connection?.last_sync_at])

  const loadConnection = async () => {
    setError(null)
    const response = await apiFetch('/api/v1/agent/calendar-connection?provider=google')
    if (!response.ok) throw new Error(await response.text())
    const payload = await response.json()
    setConnection(payload)
    setCalendarIds((payload.selected_calendar_ids || ['primary']).join(', '))
    setTokenRef(payload.token_ref || '')
  }

  useEffect(() => {
    setRedirectUri(`${window.location.origin}/agent/calendar`)
    loadConnection()
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load calendar connection.'))
      .finally(() => setLoading(false))
  }, [])

  const saveConnection = async (event?: FormEvent<HTMLFormElement>, status = 'connected') => {
    event?.preventDefault()
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const selected = calendarIds.split(',').map((item) => item.trim()).filter(Boolean)
      const response = await apiFetch('/api/v1/agent/calendar-connection', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'google',
          status,
          selected_calendar_ids: selected.length ? selected : ['primary'],
          sync_direction: 'read_freebusy_write_viewings',
          token_ref: status === 'connected' ? tokenRef.trim() || null : null,
          scopes: ['calendar.freebusy', 'calendar.events.owned'],
          settings: { timezone: 'Asia/Dubai' },
        }),
      })
      if (!response.ok) throw new Error(await response.text())
      const payload = await response.json()
      setConnection(payload)
      setNotice(status === 'connected' ? 'Calendar connection saved.' : 'Calendar disconnected.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  const startOAuth = async () => {
    setError(null)
    setNotice(null)
    try {
      const response = await apiFetch('/api/v1/agent/calendar-connection/oauth-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'google', redirect_uri: redirectUri }),
      })
      if (!response.ok) throw new Error(await response.text())
      const payload = await response.json()
      window.location.href = payload.authorization_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OAuth setup is not configured.')
    }
  }

  if (loading) {
    return <p className="py-10 text-center text-sm text-neutral-500">Loading calendar...</p>
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">Calendar</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Connect Google Calendar so Dalya avoids busy time and writes viewing events after confirmation.
        </p>
      </header>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-md border border-success-100 bg-success-50 px-4 py-3 text-sm text-success-700" role="status">
          {notice}
        </div>
      )}

      <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-neutral-900">Google Calendar</h2>
            <p className="mt-1 text-sm text-neutral-600">Status, selected calendars, and sync health.</p>
          </div>
          <span className={`inline-flex w-fit items-center rounded-full px-2.5 py-1 text-xs font-medium ${
            connected ? 'bg-success-50 text-success-700' : 'bg-neutral-100 text-neutral-600'
          }`}>
            {connection?.status || 'not_connected'}
          </span>
        </div>

        <dl className="mt-5 grid gap-4 sm:grid-cols-3">
          <Info label="Selected" value={(connection?.selected_calendar_ids || []).join(', ') || 'None'} />
          <Info label="Sync direction" value={connection?.sync_direction || 'read/write'} />
          <Info label="Last sync" value={lastSync} />
        </dl>
      </section>

      <form className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm" onSubmit={(event) => saveConnection(event, 'connected')}>
        <h2 className="text-base font-semibold text-neutral-900">Connection Settings</h2>
        <p className="mt-1 text-sm text-neutral-600">
          Use `env:NAME` or a vault token reference. Raw OAuth tokens are not stored in Dalya.
        </p>

        <div className="mt-5 grid gap-4">
          <label>
            <span className="text-xs font-medium uppercase tracking-wide text-neutral-500">Selected calendar IDs</span>
            <input
              className={`${inputCls} mt-1`}
              value={calendarIds}
              onChange={(event) => setCalendarIds(event.target.value)}
              placeholder="primary, work-calendar-id"
            />
          </label>
          <label>
            <span className="text-xs font-medium uppercase tracking-wide text-neutral-500">Token reference</span>
            <input
              className={`${inputCls} mt-1 font-mono`}
              value={tokenRef}
              onChange={(event) => setTokenRef(event.target.value)}
              placeholder="env:GOOGLE_CALENDAR_ACCESS_TOKEN"
            />
          </label>
          <label>
            <span className="text-xs font-medium uppercase tracking-wide text-neutral-500">OAuth redirect URI</span>
            <input
              className={`${inputCls} mt-1 font-mono`}
              value={redirectUri}
              onChange={(event) => setRedirectUri(event.target.value)}
            />
          </label>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-brand-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">save</span>
            {saving ? 'Saving...' : 'Save connection'}
          </button>
          <button
            type="button"
            onClick={startOAuth}
            className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">login</span>
            Connect with Google
          </button>
          <button
            type="button"
            onClick={() => saveConnection(undefined, 'not_connected')}
            className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">link_off</span>
            Disconnect
          </button>
        </div>
      </form>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">{label}</dt>
      <dd className="mt-1 break-words text-sm text-neutral-900">{value}</dd>
    </div>
  )
}
