'use client'

import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { SectionEyebrow } from '@/components/ui/SectionEyebrow'

/* ─── types ─── */

interface KBFileMeta {
  filename: string
  status: 'live' | 'needs_review'
  size_bytes: number
  modified_at: string
}

interface KBListResponse {
  files: KBFileMeta[]
  count: number
}

interface KBFileResponse extends KBFileMeta {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  content: any
}

/* ─── helpers ─── */

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
    })
  } catch {
    return iso
  }
}

function prettifyKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/Aed\b/g, 'AED')
    .replace(/Sqft\b/g, 'sqft')
    .replace(/Sqm\b/g, 'sqm')
    .replace(/Roi\b/g, 'ROI')
    .replace(/Noc\b/g, 'NOC')
    .replace(/Url\b/g, 'URL')
    .replace(/Id\b/g, 'ID')
}

function isPrimitive(v: unknown): v is string | number | boolean | null {
  return v === null || ['string', 'number', 'boolean'].includes(typeof v)
}

function isArrayOfPrimitives(v: unknown): boolean {
  return Array.isArray(v) && v.every(isPrimitive)
}

function formatPrimitive(v: unknown, hint?: string): string {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (typeof v === 'number') {
    // Heuristic: large numeric fields with "aed" / "price" / "value" → format with commas
    if (hint && /aed|price|value|amount|sqft|sqm|land_area|units?/i.test(hint)) {
      return v.toLocaleString()
    }
    return String(v)
  }
  return String(v)
}

/* ─── recursive JSON renderer ─── */

interface NodeProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  value: any
  pathKey?: string
  depth: number
}

function JSONNode({ value, pathKey, depth }: NodeProps) {
  // Primitives → simple key/value row handled by parent. Should not be reached at top level.
  if (isPrimitive(value)) {
    return <span className="font-mono text-sm text-sand">{formatPrimitive(value, pathKey)}</span>
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="text-n-500 text-xs italic">empty</span>
    }
    if (isArrayOfPrimitives(value)) {
      return (
        <div className="flex flex-wrap gap-1.5">
          {value.map((item, i) => (
            <span key={i} className="px-2 py-0.5 rounded-md bg-gold/8 text-gold/90 text-xs font-mono">
              {formatPrimitive(item, pathKey)}
            </span>
          ))}
        </div>
      )
    }
    // Array of objects → render as numbered cards
    return (
      <div className="space-y-3">
        {value.map((item, i) => (
          <div key={i} className="rounded-lg border border-gold/8 bg-ink/40 p-4">
            <div className="text-[10px] uppercase tracking-widest text-n-500 mb-2 font-semibold">
              {pathKey ? `${prettifyKey(pathKey)} #${i + 1}` : `Item ${i + 1}`}
            </div>
            <JSONNode value={item} depth={depth + 1} />
          </div>
        ))}
      </div>
    )
  }

  // Object — render as key/value grid
  const entries = Object.entries(value as Record<string, unknown>)
  if (entries.length === 0) {
    return <span className="text-n-500 text-xs italic">empty object</span>
  }

  return (
    <div className="space-y-3">
      {entries.map(([k, v]) => (
        <KVRow key={k} k={k} v={v} depth={depth} />
      ))}
    </div>
  )
}

function KVRow({ k, v, depth }: { k: string; v: unknown; depth: number }) {
  const label = prettifyKey(k)

  if (isPrimitive(v)) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-1 sm:gap-4 py-1.5">
        <div className="text-[11px] uppercase tracking-wider text-n-500 sm:pt-1">{label}</div>
        <div className="text-sand text-sm font-mono break-words">
          {v === null
            ? <span className="text-n-500 italic font-sans">not set</span>
            : formatPrimitive(v, k)}
        </div>
      </div>
    )
  }

  if (isArrayOfPrimitives(v)) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-1 sm:gap-4 py-1.5">
        <div className="text-[11px] uppercase tracking-wider text-n-500 sm:pt-1">{label}</div>
        <JSONNode value={v} pathKey={k} depth={depth + 1} />
      </div>
    )
  }

  // Complex value — collapsible section
  return <CollapsibleSection label={label} value={v} depth={depth} />
}

