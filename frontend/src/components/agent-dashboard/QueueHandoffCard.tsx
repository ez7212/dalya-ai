import Link from 'next/link'
import type { EscalationThreadItem } from './types'
import type { TodayQueueItem } from './today-queue'

interface HandoffCard {
  readonly intent: string
  readonly knownFields: readonly string[]
  readonly missingFields: readonly string[]
  readonly suggestedAction: string
  readonly routeHref?: string
  readonly routeLabel: string
  readonly source: string
  readonly offerReviewOnly: boolean
}

export function QueueHandoffCard({ item }: { readonly item: TodayQueueItem }) {
  return <HandoffPanel handoff={buildQueueHandoff(item)} />
}

export function EscalationHandoffPanel({ thread }: { readonly thread: EscalationThreadItem }) {
  return <HandoffPanel handoff={buildEscalationHandoff(thread)} />
}

export function queueActionLabel(item: TodayQueueItem): string {
  return buildQueueHandoff(item).suggestedAction
}

function HandoffPanel({ handoff }: { readonly handoff: HandoffCard }) {
  return (
    <div className="mt-3 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <HandoffFact label="Buyer intent" value={handoff.intent} />
        <HandoffList label="Known" values={handoff.knownFields} emptyValue="No readiness fields captured" />
        <HandoffList label="Missing" values={handoff.missingFields} emptyValue="No visible blockers" />
        <HandoffFact label="Suggested action" value={handoff.suggestedAction} />
        <HandoffRoute href={handoff.routeHref} label={handoff.routeLabel} />
        <HandoffFact label="Source" value={handoff.source} />
      </div>
      {handoff.offerReviewOnly && (
        <p className="mt-3 rounded-sm border border-warning-100 bg-warning-50 px-2 py-1.5 text-xs font-medium leading-relaxed text-warning-800">
          Agent review/counter guidance only. No automatic negotiation or send.
        </p>
      )}
    </div>
  )
}

function HandoffFact({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className="mt-1 text-xs font-medium leading-relaxed text-neutral-800">{value}</p>
    </div>
  )
}

function HandoffList({
  label,
  values,
  emptyValue,
}: {
  readonly label: string
  readonly values: readonly string[]
  readonly emptyValue: string
}) {
  return <HandoffFact label={label} value={values.length > 0 ? values.join(', ') : emptyValue} />
}

function HandoffRoute({ href, label }: { readonly href?: string; readonly label: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Work surface</p>
      <p className="mt-1 text-xs font-medium leading-relaxed text-neutral-800">
        {href ? (
          <Link href={href} className="text-brand-700 hover:text-brand-800">
            {label}
          </Link>
        ) : (
          label
        )}
      </p>
    </div>
  )
}

function buildQueueHandoff(item: TodayQueueItem): HandoffCard {
  const readinessKnown = knownReadinessFields(item)
  const readinessMissing = item.readiness?.missingFields.map(labelFromKey) ?? []
  const offerReviewOnly = isOfferIntent(item)
  return {
    intent: queueIntent(item),
    knownFields: uniqueList([...baseKnownFields(item), ...readinessKnown]).slice(0, 5),
    missingFields: readinessMissing.length > 0 ? readinessMissing.slice(0, 4) : fallbackMissingFields(item),
    suggestedAction: suggestedQueueAction(item, offerReviewOnly),
    routeHref: item.href,
    routeLabel: routeLabel(item),
    source: sourceLabel(item),
    offerReviewOnly,
  }
}

function buildEscalationHandoff(thread: EscalationThreadItem): HandoffCard {
  const href = `/agent/escalations?thread=${encodeURIComponent(thread.id)}`
  const offerReviewOnly = isOfferCategory(thread.category)
  return {
    intent: `${labelFromKey(thread.category)} escalation`,
    knownFields: uniqueList([
      `Buyer: ${thread.buyerName}`,
      `Listing: ${listingLabel(thread.listingName, thread.unitNumber)}`,
      `Questions: ${thread.questionCount}`,
      thread.token ? `Ref: ${thread.token}` : null,
    ]).slice(0, 5),
    missingFields: ['Agent-safe answer'],
    suggestedAction: offerReviewOnly ? 'Prepare agent review/counter guidance' : suggestedEscalationAction(thread.category),
    routeHref: href,
    routeLabel: 'Escalation inbox thread',
    source: 'Escalation inbox',
    offerReviewOnly,
  }
}

