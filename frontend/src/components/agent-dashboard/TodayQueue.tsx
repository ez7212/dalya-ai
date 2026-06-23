import Link from 'next/link'
import { QueueHandoffCard, queueActionLabel } from './QueueHandoffCard'
import type { TodayQueueItem } from './today-queue'

interface TodayQueueProps {
  readonly items: readonly TodayQueueItem[]
  readonly actionsEnabled: boolean
  readonly taskActionState: Record<string, 'done' | 'snoozed' | 'error' | 'working'>
  readonly escalationActionState: Record<string, 'resolved' | 'error' | 'working'>
  readonly refreshState: 'idle' | 'working' | 'error'
  readonly onTaskDone: (taskId: string) => void
  readonly onTaskSnooze: (taskId: string) => void
  readonly onResolveEscalation: (threadId: string) => void
  readonly onRefreshHotList: () => void
}

const KIND_LABEL: Record<TodayQueueItem['kind'], string> = {
  escalation: 'Escalation',
  overdue_task: 'Overdue',
  needs_reply: 'Reply',
  viewing: 'Viewing',
  reply_draft: 'Draft',
  hot_buyer: 'Hot buyer',
  follow_up: 'Follow-up',
}

const KIND_ICON: Record<TodayQueueItem['kind'], string> = {
  escalation: 'support_agent',
  overdue_task: 'priority_high',
  needs_reply: 'forum',
  viewing: 'event_available',
  reply_draft: 'edit_note',
  hot_buyer: 'local_fire_department',
  follow_up: 'schedule',
}

const KIND_TONE: Record<TodayQueueItem['kind'], string> = {
  escalation: 'border-warning-100 bg-warning-50 text-warning-700',
  overdue_task: 'border-error-100 bg-error-50 text-error-700',
  needs_reply: 'border-brand-100 bg-brand-50 text-brand-700',
  viewing: 'border-success-100 bg-success-50 text-success-700',
  reply_draft: 'border-neutral-200 bg-neutral-100 text-neutral-700',
  hot_buyer: 'border-brand-100 bg-brand-50 text-brand-700',
  follow_up: 'border-neutral-200 bg-white text-neutral-600',
}

export function TodayQueue({
  items,
  actionsEnabled,
  taskActionState,
  escalationActionState,
  refreshState,
  onTaskDone,
  onTaskSnooze,
  onResolveEscalation,
  onRefreshHotList,
}: TodayQueueProps) {
  return (
    <section id="today-queue" className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
      <div className="flex flex-col gap-3 border-b border-neutral-200 px-4 py-4 sm:px-5 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Today Queue</p>
          <h2 className="mt-1 text-base font-semibold text-neutral-900">Ranked work for this pilot day</h2>
          <p className="mt-1 text-sm text-neutral-600">One ordered queue across escalations, replies, viewings, drafts, hot buyers, and follow-ups.</p>
        </div>
        <button
          type="button"
          onClick={onRefreshHotList}
          disabled={!actionsEnabled || refreshState === 'working'}
          className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">sync</span>
          {refreshState === 'working' ? 'Refreshing' : 'Refresh'}
        </button>
      </div>

      <ol className="divide-y divide-neutral-200">
        {items.map((item, index) => (
          <li key={item.id} data-kind={item.kind} className="grid gap-4 px-4 py-4 sm:px-5 lg:grid-cols-[56px_minmax(0,1fr)_180px]">
            <div className="flex items-center gap-3 lg:block">
              <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-neutral-100 text-neutral-700">
                <span className="material-symbols-outlined text-[19px]" aria-hidden="true">{KIND_ICON[item.kind]}</span>
              </div>
              <span className="font-mono text-xs font-semibold text-neutral-500 lg:mt-2 lg:block">{String(index + 1).padStart(2, '0')}</span>
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-sm border px-2 py-0.5 text-[11px] font-semibold ${KIND_TONE[item.kind]}`}>{KIND_LABEL[item.kind]}</span>
                <span className="rounded-sm bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600">{item.status}</span>
                <span className="font-mono text-xs text-neutral-500">{item.timestampLabel}</span>
              </div>
              <h3 className="mt-2 text-sm font-semibold text-neutral-900">{item.title}</h3>
              <p className="mt-1 text-xs text-neutral-500">{item.subject}</p>
              <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-neutral-700">{item.detail}</p>
              <QueueHandoffCard item={item} />
            </div>

            <div className="flex flex-wrap items-start gap-2 lg:justify-end">
              <QueueActions
                item={item}
                actionsEnabled={actionsEnabled}
                taskActionState={taskActionState}
                escalationActionState={escalationActionState}
                onTaskDone={onTaskDone}
                onTaskSnooze={onTaskSnooze}
                onResolveEscalation={onResolveEscalation}
              />
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

function QueueActions({
  item,
  actionsEnabled,
  taskActionState,
  escalationActionState,
  onTaskDone,
  onTaskSnooze,
  onResolveEscalation,
}: {
  readonly item: TodayQueueItem
  readonly actionsEnabled: boolean
  readonly taskActionState: Record<string, 'done' | 'snoozed' | 'error' | 'working'>
  readonly escalationActionState: Record<string, 'resolved' | 'error' | 'working'>
  readonly onTaskDone: (taskId: string) => void
  readonly onTaskSnooze: (taskId: string) => void
  readonly onResolveEscalation: (threadId: string) => void
}) {
  if (item.task) {
    const task = item.task
    const taskState = taskActionState[task.id]
    return (
      <>
        <button
          type="button"
          onClick={() => onTaskDone(task.id)}
          disabled={!actionsEnabled || taskState === 'working'}
          className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[16px]" aria-hidden="true">check</span>
          Done
        </button>
        <button
          type="button"
          onClick={() => onTaskSnooze(task.id)}
          disabled={!actionsEnabled || taskState === 'working'}
          className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[16px]" aria-hidden="true">schedule</span>
          Snooze
        </button>
        {taskState === 'error' && <p className="basis-full text-xs font-medium text-error-600 lg:text-right">Could not update this task.</p>}
      </>
    )
  }

  if (item.escalation) {
    const escalation = item.escalation
    const escalationState = escalationActionState[escalation.id]
    return (
      <>
        <button
          type="button"
          onClick={() => onResolveEscalation(escalation.id)}
          disabled={!actionsEnabled || escalationState === 'working'}
          className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[16px]" aria-hidden="true">task_alt</span>
          Resolve
        </button>
        {item.href && <QueueLink href={item.href} label={queueActionLabel(item)} />}
        {escalationState === 'error' && <p className="basis-full text-xs font-medium text-error-600 lg:text-right">Could not resolve this escalation.</p>}
      </>
    )
  }

  if (item.href) {
    return <QueueLink href={item.href} label={queueActionLabel(item)} />
  }

  return null
}

function QueueLink({ href, label }: { readonly href: string; readonly label: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700">
      <span className="material-symbols-outlined text-[16px]" aria-hidden="true">open_in_new</span>
      {label}
    </Link>
  )
}