interface CollapsibleProps {
  label: string
  value: unknown
  depth: number
}

function CollapsibleSection({ label, value, depth }: CollapsibleProps) {
  // Default-expand only the top two levels to keep the page approachable.
  const [open, setOpen] = useState(depth < 2)
  const arr = Array.isArray(value) ? value : null
  const obj = value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null
  const itemCount = arr ? arr.length : obj ? Object.keys(obj).length : 0

  const indentCls = depth === 0
    ? 'border-l-2 border-gold/30 pl-5'
    : depth === 1
      ? 'border-l border-gold/15 pl-4'
      : 'border-l border-gold/8 pl-3'

  return (
    <div className={`py-2 ${indentCls}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 group w-full text-left mb-2"
      >
        <span
          className="material-symbols-outlined text-gold/70 group-hover:text-gold transition-colors"
          style={{ fontSize: '18px', transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}
        >
          chevron_right
        </span>
        <span className={`font-semibold ${depth === 0 ? 'text-base text-gold' : 'text-sm text-sand'}`}>
          {label}
        </span>
        <span className="text-[10px] text-n-500 font-mono">
          {arr ? `${itemCount} item${itemCount === 1 ? '' : 's'}` : `${itemCount} field${itemCount === 1 ? '' : 's'}`}
        </span>
      </button>
      {open && (
        <div className="ml-1">
          <JSONNode value={value} pathKey={label} depth={depth + 1} />
        </div>
      )}
    </div>
  )
}

/* ─── page ─── */

export default function KnowledgeBasePage() {
  const [files, setFiles] = useState<KBFileMeta[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [fileData, setFileData] = useState<KBFileResponse | null>(null)
  const [loadingList, setLoadingList] = useState(true)
  const [loadingFile, setLoadingFile] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'structured' | 'raw'>('structured')

  // Load file list
  useEffect(() => {
    let cancelled = false
    async function loadList() {
      try {
        const res = await apiFetch('/api/v1/admin/knowledge-base')
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail ?? `Failed to load KB list (${res.status})`)
        }
        const data: KBListResponse = await res.json()
        if (cancelled) return
        setFiles(data.files)
        // Auto-select the first live file
        if (data.files.length > 0 && !selected) {
          const firstLive = data.files.find(f => f.status === 'live') ?? data.files[0]
          setSelected(firstLive.filename)
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        if (!cancelled) setLoadingList(false)
      }
    }
    loadList()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load selected file
  useEffect(() => {
    if (!selected) return
    let cancelled = false
    setLoadingFile(true)
    setError(null)
    async function loadFile() {
      try {
        const res = await apiFetch(`/api/v1/admin/knowledge-base/${selected}`)
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail ?? `Failed to load file (${res.status})`)
        }
        const data: KBFileResponse = await res.json()
        if (!cancelled) setFileData(data)
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load file')
      } finally {
        if (!cancelled) setLoadingFile(false)
      }
    }
    loadFile()
    return () => { cancelled = true }
  }, [selected])

  const displayName = useMemo(() => {
    if (!fileData) return ''
    const raw = fileData.filename.replace(/^needs_review\//, '').replace(/\.json$/, '')
    // Try to use the `name` field from the KB itself for a friendlier title
    const fromContent = (fileData.content && typeof fileData.content === 'object' && (fileData.content as Record<string, unknown>).name) as string | undefined
    return fromContent || prettifyKey(raw)
  }, [fileData])

  return (
    <div>
      <SectionEyebrow>Internal</SectionEyebrow>
      <h1 className="editorial text-3xl md:text-4xl font-bold text-sand tracking-tight mb-2">
        Knowledge Base
      </h1>
      <p className="text-n-500 text-sm mb-8 leading-relaxed max-w-2xl">
        Browse the community and developer JSON files that ground Dalya&apos;s prompt-time facts.
        Live files are what the bot reads on every conversation. Needs-review files are research drafts
        awaiting promotion.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        {/* Sidebar — file list */}
        <aside className="rounded-xl border border-gold/10 bg-ink/30 p-3 h-fit lg:sticky lg:top-4">
          {loadingList ? (
            <p className="text-n-500 text-sm p-3">Loading files…</p>
          ) : files.length === 0 ? (
            <p className="text-n-500 text-sm p-3">No knowledge-base files found.</p>
          ) : (
            <ul className="space-y-1">
              {files.map((f) => {
                const isActive = f.filename === selected
                return (
                  <li key={f.filename}>
                    <button
                      type="button"
                      onClick={() => setSelected(f.filename)}
                      className={`w-full text-left px-3 py-2.5 rounded-md transition-colors ${
                        isActive ? 'bg-gold/10 text-sand' : 'text-n-500 hover:text-sand hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-gold/60" style={{ fontSize: '16px' }}>
                          {f.status === 'needs_review' ? 'pending' : 'verified'}
                        </span>
                        <span className="text-sm font-medium truncate">
                          {f.filename.replace(/^needs_review\//, '').replace(/\.json$/, '')}
                        </span>
                      </div>
                      <div className="text-[10px] text-n-500 mt-1 flex items-center gap-2 pl-6">
                        <span className={f.status === 'needs_review' ? 'text-gold/70' : 'text-sage'}>
                          {f.status === 'needs_review' ? 'Draft' : 'Live'}
                        </span>
                        <span>·</span>
                        <span className="font-mono">{formatSize(f.size_bytes)}</span>
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </aside>

        {/* Main — file view */}
        <main className="rounded-xl border border-gold/10 bg-ink/30 p-6 sm:p-8 min-h-[400px]">
          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-400/10 border border-red-400/30 text-red-300 text-sm">
              {error}
            </div>
          )}

          {loadingFile ? (
            <p className="text-n-500 text-sm">Loading file…</p>
          ) : !fileData ? (
            <p className="text-n-500 text-sm">Select a file from the left to view it.</p>
          ) : (
            <>
              {/* File header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-6 mb-6 border-b border-gold/10">
                <div className="min-w-0">
                  <h2 className="text-sand text-xl font-semibold mb-1 break-words">{displayName}</h2>
                  <div className="text-[11px] text-n-500 flex flex-wrap items-center gap-3 font-mono">
                    <span>{fileData.filename}</span>
                    <span>·</span>
                    <span>{formatSize(fileData.size_bytes)}</span>
                    <span>·</span>
                    <span>Modified {formatDate(fileData.modified_at)}</span>
                    <span>·</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-widest font-sans font-semibold ${
                        fileData.status === 'needs_review'
                          ? 'bg-gold/15 text-gold'
                          : 'bg-sage/20 text-sage-lt'
                      }`}
                    >
                      {fileData.status === 'needs_review' ? 'Needs Review' : 'Live'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => setViewMode('structured')}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      viewMode === 'structured'
                        ? 'bg-gold/15 text-gold'
                        : 'text-n-500 hover:text-sand hover:bg-white/5'
                    }`}
                  >
                    Structured
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('raw')}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      viewMode === 'raw'
                        ? 'bg-gold/15 text-gold'
                        : 'text-n-500 hover:text-sand hover:bg-white/5'
                    }`}
                  >
                    Raw JSON
                  </button>
                </div>
              </div>

              {/* File body */}
              {viewMode === 'structured' ? (
                <div>
                  <JSONNode value={fileData.content} depth={0} />
                </div>
              ) : (
                <pre className="text-xs font-mono text-sand bg-deep/50 rounded-md p-4 overflow-x-auto max-h-[70vh]">
                  {JSON.stringify(fileData.content, null, 2)}
                </pre>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  )
}
