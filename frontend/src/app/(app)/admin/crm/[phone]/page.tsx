'use client'

import { use, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { useAuth } from '@/components/providers/AuthProvider'
import {
  useAdminBuyerDetail,
  usePatchBuyer,
  useAddBuyerNote,
} from '@/lib/queries'
import { formatMoney } from '@/lib/utils'

const STAGE_OPTIONS = [
  'new',
  'engaged',
  'qualified',
  'offer',
  'negotiation',
  'closed_won',
  'closed_lost',
] as const

function StagePill({ stage }: { stage: string }) {
  const styles: Record<string, string> = {
    new: 'border border-n-500/30 text-n-500',
    engaged: 'border border-gold/30 text-gold bg-gold/10',
    qualified: 'badge-sage',
    offer: 'text-gold bg-gold/15',
    negotiation: 'text-gold bg-gold/20 font-bold',
    closed_won: 'badge-sage',
    closed_lost: 'border border-red-400/30 text-red-400',
  }
  return (
    <span
      className={`inline-flex items-center text-[10px] font-semibold px-2.5 py-1 rounded ${styles[stage] ?? styles.new}`}
    >
      {stage.replace('_', ' ')}
    </span>
  )
}

export default function BuyerDetailPage({
  params,
}: {
  params: Promise<{ phone: string }>
}) {
  const { phone: rawPhone } = use(params)
  const phone = decodeURIComponent(rawPhone)

  const { loading: authLoading } = useAuth()
  const { data: buyer, isLoading, error } = useAdminBuyerDetail(phone, !authLoading)
  const patchMutation = usePatchBuyer(phone)
  const noteMutation = useAddBuyerNote(phone)

  const [newTag, setNewTag] = useState('')
  const [noteInput, setNoteInput] = useState('')

  if (isLoading || authLoading) {
    return <p className="text-n-500 text-sm py-10 text-center">Loading buyer...</p>
  }
  if (error) {
    return <p className="text-red-400 text-sm py-10 text-center" role="alert">{error.message}</p>
  }
  if (!buyer) return null

  const handleStageChange = (stage: string) => {
    patchMutation.mutate({ lead_stage: stage })
  }

  const handleAddTag = () => {
    const tag = newTag.trim()
    if (!tag || buyer.tags.includes(tag)) return
    patchMutation.mutate({ tags: [...buyer.tags, tag] })
    setNewTag('')
  }

  const handleRemoveTag = (tag: string) => {
    patchMutation.mutate({ tags: buyer.tags.filter((t) => t !== tag) })
  }

  const handleAddNote = () => {
    const text = noteInput.trim()
    if (!text) return
    noteMutation.mutate(text, {
      onSuccess: () => setNoteInput(''),
    })
  }

  const encodedPhone = encodeURIComponent(phone)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Back link */}
      <Link
        href="/admin/crm"
        className="inline-flex items-center gap-1.5 text-sm text-n-500 hover:text-gold transition-colors mb-6"
      >
        <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
          arrow_back
        </span>
        Back to CRM
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-8">
        <div className="flex-1 min-w-0">
          <h1 className="editorial text-2xl md:text-3xl font-bold text-sand tracking-tight">
            {buyer.name || 'Unknown Buyer'}
          </h1>
          <p className="font-mono text-sm text-n-500 mt-1">{phone}</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={buyer.lead_stage}
            onChange={(e) => handleStageChange(e.target.value)}
            className="rounded-lg bg-deep border border-gold/10 px-3 py-2 text-sm text-sand focus:outline-none focus:border-gold/30 transition-colors"
          >
            {STAGE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replace('_', ' ')}
              </option>
            ))}
          </select>
          {buyer.lead_source && (
            <span className="text-xs text-n-500 bg-white/5 px-2.5 py-1 rounded">
              {buyer.lead_source}
            </span>
          )}
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap items-center gap-2 mb-8">
        {buyer.tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 rounded-full bg-gold/10 text-gold"
          >
            {tag}
            <button
              onClick={() => handleRemoveTag(tag)}
              className="hover:text-red-400 transition-colors"
              aria-label={`Remove tag ${tag}`}
            >
              &times;
            </button>
          </span>
        ))}
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            placeholder="Add tag..."
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
            className="w-28 rounded-lg bg-deep border border-gold/10 px-3 py-1.5 text-xs text-sand placeholder:text-n-500 focus:outline-none focus:border-gold/30 transition-colors"
          />
          <button
            onClick={handleAddTag}
            className="text-xs text-n-500 hover:text-gold transition-colors"
          >
            +
          </button>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile card */}
          <div className="surface-1 rounded-xl p-6 ghost-border">
            <h2 className="text-sand font-semibold text-base mb-5">Profile</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-5 gap-x-8">
              <DetailCell
                label="Budget"
                value={buyer.budget_aed != null ? `AED ${formatMoney(buyer.budget_aed)}` : '—'}
                mono
                gold
              />
              <DetailCell
                label="Bedrooms"
                value={buyer.bedroom_preferences ?? '—'}
              />
              <DetailCell
                label="Areas"
                value={buyer.area_preferences?.join(', ') || '—'}
              />
              <DetailCell
                label="Purpose"
                value={buyer.purpose ?? '—'}
              />
              <DetailCell
                label="Created"
                value={buyer.created_at ? new Date(buyer.created_at).toLocaleDateString() : '—'}
              />
              <DetailCell
                label="Last Active"
                value={buyer.last_active ? new Date(buyer.last_active).toLocaleDateString() : '—'}
              />
            </div>
          </div>

          {/* Conversations list */}
          <div className="surface-1 rounded-xl p-6 ghost-border">
            <h2 className="text-sand font-semibold text-base mb-5">Conversations</h2>
            {buyer.conversations.length === 0 ? (
              <p className="text-n-500 text-sm">No conversations yet.</p>
            ) : (
              <div className="space-y-3">
                {buyer.conversations.map((convo) => (
                  <Link
                    key={convo.conversation_id}
                    href={`/admin/crm/${encodedPhone}/conversations/${convo.conversation_id}`}
                    className="block rounded-lg p-4 bg-deep/50 hover:bg-gold/5 border border-gold/5 hover:border-gold/15 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <p className="text-sm text-sand font-medium">
                        {convo.listing_name}
                      </p>
                      <div className="flex items-center gap-2 shrink-0">
                        {convo.escalated && (
                          <span className="text-[10px] font-semibold text-gold bg-gold/15 px-2 py-0.5 rounded">
                            Escalated
                          </span>
                        )}
                        <span className="text-xs text-n-500 font-mono">
                          {convo.message_count} msgs
                        </span>
                      </div>
                    </div>
                    {convo.last_message_preview && (
                      <p className="text-xs text-n-500 truncate">
                        {convo.last_message_preview}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column — Notes */}
        <div className="space-y-6">
          <div className="surface-1 rounded-xl p-6 ghost-border">
            <h2 className="text-sand font-semibold text-base mb-4">Notes</h2>
            <div className="mb-4">
              <textarea
                rows={3}
                placeholder="Add a note..."
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                className="w-full rounded-lg bg-deep border border-gold/10 px-4 py-2.5 text-sm text-sand placeholder:text-n-500 focus:outline-none focus:border-gold/30 transition-colors resize-none"
              />
              <button
                onClick={handleAddNote}
                disabled={noteMutation.isPending || !noteInput.trim()}
                className="mt-2 px-4 py-2 text-xs font-semibold rounded-md bg-gold/15 text-gold hover:bg-gold/25 transition-colors disabled:opacity-40"
              >
                {noteMutation.isPending ? 'Saving...' : 'Add Note'}
              </button>
            </div>
            {buyer.admin_notes.length === 0 ? (
              <p className="text-n-500 text-xs">No notes yet.</p>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {[...buyer.admin_notes].reverse().map((note, i) => (
                  <div
                    key={i}
                    className="rounded-lg p-3 bg-deep/50 border border-gold/5"
                  >
                    <p className="text-sm text-sand leading-relaxed">
                      {note.note}
                    </p>
                    <p className="text-[10px] text-n-500 mt-2">
                      {new Date(note.at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function DetailCell({
  label,
  value,
  mono,
  gold,
}: {
  label: string
  value: string
  mono?: boolean
  gold?: boolean
}) {
  return (
    <div>
      <span className="text-n-500 text-[11px] block mb-1">{label}</span>
      <p
        className={`text-sm font-medium ${gold ? 'text-gold' : 'text-sand'} ${mono ? 'font-mono' : ''}`}
      >
        {value}
      </p>
    </div>
  )
}
