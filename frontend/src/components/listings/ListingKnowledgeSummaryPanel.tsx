import type { KnowledgeSummary, MissingInformationItem, RiskFlagItem } from '@/components/listings/ListingKnowledgeTypes'
import { statusLabel } from '@/components/listings/ListingKnowledgeTypes'

export function ListingKnowledgeSummaryPanel({ summary }: { readonly summary?: KnowledgeSummary | null }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Property Advisor summary</p>
          <h2 className="mt-1 text-base font-semibold text-neutral-900">{summary ? statusLabel(summary.status) : 'No summary yet'}</h2>
        </div>
        <span className={`w-fit rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${summaryTone(summary?.status)}`}>
          {summary ? statusLabel(summary.status) : 'Empty'}
        </span>
      </div>
      {summary?.buyer_safe_summary ? (
        <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-neutral-700">{summary.buyer_safe_summary}</p>
      ) : (
        <p className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-600">
          Add document text or review extracted facts, then regenerate the summary.
        </p>
      )}
      <SignalList title="Missing information" items={(summary?.missing_information ?? []).map(missingSignal)} tone="copper" />
      <SignalList title="Risk flags" items={(summary?.risk_flags ?? []).map(riskSignal)} tone="brick" />
    </section>
  )
}

type Signal = {
  readonly detail: string | null
  readonly key: string
  readonly label: string
}

function SignalList({ title, items, tone }: { readonly title: string; readonly items: readonly Signal[]; readonly tone: 'copper' | 'brick' }) {
  if (items.length === 0) return null
  const className = tone === 'brick' ? 'border-brick/20 bg-brick/5 text-brick' : 'border-copper/20 bg-copper/5 text-copper'
  return (
    <div className="mt-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{title}</p>
      <ul className="mt-2 space-y-2">
        {items.map((item) => (
          <li key={item.key} className={`rounded-md border px-3 py-2 text-sm ${className}`}>
            <span className="block font-medium">{item.label}</span>
            {item.detail && <span className="mt-1 block text-xs opacity-85">{item.detail}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

function missingSignal(item: MissingInformationItem): Signal {
  return typeof item === 'string'
    ? { detail: null, key: item, label: item }
    : { detail: `Fact group: ${item.fact_group}`, key: item.fact_group, label: item.label }
}

function riskSignal(item: RiskFlagItem): Signal {
  return typeof item === 'string'
    ? { detail: null, key: item, label: item }
    : { detail: `${statusLabel(item.fact_key)}: ${item.value}`, key: item.fact_id, label: item.label }
}

function summaryTone(status?: string): string {
  if (status === 'ready') return 'bg-sage/15 text-sage'
  if (['blocked', 'failed'].includes(status ?? '')) return 'bg-brick/15 text-brick'
  if (['needs_review', 'needs_attention', 'stale', 'empty'].includes(status ?? '')) return 'bg-copper/15 text-copper'
  return 'bg-brand-50 text-brand-700'
}
