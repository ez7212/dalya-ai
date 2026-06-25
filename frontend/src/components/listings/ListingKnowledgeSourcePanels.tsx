import type { ListingDocument } from '@/components/listings/ListingKnowledgeTypes'
import { dateLabel, statusLabel } from '@/components/listings/ListingKnowledgeTypes'

type AddDocumentPanelProps = {
  readonly documentTypes: readonly string[]
  readonly documentType: string
  readonly setDocumentType: (value: string) => void
  readonly label: string
  readonly setLabel: (value: string) => void
  readonly sourceUrl: string
  readonly setSourceUrl: (value: string) => void
  readonly text: string
  readonly setText: (value: string) => void
  readonly error: string | null
  readonly submitting: boolean
  readonly onSubmit: () => void
}

export function ListingKnowledgeAddDocumentPanel(props: AddDocumentPanelProps) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Add document text</p>
      <h2 className="mt-1 text-base font-semibold text-neutral-900">Ground a new fact source</h2>
      <div className="mt-4 space-y-3">
        <label className="block">
          <span className={labelClass}>Document type</span>
          <select value={props.documentType} onChange={(event) => props.setDocumentType(event.target.value)} className={inputClass}>
            {props.documentTypes.map((type) => <option key={type} value={type}>{statusLabel(type)}</option>)}
          </select>
        </label>
        <TextField label="Label" value={props.label} onChange={props.setLabel} placeholder="Title deed notes, inspection summary..." />
        <TextField label="Source URL" value={props.sourceUrl} onChange={props.setSourceUrl} placeholder="https://..." />
        <label className="block">
          <span className={labelClass}>Document text</span>
          <textarea rows={7} value={props.text} onChange={(event) => props.setText(event.target.value)} className={`${inputClass} resize-y`} />
        </label>
        {props.error && <p className="text-sm font-medium text-brick" role="alert">{props.error}</p>}
        <button
          type="button"
          onClick={props.onSubmit}
          disabled={props.submitting}
          className="inline-flex min-h-10 w-full items-center justify-center rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
        >
          {props.submitting ? 'Adding...' : 'Add document text'}
        </button>
      </div>
    </section>
  )
}

export function ListingKnowledgeDocumentList({ documents }: { readonly documents: readonly ListingDocument[] }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-neutral-900">Sources</h2>
        <span className="rounded-sm bg-neutral-100 px-2 py-1 text-[11px] font-medium text-neutral-700">{documents.length} files</span>
      </div>
      {documents.length === 0 ? (
        <p className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-600">No source documents yet.</p>
      ) : (
        <div className="mt-4 space-y-2">
          {documents.map((document) => (
            <div key={document.document_id} className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
              <p className="text-sm font-medium text-neutral-900">{document.label || statusLabel(document.document_type)}</p>
              <p className="mt-1 text-xs text-neutral-500">{statusLabel(document.status)} · Added {dateLabel(document.created_at)}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function TextField({ label, value, onChange, placeholder }: { readonly label: string; readonly value: string; readonly onChange: (value: string) => void; readonly placeholder?: string }) {
  return (
    <label className="block">
      <span className={labelClass}>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={inputClass} />
    </label>
  )
}

const labelClass = 'mb-2 block text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500'
const inputClass = 'w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 disabled:bg-neutral-100'
