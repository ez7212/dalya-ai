'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/lib/api'

export type PaymentInstalment = {
  instalment_number?: number
  due_date?: string | null
  milestone: string
  percentage: number
  amount_aed: number
  amount_incl_vat_aed?: number
  actually_paid?: boolean | null
}

export type SpaParseResult = {
  project?: string
  sub_community?: string | null
  unit_number?: string
  developer?: string
  property_type?: string
  bedrooms?: number | null
  bathrooms?: number | null
  bua_sqft?: number | null
  plot_sqft?: number | null
  purchase_price_aed?: number | null
  estimated_completion_date?: string | null
  payment_schedule?: PaymentInstalment[]
  total_paid_percent?: number | null
  noc_eligible?: boolean | null
}

type SpaParseResponse = {
  success: boolean
  data?: SpaParseResult | null
  error?: string | null
}

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
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset simulated progress when idle
      setProgress(0)
      setStageIndex(0)
      return
    }
    const stageTimings = [800, 3000, 6000, 5000, 4000]
    let elapsed = 0
    const interval = setInterval(() => {
      elapsed += 100
      let currentStage = 0
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
      const stageStart = currentStage > 0 ? PARSE_STAGES[currentStage - 1].target : 0
      const stageEnd = PARSE_STAGES[currentStage].target
      const stageElapsed = elapsed - stageTimings.slice(0, currentStage).reduce((a, b) => a + b, 0)
      const stageProgress = Math.min(stageElapsed / stageTimings[currentStage], 1)
      const eased = 1 - Math.pow(1 - stageProgress, 3)
      setProgress(Math.min(stageStart + (stageEnd - stageStart) * eased, 95))
    }, 100)
    return () => clearInterval(interval)
  }, [active])

  const complete = () => setProgress(100)
  const stage = PARSE_STAGES[stageIndex]?.label || 'Processing'
  return { progress, stage, complete }
}

export function SpaUploadDropzone({ onParsed }: { onParsed: (data: SpaParseResult) => void }) {
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
        throw new Error(body?.detail ?? `Could not read this SPA (${res.status}). Try a clearer scan.`)
      }
      const payload: SpaParseResponse = await res.json()
      if (!payload.success || !payload.data) {
        throw new Error(payload.error || 'Could not extract details from this SPA. Try a clearer scan.')
      }
      complete()
      await new Promise((r) => setTimeout(r, 400))
      onParsed(payload.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="py-14 px-8 text-center">
        <span className="material-symbols-outlined mb-5 block text-[var(--color-brand-600,#324B6B)]" style={{ fontSize: '44px' }}>
          document_scanner
        </span>
        <p className="text-lg font-semibold text-[var(--color-text-1,#3D3D39)]">{stage}</p>
        <p className="mt-1 text-sm text-[var(--color-text-3,#7B7B76)]">This typically takes 15–30 seconds</p>
        <div className="mx-auto mt-6 max-w-md">
          <div className="h-2 overflow-hidden rounded-full bg-[var(--color-surface-2,#E8E8E5)]">
            <div
              className="h-full rounded-full bg-[var(--color-brand-600,#324B6B)] transition-[width] duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 flex items-center justify-between">
            <span className="truncate text-[11px] text-[var(--color-text-3,#7B7B76)]">{file?.name}</span>
            <span className="font-mono text-[11px] text-[var(--color-brand-600,#324B6B)]">{Math.round(progress)}%</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        aria-label="Upload the Sale and Purchase Agreement"
        className={`relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-8 py-14 text-center transition-colors ${
          dragging
            ? 'border-[var(--color-brand-500,#3D5A80)] bg-[var(--color-surface-1,#F4F4F2)]'
            : 'border-[var(--color-surface-2,#E8E8E5)] bg-white hover:border-[var(--color-brand-500,#3D5A80)]'
        }`}
      >
        <span className="material-symbols-outlined text-[var(--color-brand-500,#3D5A80)]" style={{ fontSize: '44px' }}>
          upload_file
        </span>
        {file ? (
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[var(--color-brand-600,#324B6B)]" style={{ fontSize: '18px' }}>
              description
            </span>
            <span className="text-sm font-medium text-[var(--color-text-1,#3D3D39)]">{file.name}</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                setFile(null)
              }}
              className="ml-1 text-[var(--color-text-3,#7B7B76)] hover:text-[var(--color-text-1,#3D3D39)]"
              aria-label="Remove file"
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>close</span>
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-[var(--color-text-1,#3D3D39)]">
              Drop your SPA here or{' '}
              <span className="text-[var(--color-brand-600,#324B6B)] underline underline-offset-2">browse</span>
            </p>
            <p className="text-xs text-[var(--color-text-3,#7B7B76)]">PDF, JPEG, or PNG · PII is excluded</p>
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
        <p className="mt-3 text-sm text-[var(--color-error-500,#B84838)]" role="alert">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!file}
        className="mt-5 inline-flex items-center justify-center gap-2 rounded-md bg-[var(--color-brand-600,#324B6B)] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[var(--color-brand-500,#3D5A80)] disabled:opacity-50"
      >
        <span className="material-symbols-outlined text-[18px]" aria-hidden="true">auto_awesome</span>
        Parse SPA
      </button>
    </div>
  )
}
