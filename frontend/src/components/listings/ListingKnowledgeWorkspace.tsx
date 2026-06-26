'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/providers/AuthProvider'
import { ListingKnowledgeFactsPanel } from '@/components/listings/ListingKnowledgeFactsPanel'
import { ListingKnowledgeAddDocumentPanel, ListingKnowledgeDocumentList } from '@/components/listings/ListingKnowledgeSourcePanels'
import { ListingKnowledgeSummaryPanel } from '@/components/listings/ListingKnowledgeSummaryPanel'
import { apiFetch } from '@/lib/api'
import type { FactUpdateInput, ListingFact, ListingKnowledgeResponse } from '@/components/listings/ListingKnowledgeTypes'
import { DEFAULT_DOCUMENT_TYPE, errorDetail, errorMessage } from '@/components/listings/ListingKnowledgeTypes'

type ListingKnowledgeWorkspaceProps = {
  readonly id: string
}

export function ListingKnowledgeWorkspace({ id }: ListingKnowledgeWorkspaceProps) {
  const { loading: authLoading } = useAuth()
  const queryClient = useQueryClient()
  const knowledgeQuery = useListingKnowledge(id, !authLoading)
  const [documentType, setDocumentType] = useState(DEFAULT_DOCUMENT_TYPE)
  const [documentLabel, setDocumentLabel] = useState('')
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const [documentText, setDocumentText] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['listing-knowledge', id] })
  }
  const reset = () => {
    setDocumentLabel('')
    setDocumentFile(null)
    setDocumentText('')
    setFormError(null)
  }
  const updateFact = useFactUpdate(id, invalidate)
  const regenerate = useRegenerateKnowledge(id, invalidate)
  const addDocument = useAddKnowledgeDocument(id, invalidate, {
    documentType,
    documentLabel,
    documentText,
    reset,
  })
  const uploadDocument = useUploadKnowledgeDocument(id, invalidate, {
    documentType,
    documentLabel,
    getFile: () => documentFile,
    reset,
  })

  if (authLoading || knowledgeQuery.isLoading) return <KnowledgeSkeleton />
  if (knowledgeQuery.error) return <LoadError error={knowledgeQuery.error} />

  const knowledge = knowledgeQuery.data
  const facts = knowledge?.facts ?? []
  const mutationError = updateFact.error ?? regenerate.error ?? addDocument.error

  return (
    <div className="space-y-5" data-listing-workspace-route="knowledge" data-listing-id={id}>
      <KnowledgeHeader
        documentCount={knowledge?.documents.length ?? 0}
        factCount={facts.length}
        buyerSafeCount={facts.filter((fact) => fact.buyer_safe).length}
        missingCount={knowledge?.summary?.missing_information.length ?? 0}
        regenerating={regenerate.isPending}
        onRegenerate={() => regenerate.mutate()}
      />
      {mutationError && <p className="rounded-lg border border-brick/25 bg-white px-4 py-3 text-sm font-medium text-brick" role="alert">{errorMessage(mutationError)}</p>}
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          <ListingKnowledgeSummaryPanel summary={knowledge?.summary} />
          <ListingKnowledgeFactsPanel factsByGroup={groupFacts(facts)} onUpdate={updateFact.mutate} working={updateFact.isPending} />
        </div>
        <aside className="space-y-5">
          <ListingKnowledgeAddDocumentPanel
            documentTypes={knowledge?.document_types ?? [DEFAULT_DOCUMENT_TYPE]}
            documentType={documentType}
            setDocumentType={setDocumentType}
            label={documentLabel}
            setLabel={setDocumentLabel}
            file={documentFile}
            setFile={setDocumentFile}
            text={documentText}
            setText={setDocumentText}
            error={formError ?? (addDocument.error || uploadDocument.error ? errorMessage(addDocument.error ?? uploadDocument.error) : null)}
            submitting={addDocument.isPending || uploadDocument.isPending}
            onSubmit={() => submitDocument({ file: documentFile, text: documentText, setFormError, upload: uploadDocument.mutate, addText: addDocument.mutate })}
          />
          <ListingKnowledgeDocumentList documents={knowledge?.documents ?? []} />
        </aside>
      </section>
    </div>
  )
}

function useListingKnowledge(id: string, enabled: boolean) {
  return useQuery<ListingKnowledgeResponse>({
    queryKey: ['listing-knowledge', id],
    enabled: enabled && !!id,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/listings/${id}/knowledge`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Failed to load knowledge (${res.status})`)
      }
      return res.json()
    },
  })
}

