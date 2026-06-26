import type {
  AgentDashboardData,
  BuyerDigestItem,
  ConversationInboxItem,
  EscalationThreadItem,
  QueueItem,
  ReplyDraftItem,
  ViewingItem,
} from './types'
import type { DealReadinessSummary } from '../readiness/deal-readiness'

export type TodayQueueKind =
  | 'escalation'
  | 'overdue_task'
  | 'needs_reply'
  | 'viewing'
  | 'reply_draft'
  | 'hot_buyer'
  | 'follow_up'

export interface TodayQueueItem {
  readonly id: string
  readonly kind: TodayQueueKind
  readonly title: string
  readonly subject: string
  readonly listingName: string
  readonly detail: string
  readonly status: string
  readonly reason: string
  readonly timestampLabel: string
  readonly href?: string
  readonly dueAt?: string | null
  readonly lastBuyerMessageAt?: string | null
  readonly createdAt?: string | null
  readonly urgencyScore?: number | null
  readonly readiness?: DealReadinessSummary | null
  readonly task?: QueueItem
  readonly escalation?: EscalationThreadItem
  readonly viewing?: ViewingItem
  readonly draft?: ReplyDraftItem
  readonly buyer?: BuyerDigestItem
  readonly conversation?: ConversationInboxItem
}

interface RankedQueueItem extends TodayQueueItem {
  readonly bucket: number
  readonly sequence: number
}

interface BuildTodayQueueInput {
  readonly data: AgentDashboardData
  readonly needsReply: readonly ConversationInboxItem[]
  readonly now?: Date
}

const BUCKET = {
  escalation: 1,
  overdueTask: 2,
  needsReply: 3,
  viewing: 4,
  replyDraft: 5,
  hotBuyer: 6,
  followUp: 7,
} as const

const TWO_HOURS_MS = 2 * 60 * 60 * 1000

export function buildTodayQueue({ data, needsReply, now = new Date() }: BuildTodayQueueInput): TodayQueueItem[] {
  const nowMs = now.getTime()
  const ranked: RankedQueueItem[] = [
    ...buildEscalationItems(data.escalationInbox),
    ...buildTaskItems(data.morningQueue, nowMs),
    ...buildNeedsReplyItems(needsReply),
    ...buildViewingItems(data.todaysViewings, now, nowMs),
    ...buildReplyDraftItems(data.drafts.replyDrafts),
    ...buildHotBuyerItems(data.overnightBuyerDigest),
  ]

  return ranked
    .sort(compareRankedQueueItems)
    .map(withoutRanking)
}

const ACTIONABLE_ESCALATION_STATES = new Set(['open', 'updated', 'timed_out'])
const ESCALATION_URGENCY_RANK: Record<string, number> = { critical: 0, high: 1, normal: 2 }

function buildEscalationItems(items: readonly EscalationThreadItem[]): RankedQueueItem[] {
  return items
    // Every open escalation needs agent judgment — surface them all, not just the
    // 'critical' ones (the previous filter hid normal/high escalations entirely).
    .filter((item) => ACTIONABLE_ESCALATION_STATES.has(item.state))
    // Critical first within the escalation bucket, then high, then normal.
    .slice()
    .sort((a, b) => (ESCALATION_URGENCY_RANK[a.urgency] ?? 9) - (ESCALATION_URGENCY_RANK[b.urgency] ?? 9))
    .map((item, sequence) => ({
      id: `escalation-${item.id}`,
      kind: 'escalation',
      bucket: BUCKET.escalation,
      sequence,
      title: item.buyerName,
      subject: item.listingName,
      listingName: item.listingName,
      detail: cleanText(item.latestQuestion, 'Agent review needed.'),
      status: `${labelFromKey(item.urgency)} escalation`,
      reason: item.state === 'updated' ? 'Buyer added a new question.' : 'Open escalation is waiting on agent judgment.',
      href: `/agent/escalations?thread=${encodeURIComponent(item.id)}`,
      timestampLabel: item.lastBuyerMessageAt || item.openedAt || 'Today',
      dueAt: item.routeExpiresAtRaw ?? null,
      lastBuyerMessageAt: item.lastBuyerMessageAtRaw ?? item.lastBuyerMessageAt,
      createdAt: item.openedAtRaw ?? item.openedAt,
      escalation: item,
    }))
}

function buildTaskItems(items: readonly QueueItem[], nowMs: number): RankedQueueItem[] {
  return items
    .filter((item) => item.source === undefined || item.source === 'task')
    .map((item, sequence) => {
      const dueMs = parseDateMs(item.dueAt)
      const overdue = dueMs !== null && dueMs < nowMs
      return {
        id: `${overdue ? 'overdue-task' : 'follow-up'}-${item.id}`,
        kind: overdue ? 'overdue_task' : 'follow_up',
        bucket: overdue ? BUCKET.overdueTask : BUCKET.followUp,
        sequence,
        title: item.title,
        subject: item.buyerName,
        listingName: item.listingName ?? '',
        detail: item.context,
        status: overdue ? '' : 'Future follow-up',
        reason: item.nextAction,
        timestampLabel: item.due || 'Today',
        dueAt: item.dueAt ?? null,
        createdAt: item.createdAt ?? null,
        readiness: item.readiness ?? null,
        task: item,
      } satisfies RankedQueueItem
    })
}

