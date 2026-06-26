'use client'

import { useState } from 'react'
import type { ReactNode } from 'react'
import { sharedUi, unitProfileLabels } from '@/lib/shared-ui-tokens'
import { InspectionAudioInput, InspectionAudioReady } from './InspectionAudioInput'

export type UnitProfile = Record<string, string[] | string | null | undefined>

export interface UnitProfileHistoryItem {
  timestamp?: string | null
  source?: string | null
  agent_user_id?: string | null
  transcript?: string | null
  provenance?: string | null
}

interface UnitProfileViewProps {
  profile: UnitProfile
  history?: UnitProfileHistoryItem[]
  loading?: boolean
  onAudioReady?: (audio: InspectionAudioReady) => void | Promise<void>
  onEditCategory?: (category: string, values: string[]) => void
  renderTypedFallback?: ReactNode
}

const categoryOrder = [
  'layout',
  'condition',
  'view',
  'building_community_quirks',
  'ac_utilities',
  'parking',
  'neighbor_situation',
  'agent_subjective_notes',
]

export function UnitProfileView({
  profile,
  history = [],
  loading = false,
  onAudioReady,
  onEditCategory,
  renderTypedFallback,
}: UnitProfileViewProps) {
  const [adding, setAdding] = useState(false)
  const rows = categoryOrder.map((key) => ({
    key,
    label: unitProfileLabels[key] || key,
    values: normalizeValues(profile[key]),
  }))
  const hasProfile = rows.some((row) => row.values.length > 0)
  const latest = history[history.length - 1]

  return (
    <section className={`${sharedUi.panel} p-4 sm:p-5`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={sharedUi.label}>Unit profile</p>
          <h2 className={`${sharedUi.heading} mt-1`}>Inspection notes</h2>
          <p className={`${sharedUi.muted} mt-1`}>
            {latest?.timestamp ? `Agent-recorded, ${formatDate(latest.timestamp)}` : 'Agent-recorded listing context appears here.'}
          </p>
        </div>
        {onAudioReady && (
          <button type="button" onClick={() => setAdding((value) => !value)} className={sharedUi.primaryButton}>
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">mic</span>
            {adding ? 'Close notes' : 'Add or update notes'}
          </button>
        )}
      </div>

      {adding && onAudioReady && (
        <div className="mt-4 space-y-3">
          <InspectionAudioInput onAudioReady={onAudioReady} />
          {renderTypedFallback}
        </div>
      )}

      {loading && <p className={`${sharedUi.body} mt-4`}>Loading unit profile...</p>}
      {!loading && !hasProfile && (
        <p className={`${sharedUi.body} mt-4`}>No inspection notes yet. Add a voice note or typed memo to build the unit profile.</p>
      )}

      {hasProfile && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {rows.filter((row) => row.values.length > 0).map((row) => (
            <article key={row.key} className={`${sharedUi.inset} p-3`}>
              <div className="flex items-start justify-between gap-3">
                <p className={sharedUi.label}>{row.label}</p>
                {onEditCategory && (
                  <button type="button" onClick={() => onEditCategory(row.key, row.values)} className="text-xs font-medium text-brand-600 hover:text-brand-700">
                    Edit
                  </button>
                )}
              </div>
              <ul className="mt-2 space-y-1.5">
                {row.values.map((value) => (
                  <li key={value} className="text-sm leading-relaxed text-text-1">{value}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}

      {history.length > 0 && (
        <div className="mt-5 border-t border-neutral-200 pt-4">
          <p className={sharedUi.label}>Audit history</p>
          <ol className="mt-3 space-y-2">
            {history.map((item, index) => (
              <li key={`${item.timestamp || index}-${index}`} className="rounded bg-neutral-50 px-3 py-2">
                <p className="text-sm font-medium text-text-1">
                  {item.provenance || 'Agent-recorded'} · {item.timestamp ? formatDate(item.timestamp) : `Session ${index + 1}`}
                </p>
                {item.transcript && <p className={`${sharedUi.muted} mt-1 line-clamp-2`}>{item.transcript}</p>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}

function normalizeValues(value: string[] | string | null | undefined): string[] {
  if (Array.isArray(value)) return value.filter(Boolean).map(String)
  if (value) return [String(value)]
  return []
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
