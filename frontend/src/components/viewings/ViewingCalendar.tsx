'use client'

import Link from 'next/link'
import { useAuth } from '@/components/providers/AuthProvider'
import { useAgentViewings } from '@/lib/queries'

export function ViewingCalendar() {
  const { loading: authLoading } = useAuth()
  const { data, isLoading, error } = useAgentViewings(!authLoading)
  const viewings = data?.viewings || []

  return (
    <div className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Viewing Logistics</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-900">Viewing calendar</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-neutral-600">
              Proposed and confirmed appointments with access, tenant notice, calendar, and brief status in one queue.
            </p>
          </div>
          <Link href="/agent" className="inline-flex min-h-11 items-center justify-center rounded-md border border-neutral-300 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100">
            Back to dashboard
          </Link>
        </header>

        {isLoading || authLoading ? (
          <LoadingRows />
        ) : error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error.message}</p>
        ) : viewings.length === 0 ? (
          <section className="rounded-lg border border-neutral-200 bg-white p-6 shadow-card-sm">
            <p className="text-sm text-neutral-600">No viewings yet. Viewings proposed from buyer conversations will appear here.</p>
          </section>
        ) : (
          <div className="grid gap-3">
            {viewings.map((viewing) => (
              <Link
                key={viewing.viewing_id}
                href={`/agent/viewings/${viewing.viewing_id}`}
                className="grid gap-4 rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm transition-colors hover:border-brand-200 hover:bg-brand-50/40 md:grid-cols-[120px_minmax(0,1fr)_220px]"
              >
                <div>
                  <p className="font-mono text-sm font-semibold text-neutral-900">{formatTime(viewing.scheduled_for)}</p>
                  <p className="mt-1 text-xs text-neutral-500">{formatDate(viewing.scheduled_for)}</p>
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold text-neutral-900">{viewing.buyer_name || viewing.buyer_phone}</h2>
                    <StatusPill value={viewing.status} />
                    {viewing.tenant_notice_required && <StatusPill value="tenant notice" tone="warning" />}
                  </div>
                  <p className="mt-1 text-sm text-neutral-700">
                    {viewing.listing.project || 'Listing'}{viewing.listing.unit_number ? ` · Unit ${viewing.listing.unit_number}` : ''}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-neutral-600">{summaryLine(viewing.logistics_summary)}</p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <MiniStatus label="Buyer" value={viewing.confirmation_status?.buyer || 'draft'} />
                  <MiniStatus label="Tenant" value={viewing.confirmation_status?.tenant || (viewing.tenant_notice_required ? 'draft' : 'n/a')} />
                  <MiniStatus label="Calendar" value={viewing.confirmation_status?.calendar || 'pending'} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function LoadingRows() {
  return (
    <div className="grid gap-3">
      {[0, 1, 2].map((item) => (
        <div key={item} className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
          <div className="h-4 w-40 animate-pulse rounded bg-neutral-200" />
          <div className="mt-3 h-3 w-2/3 animate-pulse rounded bg-neutral-100" />
        </div>
      ))}
    </div>
  )
}

function StatusPill({ value, tone = 'default' }: { value: string; tone?: 'default' | 'warning' }) {
  return (
    <span className={`rounded px-2 py-1 text-[11px] font-medium ${tone === 'warning' ? 'bg-warning-50 text-warning-700' : 'bg-neutral-100 text-neutral-600'}`}>
      {value}
    </span>
  )
}

function MiniStatus({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-neutral-200 bg-neutral-50 px-2 py-2">
      <p className="font-semibold uppercase tracking-[0.08em] text-neutral-500">{label}</p>
      <p className="mt-1 truncate font-medium text-neutral-800">{value}</p>
    </div>
  )
}

function formatTime(value?: string | null) {
  if (!value) return 'Proposed'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDate(value?: string | null) {
  if (!value) return 'No time set'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
}

function summaryLine(summary: Record<string, unknown>) {
  if (!summary || !summary.configured) return 'Logistics not configured yet.'
  const access = summary.access_type ? String(summary.access_type) : 'access check'
  const keys = summary.key_location ? `keys: ${summary.key_location}` : 'keys not set'
  const tenant = summary.tenant_status ? `tenant: ${summary.tenant_status}` : 'tenant status unknown'
  return `${access} · ${keys} · ${tenant}`
}
