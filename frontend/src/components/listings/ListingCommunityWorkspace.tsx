'use client'

import { useState } from 'react'
import { useAuth } from '@/components/providers/AuthProvider'
import {
  useListingCommunity,
  useUpsertCommunityOverride,
  useDeleteCommunityOverride,
  type CommunityField,
  type ListingCommunityResponse,
} from '@/lib/queries'

type Props = { readonly id: string }

export function ListingCommunityWorkspace({ id }: Props) {
  const { loading: authLoading } = useAuth()
  const { data, isLoading, error } = useListingCommunity(id, !authLoading)

  if (authLoading || isLoading) return <LoadingState />
  if (error) return <ErrorState message={error instanceof Error ? error.message : 'Could not load community data.'} />
  if (!data || !data.project_name) return <NoProjectState />

  return (
    <div className="space-y-5">
      <Header data={data} />
      <ScopeBanner project={data.project_name} />
      {data.research_status === 'none' ? (
        <EmptyResearchState project={data.project_name} />
      ) : (
        <FieldGroups id={id} fields={data.fields} />
      )}
    </div>
  )
}

function Header({ data }: { readonly data: ListingCommunityResponse }) {
  const statusLabel =
    data.research_status === 'approved' ? 'Approved' : data.research_status === 'in_review' ? 'In review' : 'Not researched'
  const statusTone =
    data.research_status === 'approved' ? 'bg-sage/15 text-sage' : data.research_status === 'in_review' ? 'bg-copper/15 text-copper' : 'bg-neutral-100 text-neutral-600'
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold text-neutral-900">{data.project_name} — community research</h2>
        <span className={`rounded-sm px-2 py-1 text-[11px] font-semibold ${statusTone}`}>{statusLabel}</span>
      </div>
      <p className="mt-2 text-sm text-neutral-600">
        {data.research_confidence != null && (
          <span className="tabular-nums">Confidence {Math.round(data.research_confidence * 100)}%</span>
        )}
        {data.research_confidence != null && data.source_count > 0 ? ' · ' : ''}
        {data.source_count > 0 && <span className="tabular-nums">{data.source_count} sources</span>}
      </p>
    </div>
  )
}

function ScopeBanner({ project }: { readonly project: string }) {
  return (
    <div className="rounded-md border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
      <span className="font-medium">Your corrections are private.</span> Overrides apply to all your {project} listings —
      now and future — and are used by the Property Advisor for your buyers only. Other agents and the shared research are
      never affected.
    </div>
  )
}

