'use client'

import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { apiFetch } from '@/lib/api'

type Draft = {
  property_type: string
  listing_title: string | null
  listing_reference: string | null
  portal_source: string | null
  portal_listing_id: string | null
  purpose: string | null
  completion_status: string | null
  furnishing: string | null
  community: string | null
  subcommunity: string | null
  building_or_project: string | null
  unit_number: string | null
  bedrooms: number | null
  bathrooms: number | null
  size_sqft: number | null
  plot_size_sqft: number | null
  asking_price_aed: number | null
  price_per_sqft_aed: number | null
  developer: string | null
  handover_date: string | null
  amenities: string[]
  image_urls: string[]
  description: string | null
  permit_number: string | null
  permit_validation_url: string | null
  broker_name: string | null
  broker_license: string | null
  agent_name: string | null
  agent_email: string | null
  agent_phone: string | null
  agent_license: string | null
  source_url: string | null
}

type AdditionalFee = {
  label: string
  amount_aed: number | null
  paid_by: string
  public: boolean
}

type ImageItem = {
  id: string
  src: string
  label: string
  file?: File
  objectUrl?: string
}

const BLANK_DRAFT: Draft = {
  property_type: 'ready',
  listing_title: null,
  listing_reference: null,
  portal_source: null,
  portal_listing_id: null,
  purpose: 'sale',
  completion_status: null,
  furnishing: null,
  community: null,
  subcommunity: null,
  building_or_project: null,
  unit_number: null,
  bedrooms: null,
  bathrooms: null,
  size_sqft: null,
  plot_size_sqft: null,
  asking_price_aed: null,
  price_per_sqft_aed: null,
  developer: null,
  handover_date: null,
  amenities: [],
  image_urls: [],
  description: null,
  permit_number: null,
  permit_validation_url: null,
  broker_name: null,
  broker_license: null,
  agent_name: null,
  agent_email: null,
  agent_phone: null,
  agent_license: null,
  source_url: null,
}