function queueIntent(item: TodayQueueItem): string {
  if (item.escalation) return `${labelFromKey(item.escalation.category)} escalation`
  if (item.conversation?.offerCount) return 'Offer conversation'
  if (item.buyer) return `${labelFromKey(item.buyer.intent)} buyer`
  if (item.viewing) return 'Viewing logistics'
  if (item.draft) return `${labelFromKey(item.draft.intent ?? item.draft.category)} draft`
  if (item.kind === 'needs_reply') return 'Buyer reply needed'
  return labelFromKey(item.kind)
}

function baseKnownFields(item: TodayQueueItem): readonly string[] {
  const listing = listingLabel(
    item.escalation?.listingName ?? item.conversation?.listingName ?? item.draft?.listingName ?? item.task?.listingName ?? item.subject,
    item.escalation?.unitNumber ?? item.conversation?.unitNumber ?? item.draft?.unitNumber,
  )
  return uniqueList([
    item.task?.buyerName ? `Buyer: ${item.task.buyerName}` : item.title ? `Buyer: ${item.title}` : null,
    listing ? `Listing: ${listing}` : null,
    item.buyer?.budget ? `Budget: ${item.buyer.budget}` : null,
    item.timestampLabel ? `Last signal: ${item.timestampLabel}` : null,
  ])
}

function knownReadinessFields(item: TodayQueueItem): readonly string[] {
  const presentFields = item.readiness?.presentFields ?? {}
  return Object.entries(presentFields)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => (typeof value === 'string' || typeof value === 'number' ? `${labelFromKey(key)}: ${String(value)}` : labelFromKey(key)))
}

function fallbackMissingFields(item: TodayQueueItem): readonly string[] {
  if (item.draft) return ['Agent approval']
  if (item.viewing) return ['Access confirmation']
  if (item.conversation?.hasPendingDraft) return ['Agent approval']
  if (item.conversation?.offerCount) return ['Agent offer review']
  if (item.escalation) return ['Agent-safe answer']
  return []
}

function suggestedQueueAction(item: TodayQueueItem, offerReviewOnly: boolean): string {
  if (offerReviewOnly) return 'Prepare agent review/counter guidance'
  if (item.readiness?.nextBestAction) return labelFromKey(item.readiness.nextBestAction)
  if (item.escalation) return suggestedEscalationAction(item.escalation.category)
  if (item.conversation) return item.conversation.hasPendingDraft ? 'Review draft reply' : 'Reply in conversation'
  if (item.draft) return 'Review draft reply'
  if (item.viewing) return 'Confirm viewing logistics'
  if (item.buyer) return item.buyer.recommendedAction
  if (item.task) return item.task.nextAction
  return item.reason
}

function suggestedEscalationAction(category: string): string {
  const normalized = category.toLowerCase()
  if (normalized.includes('viewing')) return 'Confirm viewing logistics'
  if (normalized.includes('finance') || normalized.includes('mortgage')) return 'Clarify financing documents'
  if (normalized.includes('document')) return 'Review requested document'
  return 'Answer escalation'
}

function routeLabel(item: TodayQueueItem): string {
  if (item.escalation) return 'Escalation inbox thread'
  if (item.conversation) return 'Conversation composer'
  if (item.draft?.conversationId) return 'Conversation draft'
  if (item.draft) return 'Drafts workspace'
  if (item.viewing) return 'Viewing detail'
  if (item.buyer) return 'Buyers workspace'
  return 'Today Queue task row'
}

function sourceLabel(item: TodayQueueItem): string {
  if (item.escalation) return 'Escalation inbox'
  if (item.conversation) return item.conversation.needsReplyReason ? 'Needs-reply signal' : 'Conversation inbox'
  if (item.draft) return 'Draft queue'
  if (item.viewing) return 'Viewing schedule'
  if (item.buyer) return 'Hot-list readiness'
  return 'Agent task queue'
}

function isOfferIntent(item: TodayQueueItem): boolean {
  return item.readiness?.stage === 'offer_ready'
    || item.buyer?.intent === 'offer_ready'
    || Boolean(item.conversation?.offerCount)
    || isOfferCategory(item.escalation?.category ?? item.draft?.intent ?? item.draft?.category ?? '')
}

function isOfferCategory(value: string): boolean {
  return value.toLowerCase().includes('offer') || value.toLowerCase().includes('counter')
}

function listingLabel(name: string | null | undefined, unitNumber?: string | null): string {
  if (!name) return ''
  return unitNumber ? `${name} · ${unitNumber}` : name
}

function uniqueList(values: readonly (string | null | undefined)[]): readonly string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))))
}

function labelFromKey(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
