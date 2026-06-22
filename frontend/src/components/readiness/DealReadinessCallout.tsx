import {
  buildDealReadinessDisplay,
  type DealReadinessSummary,
} from './deal-readiness'

export function DealReadinessSummaryLine({
  readiness,
  compact = false,
  missingLimit = 3,
}: {
  readonly readiness?: DealReadinessSummary | null
  readonly compact?: boolean
  readonly missingLimit?: number
}) {
  const display = buildDealReadinessDisplay(readiness, { missingLimit })
  if (!display) return null

  return (
    <div className={`${compact ? 'mt-2 px-2.5 py-1.5' : 'mt-3 px-3 py-2'} rounded-md border border-brand-100 bg-brand-50 text-xs text-brand-900`}>
      <div className={compact ? undefined : 'flex items-start gap-2'}>
        {!compact && (
          <span className="material-symbols-outlined mt-0.5 text-[15px] text-brand-600" aria-hidden="true">fact_check</span>
        )}
        <div className={`min-w-0 ${compact ? '' : 'space-y-1'}`}>
          {display.headline && <p className="font-semibold">{display.headline}</p>}
          {display.action && (
            <p className={compact ? 'mt-0.5' : undefined}>
              <span className="font-medium">Next:</span> {display.action}
            </p>
          )}
          {display.reason && <p className={`${compact ? 'mt-0.5 line-clamp-2' : 'leading-relaxed'} text-brand-800`}>{display.reason}</p>}
          {display.missingFields.length > 0 && (
            <p className={`${compact ? 'mt-0.5' : ''} text-brand-700`}>
              <span className="font-medium">Missing:</span> {display.missingFields.join(', ')}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export function DealReadinessPanel({
  readiness,
}: {
  readonly readiness?: DealReadinessSummary | null
}) {
  const display = buildDealReadinessDisplay(readiness, { missingLimit: 4 })
  if (!display) return null

  return (
    <section className="rounded-lg border border-brand-100 bg-brand-50 p-4 shadow-card-sm">
      <div className="flex items-start gap-2">
        <span className="material-symbols-outlined mt-0.5 text-[18px] text-brand-600" aria-hidden="true">fact_check</span>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-brand-700">Readiness</p>
          {display.headline && <p className="mt-2 text-sm font-semibold text-brand-950">{display.headline}</p>}
          {display.action && (
            <p className="mt-2 text-sm text-brand-900">
              <span className="font-medium">Next:</span> {display.action}
            </p>
          )}
          {display.reason && <p className="mt-2 text-sm leading-relaxed text-brand-800">{display.reason}</p>}
          {display.missingFields.length > 0 && (
            <p className="mt-2 text-xs text-brand-700">
              <span className="font-medium">Missing:</span> {display.missingFields.join(', ')}
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