function useFactUpdate(id: string, onSuccess: () => Promise<void>) {
  return useMutation({
    mutationFn: async (input: FactUpdateInput) => {
      const res = await apiFetch(`/api/v1/listings/${id}/facts/${input.factId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input.body),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Fact update failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess,
  })
}

function useRegenerateKnowledge(id: string, onSuccess: () => Promise<void>) {
  return useMutation({
    mutationFn: async () => {
      const res = await apiFetch(`/api/v1/listings/${id}/knowledge/regenerate`, { method: 'POST' })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Regeneration failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess,
  })
}

function useAddKnowledgeDocument(id: string, onSuccess: () => Promise<void>, input: { readonly documentType: string; readonly documentLabel: string; readonly documentText: string; readonly reset: () => void }) {
  return useMutation({
    mutationFn: async () => {
      const trimmedText = input.documentText.trim()
      if (!trimmedText) throw new Error('Add document text before submitting.')
      const res = await apiFetch(`/api/v1/listings/${id}/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_type: input.documentType,
          label: input.documentLabel.trim() || null,
          content_text: trimmedText,
          metadata_json: { source: 'listing_knowledge_workspace' },
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Document add failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess: async () => {
      input.reset()
      await onSuccess()
    },
  })
}

function useUploadKnowledgeDocument(id: string, onSuccess: () => Promise<void>, input: { readonly documentType: string; readonly documentLabel: string; readonly getFile: () => File | null; readonly reset: () => void }) {
  return useMutation({
    mutationFn: async () => {
      const file = input.getFile()
      if (!file) throw new Error('Choose a file before uploading.')
      const form = new FormData()
      form.append('file', file)
      form.append('document_type', input.documentType)
      if (input.documentLabel.trim()) form.append('label', input.documentLabel.trim())
      const res = await apiFetch(`/api/v1/listings/${id}/documents/upload`, { method: 'POST', body: form })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Upload failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess: async () => {
      input.reset()
      await onSuccess()
    },
  })
}

function KnowledgeHeader({ documentCount, factCount, buyerSafeCount, missingCount, regenerating, onRegenerate }: { readonly documentCount: number; readonly factCount: number; readonly buyerSafeCount: number; readonly missingCount: number; readonly regenerating: boolean; readonly onRegenerate: () => void }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Knowledge workspace</p>
          <h2 className="mt-1 text-lg font-semibold text-neutral-900">Property Specific Facts</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-neutral-600">Upload additional documents such as DEWA statements, service charges, inspection reports and more to strengthen Dalya&apos;s knowledge about the property.</p>
        </div>
        <button type="button" onClick={onRegenerate} disabled={regenerating} className="inline-flex min-h-10 items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-800 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30">
          {regenerating ? 'Regenerating...' : 'Regenerate summary'}
        </button>
      </div>
      <div className="mt-4 grid gap-2 text-center sm:grid-cols-4">
        <Metric label="Documents" value={String(documentCount)} help="Files and notes attached to this listing." />
        <Metric label="Facts" value={String(factCount)} help="Individual facts Dalya extracted from the documents." />
        <Metric label="Buyer-safe" value={String(buyerSafeCount)} help="Facts you've approved for Dalya to tell buyers directly." />
        <Metric label="Missing" value={String(missingCount)} help="Information gaps Dalya flagged — add documents to fill them." />
      </div>
    </section>
  )
}

function Metric({ label, value, help }: { readonly label: string; readonly value: string; readonly help?: string }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2" title={help}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{value}</p>
    </div>
  )
}

function submitDocument({ file, text, setFormError, upload, addText }: { file: File | null; text: string; setFormError: (error: string | null) => void; upload: () => void; addText: () => void }) {
  setFormError(null)
  if (file) {
    upload()
    return
  }
  if (!text.trim()) {
    setFormError('Upload a file or paste document text before submitting.')
    return
  }
  addText()
}

function groupFacts(facts: readonly ListingFact[]): Record<string, readonly ListingFact[]> {
  const grouped: Record<string, ListingFact[]> = {}
  for (const fact of facts) {
    const key = fact.fact_group || 'other'
    grouped[key] = [...(grouped[key] ?? []), fact]
  }
  return grouped
}

function KnowledgeSkeleton() {
  return (
    <div className="space-y-5" aria-label="Loading knowledge">
      <div className="h-40 animate-pulse rounded-lg border border-neutral-200 bg-white" />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="h-96 animate-pulse rounded-lg border border-neutral-200 bg-white" />
        <div className="h-96 animate-pulse rounded-lg border border-neutral-200 bg-white" />
      </div>
    </div>
  )
}

function LoadError({ error }: { readonly error: unknown }) {
  return (
    <section className="rounded-lg border border-brick/25 bg-white px-4 py-8 text-center" role="alert">
      <p className="text-sm font-semibold text-brick">Knowledge could not be loaded.</p>
      <p className="mt-2 text-sm text-neutral-600">{errorMessage(error)}</p>
    </section>
  )
}
