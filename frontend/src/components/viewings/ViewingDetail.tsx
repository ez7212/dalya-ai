'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { DraftMessageCard } from '@/components/shared-ui'
import { useAuth } from '@/components/providers/AuthProvider'
import { apiFetch } from '@/lib/api'
import { useAgentViewingDetail, useViewingBrief, type ViewingNotificationDraft } from '@/lib/queries'

interface ViewingDetailProps {
  viewingId: string
}

export function ViewingDetail({ viewingId }: ViewingDetailProps) {
  const queryClient = useQueryClient()
  const { loading: authLoading } = useAuth()
  const { data: viewing, isLoading, error } = useAgentViewingDetail(viewingId, !authLoading)
  const { data: brief, isLoading: briefLoading } = useViewingBrief(viewingId, !authLoading)
  const [generating, setGenerating] = useState(false)
  const [sendingTenantNotice, setSendingTenantNotice] = useState(false)
  const [sendingDraftType, setSendingDraftType] = useState<string | null>(null)
  const [completingViewing, setCompletingViewing] = useState(false)
  const [requestingFeedback, setRequestingFeedback] = useState(false)
  const [submittingAgentFeedback, setSubmittingAgentFeedback] = useState(false)
  const [agentFeedback, setAgentFeedback] = useState('')
  const [agentScore, setAgentScore] = useState('')
  const [agentTemperature, setAgentTemperature] = useState('warm')
  const [agentFinancing, setAgentFinancing] = useState('unknown')
  const [agentNextAction, setAgentNextAction] = useState('follow_up')
  const [draftError, setDraftError] = useState<string | null>(null)
  const [followUpState, setFollowUpState] = useState<'idle' | 'working' | 'created' | 'error'>('idle')

  // DAL-166 (flagged optional): one CTA on received feedback → a review-only
  // draft into the existing queue. Flag off → CTA absent.
  const draftFollowUp = async () => {
    setFollowUpState('working')
    try {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/feedback/draft-follow-up`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Draft follow-up failed (${res.status})`)
      }
      setFollowUpState('created')
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not draft the follow-up')
      setFollowUpState('error')
    }
  }

  const generateDrafts = async () => {
    setGenerating(true)
    setDraftError(null)
    try {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/notification-drafts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Draft generation failed (${res.status})`)
      }
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not generate drafts')
    } finally {
      setGenerating(false)
    }
  }

  const sendTenantNotice = async () => {
    setSendingTenantNotice(true)
    setDraftError(null)
    try {
      const tenantDraft = drafts.find((draft) => draft.type === 'tenant_notice')
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/tenant-notice/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: tenantDraft?.body || null }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Tenant notice send failed (${res.status})`)
      }
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not send tenant notice')
    } finally {
      setSendingTenantNotice(false)
    }
  }

  const setTenantStatus = async (tenant: string) => {
    setDraftError(null)
    try {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/confirmation-status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Tenant status update failed (${res.status})`)
      }
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not update tenant status')
    }
  }

  const sendNotificationDraft = async (draft: ViewingNotificationDraft) => {
    setSendingDraftType(draft.type)
    setDraftError(null)
    try {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/notifications/${draft.type}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: draft.body }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Notification send failed (${res.status})`)
      }
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not send notification')
    } finally {
      setSendingDraftType(null)
    }
  }

  const completeViewing = async () => {
    setCompletingViewing(true)
    setDraftError(null)
    try {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/complete`, { method: 'POST' })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Completion failed (${res.status})`)
      }
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
      await queryClient.invalidateQueries({ queryKey: ['viewing-brief', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not complete viewing')
    } finally {
      setCompletingViewing(false)
    }
  }

  const requestPostViewingFeedback = async () => {
    setRequestingFeedback(true)
    setDraftError(null)
    try {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/feedback/request`, { method: 'POST' })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Feedback request failed (${res.status})`)
      }
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not request feedback')
    } finally {
      setRequestingFeedback(false)
    }
  }

  const submitAgentFeedback = async () => {
    if (!agentFeedback.trim()) {
      setDraftError('Add agent feedback notes before submitting')
      return
    }
    setSubmittingAgentFeedback(true)
    setDraftError(null)
    try {
      const parsedScore = agentScore.trim() ? Number(agentScore) : null
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/feedback/agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_body: agentFeedback,
          score: parsedScore !== null && Number.isFinite(parsedScore) ? parsedScore : null,
          temperature: agentTemperature,
          financing_status: agentFinancing,
          next_action: agentNextAction,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Agent feedback failed (${res.status})`)
      }
      setAgentFeedback('')
      setAgentScore('')
      await queryClient.invalidateQueries({ queryKey: ['agent-viewing', viewingId] })
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not submit agent feedback')
    } finally {
      setSubmittingAgentFeedback(false)
    }
  }

  if (isLoading || authLoading) {
    return (
      <div className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="h-8 w-64 animate-pulse rounded bg-neutral-200" />
          <div className="mt-4 h-36 animate-pulse rounded-lg bg-white" />
        </main>
      </div>
    )
  }

  if (error || !viewing) {
    return (
      <div className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            {error?.message || 'Viewing not found'}
          </p>
        </main>
      </div>
    )
  }

  const drafts = viewing.notification_drafts || []

  return (
    <div className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <Link href="/agent/viewings" className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-neutral-500 hover:text-brand-700">
          <span className="material-symbols-outlined text-[16px]" aria-hidden="true">arrow_back</span>
          Back to viewings
        </Link>

        <header className="mb-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Viewing detail</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-900">
              {viewing.listing.project || 'Viewing'}{viewing.listing.unit_number ? ` · Unit ${viewing.listing.unit_number}` : ''}
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              {viewing.buyer.name || viewing.buyer.phone} · {formatDateTime(viewing.scheduled_for)}
            </p>
          </div>
          <StatusGrid status={viewing.confirmation_status || {}} tenantRequired={viewing.tenant_notice_required} />
        </header>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-5">
            <Panel title="Pre-viewing brief" eyebrow="Agent briefing">
              {briefLoading || !brief ? (
                <p className="text-sm text-neutral-600">Loading brief...</p>
              ) : (
                <div className="space-y-5">
                  <FactGrid
                    items={[
                      ['Buyer', brief.buyer_profile.name || brief.buyer_profile.phone],
                      ['Budget', brief.buyer_profile.budget_aed ? `AED ${Number(brief.buyer_profile.budget_aed).toLocaleString()}` : 'Not captured'],
                      ['Scheduled', formatDateTime(brief.scheduled_for)],
                    ]}
                  />
                  <BriefSection label="Priorities" values={brief.buyer_profile.stated_priorities || []} />
                  <BriefSection label="Property highlights" values={brief.property_highlights || []} />
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Likely objections</p>
                    <div className="mt-3 space-y-3">
                      {(brief.likely_objections || []).map((item) => (
                        <article key={item.objection} className="rounded border border-neutral-200 bg-neutral-50 px-3 py-3">
                          <p className="text-sm font-semibold text-neutral-900">{item.objection}</p>
                          <p className="mt-1 text-sm leading-relaxed text-neutral-600">{item.response}</p>
                        </article>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </Panel>

            <Panel
              title="Notification drafts"
              eyebrow="Draft and approve"
              action={
                <button
                  type="button"
                  onClick={generateDrafts}
                  disabled={generating}
                  className="inline-flex min-h-10 items-center justify-center rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
                >
                  {generating ? 'Generating...' : drafts.length ? 'Regenerate' : 'Generate drafts'}
                </button>
              }
            >
              {draftError && <p className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{draftError}</p>}
              {drafts.length === 0 ? (
                <p className="text-sm text-neutral-600">Generate buyer, tenant, running-late, and reschedule drafts. Nothing sends automatically.</p>
              ) : (
                <div className="space-y-4">
                  {drafts.map((draft) => (
                    <div key={draft.draft_id} className="space-y-2">
                      <DraftMessageCard
                        title={draftLabel(draft)}
                        contextLine={`${draft.recipient_type} · ${draft.channel} · ${draft.status}`}
                        draft={draft.body}
                      />
                      {draft.type !== 'tenant_notice' && (
                        <button
                          type="button"
                          onClick={() => sendNotificationDraft(draft)}
                          disabled={sendingDraftType === draft.type}
                          className="inline-flex min-h-9 items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-60"
                        >
                          {sendingDraftType === draft.type ? 'Sending...' : draft.status === 'sent' ? 'Resend' : 'Send'}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <aside className="space-y-5">
            <Panel title="Tenant confirmation" eyebrow="WhatsApp">
              <FactGrid
                items={[
                  ['Status', viewing.tenant_confirmation?.status || viewing.confirmation_status?.tenant || (viewing.tenant_notice_required ? 'Not sent' : 'Not required')],
                  ['Sent', viewing.tenant_confirmation?.sent_at ? formatDateTime(viewing.tenant_confirmation.sent_at) : 'Not sent'],
                  ['Responded', viewing.tenant_confirmation?.responded_at ? formatDateTime(viewing.tenant_confirmation.responded_at) : 'No reply yet'],
                ]}
              />
              {viewing.tenant_confirmation?.last_inbound_body && (
                <p className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
                  {viewing.tenant_confirmation.last_inbound_body}
                </p>
              )}
              {viewing.tenant_notice_required && (
                <div className="mt-4 grid gap-2">
                  <button
                    type="button"
                    onClick={sendTenantNotice}
                    disabled={sendingTenantNotice}
                    className="inline-flex min-h-10 w-full items-center justify-center rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
                  >
                    {sendingTenantNotice ? 'Sending...' : viewing.tenant_confirmation?.sent_at ? 'Resend tenant notice' : 'Send tenant notice'}
                  </button>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setTenantStatus('confirmed')}
                      className="inline-flex min-h-10 items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
                    >
                      Mark confirmed
                    </button>
                    <button
                      type="button"
                      onClick={() => setTenantStatus('reschedule_requested')}
                      className="inline-flex min-h-10 items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
                    >
                      Needs new time
                    </button>
                  </div>
                </div>
              )}
            </Panel>

            <Panel title="Logistics summary" eyebrow="Access">
              <FactGrid
                items={[
                  ['Access', String(viewing.logistics_summary?.access_type || 'Not set')],
                  ['Meet point', String(viewing.logistics_summary?.meet_point || 'Not set')],
                  ['Parking', String(viewing.logistics_summary?.parking || 'Not set')],
                  ['Key location', String(viewing.logistics_summary?.key_location || 'Not set')],
                  ['Tenant', String(viewing.logistics_summary?.tenant_status || 'Unknown')],
                ]}
              />
              <Link
                href={`/dashboard/listings/${viewing.listing_id}/logistics`}
                className="mt-4 inline-flex min-h-10 w-full items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
              >
                Edit listing logistics
              </Link>
            </Panel>

            <Panel title="Viewing state" eyebrow="Schedule">
              <FactGrid
                items={[
                  ['Status', viewing.status],
                  ['Tenant notice', viewing.tenant_notice_required ? 'Required' : 'Not required'],
                  ['Drafts', `${drafts.length}`],
                ]}
              />
              {viewing.status !== 'completed' && (
                <button
                  type="button"
                  onClick={completeViewing}
                  disabled={completingViewing}
                  className="mt-4 inline-flex min-h-10 w-full items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-60"
                >
                  {completingViewing ? 'Completing...' : 'Mark completed'}
                </button>
              )}
            </Panel>

            <Panel title="Post-viewing feedback" eyebrow="Capture">
              <FactGrid
                items={[
                  ['Status', viewing.post_viewing?.status || 'not_requested'],
                  ['Due', viewing.post_viewing?.due_at ? formatDateTime(viewing.post_viewing.due_at) : 'Not scheduled'],
                  ['Requested', viewing.post_viewing?.requested_at ? formatDateTime(viewing.post_viewing.requested_at) : 'Not requested'],
                ]}
              />
              <div className="mt-4 space-y-3">
                <FeedbackSummary label="Buyer" feedback={viewing.post_viewing?.buyer} />
                <FeedbackSummary label="Agent" feedback={viewing.post_viewing?.agent} />
              </div>
              {Boolean((viewing as { follow_up_draft_cta_enabled?: boolean }).follow_up_draft_cta_enabled) &&
                viewing.post_viewing?.buyer && (
                <button
                  type="button"
                  onClick={draftFollowUp}
                  disabled={followUpState === 'working' || followUpState === 'created'}
                  className="mt-3 inline-flex min-h-10 w-full items-center justify-center rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-50 disabled:opacity-60"
                >
                  {followUpState === 'working'
                    ? 'Drafting...'
                    : followUpState === 'created'
                      ? 'Draft added to your queue'
                      : 'Draft follow-up'}
                </button>
              )}
              <button
                type="button"
                onClick={requestPostViewingFeedback}
                disabled={requestingFeedback}
                className="mt-4 inline-flex min-h-10 w-full items-center justify-center rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {requestingFeedback ? 'Requesting...' : viewing.post_viewing?.requested_at ? 'Request again' : 'Request feedback'}
              </button>
              <div className="mt-4 space-y-3 border-t border-neutral-200 pt-4">
                <textarea
                  value={agentFeedback}
                  onChange={(event) => setAgentFeedback(event.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                  placeholder="Agent notes: buyer rating, objections, financing, next step"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={agentScore}
                    onChange={(event) => setAgentScore(event.target.value)}
                    inputMode="numeric"
                    className="min-h-10 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900"
                    placeholder="Score /10"
                  />
                  <select value={agentTemperature} onChange={(event) => setAgentTemperature(event.target.value)} className="min-h-10 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900">
                    <option value="hot">Hot</option>
                    <option value="warm">Warm</option>
                    <option value="cold">Cold</option>
                  </select>
                  <select value={agentFinancing} onChange={(event) => setAgentFinancing(event.target.value)} className="min-h-10 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900">
                    <option value="unknown">Financing unknown</option>
                    <option value="cash">Cash</option>
                    <option value="mortgage">Mortgage</option>
                  </select>
                  <select value={agentNextAction} onChange={(event) => setAgentNextAction(event.target.value)} className="min-h-10 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900">
                    <option value="follow_up">Follow up</option>
                    <option value="call_buyer">Call buyer</option>
                    <option value="discuss_offer">Discuss offer</option>
                    <option value="send_alternatives">Send alternatives</option>
                  </select>
                </div>
                <button
                  type="button"
                  onClick={submitAgentFeedback}
                  disabled={submittingAgentFeedback}
                  className="inline-flex min-h-10 w-full items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-60"
                >
                  {submittingAgentFeedback ? 'Saving...' : 'Save agent feedback'}
                </button>
              </div>
            </Panel>
          </aside>
        </div>
      </main>
    </div>
  )
}

function Panel({ eyebrow, title, children, action }: { eyebrow: string; title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
      <div className="flex items-start justify-between gap-3 border-b border-neutral-200 px-4 py-4 sm:px-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{eyebrow}</p>
          <h2 className="mt-1 text-base font-semibold text-neutral-900">{title}</h2>
        </div>
        {action}
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  )
}

function StatusGrid({ status, tenantRequired }: { status: Record<string, string>; tenantRequired: boolean }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      <StatusTile label="Buyer" value={status.buyer || 'draft'} />
      <StatusTile label="Tenant" value={status.tenant || (tenantRequired ? 'draft' : 'n/a')} />
      <StatusTile label="Calendar" value={status.calendar || 'pending'} />
    </div>
  )
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-3 py-3 shadow-card-sm">
      <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-neutral-900">{value}</p>
    </div>
  )
}

function FactGrid({ items }: { items: Array<[string, string]> }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map(([label, value]) => (
        <div key={label}>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
          <p className="mt-1 text-sm text-neutral-800">{value}</p>
        </div>
      ))}
    </div>
  )
}

function FeedbackSummary({ label, feedback }: { label: string; feedback?: { status?: string; score?: number | null; next_action?: string | null; summary?: string | null } | null }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold text-neutral-900">{label}</p>
        <p className="text-xs text-neutral-500">{feedback?.status || 'not requested'}</p>
      </div>
      {(feedback?.score || feedback?.next_action) && (
        <p className="mt-1 text-xs text-neutral-600">
          {feedback.score ? `${feedback.score}/10` : 'No score'} · {feedback.next_action || 'No next action'}
        </p>
      )}
      {feedback?.summary && <p className="mt-2 text-sm leading-relaxed text-neutral-700">{feedback.summary}</p>}
    </div>
  )
}

function BriefSection({ label, values }: { label: string; values: string[] }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      {values.length === 0 ? (
        <p className="mt-2 text-sm text-neutral-600">Not captured</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {values.map((value) => <span key={value} className="rounded border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs text-neutral-700">{value}</span>)}
        </div>
      )}
    </div>
  )
}

function draftLabel(draft: ViewingNotificationDraft) {
  return draft.type
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatDateTime(value?: string | null) {
  if (!value) return 'No time confirmed'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
