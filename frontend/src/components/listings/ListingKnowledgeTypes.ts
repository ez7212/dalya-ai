export type ListingDocument = {
  readonly document_id: string
  readonly document_type: string
  readonly label: string | null
  readonly status: string
  readonly created_at: string | null
}

export type ListingFact = {
  readonly fact_id: string
  readonly document_id: string | null
  readonly fact_key: string
  readonly fact_group: string
  readonly value_text: string
  readonly confidence: number | null
  readonly source: string | null
  readonly verified: boolean
  readonly buyer_safe: boolean
  readonly risk_flag: boolean
  readonly notes: string | null
  readonly updated_at: string | null
}

export type MissingInformationItem =
  | string
  | {
      readonly fact_group: string
      readonly label: string
    }

export type RiskFlagItem =
  | string
  | {
      readonly fact_id: string
      readonly fact_key: string
      readonly label: string
      readonly value: string
    }

export type KnowledgeSummary = {
  readonly buyer_safe_summary: string
  readonly internal_notes: string
  readonly missing_information: readonly MissingInformationItem[]
  readonly risk_flags: readonly RiskFlagItem[]
  readonly status: string
  readonly updated_at: string | null
}

export type ListingKnowledgeResponse = {
  readonly listing_id: string
  readonly document_types: readonly string[]
  readonly documents: readonly ListingDocument[]
  readonly facts: readonly ListingFact[]
  readonly summary: KnowledgeSummary | null
}

export type FactUpdateInput = {
  readonly factId: string
  readonly body: Record<string, unknown>
}

export const DEFAULT_DOCUMENT_TYPE = 'agent_inspection_notes'

export function dateLabel(value?: string | null): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

export function statusLabel(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Open the listing again from the inventory workspace.'
}

export function errorDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  return typeof body.detail === 'string' ? body.detail : null
}
