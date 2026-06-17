'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'

type LoadState = 'loading' | 'live' | 'error'

interface TimelineMessage {
  id: string
  role: string
  content: string
  intent?: string | null
  timestamp?: string | null
  metadata?: {
    media?: { media_asset_id?: string; url?: string; mime_type?: string; filename?: string | null }[]
  } & Record<string, unknown>
}

interface MediaWindow {
  open: boolean
  last_inbound_at?: string | null
  expires_at?: string | null
}

interface ListingAsset {
  kind: string
  url: string
  label: string
}

interface OfferRow {
  offer_id: string
  amount?: number | null
  direction: string
  status: string
  created_at?: string | null
}

interface ConversationPayload {
  conversation_id: string
  ai_mode?: string
  ai_mode_changed_at?: string | null
  ai_mode_change_source?: string | null
  media_window?: MediaWindow
  buyer: {
    name?: string | null
    phone?: string | null
    budget_aed?: number | null
  }
  listing: {
    listing_id: string
    project: string
    unit_number?: string | null
    price_aed?: number | null
    bedrooms?: string | number | null
    property_status?: string | null
  }
  brief: {
    summary?: unknown
    suggested_next_action?: string | null
    reason?: string | null
  }
  timeline: TimelineMessage[]
}

interface EscalationThread {
  thread_id: string
  conversation_id: string
  category: string
  state: string
  urgency: string
  latest_question?: string | null
  question_count?: number | null
  envelope_token?: string | null
}

