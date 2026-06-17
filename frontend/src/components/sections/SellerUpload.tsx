'use client'

import { useState, useEffect, useCallback, useRef, useMemo, useSyncExternalStore } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'
import { GoldButton } from '@/components/ui/GoldButton'
import { Badge } from '@/components/ui/Badge'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/providers/AuthProvider'
import { createClient } from '@/lib/supabase/client'
import { apiFetch } from '@/lib/api'
import { formatMoney } from '@/lib/utils'

/* ---------- types ---------- */

interface PaymentMilestone {
  label: string
  percentage: number
  amount: number
  date?: string
  status?: 'paid' | 'upcoming' | 'due'
}

interface ParseResult {
  listing_id: string
  property_name: string
  developer: string
  unit_number: string
  property_type?: string
  sub_community?: string
  bua_sqft?: number
  plot_sqft?: number
  parking?: string
  property_status?: string
  total_price?: number
  paid_to_date?: number
  total_paid_percent?: number
  noc_eligible?: boolean
  handover_date?: string
  payment_milestones?: PaymentMilestone[]
}

interface ActivateResult {
  whatsapp_link: string
  listing_id: string
  property: string
}

type ContactMethod = 'whatsapp' | 'email'

type Step = 1 | 2 | 3 | 4

/* ---------- session storage helpers ---------- */

const DRAFT_PREFIX = 'dalya-spa-draft-'
const BASE_PATH = '/dashboard/listings/new'

// A tiny pub/sub around sessionStorage so useSyncExternalStore can subscribe
// to draft changes. Using useSyncExternalStore (rather than useEffect +
// setState) keeps the component free of "setState inside effect" lint errors
// and gives correct SSR behaviour (getServerSnapshot returns null).
const draftListeners = new Set<() => void>()
function notifyDrafts() {
  draftListeners.forEach(fn => fn())
}
function subscribeDrafts(cb: () => void) {
  draftListeners.add(cb)
  return () => { draftListeners.delete(cb) }
}

function saveDraft(listingId: string, parsed: ParseResult) {
  try {
    sessionStorage.setItem(`${DRAFT_PREFIX}${listingId}`, JSON.stringify(parsed))
    notifyDrafts()
  } catch {
    // sessionStorage may be unavailable (SSR, private mode); fall back to memory only
  }
}

function clearDraft(listingId: string) {
  try {
    sessionStorage.removeItem(`${DRAFT_PREFIX}${listingId}`)
    notifyDrafts()
  } catch {
    // ignore
  }
}

// Cache so getSnapshot returns a stable reference until the underlying
// JSON actually changes — useSyncExternalStore tears otherwise.
const draftSnapshotCache = new Map<string, { json: string; value: ParseResult | null }>()

function getDraftSnapshot(listingId: string): ParseResult | null {
  if (!listingId) return null
  if (typeof window === 'undefined') return null
  const raw = sessionStorage.getItem(`${DRAFT_PREFIX}${listingId}`) || ''
  const cached = draftSnapshotCache.get(listingId)
  if (cached && cached.json === raw) return cached.value
  let value: ParseResult | null = null
  if (raw) {
    try { value = JSON.parse(raw) as ParseResult } catch { value = null }
  }
  draftSnapshotCache.set(listingId, { json: raw, value })
  return value
}

/* ---------- step indicator ---------- */

const STEP_LABELS = ['Upload SPA', 'Verify Details', 'Listing Details', 'Submitted']

