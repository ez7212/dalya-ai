'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/providers/AuthProvider'
import { FileDropzone } from '@/components/listings/ListingKnowledgeSourcePanels'
import { apiFetch } from '@/lib/api'
import { useAgentListings, useListingDetail } from '@/lib/queries'
import type { ListingDetail } from '@/lib/queries'
import { formatMoney } from '@/lib/utils'

type ListingDocument = {
  readonly document_id: string
  readonly document_type: string
  readonly label: string | null
  readonly source_url: string | null
  readonly status: string
  readonly extracted_at: string | null
  readonly created_at: string | null
  readonly updated_at: string | null
  readonly metadata_json: Record<string, unknown>
  readonly content_preview: string
}

type ListingDocumentsResponse = {
  readonly listing_id: string
  readonly documents: readonly ListingDocument[]
}

const DOCUMENT_GROUPS = [
  { key: 'transfer', label: 'Transfer and ownership', types: ['title_deed', 'oqood', 'noc'] },
  { key: 'plans', label: 'Floor plans and brochures', types: ['floor_plan', 'brochure'] },
  { key: 'ready', label: 'Ready-property records', types: ['ejari', 'tenancy_contract', 'service_charge_statement', 'valuation_report', 'mortgage_liability_letter', 'snagging_report', 'dewa_utility_info', 'building_rules'] },
  { key: 'notes', label: 'Agent and seller attachments', types: ['agent_inspection_notes', 'seller_disclosure_notes'] },
] satisfies readonly { readonly key: string; readonly label: string; readonly types: readonly string[] }[]

export function ListingDocumentsWorkspace({ id }: { readonly id: string }) {
  const { loading: authLoading } = useAuth()
  const detailQuery = useListingDetail(id, !authLoading)
  const listingsQuery = useAgentListings(!authLoading)
  const documentsQuery = useListingDocuments(id, !authLoading)
  const documents = documentsQuery.data?.documents ?? []
  const grouped = groupDocuments(documents)
  const referenceCount = listingsQuery.data?.listings.find((listing) => listing.id === id)?.reference_document_count ?? 0

  if (authLoading || detailQuery.isLoading || documentsQuery.isLoading) {
    return <DocumentsSkeleton />
  }

  if (detailQuery.error || documentsQuery.error) {
    return (
      <section className="rounded-lg border border-brick/25 bg-white px-4 py-8 text-center" role="alert">
        <p className="text-sm font-semibold text-brick">Documents could not be loaded.</p>
        <p className="mt-2 text-sm text-neutral-600">{errorMessage(detailQuery.error ?? documentsQuery.error)}</p>
      </section>
    )
  }

  return (
    <div className="space-y-5" data-listing-workspace-route="documents" data-listing-id={id}>
      <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Document workspace</p>
            <h2 className="mt-1 text-lg font-semibold text-neutral-900">Listing files and extraction health</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-neutral-600">
              Keep transfer documents, ready-property records, floor plans, brochures, and attachments in one canonical workspace.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center sm:grid-cols-4">
            <Metric label="Files" value={String(documents.length)} />
            <Metric label="References" value={String(referenceCount)} />
            <Metric label="Processed" value={String(documents.filter((document) => document.status === 'processed').length)} />
            <Metric label="Pending" value={String(documents.filter((document) => document.status !== 'processed').length)} />
          </div>
        </div>
      </section>

      <UploadDocumentCard listingId={id} />

      <OffPlanContext detail={detailQuery.data} />

      {documents.length === 0 ? (
        <EmptyDocuments referenceCount={referenceCount} />
      ) : (
        <section className="grid gap-5 xl:grid-cols-2">
          {DOCUMENT_GROUPS.map((group) => (
            <DocumentGroup key={group.key} label={group.label} documents={grouped[group.key] ?? []} />
          ))}
          {(grouped.other?.length ?? 0) > 0 && <DocumentGroup label="Other attachments" documents={grouped.other ?? []} />}
        </section>
      )}
    </div>
  )
}

