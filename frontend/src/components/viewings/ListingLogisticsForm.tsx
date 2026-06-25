'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'
import { useListingLogistics } from '@/lib/queries'

type SectionKey = 'access' | 'keys' | 'tenant' | 'owner'

const sectionTabs: Array<{ key: SectionKey; label: string }> = [
  { key: 'access', label: 'Access' },
  { key: 'keys', label: 'Keys' },
  { key: 'tenant', label: 'Tenant' },
  { key: 'owner', label: 'Owner' },
]

const keyKitItems = ['unit key', 'access card', 'parking remote', 'mailbox key']

type LogisticsSection = Record<string, unknown>

interface ListingLogisticsFormProps {
  readonly listingId: string
}

export function ListingLogisticsForm({ listingId }: ListingLogisticsFormProps) {
  const queryClient = useQueryClient()
  const { data, isLoading, error } = useListingLogistics(listingId)
  const dirtyRef = useRef(false)
  const [active, setActive] = useState<SectionKey>('access')
  const [access, setAccess] = useState<LogisticsSection>({})
  const [keys, setKeys] = useState<LogisticsSection>({})
  const [tenant, setTenant] = useState<LogisticsSection>({})
  const [owner, setOwner] = useState<LogisticsSection>({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => { dirtyRef.current = false; setAccess({}); setKeys({}); setTenant({}); setOwner({}) }, [listingId])

  useEffect(() => {
    if (!data || dirtyRef.current) return
    setAccess({ ...(data.prefill?.draft?.access || {}), ...(data.logistics?.access || {}) })
    setKeys({ ...(data.prefill?.draft?.keys || {}), ...(data.logistics?.keys || {}) })
    setTenant({ ...(data.prefill?.draft?.tenant || {}), ...(data.logistics?.tenant || {}) })
    setOwner({ ...(data.prefill?.draft?.owner_permissions || {}), ...(data.logistics?.owner_permissions || {}) })
  }, [data])

  const buildingConfidence = useMemo(() => {
    if (!data?.prefill) return 'No building defaults yet'
    if (data.prefill.contributor_count === 0) return 'First configuration for this building'
    return `${data.prefill.contributor_count} agent${data.prefill.contributor_count === 1 ? '' : 's'} configured this building`
  }, [data])

  const save = async () => {
    setSaving(true)
    setSaveError(null)
    setMessage(null)
    try {
      const res = await apiFetch(`/api/v1/agent/listings/${listingId}/logistics`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          access: normalizeAccess(access),
          keys: normalizeKeys(keys),
          tenant: normalizeTenant(tenant),
          owner_permissions: normalizeOwner(owner),
          confirmed: true,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(errorDetail(body) ?? `Save failed (${res.status})`)
      }
      dirtyRef.current = false
      await queryClient.invalidateQueries({ queryKey: ['listing-logistics', listingId] })
      setMessage('Logistics saved.')
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Could not save logistics')
    } finally {
      setSaving(false)
    }
  }

  if (isLoading) {
    return <div className="space-y-5" aria-label="Loading logistics"><div className="h-28 animate-pulse rounded-lg border border-neutral-200 bg-white" /><div className="h-96 animate-pulse rounded-lg border border-neutral-200 bg-white" /></div>
  }

  if (error) {
    return <section className="rounded-lg border border-brick/25 bg-white px-4 py-8 text-center" role="alert"><p className="text-sm font-semibold text-brick">Logistics could not be loaded.</p><p className="mt-2 text-sm text-neutral-600">{error.message}</p></section>
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Building prefill</p>
            <h2 className="mt-1 text-base font-semibold text-neutral-900">{data?.prefill?.display_name || 'Listing logistics'}</h2>
            <p className="mt-1 text-sm text-neutral-600">{buildingConfidence}</p>
          </div>
          <span className="w-fit rounded-sm bg-sage/15 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-sage">{Math.round((data?.prefill?.confidence || 0) * 100)}% confidence</span>
        </div>
      </section>

      <section className="rounded-lg border border-neutral-200 bg-white">
        <nav className="flex gap-1 overflow-x-auto border-b border-neutral-200 px-4 pt-3" aria-label="Logistics sections">
          {sectionTabs.map((tab) => (
            <button key={tab.key} type="button" onClick={() => setActive(tab.key)} className={`relative px-4 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30 ${active === tab.key ? 'text-brand-700' : 'text-neutral-600 hover:text-neutral-900'}`}>
              {tab.label}
              {active === tab.key && <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-sm bg-brand-600" aria-hidden="true" />}
            </button>
          ))}
        </nav>

        <div className="p-5">
          {active === 'access' && <AccessSection value={access} onChange={(next) => { dirtyRef.current = true; setAccess(next) }} />}
          {active === 'keys' && <KeysSection value={keys} onChange={(next) => { dirtyRef.current = true; setKeys(next) }} />}
          {active === 'tenant' && <TenantSection value={tenant} onChange={(next) => { dirtyRef.current = true; setTenant(next) }} />}
          {active === 'owner' && <OwnerSection value={owner} onChange={(next) => { dirtyRef.current = true; setOwner(next) }} />}

          <div className="mt-6 flex flex-col gap-3 border-t border-neutral-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              {message && <p className="text-sm font-medium text-sage">{message}</p>}
              {saveError && <p className="text-sm font-medium text-brick" role="alert">{saveError}</p>}
            </div>
            <button type="button" onClick={save} disabled={saving} className="inline-flex min-h-11 items-center justify-center rounded-md bg-brand-700 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-neutral-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40">
              {saving ? 'Saving...' : 'Save logistics'}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

function AccessSection({ value, onChange }: SectionProps) {
  const securityHours = recordValue(value.security_office_hours)

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <SelectField label="Access type" value={str(value.type)} onChange={(next) => onChange({ ...value, type: next })} options={['front desk', 'security office', 'direct', 'keypad', 'other']} />
      <TextField label="Meet point" value={str(value.meet_point)} onChange={(next) => onChange({ ...value, meet_point: next })} />
      <NumberField label="Building/community notice hours" value={value.advance_notice_hours} onChange={(next) => onChange({ ...value, advance_notice_hours: next })} />
      <TextField label="NOC upload reference" value={str(value.noc_upload_url)} onChange={(next) => onChange({ ...value, noc_upload_url: next })} />
      <TextField label="Security opens" value={str(securityHours.start)} onChange={(next) => onChange({ ...value, security_office_hours: { ...securityHours, start: next } })} placeholder="09:00" />
      <TextField label="Security closes" value={str(securityHours.end)} onChange={(next) => onChange({ ...value, security_office_hours: { ...securityHours, end: next } })} placeholder="18:00" />
      <CheckField label="NOC required for showing" checked={Boolean(value.noc_required)} onChange={(next) => onChange({ ...value, noc_required: next })} />
      <CheckField label="Visitor parking pass at gate" checked={Boolean(value.visitor_parking_pass_required)} onChange={(next) => onChange({ ...value, visitor_parking_pass_required: next })} />
      <CheckField label="Buyer Emirates ID pre-registration" checked={Boolean(value.buyer_emirates_id_preregistration_required)} onChange={(next) => onChange({ ...value, buyer_emirates_id_preregistration_required: next })} />
    </div>
  )
}

function KeysSection({ value, onChange }: SectionProps) {
  const selected = stringList(value.key_kit_checklist)
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <SelectField label="Key location" value={str(value.location)} onChange={(next) => onChange({ ...value, location: next })} options={['agent has', 'front office', 'other agent', 'developer office', 'property mgmt company', 'lockbox', 'keypad']} />
      <TextField label="Key holder contact" value={str(value.contact_details)} onChange={(next) => onChange({ ...value, contact_details: next })} />
      <TextField label="Lockbox encrypted token" value={str(value.lockbox_code_encrypted)} onChange={(next) => onChange({ ...value, lockbox_code_encrypted: next })} placeholder="vault:..." />
      <CheckField label="Return same day required" checked={Boolean(value.return_same_day_required)} onChange={(next) => onChange({ ...value, return_same_day_required: next })} />
      <div className="md:col-span-2">
        <p className={labelClass}>Key kit checklist</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {keyKitItems.map((item) => (
            <CheckField key={item} label={item} checked={selected.includes(item)} onChange={(checked) => {
                const next = checked ? [...selected, item] : selected.filter((entry) => entry !== item)
                onChange({ ...value, key_kit_checklist: next })
              }} />
          ))}
        </div>
      </div>
    </div>
  )
}

function TenantSection({ value, onChange }: SectionProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <SelectField label="Tenant status" value={str(value.status || 'vacant')} onChange={(next) => onChange({ ...value, status: next })} options={['vacant', 'tenanted']} />
      {Boolean(value.redacted) && <p className="rounded border border-copper/30 bg-copper/10 px-3 py-2 text-sm text-copper md:col-span-2">Tenant contact fields are redacted for your role.</p>}
      <TextField label="Tenant name" value={str(value.name)} onChange={(next) => onChange({ ...value, name: next })} />
      <TextField label="WhatsApp number" value={str(value.whatsapp_number)} onChange={(next) => onChange({ ...value, whatsapp_number: next })} />
      <TextField label="Email" value={str(value.email)} onChange={(next) => onChange({ ...value, email: next })} />
      <SelectField label="Preferred contact" value={str(value.preferred_contact_method)} onChange={(next) => onChange({ ...value, preferred_contact_method: next })} options={['whatsapp', 'email', 'phone']} />
      <NumberField label="Notice period hours" value={value.notice_period_hours ?? 48} onChange={(next) => onChange({ ...value, notice_period_hours: next })} />
      <SelectField label="Cooperation level" value={str(value.cooperation_level)} onChange={(next) => onChange({ ...value, cooperation_level: next })} options={['friendly', 'neutral', 'hostile']} />
      <TextAreaField label="Preferred time windows" value={str(value.preferred_time_windows)} onChange={(next) => onChange({ ...value, preferred_time_windows: next })} />
      <TextAreaField label="Refused time windows" value={str(value.refused_time_windows)} onChange={(next) => onChange({ ...value, refused_time_windows: next })} />
      <CheckField label="Domestic helper present" checked={Boolean(value.domestic_helper_present)} onChange={(next) => onChange({ ...value, domestic_helper_present: next })} />
      <CheckField label="Pets present" checked={Boolean(value.pets)} onChange={(next) => onChange({ ...value, pets: next })} />
      <TextField label="Pet notes" value={str(value.pet_notes)} onChange={(next) => onChange({ ...value, pet_notes: next })} />
      <CheckField label="Photography permission" checked={Boolean(value.photography_permission)} onChange={(next) => onChange({ ...value, photography_permission: next })} />
    </div>
  )
}

function OwnerSection({ value, onChange }: SectionProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <TextAreaField label="Viewing restrictions" value={str(value.viewing_restrictions)} onChange={(next) => onChange({ ...value, viewing_restrictions: next })} placeholder="No Ramadan, weekends only, owner must be present..." />
      <TextAreaField label="Owner contact" value={str(value.owner_contact)} onChange={(next) => onChange({ ...value, owner_contact: next })} />
      <CheckField label="Owner must be present" checked={Boolean(value.owner_must_be_present)} onChange={(next) => onChange({ ...value, owner_must_be_present: next })} />
    </div>
  )
}

