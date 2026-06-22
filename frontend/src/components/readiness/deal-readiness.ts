export interface DealReadinessMetadata {
  readonly stage?: unknown
  readonly missing_fields?: unknown
  readonly next_best_action?: unknown
  readonly next_best_action_reason?: unknown
  readonly score?: unknown
  readonly priority_band?: unknown
  readonly present_fields?: unknown
}

export interface DealReadinessSummary {
  readonly stage: string | null
  readonly missingFields: readonly string[]
  readonly nextBestAction: string | null
  readonly nextBestActionReason: string | null
  readonly score: number | null
  readonly priorityBand: string | null
  readonly presentFields: Readonly<Record<string, unknown>>
}

export interface DealReadinessDisplay {
  readonly headline: string | null
  readonly action: string | null
  readonly reason: string | null
  readonly missingFields: readonly string[]
}

export function normalizeDealReadiness(value: DealReadinessMetadata | null | undefined): DealReadinessSummary | null {
  const stage = cleanText(value?.stage)
  const missingFields = cleanTextList(value?.missing_fields)
  const nextBestAction = cleanText(value?.next_best_action)
  const nextBestActionReason = cleanText(value?.next_best_action_reason)
  const score = cleanNumber(value?.score)
  const priorityBand = cleanText(value?.priority_band)
  const presentFields = cleanRecord(value?.present_fields)

  const hasDisplayValue = Boolean(stage)
    || missingFields.length > 0
    || Boolean(nextBestAction)
    || Boolean(nextBestActionReason)
    || score !== null
    || Boolean(priorityBand)
    || Object.keys(presentFields).length > 0

  if (!hasDisplayValue) return null

  return {
    stage,
    missingFields,
    nextBestAction,
    nextBestActionReason,
    score,
    priorityBand,
    presentFields,
  }
}

export function buildDealReadinessDisplay(
  readiness: DealReadinessSummary | null | undefined,
  options: { readonly missingLimit?: number } = {},
): DealReadinessDisplay | null {
  if (!readiness) return null

  const headline = [
    readiness.stage ? labelFromKey(readiness.stage) : null,
    readiness.priorityBand ? `${labelFromKey(readiness.priorityBand)} priority` : null,
    readiness.score === null ? null : `${readiness.score}/100`,
  ].filter((item): item is string => Boolean(item)).join(' · ')
  const action = readiness.nextBestAction ? labelFromKey(readiness.nextBestAction) : null
  const missingLimit = options.missingLimit ?? 3
  const missingFields = readiness.missingFields.slice(0, missingLimit).map(labelFromKey)

  if (!headline && !action && !readiness.nextBestActionReason && missingFields.length === 0) {
    return null
  }

  return {
    headline: headline || null,
    action,
    reason: readiness.nextBestActionReason,
    missingFields,
  }
}

export function labelFromKey(value: string): string {
  return value
    .split('_')
    .filter(Boolean)
    .map((part, index) => (
      index === 0 ? part.charAt(0).toUpperCase() + part.slice(1) : part
    ))
    .join(' ')
}

function cleanText(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function cleanNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function cleanTextList(value: unknown): readonly string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0).map((item) => item.trim())
}

function cleanRecord(value: unknown): Readonly<Record<string, unknown>> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return {}
  return Object.fromEntries(
    Object.entries(value).filter(([key]) => key.trim().length > 0),
  )
}