function useListingDocuments(id: string, enabled: boolean) {
  return useQuery<ListingDocumentsResponse>({
    queryKey: ['listing-documents', id],
    enabled: enabled && !!id,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/listings/${id}/documents`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Failed to load documents (${res.status})`)
      }
      return res.json()
    },
  })
}

const UPLOADABLE_TYPES = [
  'title_deed', 'oqood', 'ejari', 'tenancy_contract', 'service_charge_statement', 'noc',
  'valuation_report', 'mortgage_liability_letter', 'floor_plan', 'snagging_report',
  'dewa_utility_info', 'building_rules', 'agent_inspection_notes', 'seller_disclosure_notes',
] as const

function UploadDocumentCard({ listingId }: { readonly listingId: string }) {
  const queryClient = useQueryClient()
  const [documentType, setDocumentType] = useState<string>(UPLOADABLE_TYPES[0])
  const [file, setFile] = useState<File | null>(null)

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Choose a file to upload.')
      const form = new FormData()
      form.append('file', file)
      form.append('document_type', documentType)
      const res = await apiFetch(`/api/v1/listings/${listingId}/documents/upload`, { method: 'POST', body: form })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Upload failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess: async () => {
      setFile(null)
      await queryClient.invalidateQueries({ queryKey: ['listing-documents', listingId] })
      await queryClient.invalidateQueries({ queryKey: ['listing-knowledge', listingId] })
    },
  })

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Add a document</p>
      <h2 className="mt-1 text-base font-semibold text-neutral-900">Upload title deed, Ejari, service charges, and more</h2>
      <div className="mt-4 space-y-3">
        <label className="block sm:max-w-xs">
          <span className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Document type</span>
          <select value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20">
            {UPLOADABLE_TYPES.map((type) => <option key={type} value={type}>{documentTypeLabel(type)}</option>)}
          </select>
        </label>
        <FileDropzone file={file} setFile={setFile} />
        <button
          type="button"
          onClick={() => upload.mutate()}
          disabled={!file || upload.isPending}
          className="inline-flex min-h-10 items-center justify-center rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
        >
          {upload.isPending ? 'Uploading...' : 'Upload'}
        </button>
      </div>
      {upload.error && <p className="mt-3 text-sm font-medium text-brick" role="alert">{errorMessage(upload.error)}</p>}
    </section>
  )
}

function DocumentsSkeleton() {
  return (
    <div className="space-y-5" aria-label="Loading documents">
      <div className="h-36 animate-pulse rounded-lg border border-neutral-200 bg-white" />
      <div className="grid gap-5 xl:grid-cols-2">
        {['transfer', 'plans', 'ready', 'notes'].map((key) => (
          <div key={key} className="h-52 animate-pulse rounded-lg border border-neutral-200 bg-white" />
        ))}
      </div>
    </div>
  )
}

function OffPlanContext({ detail }: { readonly detail?: ListingDetail }) {
  const hasOffPlanContext = detail?.property_type === 'off_plan' || detail?.handover_date || detail?.total_paid_percent != null || (detail?.payment_schedule?.length ?? 0) > 0
  if (!hasOffPlanContext) return null

  const rows = [
    ['Handover', dateLabel(detail?.handover_date)],
    ['Paid to date', detail?.total_paid_percent == null ? 'Not recorded' : `${formatMoney(detail.total_paid_percent)}%`],
    ['NOC eligible', detail?.noc_eligible == null ? 'Not recorded' : detail.noc_eligible ? 'Yes' : 'No'],
    ['Payment milestones', String(detail?.payment_schedule?.length ?? 0)],
  ] satisfies readonly (readonly [string, string])[]

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Off-plan context</p>
      <h2 className="mt-1 text-base font-semibold text-neutral-900">SPA-derived details when available</h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
            <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</dt>
            <dd className="mt-1 text-sm font-medium text-neutral-900 tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function EmptyDocuments({ referenceCount }: { readonly referenceCount: number }) {
  const detail = referenceCount > 0
    ? `${referenceCount} reference attachment${referenceCount === 1 ? '' : 's'} are linked on the listing; processed extraction rows will appear here after ingestion.`
    : 'Attach title deed, Oqood, Ejari, service-charge, NOC, valuation, floor-plan, brochure, or inspection files from the listing creation flow so agents can answer from grounded context.'

  return (
    <section className="rounded-lg border border-neutral-200 bg-white px-4 py-10 text-center">
      <span className="material-symbols-outlined text-[32px] text-brand-700" aria-hidden="true">folder_open</span>
      <h2 className="mt-3 text-base font-semibold text-neutral-900">No listing documents uploaded yet</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-neutral-600">{detail}</p>
    </section>
  )
}