function StepIndicator({ current }: { current: Step }) {
  return (
    <div className="flex items-center gap-2 sm:gap-4 mb-12">
      {STEP_LABELS.map((label, i) => {
        const stepNum = (i + 1) as Step
        const isActive = stepNum === current
        const isDone = stepNum < current
        return (
          <div key={label} className="flex items-center gap-2 sm:gap-4">
            {i > 0 && (
              <div className={`w-6 sm:w-10 h-px ${isDone ? 'bg-gold/40' : 'bg-gold/10'}`} />
            )}
            <div className="flex items-center gap-2">
              <span
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold font-mono shrink-0
                  ${isActive ? 'bg-gold text-ink' : isDone ? 'bg-gold/20 text-gold' : 'bg-gold/5 text-n-500'}
                `}
              >
                {isDone ? (
                  <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>check</span>
                ) : (
                  stepNum
                )}
              </span>
              <span className={`text-xs tracking-wide hidden sm:inline ${isActive ? 'text-sand' : 'text-n-500'}`}>
                {label}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ---------- step 1: upload ---------- */

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']

const PARSE_STAGES = [
  { label: 'Uploading document', target: 15 },
  { label: 'Analyzing document', target: 45 },
  { label: 'Extracting property details', target: 70 },
  { label: 'Processing payment schedule', target: 85 },
  { label: 'Finalizing', target: 95 },
]

function useParseProgress(active: boolean) {
  const [progress, setProgress] = useState(0)
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    if (!active) {
      setProgress(0)
      setStageIndex(0)
      return
    }

    // Advance through stages on a schedule that mimics real parse timing
    const stageTimings = [800, 3000, 6000, 5000, 4000] // ms per stage
    let elapsed = 0
    let currentStage = 0

    const interval = setInterval(() => {
      elapsed += 100
      // Find which stage we're in based on elapsed time
      let timeSum = 0
      for (let i = 0; i < stageTimings.length; i++) {
        timeSum += stageTimings[i]
        if (elapsed < timeSum) {
          currentStage = i
          break
        }
        if (i === stageTimings.length - 1) currentStage = i
      }

      setStageIndex(currentStage)

      // Calculate progress within current stage with deceleration
      const stageStart = currentStage > 0
        ? PARSE_STAGES[currentStage - 1].target
        : 0
      const stageEnd = PARSE_STAGES[currentStage].target
      const stageElapsed = elapsed - stageTimings.slice(0, currentStage).reduce((a, b) => a + b, 0)
      const stageDuration = stageTimings[currentStage]
      const stageProgress = Math.min(stageElapsed / stageDuration, 1)
      // Ease-out curve: fast start, slow approach to target
      const eased = 1 - Math.pow(1 - stageProgress, 3)
      const newProgress = stageStart + (stageEnd - stageStart) * eased

      setProgress(Math.min(newProgress, 95)) // never exceed 95% until done
    }, 100)

    return () => clearInterval(interval)
  }, [active])

  const complete = () => setProgress(100)
  const stage = PARSE_STAGES[stageIndex]?.label || 'Processing'

  return { progress, stage, complete }
}

function StepUpload({
  onParsed,
}: {
  onParsed: (result: ParseResult) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { progress, stage, complete } = useParseProgress(loading)

  const handleFile = useCallback((f: File) => {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      setError('Please upload a PDF, JPEG, or PNG file.')
      return
    }
    setError(null)
    setFile(f)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const f = e.dataTransfer.files[0]
      if (f) handleFile(f)
    },
    [handleFile],
  )

  const handleSubmit = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await apiFetch('/api/v1/parse-spa', { method: 'POST', body: form })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Upload failed (${res.status})`)
      }
      const raw = await res.json()
      complete() // jump to 100%

      // Map backend SPAParseResponse shape to frontend ParseResult
      const spa = raw.data || raw
      const schedule = spa.payment_schedule || []
      const now = new Date()

      const milestones: PaymentMilestone[] = schedule.map((m: Record<string, unknown>) => {
        const dueDate = m.due_date ? new Date(m.due_date as string) : null
        const isPaid = dueDate ? dueDate <= now : false
        return {
          label: (m.milestone as string) || `Installment ${m.instalment_number}`,
          percentage: (m.percentage as number) || 0,
          amount: (m.amount_aed as number) || 0,
          date: m.due_date as string | undefined,
          status: isPaid ? 'paid' as const : 'upcoming' as const,
        }
      })

      const totalPaid = milestones
        .filter(m => m.status === 'paid')
        .reduce((sum, m) => sum + m.amount, 0)

      // Brief pause at 100% before advancing
      await new Promise(r => setTimeout(r, 400))

      const parsed: ParseResult = {
        listing_id: raw.listing_id || spa.listing_id || '',
        property_name: spa.project || 'Unknown',
        developer: spa.developer || 'Unknown',
        unit_number: spa.unit_number || '—',
        property_type: spa.property_type,
        sub_community: spa.sub_community,
        bua_sqft: spa.bua_sqft,
        plot_sqft: spa.plot_sqft,
        parking: spa.parking as string | undefined,
        property_status: spa.property_status as string | undefined,
        total_price: spa.purchase_price_aed,
        paid_to_date: totalPaid || undefined,
        total_paid_percent: spa.total_paid_percent as number | undefined,
        noc_eligible: spa.noc_eligible as boolean | undefined,
        handover_date: spa.estimated_completion_date || spa.handover_date_description,
        payment_milestones: milestones,
      }
      onParsed(parsed)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.35 }}
    >
      {loading ? (
        /* Progress state */
        <div className="py-16 px-8 text-center">
          <span className="material-symbols-outlined text-gold mb-6 block" style={{ fontSize: '48px' }}>
            document_scanner
          </span>
          <p className="text-sand text-lg font-semibold mb-2">{stage}</p>
          <p className="text-n-500 text-sm mb-8">This typically takes 15–30 seconds</p>

          {/* Progress bar */}
          <div className="max-w-md mx-auto">
            <div className="h-2 rounded-full bg-ink/60 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gold"
                initial={{ width: '0%' }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              />
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-n-500">{file?.name}</span>
              <span className="text-[11px] text-gold font-mono">{Math.round(progress)}%</span>
            </div>
          </div>
        </div>
      ) : (
        /* Upload state */
        <>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
            aria-label="Upload your SPA PDF"
            className={`
              relative flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed
              cursor-pointer transition-colors py-20 px-8 text-center min-h-[240px]
              ${dragging ? 'border-gold/50 bg-gold/5' : 'border-gold/15 hover:border-gold/30 bg-ink/40'}
            `}
          >
            <span className="material-symbols-outlined text-gold/40" style={{ fontSize: '48px' }}>
              upload_file
            </span>

            {file ? (
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-gold" style={{ fontSize: '18px' }}>description</span>
                <span className="text-sand text-sm font-medium">{file.name}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null) }}
                  className="text-n-500 hover:text-sand ml-1"
                  aria-label="Remove file"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>close</span>
                </button>
              </div>
            ) : (
              <>
                <p className="text-sand text-sm font-medium">
                  Drop your SPA here or <span className="text-gold underline underline-offset-2">browse</span>
                </p>
                <p className="text-n-500 text-xs">PDF, JPEG, or PNG</p>
              </>
            )}

            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,image/jpeg,image/png"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) handleFile(f)
              }}
            />
          </div>

          {error && (
            <p className="mt-4 text-sm text-red-400" role="alert">{error}</p>
          )}

          <div className="mt-8">
            <GoldButton onClick={handleSubmit} className={!file ? 'opacity-50 pointer-events-none' : ''}>
              Continue
            </GoldButton>
          </div>
        </>
      )}
    </motion.div>
  )
}

