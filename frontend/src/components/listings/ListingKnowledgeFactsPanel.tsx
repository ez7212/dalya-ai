import type { FactUpdateInput, ListingFact } from '@/components/listings/ListingKnowledgeTypes'
import { dateLabel, statusLabel } from '@/components/listings/ListingKnowledgeTypes'

type FactsPanelProps = {
  readonly factsByGroup: Record<string, readonly ListingFact[]>
  readonly onUpdate: (input: FactUpdateInput) => void
  readonly working: boolean
}

export function ListingKnowledgeFactsPanel({ factsByGroup, onUpdate, working }: FactsPanelProps) {
  const groups = Object.entries(factsByGroup)
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-neutral-900">Review facts</h2>
        <span className="rounded-sm bg-neutral-100 px-2 py-1 text-[11px] font-medium text-neutral-700">{groups.length} groups</span>
      </div>
      {groups.length === 0 ? (
        <p className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-600">No extracted facts yet.</p>
      ) : (
        <div className="mt-4 space-y-4">
          {groups.map(([group, facts]) => (
            <div key={group} className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
              <h3 className="text-sm font-semibold text-neutral-900">{statusLabel(group)}</h3>
              <div className="mt-3 space-y-3">
                {facts.map((fact) => <FactCard key={fact.fact_id} fact={fact} onUpdate={onUpdate} working={working} />)}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function FactCard({ fact, onUpdate, working }: { readonly fact: ListingFact; readonly onUpdate: (input: FactUpdateInput) => void; readonly working: boolean }) {
  return (
    <article className="rounded-md border border-neutral-200 bg-white p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-neutral-900">{statusLabel(fact.fact_key)}</p>
          <p className="mt-1 text-sm leading-relaxed text-neutral-700">{fact.value_text}</p>
        </div>
        <span className={`w-fit rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${factTone(fact)}`}>
          {fact.risk_flag ? 'Risk' : fact.verified ? 'Verified' : 'Review'}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <ReviewButton active={fact.verified} disabled={working} label="Verify" onClick={() => onUpdate({ factId: fact.fact_id, body: { verified: !fact.verified } })} />
        <ReviewButton active={fact.buyer_safe} disabled={working} label="Buyer-safe" onClick={() => onUpdate({ factId: fact.fact_id, body: { buyer_safe: !fact.buyer_safe } })} />
        <ReviewButton active={fact.risk_flag} disabled={working} label="Risk flag" onClick={() => onUpdate({ factId: fact.fact_id, body: { risk_flag: !fact.risk_flag } })} />
      </div>
      <p className="mt-3 text-xs text-neutral-500">Confidence {confidenceLabel(fact.confidence)} · Updated {dateLabel(fact.updated_at)}</p>
    </article>
  )
}

function ReviewButton({ label, active, disabled, onClick }: { readonly label: string; readonly active: boolean; readonly disabled: boolean; readonly onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30 ${active ? 'border-brand-200 bg-brand-50 text-brand-700' : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}`}
    >
      {label}
    </button>
  )
}

function factTone(fact: ListingFact): string {
  if (fact.risk_flag) return 'bg-brick/15 text-brick'
  return fact.verified ? 'bg-sage/15 text-sage' : 'bg-copper/15 text-copper'
}

function confidenceLabel(value: number | null): string {
  return value == null ? 'not scored' : `${Math.round(value * 100)}%`
}