interface SectionProps {
  readonly value: LogisticsSection
  readonly onChange: (value: LogisticsSection) => void
}

function TextField({ label, value, onChange, placeholder }: { readonly label: string; readonly value: string; readonly onChange: (value: string) => void; readonly placeholder?: string }) {
  return <label className="block"><span className={labelClass}>{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={inputClass} /></label>
}

function NumberField({ label, value, onChange }: { readonly label: string; readonly value: unknown; readonly onChange: (value: number | null) => void }) {
  return <label className="block"><span className={labelClass}>{label}</span><input type="number" value={value == null ? '' : String(value)} onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)} className={inputClass} /></label>
}

function TextAreaField({ label, value, onChange, placeholder }: { readonly label: string; readonly value: string; readonly onChange: (value: string) => void; readonly placeholder?: string }) {
  return <label className="block"><span className={labelClass}>{label}</span><textarea rows={4} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={`${inputClass} resize-y`} /></label>
}

function SelectField({ label, value, onChange, options }: { readonly label: string; readonly value: string; readonly onChange: (value: string) => void; readonly options: readonly string[] }) {
  return (
    <label className="block">
      <span className={labelClass}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className={inputClass}>
        <option value="">Select</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  )
}

function CheckField({ label, checked, onChange }: { readonly label: string; readonly checked: boolean; readonly onChange: (value: boolean) => void }) {
  return <label className="flex min-h-11 items-center gap-3 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-800 transition-colors focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-500/20"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-brand-700" />{label}</label>
}

const labelClass = 'mb-2 block text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500'
const inputClass = 'w-full rounded-md border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 outline-none transition-colors placeholder:text-neutral-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 disabled:bg-neutral-100'

function str(value: unknown): string {
  return value == null ? '' : String(value)
}

function normalizeAccess(value: LogisticsSection) {
  return {
    ...value,
    advance_notice_hours: value.advance_notice_hours == null ? null : Number(value.advance_notice_hours),
  }
}

function normalizeKeys(value: LogisticsSection) {
  const next = { ...value }
  delete next.lockbox_code
  return next
}

function normalizeTenant(value: LogisticsSection) {
  return {
    ...value,
    notice_period_hours: value.notice_period_hours == null ? null : Number(value.notice_period_hours),
  }
}

function normalizeOwner(value: LogisticsSection) {
  return { ...value }
}

function recordValue(value: unknown): LogisticsSection {
  return typeof value === 'object' && value !== null ? Object.fromEntries(Object.entries(value)) : {}
}

function stringList(value: unknown): readonly string[] {
  return Array.isArray(value) ? value.filter((item) => typeof item === 'string') : []
}

function errorDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  return typeof body.detail === 'string' ? body.detail : null
}