export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [conversation, setConversation] = useState<ConversationPayload | null>(null)
  const [threads, setThreads] = useState<EscalationThread[]>([])
  const [replyBodies, setReplyBodies] = useState<Record<string, string>>({})
  const [replyState, setReplyState] = useState<Record<string, 'working' | 'sent' | 'error'>>({})
  const [aiModeState, setAiModeState] = useState<'idle' | 'working' | 'error'>('idle')
  const [mediaFiles, setMediaFiles] = useState<File[]>([])
  const [mediaCaption, setMediaCaption] = useState('')
  const [listingAssets, setListingAssets] = useState<ListingAsset[]>([])
  const [selectedAssetUrls, setSelectedAssetUrls] = useState<string[]>([])
  const [mediaState, setMediaState] = useState<'idle' | 'working' | 'sent' | 'error'>('idle')
  const [mediaError, setMediaError] = useState('')
  const [offers, setOffers] = useState<OfferRow[]>([])
  const [offerAmount, setOfferAmount] = useState('')
  const [offerState, setOfferState] = useState<'idle' | 'working' | 'error'>('idle')

  useEffect(() => {
    let active = true

    async function loadConversation() {
      setLoadState('loading')
      try {
        const [detailResponse, escalationResponse] = await Promise.all([
          apiFetch(`/api/v1/agent/leads/${conversationId}`),
          apiFetch('/api/v1/agent/escalations?state=active&limit=100'),
        ])
        if (!detailResponse.ok) throw new Error(`Conversation returned ${detailResponse.status}`)
        const detail = await detailResponse.json()
        let escalationThreads: EscalationThread[] = []
        if (escalationResponse.ok) {
          const escalationPayload = await escalationResponse.json()
          escalationThreads = (escalationPayload.threads ?? []).filter(
            (thread: EscalationThread) => thread.conversation_id === conversationId,
          )
        }
        if (!active) return
        setConversation(detail)
        setThreads(escalationThreads)
        setLoadState('live')

        // Offer strip (DAL-165) — best-effort load.
        try {
          const offersResponse = await apiFetch(`/api/v1/agent/offers?conversation_id=${conversationId}`)
          if (offersResponse.ok && active) {
            const offersPayload = await offersResponse.json()
            setOffers(offersPayload.offers ?? [])
          }
        } catch {
          // Offer strip is non-blocking.
        }

        // Attach-from-listing assets (the 80% case) — best-effort load.
        if (detail?.listing?.listing_id) {
          try {
            const assetsResponse = await apiFetch(`/api/v1/agent/listings/${detail.listing.listing_id}/assets`)
            if (assetsResponse.ok && active) {
              const assetsPayload = await assetsResponse.json()
              setListingAssets(assetsPayload.assets ?? [])
            }
          } catch {
            // Asset shortcut is optional — uploads still work without it.
          }
        }
      } catch {
        if (!active) return
        setLoadState('error')
      }
    }

    loadConversation()
    return () => {
      active = false
    }
  }, [conversationId])

  const summary = useMemo(() => summarizeBrief(conversation?.brief.summary), [conversation?.brief.summary])

  async function toggleAiMode() {
    if (!conversation) return
    const paused = conversation.ai_mode === 'agent_controlled'
    // Pausing is confirmation-free — the dangerous direction is resuming.
    if (paused && !window.confirm('Resume Dalya for this buyer? It will answer their next message.')) {
      return
    }
    setAiModeState('working')
    try {
      const response = await apiFetch(`/api/v1/agent/leads/${conversationId}/ai-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: paused ? 'active' : 'agent_controlled' }),
      })
      if (!response.ok) throw new Error(`AI mode returned ${response.status}`)
      const payload = await response.json()
      setConversation((current) => (current ? { ...current, ai_mode: payload.ai_mode } : current))
      setAiModeState('idle')
    } catch {
      setAiModeState('error')
    }
  }

  async function refreshOffers() {
    try {
      const response = await apiFetch(`/api/v1/agent/offers?conversation_id=${conversationId}`)
      if (response.ok) {
        const payload = await response.json()
        setOffers(payload.offers ?? [])
      }
    } catch {
      // non-blocking
    }
  }

  async function logOffer() {
    const amount = Number(offerAmount.replace(/,/g, ''))
    if (!amount || Number.isNaN(amount)) return
    setOfferState('working')
    try {
      const response = await apiFetch('/api/v1/agent/offers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, amount }),
      })
      if (!response.ok) throw new Error(`Offer returned ${response.status}`)
      setOfferAmount('')
      setOfferState('idle')
      await refreshOffers()
    } catch {
      setOfferState('error')
    }
  }

  async function actOnOffer(offerId: string, action: 'confirm' | 'discard') {
    setOfferState('working')
    try {
      const response = await apiFetch(`/api/v1/agent/offers/${offerId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!response.ok) throw new Error(`Offer ${action} returned ${response.status}`)
      setOfferState('idle')
      await refreshOffers()
    } catch {
      setOfferState('error')
    }
  }

  async function sendMedia() {
    if (mediaFiles.length === 0 && selectedAssetUrls.length === 0) return
    setMediaState('working')
    setMediaError('')
    try {
      if (mediaFiles.length > 0) {
        const form = new FormData()
        for (const file of mediaFiles) form.append('files', file)
        form.append('caption', mediaCaption)
        const response = await apiFetch(`/api/v1/agent/leads/${conversationId}/media`, {
          method: 'POST',
          body: form,
        })
        if (!response.ok) throw new Error(await describeMediaError(response))
      }
      if (selectedAssetUrls.length > 0) {
        const response = await apiFetch(`/api/v1/agent/leads/${conversationId}/media/from-listing`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ urls: selectedAssetUrls, caption: mediaFiles.length > 0 ? '' : mediaCaption }),
        })
        if (!response.ok) throw new Error(await describeMediaError(response))
      }
      setMediaFiles([])
      setMediaCaption('')
      setSelectedAssetUrls([])
      setMediaState('sent')
    } catch (error) {
      setMediaError(error instanceof Error ? error.message : 'Could not send the attachments.')
      setMediaState('error')
    }
  }

  async function sendReply(threadId: string) {
    const body = (replyBodies[threadId] ?? '').trim()
    if (!body) {
      setReplyState((current) => ({ ...current, [threadId]: 'error' }))
      return
    }
    setReplyState((current) => ({ ...current, [threadId]: 'working' }))
    try {
      const response = await apiFetch(`/api/v1/agent/escalations/${threadId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body, send_to_buyer: true }),
      })
      if (!response.ok) throw new Error(`Reply returned ${response.status}`)
      setThreads((current) => current.filter((thread) => thread.thread_id !== threadId))
      setReplyState((current) => ({ ...current, [threadId]: 'sent' }))
    } catch {
      setReplyState((current) => ({ ...current, [threadId]: 'error' }))
    }
  }

  return (
    <main className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
      <div className="mx-auto max-w-[1200px]">
        <header className="mb-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
            <Link href="/agent" className="font-medium text-brand-700 hover:text-brand-800">Agent desk</Link>
            <span aria-hidden="true">/</span>
            <Link href="/agent/drafts" className="font-medium text-brand-700 hover:text-brand-800">Drafts</Link>
            <span aria-hidden="true">/</span>
            <span>Conversation</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
            {conversation?.buyer.name || conversation?.buyer.phone || 'Buyer conversation'}
          </h1>
        </header>

        {loadState === 'loading' ? (
          <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-card-sm">
            <div className="h-5 w-64 animate-pulse rounded bg-neutral-200" />
            <div className="mt-4 h-32 animate-pulse rounded bg-neutral-100" />
          </div>
        ) : loadState === 'error' || !conversation ? (
          <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-card-sm">
            <p className="text-sm font-medium text-error-600">Could not load this conversation.</p>
          </div>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
            <section className="rounded-lg border border-neutral-200 bg-white shadow-card-sm">
              <div className="border-b border-neutral-200 px-4 py-4 sm:px-5">
                <p className="text-sm font-semibold text-neutral-900">{conversation.listing.project}</p>
                <p className="mt-1 text-xs text-neutral-500">
                  {conversation.listing.unit_number || 'Unit'} · {formatAed(conversation.listing.price_aed)}
                </p>
                {summary && <p className="mt-3 text-sm leading-relaxed text-neutral-700">{summary}</p>}
              </div>
              <div className="divide-y divide-neutral-200">
                {conversation.timeline.map((message) => (
                  <article key={message.id} className="px-4 py-4 sm:px-5">
                    <div className="flex items-center justify-between gap-3">
                      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                        message.role === 'user'
                          ? 'border-neutral-200 bg-neutral-50 text-neutral-700'
                          : 'border-brand-100 bg-brand-50 text-brand-700'
                      }`}>
                        {message.role === 'user' ? 'Buyer' : 'Dalya / agent'}
                      </span>
                      <span className="text-xs text-neutral-500">{formatShortTime(message.timestamp)}</span>
                    </div>
                    {/* dir="auto" keeps RTL content (Arabic voice transcriptions) rendering correctly */}
                    <p dir="auto" className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-neutral-800">{message.content}</p>
                    {message.intent === 'media_unprocessable' && (
                      <p className="mt-1 text-xs font-medium text-warning-700">Voice/video message Dalya couldn't process — buyer was asked to type it.</p>
                    )}
                    {(message.metadata?.media?.length ?? 0) > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {message.metadata!.media!.map((item, index) => (
                          <a
                            key={item.media_asset_id ?? index}
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
                          >
                            <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                              {item.mime_type?.startsWith('image/') ? 'image' : 'description'}
                            </span>
                            {item.filename || item.mime_type || 'Attachment'}
                          </a>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>

            <aside className="space-y-5">
              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Dalya</p>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                    conversation.ai_mode === 'agent_controlled'
                      ? 'border-warning-100 bg-warning-50 text-warning-700'
                      : 'border-success-100 bg-success-50 text-success-700'
                  }`}>
                    {conversation.ai_mode === 'agent_controlled' ? 'Paused — you have this buyer' : 'Answering buyers'}
                  </span>
                  <button
                    type="button"
                    onClick={toggleAiMode}
                    disabled={aiModeState === 'working'}
                    className="inline-flex items-center justify-center rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-xs font-medium text-neutral-800 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:text-neutral-400"
                  >
                    {aiModeState === 'working'
                      ? 'Updating'
                      : conversation.ai_mode === 'agent_controlled'
                        ? 'Resume Dalya'
                        : 'Pause Dalya'}
                  </button>
                </div>
                {conversation.ai_mode === 'agent_controlled' && (
                  <p className="mt-2 text-xs leading-relaxed text-neutral-600">
                    Buyer messages are forwarded to you on WhatsApp and wait here unanswered.
                  </p>
                )}
                {aiModeState === 'error' && (
                  <p className="mt-2 text-xs font-medium text-error-600">Could not update Dalya for this conversation.</p>
                )}
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Buyer</p>
                <dl className="mt-3 grid gap-3 text-sm">
                  <Fact label="Phone" value={conversation.buyer.phone || 'Not captured'} />
                  <Fact label="Budget" value={formatAed(conversation.buyer.budget_aed)} />
                  <Fact label="Next action" value={conversation.brief.suggested_next_action || 'Review'} />
                </dl>
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Offers</p>
                {offers.length === 0 ? (
                  <p className="mt-3 text-sm text-neutral-600">No offers logged on this thread.</p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {offers.map((offer) => (
                      <div key={offer.offer_id} className="rounded-md border border-neutral-200 px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-neutral-900">
                            {offer.amount ? `AED ${Number(offer.amount).toLocaleString()}` : 'Amount TBC'}
                          </p>
                          <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                            offer.status === 'draft_pending_confirm'
                              ? 'border-brand-100 bg-brand-50 text-brand-700'
                              : offer.status === 'submitted' || offer.status === 'countered'
                                ? 'border-warning-100 bg-warning-50 text-warning-700'
                                : offer.status === 'accepted'
                                  ? 'border-success-100 bg-success-50 text-success-700'
                                  : 'border-neutral-200 bg-neutral-100 text-neutral-600'
                          }`}>
                            {offer.status === 'draft_pending_confirm' ? 'Pending confirm' : labelFromKey(offer.status)}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-neutral-500">
                          {offer.direction === 'seller_counter' ? 'Seller counter' : 'Buyer offer'}
                        </p>
                        {offer.status === 'draft_pending_confirm' && (
                          <div className="mt-2 flex gap-2">
                            <button
                              type="button"
                              onClick={() => actOnOffer(offer.offer_id, 'confirm')}
                              disabled={offerState === 'working'}
                              className="rounded-md bg-brand-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-800 disabled:bg-neutral-300"
                            >
                              Confirm
                            </button>
                            <button
                              type="button"
                              onClick={() => actOnOffer(offer.offer_id, 'discard')}
                              disabled={offerState === 'working'}
                              className="rounded-md border border-neutral-300 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                            >
                              Discard
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-3 flex items-center gap-2 border-t border-neutral-200 pt-3">
                  <input
                    type="text"
                    inputMode="numeric"
                    value={offerAmount}
                    onChange={(event) => setOfferAmount(event.target.value)}
                    placeholder="Log offer (AED)"
                    className="w-full rounded-md border border-neutral-300 px-2.5 py-1.5 text-sm outline-none placeholder:text-neutral-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                  />
                  <button
                    type="button"
                    onClick={logOffer}
                    disabled={offerState === 'working' || !offerAmount.trim()}
                    className="shrink-0 rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-medium text-neutral-800 hover:bg-neutral-50 disabled:opacity-50"
                  >
                    Log
                  </button>
                </div>
                {offerState === 'error' && <p className="mt-2 text-xs font-medium text-error-600">Could not update offers.</p>}
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Send media</p>
                {conversation.media_window && !conversation.media_window.open ? (
                  <p className="mt-3 text-sm leading-relaxed text-neutral-600">
                    The buyer's 24-hour session window is closed. Send an approved template first to reopen the
                    conversation — free-form media is blocked until they reply.
                  </p>
                ) : (
                  <>
                    <label className="mt-3 block">
                      <span className="sr-only">Attachments</span>
                      <input
                        type="file"
                        multiple
                        accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                        onChange={(event) => setMediaFiles(Array.from(event.target.files ?? []))}
                        className="block w-full text-xs text-neutral-600 file:mr-3 file:rounded-md file:border file:border-neutral-300 file:bg-white file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-neutral-800 hover:file:bg-neutral-50"
                      />
                    </label>
                    {listingAssets.length > 0 && (
                      <div className="mt-3">
                        <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">Attach from listing</p>
                        <div className="mt-2 max-h-32 space-y-1 overflow-y-auto">
                          {listingAssets.map((asset) => (
                            <label key={asset.url} className="flex items-center gap-2 text-xs text-neutral-700">
                              <input
                                type="checkbox"
                                checked={selectedAssetUrls.includes(asset.url)}
                                onChange={(event) =>
                                  setSelectedAssetUrls((current) =>
                                    event.target.checked
                                      ? [...current, asset.url]
                                      : current.filter((url) => url !== asset.url),
                                  )
                                }
                                className="h-3.5 w-3.5 rounded border-neutral-300"
                              />
                              <span className="truncate">{asset.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                    <input
                      type="text"
                      value={mediaCaption}
                      onChange={(event) => setMediaCaption(event.target.value)}
                      placeholder="Caption (optional)"
                      className="mt-3 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                    />
                    <button
                      type="button"
                      onClick={sendMedia}
                      disabled={mediaState === 'working' || (mediaFiles.length === 0 && selectedAssetUrls.length === 0)}
                      className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
                    >
                      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">attach_file</span>
                      {mediaState === 'working' ? 'Sending' : 'Send to buyer'}
                    </button>
                    {mediaState === 'sent' && <p className="mt-2 text-xs font-medium text-success-700">Attachments sent.</p>}
                    {mediaState === 'error' && <p className="mt-2 text-xs font-medium text-error-600">{mediaError}</p>}
                  </>
                )}
              </section>

              <section className="rounded-lg border border-neutral-200 bg-white p-4 shadow-card-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Open escalations</p>
                {threads.length === 0 ? (
                  <p className="mt-3 text-sm text-neutral-600">None open.</p>
                ) : (
                  <div className="mt-3 space-y-4">
                    {threads.map((thread) => (
                      <div key={thread.thread_id} className="rounded-md border border-neutral-200 p-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full border border-warning-100 bg-warning-50 px-2 py-0.5 text-[11px] font-medium text-warning-700">
                            {labelFromKey(thread.urgency)}
                          </span>
                          <span className="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-700">
                            {labelFromKey(thread.category)}
                          </span>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-neutral-800">{thread.latest_question || 'Agent review needed.'}</p>
                        <textarea
                          value={replyBodies[thread.thread_id] ?? ''}
                          onChange={(event) => setReplyBodies((current) => ({ ...current, [thread.thread_id]: event.target.value }))}
                          rows={4}
                          className="mt-3 w-full resize-none rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm leading-relaxed text-neutral-900 outline-none transition-colors focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                        />
                        <button
                          type="button"
                          onClick={() => sendReply(thread.thread_id)}
                          disabled={replyState[thread.thread_id] === 'working' || !(replyBodies[thread.thread_id] ?? '').trim()}
                          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300"
                        >
                          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">send</span>
                          {replyState[thread.thread_id] === 'working' ? 'Sending' : 'Send to buyer'}
                        </button>
                        {replyState[thread.thread_id] === 'error' && <p className="mt-2 text-xs font-medium text-error-600">Could not send this reply.</p>}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </aside>
          </div>
        )}
      </div>
    </main>
  )
}

async function describeMediaError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (detail?.reason === 'session_window_closed') {
      return 'The buyer’s 24-hour session window is closed. Use the template-first reopen flow before sending media.'
    }
    if (detail?.message) return String(detail.message)
  } catch {
    // fall through to the generic message
  }
  return `Send failed (${response.status}).`
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-[0.1em] text-neutral-500">{label}</dt>
      <dd className="mt-1 font-medium text-neutral-800">{value}</dd>
    </div>
  )
}

function summarizeBrief(value: unknown): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    return String(record.summary || record.one_line || record.key_question || '')
  }
  return ''
}

function formatAed(value: number | null | undefined): string {
  if (!value) return 'Not confirmed'
  return `AED ${Number(value).toLocaleString()}`
}

function labelFromKey(value: string | null | undefined): string {
  return String(value || 'general')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatShortTime(value: string | null | undefined): string {
  if (!value) return 'Today'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