function FieldGroups({ id, fields }: { readonly id: string; readonly fields: readonly CommunityField[] }) {
  const groups: string[] = []
  for (const f of fields) if (!groups.includes(f.group)) groups.push(f.group)
  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <section key={group} className="rounded-lg border border-neutral-200 bg-white">
          <h3 className="border-b border-neutral-200 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
            {group}
          </h3>
          <div className="divide-y divide-neutral-100">
            {fields.filter((f) => f.group === group).map((field) => (
              <FieldRow key={field.key} id={id} field={field} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function FieldRow({ id, field }: { readonly id: string; readonly field: CommunityField }) {
  const upsert = useUpsertCommunityOverride(id)
  const remove = useDeleteCommunityOverride(id)
  const hasOverride = field.override != null
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(field.override?.value_text ?? field.researched_value ?? '')
  const [note, setNote] = useState(field.override?.note ?? '')
  const [buyerSafe, setBuyerSafe] = useState(field.override?.buyer_safe ?? true)
  const busy = upsert.isPending || remove.isPending

  function startEdit() {
    setValue(field.override?.value_text ?? field.researched_value ?? '')
    setNote(field.override?.note ?? '')
    setBuyerSafe(field.override?.buyer_safe ?? true)
    setEditing(true)
  }

  async function save() {
    if (!value.trim()) return
    await upsert.mutateAsync({ fieldKey: field.key, value_text: value.trim(), note: note.trim() || null, buyer_safe: buyerSafe })
    setEditing(false)
  }

  async function clearOverride() {
    await remove.mutateAsync(field.key)
    setEditing(false)
  }

  return (
    <div className="px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-neutral-900">{field.label}</p>
          <p className="mt-0.5 text-sm text-neutral-600">
            {field.researched_value ?? <span className="italic text-neutral-400">Not in research</span>}
          </p>
        </div>
        {!editing && (
          hasOverride ? (
            <div className="flex items-center gap-2">
              <span className="rounded-sm bg-brand-50 px-2 py-1 text-[11px] font-semibold text-brand-700">
                Overridden{field.override && !field.override.buyer_safe ? ' · internal' : ''}
              </span>
              <button type="button" onClick={startEdit} className="text-xs font-medium text-brand-600 hover:underline">Edit</button>
            </div>
          ) : (
            <button
              type="button"
              onClick={startEdit}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-neutral-300 bg-white px-2.5 text-xs font-semibold text-neutral-700 transition-colors hover:border-brand-300 hover:text-brand-700"
            >
              <span className="material-symbols-outlined text-[15px]" aria-hidden="true">edit</span>
              Override
            </button>
          )
        )}
      </div>

      {hasOverride && !editing && (
        <p className="mt-2 rounded-md bg-brand-50/60 px-3 py-2 text-sm text-neutral-800">
          <span className="font-medium text-brand-700">Your value:</span> {field.override?.value_text}
          {field.override?.note ? <span className="text-neutral-500"> — {field.override.note}</span> : null}
        </p>
      )}

      {editing && (
        <div className="mt-3 space-y-2 rounded-md border border-neutral-200 bg-neutral-50 p-3">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Your value</span>
            <input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Custom value for your buyers"
              className="mt-1 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-500/20"
            />
          </label>
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">Note (optional)</span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. confirmed with the developer"
              className="mt-1 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-500/20"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" checked={buyerSafe} onChange={(e) => setBuyerSafe(e.target.checked)} className="h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500/30" />
            The Property Advisor may share this value with buyers
          </label>
          {(upsert.error || remove.error) && (
            <p className="text-xs text-brick">{(upsert.error || remove.error) instanceof Error ? (upsert.error || remove.error)!.message : 'Action failed.'}</p>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              onClick={save}
              disabled={busy || !value.trim()}
              className="inline-flex h-9 items-center rounded-md bg-brand-700 px-3 text-xs font-semibold text-white transition-colors hover:bg-brand-800 disabled:opacity-50"
            >
              {upsert.isPending ? 'Saving…' : 'Save override'}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              disabled={busy}
              className="inline-flex h-9 items-center rounded-md border border-neutral-300 bg-white px-3 text-xs font-semibold text-neutral-700 hover:bg-neutral-50"
            >
              Cancel
            </button>
            {hasOverride && (
              <button
                type="button"
                onClick={clearOverride}
                disabled={busy}
                className="inline-flex h-9 items-center rounded-md px-3 text-xs font-semibold text-brick hover:bg-brick/10"
              >
                {remove.isPending ? 'Removing…' : 'Remove override'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function LoadingState() {
  return (
    <div className="space-y-3" aria-label="Loading community data">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-20 animate-pulse rounded-lg border border-neutral-200 bg-white" />
      ))}
    </div>
  )
}

function ErrorState({ message }: { readonly message: string }) {
  return (
    <div className="rounded-lg border border-brick/25 bg-white px-4 py-10 text-center" role="alert">
      <p className="text-sm font-semibold text-brick">Community data could not be loaded.</p>
      <p className="mt-2 text-sm text-neutral-600">{message}</p>
    </div>
  )
}

function NoProjectState() {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-12 text-center">
      <p className="text-sm font-semibold text-neutral-900">No project linked to this listing.</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-neutral-600">
        Set the listing&apos;s project (development) so Dalya can attach community research and let you correct it.
      </p>
    </div>
  )
}

function EmptyResearchState({ project }: { readonly project: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-12 text-center">
      <p className="text-sm font-semibold text-neutral-900">No community research yet for {project}.</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-neutral-600">
        Research is generated automatically when a listing in this project is added. It will appear here once it runs.
      </p>
    </div>
  )
}
