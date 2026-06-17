'use client'

import { FormEvent, use, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '@/components/providers/AuthProvider'
import { Badge } from '@/components/ui/Badge'
import { apiFetch } from '@/lib/api'

interface KnowledgeDocument {
  document_id: string
  document_type: string
  label: string | null
  source_url: string | null
  status: string
  extracted_at: string | null
  content_preview: string
}

interface KnowledgeFact {
  fact_id: string
  document_id: string | null
  fact_key: string
  fact_group: string
  value_text: string
  confidence: number
  verified: boolean
  buyer_safe: boolean
  risk_flag: boolean
  notes: string | null
}

interface KnowledgeSummary {
  buyer_safe_summary: string | null
  internal_notes: string | null
  missing_information: Array<{ fact_group: string; label: string }>
  risk_flags: Array<{ fact_id: string; fact_key: string; label: string; value: string }>
  status: string
  metadata_json: Record<string, number>
}

interface KnowledgePayload {
  listing_id: string
  document_types: string[]
  documents: KnowledgeDocument[]
  facts: KnowledgeFact[]
  summary: KnowledgeSummary | null
}

const TYPE_LABELS: Record<string, string> = {
  title_deed: 'Title deed',
  oqood: 'Oqood',
  ejari: 'Ejari',
  tenancy_contract: 'Tenancy contract',
  service_charge_statement: 'Service charge statement',
  noc: 'NOC',
  valuation_report: 'Valuation report',
  mortgage_liability_letter: 'Mortgage liability letter',
  floor_plan: 'Floor plan',
  snagging_report: 'Snagging report',
  dewa_utility_info: 'DEWA / utility info',
  building_rules: 'Building rules',
  agent_inspection_notes: 'Agent inspection notes',
  seller_disclosure_notes: 'Seller disclosure notes',
}

export default function ListingKnowledgePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { loading: authLoading } = useAuth()
  const [data, setData] = useState<KnowledgePayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [docType, setDocType] = useState('service_charge_statement')
  const [label, setLabel] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [contentText, setContentText] = useState('')

  const loadKnowledge = async () => {
    setError(null)
    const res = await apiFetch(`/api/v1/listings/${id}/knowledge`)
    if (!res.ok) {
      throw new Error(await res.text())
    }
    setData(await res.json())
  }

  useEffect(() => {
    if (authLoading) return
    setLoading(true)
    loadKnowledge()
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load ready knowledge.'))
      .finally(() => setLoading(false))
  }, [authLoading, id])

  const groupedFacts = useMemo(() => {
    const groups = new Map<string, KnowledgeFact[]>()
    for (const fact of data?.facts || []) {
      const group = fact.fact_group.replaceAll('_', ' ')
      groups.set(group, [...(groups.get(group) || []), fact])
    }
    return Array.from(groups.entries())
  }, [data?.facts])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const res = await apiFetch(`/api/v1/listings/${id}/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_type: docType,
          label: label.trim() || TYPE_LABELS[docType] || docType,
          source_url: sourceUrl.trim() || null,
          content_text: contentText.trim() || null,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      setLabel('')
      setSourceUrl('')
      setContentText('')
      await loadKnowledge()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not upload document.')
    } finally {
      setSubmitting(false)
    }
  }

  const updateFact = async (factId: string, patch: Partial<KnowledgeFact>) => {
    setError(null)
    const res = await apiFetch(`/api/v1/listings/${id}/facts/${factId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    if (!res.ok) {
      setError(await res.text())
      return
    }
    await loadKnowledge()
  }

  if (loading || authLoading) {
    return <p className="text-n-500 text-sm py-10 text-center">Loading ready knowledge...</p>
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {error && (
        <div className="rounded-lg bg-red-500/10 text-red-200 border border-red-400/20 px-4 py-3 text-sm" role="alert">
          {error}
        </div>
      )}

      <section className="surface-1 rounded-xl p-6 ghost-border">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-sand font-semibold text-base">Ready Property Knowledge</h2>
            <p className="text-n-500 text-xs mt-1">
              Buyer-safe facts extracted from title, tenancy, service-charge, utility, NOC, and inspection documents.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={data?.summary?.status === 'ready' ? 'sage' : 'verified'}>
              {data?.summary?.status || 'empty'}
            </Badge>
            <Badge variant="verified">{data?.facts.length || 0} facts</Badge>
            <Badge variant="verified">{data?.documents.length || 0} documents</Badge>
          </div>
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-[1.3fr_0.7fr]">
          <div>
            <h3 className="text-[11px] text-n-500 uppercase tracking-widest font-medium mb-3">Buyer-Safe Summary</h3>
            <div className="rounded-lg bg-deep/35 p-4 text-sm text-sand/90 whitespace-pre-line min-h-24">
              {data?.summary?.buyer_safe_summary || 'No buyer-safe facts yet. Upload a ready-property document or inspection note to build the knowledge layer.'}
            </div>
          </div>
          <div className="space-y-4">
            <SignalList
              title="Missing"
              empty="Core facts covered"
              items={(data?.summary?.missing_information || []).map((item) => item.label)}
            />
            <SignalList
              title="Risk Flags"
              empty="No risk flags"
              items={(data?.summary?.risk_flags || []).map((item) => item.value)}
              copper
            />
          </div>
        </div>
      </section>

      <section className="surface-1 rounded-xl p-6 ghost-border">
        <h2 className="text-sand font-semibold text-base mb-5">Add Document Text</h2>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="text-xs text-n-500">Document type</span>
              <select
                value={docType}
                onChange={(event) => setDocType(event.target.value)}
                className="mt-1 w-full rounded-lg bg-deep/60 border border-gold/10 px-3 py-2 text-sm text-sand focus:outline-none focus:border-gold/40"
              >
                {(data?.document_types || []).map((type) => (
                  <option key={type} value={type}>{TYPE_LABELS[type] || type}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs text-n-500">Label</span>
              <input
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                placeholder="Q2 2026 service charge"
                className="mt-1 w-full rounded-lg bg-deep/60 border border-gold/10 px-3 py-2 text-sm text-sand placeholder:text-n-500 focus:outline-none focus:border-gold/40"
              />
            </label>
            <label className="block">
              <span className="text-xs text-n-500">Source URL</span>
              <input
                value={sourceUrl}
                onChange={(event) => setSourceUrl(event.target.value)}
                placeholder="Optional"
                className="mt-1 w-full rounded-lg bg-deep/60 border border-gold/10 px-3 py-2 text-sm text-sand placeholder:text-n-500 focus:outline-none focus:border-gold/40"
              />
            </label>
          </div>
          <label className="block">
            <span className="text-xs text-n-500">Document text or agent note</span>
            <textarea
              value={contentText}
              onChange={(event) => setContentText(event.target.value)}
              rows={7}
              placeholder="Paste the relevant text. Tenant phone numbers, emails, and Emirates IDs are redacted from buyer-safe summaries."
              className="mt-1 w-full rounded-lg bg-deep/60 border border-gold/10 px-3 py-2 text-sm text-sand placeholder:text-n-500 focus:outline-none focus:border-gold/40"
            />
          </label>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting || (!contentText.trim() && !sourceUrl.trim())}
              className="btn-gold rounded-md px-6 py-3 text-sm font-semibold uppercase tracking-wide shadow-gold disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? 'Processing...' : 'Process document'}
            </button>
          </div>
        </form>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="surface-1 rounded-xl p-6 ghost-border">
          <h2 className="text-sand font-semibold text-base mb-4">Documents</h2>
          <div className="space-y-3">
            {(data?.documents || []).length === 0 ? (
              <p className="text-sm text-n-500">No ready-property documents yet.</p>
            ) : (
              data?.documents.map((doc) => (
                <div key={doc.document_id} className="rounded-lg bg-deep/35 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm text-sand font-medium">{doc.label || TYPE_LABELS[doc.document_type] || doc.document_type}</p>
                      <p className="text-xs text-n-500 mt-1">{TYPE_LABELS[doc.document_type] || doc.document_type}</p>
                    </div>
                    <Badge variant={doc.status === 'processed' ? 'sage' : 'verified'}>{doc.status}</Badge>
                  </div>
                  {doc.content_preview && <p className="text-xs text-n-500 mt-3 line-clamp-3">{doc.content_preview}</p>}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="surface-1 rounded-xl p-6 ghost-border">
          <h2 className="text-sand font-semibold text-base mb-4">Extracted Facts</h2>
          <div className="space-y-5">
            {groupedFacts.length === 0 ? (
              <p className="text-sm text-n-500">No facts extracted yet.</p>
            ) : (
              groupedFacts.map(([group, facts]) => (
                <div key={group}>
                  <h3 className="text-[11px] text-n-500 uppercase tracking-widest font-medium mb-2">{group}</h3>
                  <div className="space-y-3">
                    {facts.map((fact) => (
                      <FactRow key={fact.fact_id} fact={fact} onUpdate={updateFact} />
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </motion.div>
  )
}

function SignalList({ title, items, empty, copper = false }: { title: string; items: string[]; empty: string; copper?: boolean }) {
  return (
    <div>
      <h3 className="text-[11px] text-n-500 uppercase tracking-widest font-medium mb-2">{title}</h3>
      <div className="space-y-2">
        {items.length === 0 ? (
          <p className="text-xs text-sage-lt">{empty}</p>
        ) : (
          items.map((item, index) => (
            <p key={`${title}-${index}`} className={`text-xs ${copper ? 'text-amber-200' : 'text-n-500'}`}>{item}</p>
          ))
        )}
      </div>
    </div>
  )
}

function FactRow({ fact, onUpdate }: { fact: KnowledgeFact; onUpdate: (factId: string, patch: Partial<KnowledgeFact>) => void }) {
  return (
    <div className="rounded-lg bg-deep/35 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <p className="text-sm text-sand/90 leading-relaxed">{fact.value_text}</p>
        <div className="flex flex-wrap gap-2 shrink-0">
          <Badge variant={fact.verified ? 'sage' : 'verified'}>{fact.verified ? 'verified' : 'unverified'}</Badge>
          <Badge variant={fact.buyer_safe ? 'sage' : 'verified'}>{fact.buyer_safe ? 'buyer-safe' : 'internal'}</Badge>
          {fact.risk_flag && <Badge variant="copper">risk</Badge>}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onUpdate(fact.fact_id, { verified: !fact.verified })}
          className="inline-flex items-center gap-1 rounded-md border border-gold/10 px-3 py-1.5 text-xs text-sand hover:border-gold/35 hover:text-gold transition-colors"
        >
          <span className="material-symbols-outlined" aria-hidden="true" style={{ fontSize: '15px' }}>verified</span>
          {fact.verified ? 'Unverify' : 'Verify'}
        </button>
        <button
          type="button"
          onClick={() => onUpdate(fact.fact_id, { buyer_safe: !fact.buyer_safe })}
          className="inline-flex items-center gap-1 rounded-md border border-gold/10 px-3 py-1.5 text-xs text-sand hover:border-gold/35 hover:text-gold transition-colors"
        >
          <span className="material-symbols-outlined" aria-hidden="true" style={{ fontSize: '15px' }}>visibility</span>
          {fact.buyer_safe ? 'Make internal' : 'Make buyer-safe'}
        </button>
        <button
          type="button"
          onClick={() => onUpdate(fact.fact_id, { risk_flag: !fact.risk_flag })}
          className="inline-flex items-center gap-1 rounded-md border border-gold/10 px-3 py-1.5 text-xs text-sand hover:border-gold/35 hover:text-gold transition-colors"
        >
          <span className="material-symbols-outlined" aria-hidden="true" style={{ fontSize: '15px' }}>flag</span>
          {fact.risk_flag ? 'Clear risk' : 'Flag risk'}
        </button>
      </div>
    </div>
  )
}
