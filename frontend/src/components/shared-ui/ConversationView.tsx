import { sharedUi } from '@/lib/shared-ui-tokens'

export interface TranscriptPriceExtraction {
  amount?: number | null
  currency?: string
  confidence: 'high' | 'medium' | 'low'
  source_phrase: string
  unit_inferred?: boolean
  candidate_amounts?: number[]
}

export interface LowConfidenceSegment {
  source_phrase: string
  reason: string
  candidates?: string[]
}

export interface ConversationTurn {
  id: string
  role: 'buyer' | 'property_advisor' | 'agent'
  content: string
  timestamp?: string | null
  origin?: 'text' | 'voice'
  correctedTranscript?: string
  lowConfidenceSegments?: LowConfidenceSegment[]
  priceExtractions?: TranscriptPriceExtraction[]
}

export interface ConversationSummary {
  title?: string
  buyerGoal?: string
  budgetSignal?: string
  objections?: string[]
  status?: string
  nextStep?: string
}

interface ConversationViewProps {
  summary: ConversationSummary
  turns: ConversationTurn[]
  loading?: boolean
  emptyText?: string
}

const roleStyles: Record<ConversationTurn['role'], string> = {
  buyer: 'border-brand-100 bg-brand-50',
  property_advisor: 'border-neutral-200 bg-white',
  agent: 'border-success-100 bg-success-50',
}

const roleLabels: Record<ConversationTurn['role'], string> = {
  buyer: 'Buyer',
  property_advisor: 'Property Advisor',
  agent: 'Agent',
}

export function ConversationView({
  summary,
  turns,
  loading = false,
  emptyText = 'No conversation turns yet.',
}: ConversationViewProps) {
  return (
    <section className={`${sharedUi.panel} overflow-hidden`}>
      <div className="border-b border-neutral-200 bg-neutral-50 p-4 sm:p-5">
        <p className={sharedUi.label}>Conversation summary</p>
        <h3 className={`${sharedUi.heading} mt-1`}>{summary.title || 'Buyer context'}</h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <SummaryItem label="Goal" value={summary.buyerGoal} />
          <SummaryItem label="Budget" value={summary.budgetSignal} />
          <SummaryItem label="Status" value={summary.status} />
          <SummaryItem label="Next step" value={summary.nextStep} />
        </div>
        {summary.objections && summary.objections.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {summary.objections.map((item) => (
              <span key={item} className={sharedUi.chip}>{item}</span>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-3 p-4 sm:p-5">
        {loading && <p className={sharedUi.body}>Loading conversation...</p>}
        {!loading && turns.length === 0 && <p className={sharedUi.body}>{emptyText}</p>}
        {turns.map((turn) => (
          <TurnCard key={turn.id} turn={turn} />
        ))}
      </div>
    </section>
  )
}

function SummaryItem({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className={sharedUi.label}>{label}</p>
      <p className="mt-1 text-sm text-text-1">{value || 'Not captured'}</p>
    </div>
  )
}

function TurnCard({ turn }: { turn: ConversationTurn }) {
  const text = turn.origin === 'voice' ? turn.correctedTranscript || turn.content : turn.content
  return (
    <article className={`rounded border p-3 ${roleStyles[turn.role]}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-text-1">{roleLabels[turn.role]}</span>
          {turn.origin === 'voice' && (
            <span className={`${sharedUi.chip} bg-white`}>
              <span className="material-symbols-rounded text-[14px]" aria-hidden="true">graphic_eq</span>
              Voice note transcription
            </span>
          )}
        </div>
        {turn.timestamp && <span className={sharedUi.mono + ' text-text-3'}>{formatTime(turn.timestamp)}</span>}
      </div>

      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-text-1">{text}</p>

      {turn.lowConfidenceSegments && turn.lowConfidenceSegments.length > 0 && (
        <div className="mt-3 space-y-2">
          {turn.lowConfidenceSegments.map((segment) => (
            <div key={`${turn.id}-${segment.source_phrase}`} className="rounded border border-warning-100 bg-warning-50 px-3 py-2">
              <p className="text-xs font-semibold text-warning-700">Low-confidence transcript segment</p>
              <p className="mt-1 text-sm text-warning-800">{segment.source_phrase}</p>
              <p className="mt-1 text-xs text-warning-700">{segment.reason}</p>
              {segment.candidates && segment.candidates.length > 0 && (
                <p className="mt-1 text-xs text-warning-700">Candidates: {segment.candidates.join(', ')}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {turn.priceExtractions && turn.priceExtractions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {turn.priceExtractions.map((price) => (
            <span key={`${turn.id}-${price.source_phrase}`} className={`${sharedUi.chip} ${price.confidence === 'low' ? 'border-warning-100 bg-warning-50 text-warning-700' : 'border-success-100 bg-success-50 text-success-700'}`}>
              offer: {formatAmount(price)} · {price.confidence} confidence
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

function formatAmount(price: TranscriptPriceExtraction): string {
  if (price.amount) return `${price.currency || 'AED'} ${price.amount.toLocaleString()}`
  if (price.candidate_amounts?.length) return price.candidate_amounts.map((amount) => `${price.currency || 'AED'} ${amount.toLocaleString()}`).join(' / ')
  return price.source_phrase
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