function buildNeedsReplyItems(items: readonly ConversationInboxItem[]): RankedQueueItem[] {
  return items
    .filter((item) => item.needsReply)
    .map((item, sequence) => ({
      id: `needs-reply-${item.id}`,
      kind: 'needs_reply',
      bucket: BUCKET.needsReply,
      sequence,
      title: item.buyerName,
      subject: item.listingName,
      listingName: item.listingName,
      detail: cleanText(item.lastMessage, item.summary),
      status: item.hasPendingDraft ? 'Draft ready' : 'Needs reply',
      reason: item.needsReplyReason || item.nextStep,
      href: `/agent/conversations/${item.id}`,
      timestampLabel: item.lastSeen,
      lastBuyerMessageAt: item.lastBuyerMessageAtRaw ?? item.lastBuyerMessageAt,
      urgencyScore: item.needsReplyPriorityScore ?? null,
      readiness: item.readiness ?? null,
      conversation: item,
    }))
}

function buildViewingItems(items: readonly ViewingItem[], now: Date, nowMs: number): RankedQueueItem[] {
  return items
    .filter((item) => isViewingActionable(item.scheduledFor, now, nowMs))
    .map((item, sequence) => ({
      id: `viewing-${item.id}`,
      kind: 'viewing',
      bucket: BUCKET.viewing,
      sequence,
      title: item.buyerName,
      subject: item.property,
      listingName: item.property,
      detail: item.preparation,
      status: `${labelFromKey(item.status)} viewing`,
      reason: item.location,
      href: `/agent/viewings/${item.id}`,
      timestampLabel: item.time,
      dueAt: item.scheduledFor ?? null,
      viewing: item,
    }))
}

function buildReplyDraftItems(items: readonly ReplyDraftItem[]): RankedQueueItem[] {
  return items.map((item, sequence) => ({
    id: `reply-draft-${item.id}`,
    kind: 'reply_draft',
    bucket: BUCKET.replyDraft,
    sequence,
    title: item.buyerName,
    subject: item.listingName,
    listingName: item.listingName,
    detail: cleanText(item.body, 'Draft reply is ready for review.'),
    status: 'Draft awaiting approval',
    reason: labelFromKey(item.category),
    href: item.conversationId ? `/agent/conversations/${item.conversationId}` : '/agent/drafts',
    timestampLabel: 'Review',
    createdAt: item.createdAt ?? null,
    draft: item,
  }))
}

function buildHotBuyerItems(items: readonly BuyerDigestItem[]): RankedQueueItem[] {
  return items.map((item, sequence) => ({
    id: `hot-buyer-${item.id}`,
    kind: 'hot_buyer',
    bucket: BUCKET.hotBuyer,
    sequence,
    title: item.buyerName,
    subject: item.target,
    listingName: item.target,
    detail: item.message,
    status: `${labelFromKey(item.intent)} buyer`,
    reason: item.recommendedAction,
    href: '/agent/buyers',
    timestampLabel: item.lastSeen,
    dueAt: item.dueAt ?? null,
    lastBuyerMessageAt: item.lastMessageAt ?? null,
    urgencyScore: item.urgencyScore ?? null,
    readiness: item.readiness ?? null,
    buyer: item,
  }))
}

function compareRankedQueueItems(left: RankedQueueItem, right: RankedQueueItem): number {
  const bucketDelta = left.bucket - right.bucket
  if (bucketDelta !== 0) return bucketDelta

  if (
    (left.kind === 'hot_buyer' && right.kind === 'hot_buyer') ||
    (left.kind === 'needs_reply' && right.kind === 'needs_reply')
  ) {
    const urgencyDelta = Number(right.urgencyScore ?? 0) - Number(left.urgencyScore ?? 0)
    if (urgencyDelta !== 0) return urgencyDelta
  }

  const dueDelta = sortableDate(left.dueAt, Number.POSITIVE_INFINITY) - sortableDate(right.dueAt, Number.POSITIVE_INFINITY)
  if (dueDelta !== 0) return dueDelta

  const lastBuyerDelta = sortableDate(right.lastBuyerMessageAt, Number.NEGATIVE_INFINITY) - sortableDate(left.lastBuyerMessageAt, Number.NEGATIVE_INFINITY)
  if (lastBuyerDelta !== 0) return lastBuyerDelta

  const createdDelta = sortableDate(left.createdAt, Number.POSITIVE_INFINITY) - sortableDate(right.createdAt, Number.POSITIVE_INFINITY)
  if (createdDelta !== 0) return createdDelta

  return left.sequence - right.sequence
}

function withoutRanking(item: RankedQueueItem): TodayQueueItem {
  return item
}

function isViewingActionable(value: string | null | undefined, now: Date, nowMs: number): boolean {
  const scheduledMs = parseDateMs(value)
  if (scheduledMs === null) return true
  if (scheduledMs <= nowMs + TWO_HOURS_MS) return true
  const scheduled = new Date(scheduledMs)
  return scheduled.toDateString() === now.toDateString()
}

function sortableDate(value: string | null | undefined, fallback: number): number {
  return parseDateMs(value) ?? fallback
}

function parseDateMs(value: string | null | undefined): number | null {
  if (!value) return null
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : null
}

function cleanText(value: string | null | undefined, fallback: string): string {
  if (!value) return fallback
  return value
}

function labelFromKey(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}
