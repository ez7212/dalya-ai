'use client'

import { useState } from 'react'
import type { ReactNode } from 'react'
import { sharedUi } from '@/lib/shared-ui-tokens'

interface DraftMessageCardProps {
  draft: string
  contextLine: string
  title?: string
  disabled?: boolean
  onDraftChange?: (draft: string) => void
  onCopy?: (draft: string) => void | Promise<void>
  futureSendSlot?: ReactNode
}

export function DraftMessageCard({
  draft,
  contextLine,
  title = 'Draft outreach',
  disabled = false,
  onDraftChange,
  onCopy,
  futureSendSlot,
}: DraftMessageCardProps) {
  const [value, setValue] = useState(draft)
  const [copied, setCopied] = useState(false)
  const [copyError, setCopyError] = useState<string | null>(null)
  const hasEmDash = value.includes('—')

  const update = (next: string) => {
    setValue(next)
    onDraftChange?.(next)
  }

  const copy = async () => {
    setCopyError(null)
    try {
      await navigator.clipboard.writeText(value)
      await onCopy?.(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2200)
    } catch {
      setCopyError('Copy failed. Select the draft text and copy manually.')
    }
  }

  return (
    <article className={`${sharedUi.panel} p-4`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={sharedUi.label}>{title}</p>
          <p className={`${sharedUi.muted} mt-1`}>{contextLine}</p>
        </div>
        <button type="button" onClick={copy} disabled={disabled} className={sharedUi.iconButton} aria-label="Copy draft" title="Copy draft">
          <span className="material-symbols-rounded text-[18px]" aria-hidden="true">{copied ? 'check' : 'content_copy'}</span>
        </button>
      </div>
      <textarea
        value={value}
        onChange={(event) => update(event.target.value)}
        disabled={disabled}
        rows={5}
        className={`${sharedUi.textInput} mt-3 resize-y leading-relaxed`}
      />
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className={sharedUi.muted}>Manual v1: copy and send from WhatsApp Business.</p>
        {futureSendSlot || (
          <span className="inline-flex items-center gap-1 text-xs text-text-3">
            <span className="material-symbols-rounded text-[16px]" aria-hidden="true">lock</span>
            Send via Property Advisor: future template path
          </span>
        )}
      </div>
      {hasEmDash && (
        <p className="mt-2 rounded border border-warning-100 bg-warning-50 px-2 py-1 text-xs text-warning-700">
          Review tone: this draft contains an em dash.
        </p>
      )}
      {copied && <p className="mt-2 text-xs text-success-600">Draft copied.</p>}
      {copyError && <p className="mt-2 text-xs text-error-600" role="alert">{copyError}</p>}
    </article>
  )
}