function DocumentGroup({ label, documents }: { readonly label: string; readonly documents: readonly ListingDocument[] }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-neutral-900">{label}</h2>
        <span className="rounded-sm bg-neutral-100 px-2 py-1 text-[11px] font-medium text-neutral-700">{documents.length} files</span>
      </div>
      {documents.length === 0 ? (
        <p className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-600">No files in this section yet.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {documents.map((document) => (
            <DocumentCard key={document.document_id} document={document} />
          ))}
        </div>
      )}
    </section>
  )
}

function DocumentCard({ document }: { readonly document: ListingDocument }) {
  return (
    <article className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-neutral-900">{document.label || documentTypeLabel(document.document_type)}</p>
          <p className="mt-1 text-xs text-neutral-500">{documentTypeLabel(document.document_type)} · Added {dateLabel(document.created_at)}</p>
        </div>
        <span className={`w-fit rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] ${statusTone(document.status)}`}>
          {statusLabel(document.status)}
        </span>
      </div>
      {document.content_preview && <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-neutral-700">{document.content_preview}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-neutral-500">
        <span className="tabular-nums">Extracted {dateLabel(document.extracted_at)}</span>
        {document.source_url && (
          <a href={document.source_url} target="_blank" rel="noreferrer" className="font-medium text-brand-700 hover:text-brand-800">
            Open source
          </a>
        )}
      </div>
    </article>
  )
}

function Metric({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="min-w-20 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{value}</p>
    </div>
  )
}

function groupDocuments(documents: readonly ListingDocument[]): Record<string, readonly ListingDocument[]> {
  const entries = DOCUMENT_GROUPS.map((group) => [group.key, documents.filter((document) => group.types.includes(document.document_type))])
  const knownTypes = new Set(DOCUMENT_GROUPS.flatMap((group) => group.types))
  return Object.fromEntries([...entries, ['other', documents.filter((document) => !knownTypes.has(document.document_type))]])
}

function documentTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    title_deed: 'Title deed',
    oqood: 'Oqood',
    ejari: 'Ejari',
    tenancy_contract: 'Tenancy contract',
    service_charge_statement: 'Service charge statement',
    noc: 'NOC',
    valuation_report: 'Valuation report',
    mortgage_liability_letter: 'Mortgage liability letter',
    floor_plan: 'Floor plan',
    brochure: 'Brochure',
    snagging_report: 'Snagging report',
    dewa_utility_info: 'DEWA and utilities',
    building_rules: 'Building rules',
    agent_inspection_notes: 'Agent inspection notes',
    seller_disclosure_notes: 'Seller disclosure notes',
  }
  return labels[value] ?? statusLabel(value)
}

function statusLabel(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function statusTone(status: string): string {
  if (status === 'processed') return 'bg-sage/15 text-sage'
  if (status === 'failed') return 'bg-brick/15 text-brick'
  return 'bg-copper/15 text-copper'
}

function dateLabel(value?: string | null): string {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Open the listing again from the inventory workspace.'
}

function errorDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  return typeof body.detail === 'string' ? body.detail : null
}
