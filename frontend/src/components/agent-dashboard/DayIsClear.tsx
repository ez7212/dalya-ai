import type { AgentDashboardData } from './types'

interface DayIsClearProps {
  readonly sourceLabel: string
  readonly emptyState?: AgentDashboardData['emptyState']
  readonly refreshState: 'idle' | 'working' | 'error'
  readonly onRefreshHotList: () => void
}

interface FirstRunStepProps {
  readonly icon: string
  readonly label: string
  readonly detail: string
}

export function DayIsClear({
  sourceLabel,
  emptyState,
  refreshState,
  onRefreshHotList,
}: DayIsClearProps) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white px-4 py-6 shadow-card-sm sm:px-6 sm:py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <span className="material-symbols-outlined text-[36px] text-success-600" aria-hidden="true">task_alt</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-success-700">Workspace is connected</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-neutral-900">
            Start with an internal pilot rehearsal
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-neutral-600">
            {emptyState ? 'This authenticated workspace has no live buyer activity yet.' : 'Your day is clear.'}{' '}
            Use synthetic/internal records only until Eric approves the pilot users, WhatsApp numbers, and data class.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 border-y border-neutral-200 py-5 md:grid-cols-3">
        <FirstRunStep
          icon="rule"
          label="Confirm pilot scope"
          detail="Use the friendly-pilot runbook before any rehearsal. Real customer data stays blocked."
        />
        <FirstRunStep
          icon="science"
          label="Trigger safe activity"
          detail="Seed or send only approved synthetic/internal records, then refresh the hot list."
        />
        <FirstRunStep
          icon="rate_review"
          label="Keep agent control"
          detail="Review drafts and handle WhatsApp manually if anything looks off."
        />
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-relaxed text-neutral-600">
          {emptyState?.message ?? (
            <>
              No buyers waiting on a reply, no hot signals, no drafts to review, and no viewings or escalations open right now.
              New activity lands here the moment a buyer engages.
            </>
          )}
        </p>
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={onRefreshHotList}
            disabled={refreshState === 'working'}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">sync</span>
            {refreshState === 'working' ? 'Refreshing' : 'Refresh hot list'}
          </button>
          <a
            href="/component-showcase"
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">preview</span>
            Preview safe demo states
          </a>
        </div>
      </div>
      <p className="mt-4 text-xs text-neutral-400">{sourceLabel}</p>
    </section>
  )
}

function FirstRunStep({ icon, label, detail }: FirstRunStepProps) {
  return (
    <div className="flex min-w-0 gap-3">
      <span className="material-symbols-outlined mt-0.5 text-[20px] text-brand-700" aria-hidden="true">{icon}</span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-neutral-900">{label}</p>
        <p className="mt-1 text-sm leading-relaxed text-neutral-600">{detail}</p>
      </div>
    </div>
  )
}
