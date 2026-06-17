'use client'

import { useMemo, useState } from 'react'
import { sharedUi } from '@/lib/shared-ui-tokens'
import { DraftMessageCard } from './DraftMessageCard'

export interface InterestedBuyerMatch {
  id: string
  buyerLabel: string
  matchScore: number
  matchReasons: string[]
  tracedInquiries?: string[]
  outreachDraft: string
  status?: string
}

interface InterestedBuyersPanelProps {
  matches: InterestedBuyerMatch[]
  loading?: boolean
  error?: string | null
  defaultLimit?: number
  onDraftChange?: (matchId: string, draft: string) => void
  onCopyDraft?: (matchId: string, draft: string) => void | Promise<void>
}

export function InterestedBuyersPanel({
  matches,
  loading = false,
  error = null,
  defaultLimit = 5,
  onDraftChange,
  onCopyDraft,
}: InterestedBuyersPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const sorted = useMemo(
    () => [...matches].sort((a, b) => b.matchScore - a.matchScore),
    [matches]
  )
  const visible = expanded ? sorted : sorted.slice(0, defaultLimit)
  const hiddenCount = Math.max(sorted.length - visible.length, 0)

  return (
    <section className={`${sharedUi.panel} p-4 sm:p-5`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={sharedUi.label}>Buyer matching</p>
          <h2 className={`${sharedUi.heading} mt-1`}>Buyers who may be interested</h2>
          <p className={`${sharedUi.muted} mt-1`}>Ranked from same-brokerage buyer preferences and inquiry history.</p>
        </div>
        <span className={`${sharedUi.chip} w-fit`}>{sorted.length} matches</span>
      </div>

      {loading && <p className={`${sharedUi.body} mt-4`}>Checking buyer profiles...</p>}
      {error && <p className="mt-4 rounded border border-error-100 bg-error-50 px-3 py-2 text-sm text-error-700" role="alert">{error}</p>}
      {!loading && !error && sorted.length === 0 && (
        <p className={`${sharedUi.body} mt-4`}>No matching buyers yet. As buyers inquire, they&apos;ll appear here.</p>
      )}

      <div className="mt-4 space-y-4">
        {visible.map((match, index) => (
          <article key={match.id} className={`${sharedUi.inset} p-3 sm:p-4`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-text-1">{match.buyerLabel}</p>
                <p className={`${sharedUi.mono} mt-0.5 text-text-3`}>Rank {index + 1} · score {match.matchScore.toFixed(1)}</p>
              </div>
              {match.status && <span className={sharedUi.chip}>{match.status}</span>}
            </div>
            {match.matchReasons.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {match.matchReasons.map((reason) => (
                  <span key={reason} className={`${sharedUi.chip} border-success-100 bg-success-50 text-success-700`}>{reason}</span>
                ))}
              </div>
            )}
            {match.tracedInquiries && match.tracedInquiries.length > 0 && (
              <p className={`${sharedUi.muted} mt-3`}>Traced to: {match.tracedInquiries.join(', ')}</p>
            )}
            <div className="mt-3">
              <DraftMessageCard
                draft={match.outreachDraft}
                contextLine={`${match.buyerLabel} · ${match.matchReasons[0] || 'matching prior inquiry'}`}
                onDraftChange={(draft) => onDraftChange?.(match.id, draft)}
                onCopy={(draft) => onCopyDraft?.(match.id, draft)}
              />
            </div>
          </article>
        ))}
      </div>

      {hiddenCount > 0 && (
        <button type="button" onClick={() => setExpanded(true)} className={`${sharedUi.secondaryButton} mt-4 w-full sm:w-auto`}>
          Show {hiddenCount} more
        </button>
      )}
      {expanded && sorted.length > defaultLimit && (
        <button type="button" onClick={() => setExpanded(false)} className={`${sharedUi.secondaryButton} mt-4 w-full sm:w-auto`}>
          Show fewer
        </button>
      )}
    </section>
  )
}