/* ---------- step 2: verify parsed details ---------- */

function StepVerify({
  parseResult,
  onConfirm,
  onReupload,
}: {
  parseResult: ParseResult
  onConfirm: () => void
  onReupload: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.35 }}
      className="max-w-2xl"
    >
      <h3 className="text-sand text-lg font-semibold mb-2">Does this look correct?</h3>
      <p className="text-n-500 text-sm mb-8 leading-relaxed">
        We extracted the following from your SPA. Confirm these details before setting your asking price.
      </p>

      <div className="rounded-xl surface-2 p-5 sm:p-7">
        {/* NOC eligibility pill — brand-required trust signal */}
        {parseResult.noc_eligible != null && (
          <div className="flex items-center justify-between mb-5 pb-5 border-b border-gold/8">
            <div className="flex items-center gap-3">
              <Badge variant={parseResult.noc_eligible ? 'sage' : 'copper'}>
                {parseResult.noc_eligible ? 'NOC Eligible' : 'NOC Pending'}
              </Badge>
              {parseResult.total_paid_percent != null && (
                <span className="text-xs text-n-500 font-mono">
                  {parseResult.total_paid_percent}% paid
                </span>
              )}
            </div>
            {parseResult.property_status && (
              <span className="text-[11px] text-n-500 uppercase tracking-widest">
                {parseResult.property_status}
              </span>
            )}
          </div>
        )}

        {/* property details grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-y-6 gap-x-8">
          <DetailCell label="Project" value={parseResult.property_name} />
          {parseResult.sub_community && (
            <DetailCell label="Sub-community" value={parseResult.sub_community} />
          )}
          <DetailCell label="Developer" value={parseResult.developer} />
          <DetailCell label="Unit" value={parseResult.unit_number} />
          {parseResult.property_type && (
            <DetailCell label="Type" value={parseResult.property_type} />
          )}
          {parseResult.bua_sqft != null && (
            <DetailCell
              label="BUA"
              value={`${parseResult.bua_sqft.toLocaleString()} sqft`}
              mono
            />
          )}
          {parseResult.plot_sqft != null && (
            <DetailCell
              label="Plot"
              value={`${parseResult.plot_sqft.toLocaleString()} sqft`}
              mono
            />
          )}
          {parseResult.total_price != null && (
            <DetailCell
              label="Purchase Price"
              value={`AED ${formatMoney(parseResult.total_price)}`}
              mono
              gold
            />
          )}
          {parseResult.paid_to_date != null && (
            <DetailCell
              label="Paid to Date"
              value={`AED ${formatMoney(parseResult.paid_to_date)}`}
              mono
            />
          )}
          {parseResult.handover_date && (
            <DetailCell
              label="Handover"
              value={parseResult.handover_date}
              mono={/^\d{4}-\d{2}-\d{2}$/.test(parseResult.handover_date)}
            />
          )}
        </div>

        {/* payment milestones */}
        {parseResult.payment_milestones && parseResult.payment_milestones.length > 0 && (
          <div className="mt-7 pt-6 border-t border-gold/8">
            <p className="text-[11px] text-n-500 uppercase tracking-widest mb-4">Payment Schedule</p>
            <div className="space-y-2.5">
              {parseResult.payment_milestones.map((m, i) => (
                <div
                  key={i}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between text-sm py-1.5 gap-1 sm:gap-0"
                >
                  <span className="text-sand">
                    {m.label
                      .replace(/\bInstalment\b/gi, 'Installment')
                      .replace(/\s*\(\*+\)/g, '')
                      .trim()}
                  </span>
                  <div className="flex items-center gap-4">
                    {m.date && <span className="text-n-500 text-xs hidden sm:inline">{m.date}</span>}
                    <span className="font-mono text-n-500 text-xs w-10 text-right">{m.percentage}%</span>
                    <span className="font-mono text-sand text-sm w-32 text-right">
                      AED {formatMoney(m.amount)}
                    </span>
                    <span
                      className={`text-xs font-semibold ml-1 w-16 text-right ${
                        m.status === 'paid' ? 'text-sage' : 'text-gold/70'
                      }`}
                    >
                      {m.status === 'paid' ? 'Paid' : 'Upcoming'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 flex items-center gap-6">
        <GoldButton onClick={onConfirm}>Confirm &amp; Continue</GoldButton>
        <button
          onClick={onReupload}
          className="text-n-500 text-sm hover:text-sand transition-colors underline underline-offset-2"
        >
          Re-upload
        </button>
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

/* ---------- step 3: listing details ---------- */

function StepDetails({
  parseResult,
  onActivated,
}: {
  parseResult: ParseResult
  onActivated: (result: ActivateResult) => void
}) {
  const { user } = useAuth()
  const metadata = (user?.user_metadata ?? {}) as Record<string, unknown>
  const savedPhone = (metadata.phone as string) || ''
  const userEmail = user?.email || ''

  const [askingPrice, setAskingPrice] = useState('')
  const [threshold, setThreshold] = useState('')
  const [notes, setNotes] = useState('')
  // Default to whatsapp if we have a saved phone, otherwise email if we have an email
  const [contactMethod, setContactMethod] = useState<ContactMethod>(savedPhone ? 'whatsapp' : 'whatsapp')
  const [contactValue, setContactValue] = useState(savedPhone || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // When switching contact method, pre-fill from saved profile data
  const handleContactMethodChange = (method: ContactMethod) => {
    setContactMethod(method)
    if (method === 'whatsapp' && savedPhone && !contactValue) {
      setContactValue(savedPhone)
    } else if (method === 'email' && userEmail && !contactValue) {
      setContactValue(userEmail)
    }
  }

  // Strip commas and format numeric input; allow digits + single decimal point
  const formatNumericInput = (raw: string): string => {
    // Remove everything except digits and dots
    const cleaned = raw.replace(/[^\d.]/g, '')
    // Keep only the first decimal point
    const parts = cleaned.split('.')
    const intPart = parts[0] || ''
    const decPart = parts.length > 1 ? '.' + parts.slice(1).join('').slice(0, 2) : ''
    // Add commas to integer portion
    const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    return withCommas + decPart
  }

  const parseNumericInput = (formatted: string): string => {
    return formatted.replace(/,/g, '')
  }

  const handleSubmit = async () => {
    if (!askingPrice || !contactValue) return
    if (threshold) {
      const askNum = Number(parseNumericInput(askingPrice))
      const thrNum = Number(parseNumericInput(threshold))
      if (thrNum >= askNum) {
        setError('Minimum offer to alert must be less than the asking price.')
        return
      }
    }
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      params.set('seller_asking_price', parseNumericInput(askingPrice))
      if (threshold) params.set('negotiation_threshold_aed', parseNumericInput(threshold))
      if (notes) params.set('seller_notes', notes)
      const res = await apiFetch(`/api/v1/listings/${parseResult.listing_id}/activate?${params.toString()}`, {
        method: 'POST',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Submission failed (${res.status})`)
      }
      const data = await res.json()

      // Save phone to user_metadata if seller entered one via WhatsApp and it wasn't saved before
      if (contactMethod === 'whatsapp' && contactValue && contactValue !== savedPhone) {
        try {
          const supabase = createClient()
          await supabase.auth.updateUser({
            data: { ...metadata, phone: contactValue },
          })
        } catch {
          // Non-critical — don't block listing submission
        }
      }

      onActivated({
        whatsapp_link: data.whatsapp_link,
        listing_id: data.listing_id,
        property: data.property,
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const inputCls =
    'w-full rounded-lg bg-deep border border-gold/10 px-4 py-3 text-sand text-sm placeholder:text-n-500 focus:outline-none focus:border-gold/30 transition-colors'

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.35 }}
      className="max-w-lg"
    >
      <div className="space-y-6">
        <div>
          <label htmlFor="asking-price" className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Asking Price (AED) <span className="text-gold">*</span>
          </label>
          <input
            id="asking-price"
            type="text"
            inputMode="decimal"
            required
            className={`${inputCls} font-mono`}
            placeholder="e.g. 1,850,000"
            value={askingPrice}
            onChange={(e) => setAskingPrice(formatNumericInput(e.target.value))}
          />
        </div>

        <div>
          <label htmlFor="threshold" className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Minimum offer to alert you (AED)
          </label>
          <input
            id="threshold"
            type="text"
            inputMode="decimal"
            className={`${inputCls} font-mono`}
            placeholder="Optional"
            value={threshold}
            onChange={(e) => setThreshold(formatNumericInput(e.target.value))}
          />
        </div>

        {/* Contact method */}
        <div>
          <span className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Preferred contact method <span className="text-gold">*</span>
          </span>
          <div className="flex gap-3 mb-3">
            <button
              type="button"
              onClick={() => handleContactMethodChange('whatsapp')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                contactMethod === 'whatsapp'
                  ? 'border-gold/30 bg-gold/10 text-gold'
                  : 'border-gold/10 bg-deep text-n-500 hover:border-gold/20'
              }`}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>chat</span>
              WhatsApp
            </button>
            <button
              type="button"
              onClick={() => handleContactMethodChange('email')}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                contactMethod === 'email'
                  ? 'border-gold/30 bg-gold/10 text-gold'
                  : 'border-gold/10 bg-deep text-n-500 hover:border-gold/20'
              }`}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>mail</span>
              Email
            </button>
          </div>
          <input
            id="contact-value"
            type={contactMethod === 'email' ? 'email' : 'tel'}
            required
            className={inputCls}
            placeholder={contactMethod === 'whatsapp' ? '+971 50 123 4567' : 'you@example.com'}
            value={contactValue}
            onChange={(e) => setContactValue(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="seller-notes" className="block text-[11px] text-n-500 uppercase tracking-widest mb-2.5">
            Notes for the AI about this property
          </label>
          <textarea
            id="seller-notes"
            rows={4}
            className={inputCls}
            placeholder="e.g. Pool view, upgraded flooring, willing to negotiate on payment plan timing"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <p className="mt-4 text-sm text-red-400" role="alert">{error}</p>
      )}

      <div className="mt-8">
        <GoldButton onClick={handleSubmit} className={!askingPrice || !contactValue || loading ? 'opacity-50 pointer-events-none' : ''}>
          {loading ? 'Submitting...' : 'Submit Listing'}
        </GoldButton>
      </div>
    </motion.div>
  )
}

/* ---------- step 4: confirmation ---------- */

interface ProcessingStage {
  key: string
  label: string
  description: string
  status: 'pending' | 'in_progress' | 'complete' | 'blocked'
  at: string | null
  note: string | null
}

const STAGE_ICONS: Record<string, string> = {
  spa_verified: 'check_circle',
  listing_review: 'hourglass_top',
  trakheesi_permit: 'verified',
  portal_listings: 'language',
  ai_advisor_live: 'smart_toy',
}

function StepConfirmation({ propertyName, listingId }: { propertyName: string; listingId: string }) {
  const [stages, setStages] = useState<ProcessingStage[]>([])

  useEffect(() => {
    let cancelled = false
    async function fetchStages() {
      try {
        const res = await apiFetch(`/api/v1/seller/listings/${listingId}/leads`)
        if (!res.ok || cancelled) return
        const data = await res.json()
        if (!cancelled && data.processing_stages) {
          setStages(data.processing_stages)
        }
      } catch {
        // Stages are optional — fail silently
      }
    }
    if (listingId) fetchStages()
    return () => { cancelled = true }
  }, [listingId])

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.35 }}
      className="max-w-lg"
    >
      <div className="flex items-center gap-4 mb-6">
        <span className="material-symbols-outlined text-sage" style={{ fontSize: '36px' }}>check_circle</span>
        <h3 className="editorial text-3xl font-bold text-sand">Listing submitted</h3>
      </div>

      <p className="text-n-500 text-sm mb-8 leading-relaxed max-w-md">
        Your listing for <span className="text-sand font-medium">{propertyName}</span> has been received.
        Our team will review and process your listing through the following steps:
      </p>

      {/* Status pipeline */}
      <div className="rounded-xl surface-2 p-5 sm:p-7 space-y-4">
        {stages.length === 0 ? (
          <p className="text-n-500 text-sm">Loading status...</p>
        ) : (
          stages.map((s) => (
            <StatusRow
              key={s.key}
              icon={STAGE_ICONS[s.key] || 'circle'}
              label={s.label}
              description={s.description}
              status={s.status}
              note={s.note}
            />
          ))
        )}
      </div>

      <p className="text-n-500 text-xs mt-6 leading-relaxed">
        You&apos;ll be notified as each step completes. Track progress from your dashboard.
      </p>

      <div className="mt-8">
        <GoldButton href="/dashboard">Go to Dashboard</GoldButton>
      </div>
    </motion.div>
  )
}

export function StatusRow({
  icon,
  label,
  description,
  status,
  note,
}: {
  icon: string
  label: string
  description: string
  status: 'pending' | 'in_progress' | 'complete' | 'blocked'
  note?: string | null
}) {
  const iconColor =
    status === 'complete' ? 'text-sage' :
    status === 'in_progress' ? 'text-gold' :
    status === 'blocked' ? 'text-red-400' :
    'text-n-500/40'
  const labelColor = status === 'pending' ? 'text-n-500' : 'text-sand'

  const badge =
    status === 'complete' ? { text: 'Complete', cls: 'text-sage' } :
    status === 'in_progress' ? { text: 'In Progress', cls: 'text-gold' } :
    status === 'blocked' ? { text: 'Blocked', cls: 'text-red-400' } :
    null

  return (
    <div className={`flex items-start gap-4 ${status === 'blocked' ? 'rounded-lg bg-red-400/5 p-3 -m-3' : ''}`}>
      <span className={`material-symbols-outlined mt-0.5 ${iconColor}`} style={{ fontSize: '20px' }}>{icon}</span>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${labelColor}`}>{label}</p>
        {status === 'blocked' && note ? (
          <p className="text-xs text-red-400/80 mt-1">{note}</p>
        ) : (
          <p className="text-xs text-n-500 mt-0.5">{note || description}</p>
        )}
      </div>
      {badge && (
        <span className={`text-[10px] font-semibold uppercase tracking-widest mt-0.5 ${badge.cls} whitespace-nowrap`}>
          {badge.text}
        </span>
      )}
    </div>
  )
}

/* ---------- main ---------- */

export function SellerUpload() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()

  const rawStep = Number(searchParams.get('step') || '1')
  const urlStep = (rawStep >= 1 && rawStep <= 4 ? rawStep : 1) as Step
  const urlId = searchParams.get('id') || ''

  // Parsed SPA data lives in sessionStorage (too large for the URL). We read
  // it through useSyncExternalStore so that refresh/back/forward/tab-reopen
  // all pick up the latest draft automatically.
  const getSnapshot = useCallback(() => getDraftSnapshot(urlId), [urlId])
  const getServerSnapshot = useCallback(() => null, [])
  const parseResult = useSyncExternalStore(subscribeDrafts, getSnapshot, getServerSnapshot)

  // propertyName is only used on step 4 to show a confirmation header after
  // activation. Falls back to the parsed property_name when sessionStorage
  // has already been cleared by handleActivated.
  const [propertyName, setPropertyName] = useState('')

  // Determine the effective step. If the URL says step 2/3 but we have no
  // parsed data, fall back to step 1 (handles: user bookmarked mid-flow,
  // sessionStorage was cleared, user landed on ?step=2 without an id).
  // Note: during SSR parseResult is null, so steps 2/3/4 will render as step 1
  // on the server. This is fine because the wizard is only reached after
  // client-side navigation from the dashboard anyway.
  const effectiveStep: Step = useMemo(() => {
    if (urlStep === 1) return 1
    if (urlStep === 4) return parseResult || propertyName ? 4 : 1
    // steps 2, 3 require parsed data
    if (!parseResult) return 1
    return urlStep
  }, [urlStep, parseResult, propertyName])

  const goToStep = useCallback((step: Step, listingId?: string) => {
    const params = new URLSearchParams()
    if (step > 1) {
      params.set('step', String(step))
      if (listingId) params.set('id', listingId)
    }
    const qs = params.toString()
    router.push(qs ? `${BASE_PATH}?${qs}` : BASE_PATH, { scroll: false })
  }, [router])

  const handleParsed = useCallback((result: ParseResult) => {
    if (result.listing_id) {
      saveDraft(result.listing_id, result)
    }
    goToStep(2, result.listing_id)
  }, [goToStep])

  const handleReupload = useCallback(() => {
    if (parseResult?.listing_id) {
      clearDraft(parseResult.listing_id)
    }
    goToStep(1)
  }, [parseResult, goToStep])

  const handleConfirm = useCallback(() => {
    if (!parseResult) return
    goToStep(3, parseResult.listing_id)
  }, [parseResult, goToStep])

  const handleActivated = useCallback((result: ActivateResult) => {
    setPropertyName(result.property || parseResult?.property_name || '')
    // Clean up the sessionStorage draft once the listing is submitted
    if (result.listing_id) {
      clearDraft(result.listing_id)
    }
    // Invalidate cached listings so dashboard shows the new listing immediately
    queryClient.invalidateQueries({ queryKey: ['seller-listings'] })
    goToStep(4, result.listing_id)
  }, [parseResult, goToStep, queryClient])

  return (
    <section className="pt-12 pb-24">
      <div className="max-w-3xl mx-auto px-6 lg:px-10">
        <SectionEyebrow>Upload Your SPA</SectionEyebrow>
        <h2 className="editorial text-4xl md:text-5xl font-bold text-sand tracking-tight mb-5">
          List your off-plan in minutes
        </h2>
        <p className="text-n-500 text-sm mb-14 max-w-md leading-relaxed">
          Dalya parses your Sale and Purchase Agreement automatically.
          No manual data entry. Live on every portal in 30 minutes.
        </p>

        <StepIndicator current={effectiveStep} />

        <AnimatePresence mode="wait">
          {effectiveStep === 1 && (
            <StepUpload key="step-1" onParsed={handleParsed} />
          )}
          {effectiveStep === 2 && parseResult && (
            <StepVerify
              key="step-2"
              parseResult={parseResult}
              onConfirm={handleConfirm}
              onReupload={handleReupload}
            />
          )}
          {effectiveStep === 3 && parseResult && (
            <StepDetails
              key="step-3"
              parseResult={parseResult}
              onActivated={handleActivated}
            />
          )}
          {effectiveStep === 4 && (
            <StepConfirmation
              key="step-4"
              propertyName={propertyName || parseResult?.property_name || ''}
              listingId={urlId || parseResult?.listing_id || ''}
            />
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