export function FinishedListingFlow({ startManual = false }: { startManual?: boolean }) {
  const objectUrlsRef = useRef<Set<string>>(new Set())
  const [url, setUrl] = useState('')
  const [draft, setDraft] = useState<Draft | null>(startManual ? BLANK_DRAFT : null)
  const [scrapeMessage, setScrapeMessage] = useState<string | null>(null)
  const [scraping, setScraping] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ listing_id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [reference, setReference] = useState('')
  const [purpose, setPurpose] = useState(startManual ? 'sale' : '')
  const [completionStatus, setCompletionStatus] = useState('')
  const [furnishing, setFurnishing] = useState('')
  const [community, setCommunity] = useState('')
  const [subcommunity, setSubcommunity] = useState('')
  const [building, setBuilding] = useState('')
  const [unit, setUnit] = useState('')
  const [bedrooms, setBedrooms] = useState<number | ''>('')
  const [bathrooms, setBathrooms] = useState<number | ''>('')
  const [sizeSqft, setSizeSqft] = useState<number | ''>('')
  const [plotSizeSqft, setPlotSizeSqft] = useState<number | ''>('')
  const [asking, setAsking] = useState<number | ''>('')
  const [pricePerSqft, setPricePerSqft] = useState<number | ''>('')
  const [developer, setDeveloper] = useState('')
  const [handoverDate, setHandoverDate] = useState('')
  const [amenitiesText, setAmenitiesText] = useState('')
  const [description, setDescription] = useState('')
  const [images, setImages] = useState<ImageItem[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [permitNumber, setPermitNumber] = useState('')
  const [permitUrl, setPermitUrl] = useState('')
  const [brokerName, setBrokerName] = useState('')
  const [brokerLicense, setBrokerLicense] = useState('')
  const [agentName, setAgentName] = useState('')
  const [agentEmail, setAgentEmail] = useState('')
  const [agentPhone, setAgentPhone] = useState('')
  const [agentLicense, setAgentLicense] = useState('')
  const [threshold, setThreshold] = useState<number | ''>('')
  const [commissionPct, setCommissionPct] = useState<number | ''>('')
  const [fees, setFees] = useState<AdditionalFee[]>([])

  async function handleScrape(e: React.FormEvent) {
    e.preventDefault()
    setScraping(true)
    setError(null)
    try {
      const response = await apiFetch('/api/v1/listings/draft-from-url', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      const payload = await response.json()
      const d = payload.draft as Draft
      setDraft(d)
      setTitle(d.listing_title ?? '')
      setReference(d.listing_reference ?? '')
      setPurpose(d.purpose ?? '')
      setCompletionStatus(d.completion_status ?? '')
      setFurnishing(normalizeFurnishing(d.furnishing))
      setCommunity(d.community ?? '')
      setSubcommunity(d.subcommunity ?? '')
      setBuilding(d.building_or_project ?? '')
      setUnit(d.unit_number ?? '')
      setBedrooms(d.bedrooms ?? '')
      setBathrooms(d.bathrooms ?? '')
      setSizeSqft(d.size_sqft ?? '')
      setPlotSizeSqft(d.plot_size_sqft ?? '')
      setAsking(d.asking_price_aed ?? '')
      setPricePerSqft(d.price_per_sqft_aed ?? '')
      setDeveloper(d.developer ?? '')
      setHandoverDate(d.handover_date ?? '')
      setAmenitiesText((d.amenities ?? []).join('\n'))
      setDescription(d.description ?? '')
      setImages((d.image_urls ?? []).map((src, index) => ({
        id: `remote-${index}-${src}`,
        src,
        label: `Imported photo ${index + 1}`,
      })))
      setPermitNumber(d.permit_number ?? '')
      setPermitUrl(d.permit_validation_url ?? '')
      setBrokerName(d.broker_name ?? '')
      setBrokerLicense(d.broker_license ?? '')
      setAgentName(d.agent_name ?? '')
      setAgentEmail(d.agent_email ?? '')
      setAgentPhone(d.agent_phone ?? '')
      setAgentLicense(d.agent_license ?? '')
      const scraped = payload.scrape
      const filled = [
        scraped.asking_price_aed && 'price',
        scraped.bedrooms && 'bedrooms',
        scraped.bathrooms && 'bathrooms',
        scraped.size_sqft && 'size',
        scraped.community && 'community',
        scraped.amenities?.length && 'amenities',
        scraped.image_urls?.length && 'photos',
      ].filter(Boolean)
      setScrapeMessage(
        filled.length > 0
          ? `Prefilled from listing: ${filled.join(', ')}. Review and complete the rest below.`
          : 'Scrape returned no structured data — fill the form manually.'
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scrape failed')
      // Even on failure, surface the manual form
      setDraft({ ...BLANK_DRAFT, source_url: url })
      setPurpose('sale')
      setScrapeMessage('Scrape failed — fill the form manually below.')
    } finally {
      setScraping(false)
    }
  }

  function addFee() {
    setFees([...fees, { label: '', amount_aed: null, paid_by: 'buyer', public: true }])
  }

  useEffect(() => {
    return () => {
      objectUrlsRef.current.forEach((objectUrl) => URL.revokeObjectURL(objectUrl))
      objectUrlsRef.current.clear()
    }
  }, [])

  function addImageFiles(files: FileList | File[]) {
    const imageFiles = Array.from(files).filter((file) => file.type.startsWith('image/'))
    if (!imageFiles.length) return
    setImages((current) => [
      ...current,
      ...imageFiles.map((file) => {
        const objectUrl = URL.createObjectURL(file)
        objectUrlsRef.current.add(objectUrl)
        return {
          id: `${file.name}-${file.size}-${file.lastModified}-${objectUrl}`,
          src: objectUrl,
          label: file.name,
          file,
          objectUrl,
        }
      }),
    ])
  }

  function removeImage(id: string) {
    setImages((current) => {
      const image = current.find((item) => item.id === id)
      if (image?.objectUrl) {
        URL.revokeObjectURL(image.objectUrl)
        objectUrlsRef.current.delete(image.objectUrl)
      }
      return current.filter((item) => item.id !== id)
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (commissionPct === '') {
      setError('Enter the brokerage commission rate before publishing.')
      return
    }
    setSubmitting(true)
    try {
      const amenities = amenitiesText
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean)
      const imageUrls = await Promise.all(
        images.map((image) => image.file ? fileToDataUrl(image.file) : Promise.resolve(image.src))
      )
      const body = {
        property_type: 'ready',
        listing_title: title || null,
        listing_reference: reference || null,
        portal_source: draft?.portal_source ?? null,
        portal_listing_id: draft?.portal_listing_id ?? null,
        purpose: purpose || null,
        completion_status: completionStatus || null,
        furnishing: furnishing || null,
        community: community || null,
        subcommunity: subcommunity || null,
        building_or_project: building || null,
        unit_number: unit || null,
        bedrooms: bedrooms === '' ? null : Number(bedrooms),
        bathrooms: bathrooms === '' ? null : Number(bathrooms),
        size_sqft: sizeSqft === '' ? null : Number(sizeSqft),
        plot_size_sqft: plotSizeSqft === '' ? null : Number(plotSizeSqft),
        asking_price_aed: asking === '' ? null : Number(asking),
        price_per_sqft_aed: pricePerSqft === '' ? null : Number(pricePerSqft),
        developer: developer || null,
        handover_date: handoverDate || null,
        amenities,
        image_urls: imageUrls,
        description: description || null,
        permit_number: permitNumber || null,
        permit_validation_url: permitUrl || null,
        broker_name: brokerName || null,
        broker_license: brokerLicense || null,
        agent_name: agentName || null,
        agent_email: agentEmail || null,
        agent_phone: agentPhone || null,
        agent_license: agentLicense || null,
        notification_threshold_aed: threshold === '' ? null : Number(threshold),
        commission_rate: Number(commissionPct) / 100,
        additional_fees: fees.filter((f) => f.label.trim().length > 0),
        source_url: draft?.source_url ?? url ?? null,
        reference_documents: [],
      }
      const response = await apiFetch('/api/v1/listings', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      })
      const payload = await response.json()
      setResult(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <div className="rounded-md border border-[color:var(--color-success-500,#4A7C6F)] bg-[var(--color-surface-1,#F4F4F2)] p-6">
        <h3 className="text-lg font-semibold text-[var(--color-text-1,#3D3D39)]">Listing created</h3>
        <p className="mt-2 text-sm text-[var(--color-text-2,#5C5C57)]">
          Listing ID: <span className="font-mono">{result.listing_id}</span>
        </p>
        <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
          The Property Advisor is live for this listing. Community research has been queued if needed.
        </p>
        <a
          href={`/dashboard/listings/${result.listing_id}`}
          className="mt-4 inline-flex items-center gap-2 rounded-md bg-[var(--color-brand-600,#324B6B)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-500,#3D5A80)]"
        >
          <span className="material-symbols-rounded text-[18px]" aria-hidden="true">mic</span>
          Add inspection notes
        </a>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Step 1: URL paste */}
      {!draft && (
        <form onSubmit={handleScrape} className="space-y-3">
          <label className="block text-sm font-medium text-[var(--color-text-1,#3D3D39)]">
            Paste a Property Finder or Bayut listing URL
          </label>
          <input
            type="url"
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.propertyfinder.ae/en/plp/..."
            className="w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
          />
          <button
            type="submit"
            disabled={scraping || !url}
            className="rounded-md bg-[var(--color-brand-600,#324B6B)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-500,#3D5A80)] disabled:opacity-60"
          >
            {scraping ? 'Fetching…' : 'Fetch listing data'}
          </button>
          <p className="text-xs text-[var(--color-text-3,#7B7B76)]">
            We&apos;ll prefill as much as we can. If the scrape fails, you&apos;ll get a blank form to fill manually.
          </p>
        </form>
      )}

      {/* Step 2: Review + confirm */}
      {draft && (
        <form onSubmit={handleSubmit} className="space-y-4">
          {scrapeMessage && (
            <div className="rounded-md bg-[var(--color-surface-2,#E8E8E5)] px-3 py-2 text-xs text-[var(--color-text-2,#5C5C57)]">
              {scrapeMessage}
            </div>
          )}
          <FormSection title="Location">
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Community" value={community} onChange={setCommunity} />
              <Field label="Subcommunity / Building" value={subcommunity} onChange={setSubcommunity} />
              <Field label="Project" value={building} onChange={setBuilding} />
              <Field label="Unit number" value={unit} onChange={setUnit} />
            </div>
          </FormSection>

          <FormSection title="Property details">
            <div className="grid gap-3 md:grid-cols-2">
              <IntegerField label="Bedrooms" value={bedrooms} onChange={setBedrooms} />
              <IntegerField label="Bathrooms" value={bathrooms} onChange={setBathrooms} />
              <NumberField label="Built-up area (sqft)" value={sizeSqft} onChange={setSizeSqft} />
              <NumberField label="Plot size (sqft)" value={plotSizeSqft} onChange={setPlotSizeSqft} />
              <SelectField
                label="Furnished"
                value={furnishing}
                onChange={setFurnishing}
                options={[
                  { value: '', label: 'Select' },
                  { value: 'yes', label: 'Yes' },
                  { value: 'no', label: 'No' },
                ]}
              />
              <Field label="Developer" value={developer} onChange={setDeveloper} />
              <DateField label="Handover date" value={handoverDate} onChange={setHandoverDate} />
            </div>
          </FormSection>

          <FormSection title="Pricing">
            <div className="grid gap-3 md:grid-cols-2">
              <CurrencyField label="Asking price (AED)" value={asking} onChange={setAsking} />
              <CurrencyField label="Price per sqft (AED)" value={pricePerSqft} onChange={setPricePerSqft} />
              <CurrencyField
                label="Notification threshold (AED)"
                tooltip="Dalya notifies the agent immediately when a buyer makes an offer above this amount."
                value={threshold}
                onChange={setThreshold}
              />
              <NumberField
                label="Commission rate (%)"
                value={commissionPct}
                onChange={setCommissionPct}
                step={0.05}
                required
              />
            </div>
          </FormSection>

          <FormSection title="Amenities and description">
            <div className="grid gap-3">
              <TextArea
                label="Amenities"
                value={amenitiesText}
                onChange={setAmenitiesText}
                helper="One amenity per line."
                rows={6}
              />
              <TextArea
                label="Description"
                value={description}
                onChange={setDescription}
                rows={7}
              />
            </div>
          </FormSection>

          <FormSection title="Photos">
            <div className="space-y-3">
              <label
                onDragEnter={(event) => {
                  event.preventDefault()
                  setDragActive(true)
                }}
                onDragOver={(event) => {
                  event.preventDefault()
                  setDragActive(true)
                }}
                onDragLeave={(event) => {
                  event.preventDefault()
                  setDragActive(false)
                }}
                onDrop={(event) => {
                  event.preventDefault()
                  setDragActive(false)
                  addImageFiles(event.dataTransfer.files)
                }}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-4 py-8 text-center transition ${
                  dragActive
                    ? 'border-[var(--color-brand-500,#3D5A80)] bg-[var(--color-surface-1,#F4F4F2)]'
                    : 'border-[var(--color-surface-2,#E8E8E5)] bg-white hover:border-[var(--color-brand-500,#3D5A80)]'
                }`}
              >
                <span className="material-symbols-outlined text-[28px] text-[var(--color-brand-500,#3D5A80)]" aria-hidden="true">
                  upload_file
                </span>
                <span className="mt-2 text-sm font-medium text-[var(--color-text-1,#3D3D39)]">
                  Drag photos here, or browse a folder
                </span>
                <span className="mt-1 text-xs text-[var(--color-text-3,#7B7B76)]">
                  JPEG, PNG, or WebP images. Agents should confirm publishing rights.
                </span>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="sr-only"
                  onChange={(event) => {
                    if (event.target.files) addImageFiles(event.target.files)
                    event.target.value = ''
                  }}
                />
              </label>
              {images.length > 0 ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {images.map((image) => (
                    <div key={image.id} className="overflow-hidden rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={image.src} alt="" className="aspect-[4/3] w-full object-cover" />
                      <div className="flex items-center justify-between gap-2 p-2">
                        <span className="min-w-0 truncate text-[11px] text-[var(--color-text-3,#7B7B76)]">
                          {image.label}
                        </span>
                        <button
                          type="button"
                          onClick={() => removeImage(image.id)}
                          className="shrink-0 rounded px-2 py-1 text-xs font-medium text-[var(--color-error-500,#B84838)] hover:bg-[color:var(--color-error-500,#B84838)]/10"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[var(--color-text-3,#7B7B76)]">
                  No photos added yet.
                </p>
              )}
            </div>
          </FormSection>

          <FormSection title="Agent, brokerage, and permit">
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Agent name" value={agentName} onChange={setAgentName} />
              <Field label="Agent email" value={agentEmail} onChange={setAgentEmail} />
              <Field label="Agent phone" value={agentPhone} onChange={setAgentPhone} />
              <Field label="Agent license" value={agentLicense} onChange={setAgentLicense} />
              <Field label="Brokerage" value={brokerName} onChange={setBrokerName} />
              <Field label="Broker license" value={brokerLicense} onChange={setBrokerLicense} />
              <Field label="Permit number" value={permitNumber} onChange={setPermitNumber} />
              <Field label="Permit validation URL" value={permitUrl} onChange={setPermitUrl} />
            </div>
          </FormSection>

          <div>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-[var(--color-text-1,#3D3D39)]">
                Additional fee line items
              </h4>
              <button
                type="button"
                onClick={addFee}
                className="text-xs font-medium text-[var(--color-brand-500,#3D5A80)] hover:underline"
              >
                + Add line item
              </button>
            </div>
            <div className="mt-2 space-y-2">
              {fees.map((fee, i) => (
                <div key={i} className="grid gap-2 md:grid-cols-[1fr_140px_120px]">
                  <input
                    type="text"
                    placeholder="Label (e.g. POA fee)"
                    value={fee.label}
                    onChange={(e) => {
                      const next = [...fees]
                      next[i] = { ...fee, label: e.target.value }
                      setFees(next)
                    }}
                    className="rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm"
                  />
                  <input
                    type="number"
                    placeholder="Amount AED"
                    value={fee.amount_aed ?? ''}
                    onChange={(e) => {
                      const next = [...fees]
                      next[i] = {
                        ...fee,
                        amount_aed: e.target.value === '' ? null : Number(e.target.value),
                      }
                      setFees(next)
                    }}
                    className="rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm"
                  />
                  <select
                    value={fee.paid_by}
                    onChange={(e) => {
                      const next = [...fees]
                      next[i] = { ...fee, paid_by: e.target.value }
                      setFees(next)
                    }}
                    className="rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm"
                  >
                    <option value="buyer">Buyer</option>
                    <option value="seller">Seller</option>
                    <option value="either">Either</option>
                  </select>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div className="rounded-md border border-[color:var(--color-error-500,#B84838)] bg-[color:var(--color-error-500,#B84838)]/5 px-3 py-2 text-sm text-[var(--color-error-500,#B84838)]">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-[var(--color-brand-600,#324B6B)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-500,#3D5A80)] disabled:opacity-60"
            >
              {submitting ? 'Creating…' : 'Confirm and publish listing'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

function FormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-[var(--color-surface-2,#E8E8E5)] bg-white p-4">
      <h3 className="text-sm font-semibold text-[var(--color-text-1,#3D3D39)]">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <label className="block text-sm">
      <span className="block text-xs text-[var(--color-text-3,#7B7B76)]">{label}</span>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      />
    </label>
  )
}

function TextArea({
  label,
  value,
  onChange,
  helper,
  rows = 4,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  helper?: string
  rows?: number
}) {
  return (
    <label className="block text-sm">
      <span className="block text-xs text-[var(--color-text-3,#7B7B76)]">{label}</span>
      <textarea
        value={value}
        rows={rows}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      />
      {helper && <span className="mt-1 block text-xs text-[var(--color-text-3,#7B7B76)]">{helper}</span>}
    </label>
  )
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: Array<{ value: string; label: string }>
}) {
  return (
    <label className="block text-sm">
      <span className="block text-xs text-[var(--color-text-3,#7B7B76)]">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <label className="block text-sm">
      <span className="block text-xs text-[var(--color-text-3,#7B7B76)]">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      />
    </label>
  )
}

function NumberField({
  label,
  value,
  onChange,
  step,
  required,
  tooltip,
}: {
  label: string
  value: number | ''
  onChange: (v: number | '') => void
  step?: number
  required?: boolean
  tooltip?: string
}) {
  return (
    <label className="block text-sm">
      <FieldLabel label={label} tooltip={tooltip} />
      <input
        type="number"
        value={value === '' ? '' : value}
        step={step}
        required={required}
        onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      />
    </label>
  )
}

function IntegerField({
  label,
  value,
  onChange,
}: {
  label: string
  value: number | ''
  onChange: (v: number | '') => void
}) {
  return (
    <label className="block text-sm">
      <FieldLabel label={label} />
      <input
        type="number"
        value={value === '' ? '' : value}
        step={1}
        min={0}
        onChange={(event) => {
          const next = event.target.value
          onChange(next === '' ? '' : Math.max(0, Math.trunc(Number(next))))
        }}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      />
    </label>
  )
}

function CurrencyField({
  label,
  value,
  onChange,
  tooltip,
}: {
  label: string
  value: number | ''
  onChange: (v: number | '') => void
  tooltip?: string
}) {
  return (
    <label className="block text-sm">
      <FieldLabel label={label} tooltip={tooltip} />
      <input
        type="text"
        inputMode="numeric"
        value={value === '' ? '' : formatNumber(value)}
        onChange={(event) => onChange(parseFormattedNumber(event.target.value))}
        className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
      />
    </label>
  )
}

function FieldLabel({ label, tooltip }: { label: string; tooltip?: string }) {
  return (
    <span className="flex items-center gap-1 text-xs text-[var(--color-text-3,#7B7B76)]">
      {label}
      {tooltip && (
        <span
          tabIndex={0}
          title={tooltip}
          className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-[var(--color-surface-2,#E8E8E5)] text-[10px] font-semibold text-[var(--color-brand-500,#3D5A80)]"
          aria-label={tooltip}
        >
          i
        </span>
      )}
    </span>
  )
}

function normalizeFurnishing(value: string | null): string {
  if (!value) return ''
  const normalized = value.toLowerCase()
  if (['yes', 'true', 'furnished'].includes(normalized)) return 'yes'
  if (['no', 'false', 'unfurnished'].includes(normalized)) return 'no'
  return ''
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value)
}

function parseFormattedNumber(value: string): number | '' {
  const normalized = value.replace(/[^\d]/g, '')
  return normalized ? Number(normalized) : ''
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error ?? new Error('Failed to read image file.'))
    reader.readAsDataURL(file)
  })
}
