'use client'

import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { useAuth } from '@/components/providers/AuthProvider'
import { useSellerActivity } from '@/lib/queries'
import type { ActivityEvent } from '@/lib/queries'

type ActivityKind = ActivityEvent['type']

const FILTERS: { key: 'all' | ActivityKind; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'inquiry', label: 'Conversations' },
  { key: 'offer', label: 'Offers' },
  { key: 'milestone', label: 'Status Changes' },
]

const KIND_ICON: Record<ActivityKind, string> = {
  inquiry: 'chat',
  offer: 'handshake',
  milestone: 'sync',
  escalation: 'priority_high',
}

const KIND_ICON_COLOR: Record<ActivityKind, string> = {
  inquiry: 'text-gold',
  offer: 'text-sage',
  milestone: 'text-n-500',
  escalation: 'text-gold',
}

function formatRelativeTime(iso: string): string {
  const now = Date.now()
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const diff = now - then
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function ActivityPage() {
  const { user, loading: authLoading } = useAuth()
  const { data, isLoading, error } = useSellerActivity(!authLoading && !!user)
  const [filter, setFilter] = useState<'all' | ActivityKind>('all')

  const events = data?.events ?? []

  const filtered = useMemo(() => {
    if (filter === 'all') return events
    if (filter === 'milestone') {
      return events.filter((e) => e.type === 'milestone' || e.type === 'escalation')
    }
    return events.filter((e) => e.type === filter)
  }, [events, filter])

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <h1 className="editorial text-3xl md:text-4xl font-bold text-sand tracking-tight">
          Activity
        </h1>
        <p className="text-n-500 text-sm mt-2 mb-8">
          Conversations, offers, and status updates across your listings
        </p>

        {/* Filter chips */}
        <div
          className="flex flex-wrap items-center gap-2 mb-8"
          role="tablist"
          aria-label="Filter activity"
        >
          {FILTERS.map((f) => {
            const active = filter === f.key
            return (
              <button
                key={f.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setFilter(f.key)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium tracking-wide transition-colors border ${
                  active
                    ? 'border-gold/30 bg-gold/10 text-gold'
                    : 'border-gold/10 bg-deep text-n-500 hover:border-gold/20 hover:text-sand'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>

        {/* Feed content */}
        {isLoading || authLoading ? (
          <div className="text-center py-20">
            <p className="text-n-500 text-sm">Loading activity...</p>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm" role="alert">{error.message}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 max-w-md mx-auto">
            <span
              className="material-symbols-outlined text-gold/30 block mb-4"
              style={{ fontSize: '48px' }}
              aria-hidden="true"
            >
              notifications_active
            </span>
            <p className="text-sand text-base font-semibold mb-2">No activity yet</p>
            <p className="text-n-500 text-sm leading-relaxed">
              Once buyers start engaging with your listings, their inquiries and offers will
              appear here.
            </p>
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {filtered.map((event, i) => (
              <motion.li
                key={`${event.listing_id}-${event.type}-${event.timestamp}-${i}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: Math.min(i * 0.03, 0.3) }}
              >
                <Link
                  href={`/dashboard/listings/${event.listing_id}`}
                  className="block"
                >
                  <div className="surface-1 rounded-xl p-4 sm:p-5 ghost-border flex items-start gap-4 hover:border-gold/25 transition-colors">
                    <span
                      className={`material-symbols-outlined mt-0.5 shrink-0 ${KIND_ICON_COLOR[event.type]}`}
                      aria-hidden="true"
                      style={{ fontSize: '22px' }}
                    >
                      {KIND_ICON[event.type]}
                    </span>

                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] text-n-500 uppercase tracking-widest mb-1">
                        {event.listing_name}
                      </p>
                      <p className="text-sand text-sm font-medium truncate">
                        {event.description}
                      </p>
                      <p className="text-n-500 text-xs mt-1 font-mono">
                        {formatRelativeTime(event.timestamp)}
                      </p>
                    </div>
                  </div>
                </Link>
              </motion.li>
            ))}
          </ul>
        )}
      </motion.div>
    </div>
  )
}
