'use client'

import Link from 'next/link'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FocusEvent, ReactNode } from 'react'
import { apiFetch } from '@/lib/api'
import { formatMoney } from '@/lib/utils'
import { SpaUploadDropzone, type PaymentInstalment, type SpaParseResult } from './SpaUploadDropzone'

type ListingPropertyType = 'ready' | 'off_plan'
type EntryMethod = 'portal' | 'manual' | 'spa'

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

type SupportingDocumentItem = {
  id: string
  documentType: string
  customDocumentType: string
  label: string
  fileName: string
  mimeType: string
  sizeBytes: number
  file?: File
  contentText: string
  extractionStatus: 'parsed' | 'metadata_only' | 'failed'
}

type SelectOption = {
  readonly value: string
  readonly label: string
}

type DraftFromUrlResponse = {
  readonly draft: Draft
  readonly scrape: {
    readonly warning?: string | null
    readonly property_type?: string | null
    readonly asking_price_aed?: number | null
    readonly bedrooms?: number | null
    readonly bathrooms?: number | null
    readonly size_sqft?: number | null
    readonly community?: string | null
    readonly amenities?: readonly string[] | null
    readonly image_urls?: readonly string[] | null
  }
}

const DEVELOPER_OPTIONS = [
  'Emaar Properties',
  'Sobha Realty',
  'Nakheel Properties',
  'Damac Properties',
  'Dubai Properties',
  'Meraas',
  'Ellington Properties',
  'Azizi Developments',
  'Danube Properties',
  'Omniyat',
  'Aldar Properties',
  'Meydan',
  'Select Group',
  'MAG Property Development',
  'Binghatti',
] as const

const PROPERTY_CATEGORY_OPTIONS = ['Apartment', 'Villa', 'Townhouse', 'Penthouse'] as const

const OTHER_DEVELOPER_VALUE = '__other_developer__'
const OTHER_PROPERTY_CATEGORY_VALUE = '__other_property_category__'
const OTHER_DOCUMENT_TYPE_VALUE = '__other_document_type__'
const FALLBACK_OTHER_DOCUMENT_TYPE = 'seller_disclosure_notes'
const DLD_FEE_LABEL = 'DLD 4% fee'
const DLD_FEE_RATE = 0.04
const MAX_DOCUMENT_TEXT_CHARS = 18000

const DOCUMENT_TYPE_OPTIONS = [
  { value: 'title_deed', label: 'Title deed' },
  { value: 'service_charge_statement', label: 'Service charge statement' },
  { value: 'dewa_utility_info', label: 'DEWA bill' },
  { value: 'ejari', label: 'Ejari' },
  { value: 'tenancy_contract', label: 'Tenancy contract' },
  { value: 'noc', label: 'NOC' },
  { value: 'valuation_report', label: 'Valuation report' },
  { value: 'mortgage_liability_letter', label: 'Mortgage liability letter' },
  { value: 'floor_plan', label: 'Floor plan' },
  { value: 'snagging_report', label: 'Snagging report' },
  { value: 'building_rules', label: 'Building rules' },
  { value: OTHER_DOCUMENT_TYPE_VALUE, label: 'Other' },
] as const

const HANDOVER_MONTH_OPTIONS = buildHandoverMonthOptions()

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
  const [listingType, setListingType] = useState<ListingPropertyType>('ready')
  const [entryMethod, setEntryMethod] = useState<EntryMethod | null>(startManual ? 'manual' : null)
  const [url, setUrl] = useState('')
  const [draft, setDraft] = useState<Draft | null>(startManual ? BLANK_DRAFT : null)
  const [scrapeMessage, setScrapeMessage] = useState<string | null>(null)
  const [scraping, setScraping] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ listing_id: string } | null>(null)
  const [resultNote, setResultNote] = useState<string | null>(null)
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
  const [propertyCategory, setPropertyCategory] = useState('')
  const [paymentSchedule, setPaymentSchedule] = useState<PaymentInstalment[]>([])
  const [bedrooms, setBedrooms] = useState<number | ''>('')
  const [bathrooms, setBathrooms] = useState<number | ''>('')
  const [sizeSqft, setSizeSqft] = useState<number | ''>('')
  const [plotSizeSqft, setPlotSizeSqft] = useState<number | ''>('')
  const [asking, setAsking] = useState<number | ''>('')
  const [developer, setDeveloper] = useState('')
  const [handoverDate, setHandoverDate] = useState('')
  const [amenitiesText, setAmenitiesText] = useState('')
  const [description, setDescription] = useState('')
  const [images, setImages] = useState<ImageItem[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [supportingDocuments, setSupportingDocuments] = useState<SupportingDocumentItem[]>([])
  const [documentDragActive, setDocumentDragActive] = useState(false)
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
  const calculatedPricePerSqft = useMemo(
    () => calculatePricePerSqft(asking, sizeSqft),
    [asking, sizeSqft]
  )
  const calculatedDldFee = useMemo(
    () => calculatePercentageFee(asking, DLD_FEE_RATE),
    [asking]
  )

  function startBlankManual(nextListingType: ListingPropertyType) {
    setListingType(nextListingType)
    setEntryMethod('manual')
    setDraft({ ...BLANK_DRAFT, property_type: nextListingType })
    setPropertyCategory('')
    setPaymentSchedule([])
    setPurpose('sale')
    setCompletionStatus(nextListingType === 'ready' ? 'completed' : '')
    setHandoverDate('')
    setScrapeMessage(
      nextListingType === 'ready'
        ? 'Manual ready-property form opened. Fill the details below, then publish.'
        : 'Manual off-plan listings use the SPA upload flow so Dalya can ground payment plan, NOC, and handover facts.'
    )
  }

  function resetForm() {
    setListingType('ready')
    setEntryMethod(null)
    setUrl('')
    setDraft(null)
    setScrapeMessage(null)
    setResult(null)
    setResultNote(null)
    setError(null)
    setTitle('')
    setReference('')
    setPurpose('')
    setCompletionStatus('')
    setFurnishing('')
    setCommunity('')
    setSubcommunity('')
    setBuilding('')
    setUnit('')
    setPropertyCategory('')
    setPaymentSchedule([])
    setBedrooms('')
    setBathrooms('')
    setSizeSqft('')
    setPlotSizeSqft('')
    setAsking('')
    setDeveloper('')
    setHandoverDate('')
    setAmenitiesText('')
    setDescription('')
    setImages([])
    setSupportingDocuments([])
    setPermitNumber('')
    setPermitUrl('')
    setBrokerName('')
    setBrokerLicense('')
    setAgentName('')
    setAgentEmail('')
    setAgentPhone('')
    setAgentLicense('')
    setThreshold('')
    setCommissionPct('')
    setFees([])
    if (typeof window !== 'undefined') window.scrollTo({ top: 0 })
  }

  function handleSpaParsed(d: SpaParseResult) {
    setListingType('off_plan')
    setDraft({ ...BLANK_DRAFT, property_type: 'off_plan' })
    setTitle('')
    setReference('')
    setPurpose('sale')
    setCompletionStatus('')
    setFurnishing('')
    setCommunity(d.project ?? '')
    setSubcommunity(d.sub_community ?? '')
    setBuilding(d.project ?? '')
    setUnit(d.unit_number ?? '')
    setPropertyCategory(normalizePropertyCategory(d.property_type))
    setBedrooms(d.bedrooms ?? '')
    setBathrooms(d.bathrooms ?? '')
    setSizeSqft(d.bua_sqft ?? '')
    setPlotSizeSqft(d.plot_sqft ?? '')
    setAsking(d.purchase_price_aed ?? '')
    setDeveloper(normalizeDeveloper(d.developer ?? null))
    setHandoverDate(toMonthValue(d.estimated_completion_date ?? null))
    setPaymentSchedule(d.payment_schedule ?? [])
    const milestoneCount = d.payment_schedule?.length ?? 0
    const nocNote = d.noc_eligible != null ? `, NOC ${d.noc_eligible ? 'eligible' : 'pending'}` : ''
    setScrapeMessage(
      `Parsed SPA: ${milestoneCount} payment milestone${milestoneCount === 1 ? '' : 's'}${nocNote}. Review and complete the details below.`,
    )
  }

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
      const payload: DraftFromUrlResponse = await response.json()
      const d = payload.draft
      setDraft({ ...d, property_type: listingType })
      setTitle(d.listing_title ?? '')
      setReference(d.listing_reference ?? '')
      setPurpose(d.purpose ?? '')
      setCompletionStatus(d.completion_status ?? '')
      setFurnishing(normalizeFurnishing(d.furnishing))
      setCommunity(d.community ?? '')
      setSubcommunity(d.subcommunity ?? '')
      setBuilding(d.building_or_project ?? '')
      setUnit(d.unit_number ?? '')
      setPropertyCategory(normalizePropertyCategory(payload.scrape.property_type))
      setPaymentSchedule([])
      setBedrooms(d.bedrooms ?? '')
      setBathrooms(d.bathrooms ?? '')
      setSizeSqft(d.size_sqft ?? '')
      setPlotSizeSqft(d.plot_size_sqft ?? '')
      setAsking(d.asking_price_aed ?? '')
      setDeveloper(normalizeDeveloper(d.developer))
      setHandoverDate(listingType === 'off_plan' ? toMonthValue(d.handover_date) : '')
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
          : (scraped.warning ?? 'Scrape returned no structured data — fill the form manually.')
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scrape failed')
      // Even on failure, surface the manual form
      setDraft({ ...BLANK_DRAFT, property_type: listingType, source_url: url })
      setPurpose('sale')
      setHandoverDate('')
      setScrapeMessage('Scrape failed — fill the form manually below.')
    } finally {
      setScraping(false)
    }
  }

  function addFee() {
    setFees([...fees, { label: '', amount_aed: null, paid_by: 'buyer', public: true }])
  }

  useEffect(() => {
    setFees((currentFees) => {
      const dldFee: AdditionalFee = {
        label: DLD_FEE_LABEL,
        amount_aed: calculatedDldFee,
        paid_by: 'buyer',
        public: true,
      }
      const existingIndex = currentFees.findIndex((fee) => fee.label === DLD_FEE_LABEL)
      if (existingIndex === -1) return [dldFee, ...currentFees]
      const existing = currentFees[existingIndex]
      if (
        existing?.amount_aed === dldFee.amount_aed
        && existing.paid_by === dldFee.paid_by
        && existing.public === dldFee.public
      ) {
        return currentFees
      }
      return currentFees.map((fee, index) => (index === existingIndex ? dldFee : fee))
    })
  }, [calculatedDldFee])

  useEffect(() => {
    const objectUrls = objectUrlsRef.current
    return () => {
      objectUrls.forEach((objectUrl) => URL.revokeObjectURL(objectUrl))
      objectUrls.clear()
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

  async function addDocumentFiles(files: FileList | File[]) {
    const documents = await Promise.all(Array.from(files).map(toSupportingDocument))
    if (!documents.length) return
    setSupportingDocuments((current) => [...current, ...documents])
  }

  function updateSupportingDocument(id: string, patch: Partial<SupportingDocumentItem>) {
    setSupportingDocuments((current) => current.map((document) => (
      document.id === id ? { ...document, ...patch } : document
    )))
  }

  function removeSupportingDocument(id: string) {
    setSupportingDocuments((current) => current.filter((document) => document.id !== id))
  }

  function addManualSupportingDocument() {
    const documentType = 'title_deed'
    setSupportingDocuments((current) => [
      ...current,
      {
        id: `manual-${crypto.randomUUID()}`,
        documentType,
        customDocumentType: '',
        label: documentLabelForType(documentType),
        fileName: 'Manual document',
        mimeType: 'text/plain',
        sizeBytes: 0,
        contentText: '',
        extractionStatus: 'metadata_only',
      },
    ])
  }

  async function attachSupportingDocuments(listingId: string): Promise<string | null> {
    if (!supportingDocuments.length) return null
    const results = await Promise.all(
      supportingDocuments.map(async (document) => {
        const response = await apiFetch(`/api/v1/listings/${listingId}/documents`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            document_type: documentTypeForParser(document.documentType),
            label: labelForSupportingDocument(document),
            source_url: null,
            content_text: document.contentText.trim() || null,
            metadata_json: {
              file_name: document.fileName,
              mime_type: document.mimeType,
              size_bytes: document.sizeBytes,
              upload_source: 'listing_onboarding',
              extraction_status: document.extractionStatus,
              selected_document_type: document.documentType,
              custom_document_type: document.customDocumentType.trim() || null,
            },
          }),
        })
        if (!response.ok) {
          return document.label || document.fileName
        }
        return null
      })
    )
    const failedDocuments = results.filter((item): item is string => Boolean(item))
    if (failedDocuments.length > 0) {
      return `Listing created, but ${failedDocuments.length} document(s) could not be processed: ${failedDocuments.join(', ')}.`
    }
    return `${supportingDocuments.length} supporting document${supportingDocuments.length === 1 ? '' : 's'} processed into listing context.`
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResultNote(null)
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
        property_type: listingType,
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
        property_category: propertyCategory || null,
        payment_schedule: listingType === 'off_plan' ? paymentSchedule : [],
        bedrooms: bedrooms === '' ? null : Number(bedrooms),
        bathrooms: bathrooms === '' ? null : Number(bathrooms),
        size_sqft: sizeSqft === '' ? null : Number(sizeSqft),
        plot_size_sqft: plotSizeSqft === '' ? null : Number(plotSizeSqft),
        asking_price_aed: asking === '' ? null : Number(asking),
        price_per_sqft_aed: calculatedPricePerSqft,
        developer: developer || null,
        handover_date: listingType === 'off_plan' ? handoverDate || null : null,
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
        reference_documents: supportingDocuments.map((document) => ({
          kind: documentTypeForParser(document.documentType),
          url: null,
          label: labelForSupportingDocument(document),
        })),
      }
      const response = await apiFetch('/api/v1/listings', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        const errBody = await response.json().catch(() => null)
        const detail = typeof errBody?.detail === 'string' ? errBody.detail : `Publish failed (${response.status})`
        throw new Error(detail)
      }
      const payload: { listing_id?: string } = await response.json()
      if (!payload?.listing_id) {
        throw new Error('The listing was submitted but the server did not return a listing id.')
      }
      const created = { listing_id: payload.listing_id }
      const documentNote = await attachSupportingDocuments(created.listing_id)
      setResultNote(documentNote)
      setResult(created)
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
        {resultNote && (
          <p className="mt-2 text-sm text-[var(--color-text-2,#5C5C57)]">
            {resultNote}
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href={`/listings/${result.listing_id}`}
            className="inline-flex items-center rounded-md bg-[var(--color-brand-600,#324B6B)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-500,#3D5A80)]"
          >
            Go to listing page
          </Link>
          <button
            type="button"
            onClick={resetForm}
            className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-4 py-2 text-sm font-medium text-[var(--color-text-1,#3D3D39)] transition hover:border-[var(--color-brand-500,#3D5A80)] hover:bg-[var(--color-surface-1,#F4F4F2)]"
          >
            <span className="material-symbols-outlined text-[18px]" aria-hidden="true">add</span>
            Add another listing
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {!draft && (
        <div className="space-y-5">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-text-1,#3D3D39)]">Add a listing</h1>
            <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
              Choose the listing type, then start from a Property Finder / Bayut link or enter it manually.
            </p>
          </div>
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-text-3,#7B7B76)]">
              Listing type
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <ChoiceCard
                title="Finished property"
                body="Ready resale inventory with permit, viewing, tenancy, and inspection details."
                selected={listingType === 'ready'}
                onClick={() => {
                  setListingType('ready')
                  setEntryMethod(null)
                  setUrl('')
                }}
              />
              <ChoiceCard
                title="Off-plan"
                body="Developer inventory or off-plan resale where handover is month-based."
                selected={listingType === 'off_plan'}
                onClick={() => {
                  setListingType('off_plan')
                  setEntryMethod(null)
                  setUrl('')
                }}
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-text-3,#7B7B76)]">
              Start from
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <ChoiceCard
                title="Property Finder / Bayut link"
                body="Paste a portal URL and review the prefilled draft before publishing."
                selected={entryMethod === 'portal'}
                onClick={() => setEntryMethod('portal')}
              />
              {listingType === 'off_plan' ? (
                <ChoiceCard
                  title="Upload SPA"
                  body="Upload the SPA — Dalya parses the payment plan, NOC, and handover, then you review the same details form."
                  selected={entryMethod === 'spa'}
                  onClick={() => setEntryMethod('spa')}
                />
              ) : (
                <ChoiceCard
                  title="Manual entry"
                  body="Open a blank ready-property form when there is no portal link."
                  selected={entryMethod === 'manual'}
                  onClick={() => startBlankManual('ready')}
                />
              )}
            </div>
          </div>

          {entryMethod === 'spa' && listingType === 'off_plan' && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-[var(--color-text-1,#3D3D39)]">
                Upload the Sale &amp; Purchase Agreement
              </label>
              <SpaUploadDropzone onParsed={handleSpaParsed} />
            </div>
          )}

          {entryMethod === 'portal' && (
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
                className="rounded-md bg-[var(--color-brand-600,#324B6B)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--color-brand-500,#3D5A80)] disabled:opacity-60"
              >
                {scraping ? 'Fetching…' : 'Fetch listing data'}
              </button>
              <p className="text-xs text-[var(--color-text-3,#7B7B76)]">
                We&apos;ll prefill as much as we can. If the scrape fails, you&apos;ll get a blank form to fill manually.
              </p>
            </form>
          )}
        </div>
      )}

      {/* Step 2: Review + confirm */}
      {draft && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--color-text-1,#3D3D39)]">Listing Details</h2>
          {scrapeMessage && (
            <div className="rounded-md bg-[var(--color-surface-2,#E8E8E5)] px-3 py-2 text-xs text-[var(--color-text-2,#5C5C57)]">
              {scrapeMessage}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-sm bg-[var(--color-brand-wash,#EEF2F7)] px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-brand-700,#283C56)]">
              {listingType === 'ready' ? 'Finished property' : 'Off-plan'}
            </span>
            <button
              type="button"
              onClick={() => {
                setDraft(null)
                setEntryMethod(null)
                setScrapeMessage(null)
                setError(null)
              }}
              className="text-xs font-medium text-[var(--color-brand-500,#3D5A80)] hover:underline"
            >
              Change
            </button>
          </div>
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
              <PropertyCategorySelectField value={propertyCategory} onChange={setPropertyCategory} />
              <IntegerField label="Bedrooms" value={bedrooms} onChange={setBedrooms} />
              <IntegerField label="Bathrooms" value={bathrooms} onChange={setBathrooms} />
              <NumberField label="Built-up area (sqft)" value={sizeSqft} onChange={setSizeSqft} />
              <NumberField label="Plot size (sqft)" value={plotSizeSqft} onChange={setPlotSizeSqft} />
              <SegmentedField
                label="Furnished"
                value={furnishing}
                onChange={setFurnishing}
                options={[
                  { value: 'yes', label: 'Yes' },
                  { value: 'no', label: 'No' },
                  { value: '', label: 'Unknown' },
                ]}
              />
              <DeveloperSelectField value={developer} onChange={setDeveloper} />
              {listingType === 'off_plan' && (
                <MonthField label="Handover month" value={handoverDate} onChange={setHandoverDate} />
              )}
            </div>
          </FormSection>

          <FormSection title="Pricing">
            <div className="grid gap-3 md:grid-cols-2">
              <CurrencyField label="Asking price (AED)" value={asking} onChange={setAsking} />
              <ReadOnlyCurrencyField
                label="Price per sqft (AED)"
                value={calculatedPricePerSqft}
                tooltip="Calculated automatically as Asking Price divided by Built-up area."
              />
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

          {listingType === 'off_plan' && paymentSchedule.length > 0 && (
            <FormSection title="Payment schedule">
              <PaymentScheduleTable schedule={paymentSchedule} />
            </FormSection>
          )}

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

          <FormSection title="Supporting documents">
            <div className="space-y-3">
              <label
                onDragEnter={(event) => {
                  event.preventDefault()
                  setDocumentDragActive(true)
                }}
                onDragOver={(event) => {
                  event.preventDefault()
                  setDocumentDragActive(true)
                }}
                onDragLeave={(event) => {
                  event.preventDefault()
                  setDocumentDragActive(false)
                }}
                onDrop={(event) => {
                  event.preventDefault()
                  setDocumentDragActive(false)
                  void addDocumentFiles(event.dataTransfer.files)
                }}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-4 py-7 text-center transition ${
                  documentDragActive
                    ? 'border-[var(--color-brand-500,#3D5A80)] bg-[var(--color-surface-1,#F4F4F2)]'
                    : 'border-[var(--color-surface-2,#E8E8E5)] bg-white hover:border-[var(--color-brand-500,#3D5A80)]'
                }`}
              >
                <span className="material-symbols-outlined text-[28px] text-[var(--color-brand-500,#3D5A80)]" aria-hidden="true">
                  docs
                </span>
                <span className="mt-2 text-sm font-medium text-[var(--color-text-1,#3D3D39)]">
                  Upload DEWA bills, title deeds, service-charge statements, or other documents
                </span>
                <span className="mt-1 text-xs text-[var(--color-text-3,#7B7B76)]">
                  Dalya reads available document text and extracts buyer-safe listing facts.
                </span>
                <input
                  type="file"
                  accept=".pdf,.txt,.text,.csv,.doc,.docx,.jpg,.jpeg,.png,application/pdf,text/*,image/*"
                  multiple
                  className="sr-only"
                  onChange={(event) => {
                    if (event.target.files) void addDocumentFiles(event.target.files)
                    event.target.value = ''
                  }}
                />
              </label>
              <button
                type="button"
                onClick={addManualSupportingDocument}
                className="rounded-md border border-[var(--color-surface-2,#E8E8E5)] px-3 py-2 text-sm font-medium text-[var(--color-text-1,#3D3D39)] transition hover:border-[var(--color-brand-500,#3D5A80)] hover:bg-[var(--color-surface-1,#F4F4F2)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
              >
                Add document manually
              </button>
              {supportingDocuments.length > 0 ? (
                <div className="space-y-3">
                  {supportingDocuments.map((document) => (
                    <SupportingDocumentRow
                      key={document.id}
                      document={document}
                      onChange={(patch) => updateSupportingDocument(document.id, patch)}
                      onRemove={() => removeSupportingDocument(document.id)}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[var(--color-text-3,#7B7B76)]">
                  No supporting documents added yet.
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
              {fees.map((fee, i) => {
                const dldFee = fee.label === DLD_FEE_LABEL
                return (
                  <div key={i} className="grid gap-2 md:grid-cols-[1fr_140px_140px]">
                    <input
                      type="text"
                      aria-label="Fee label"
                      placeholder="Label (e.g. POA fee)"
                      value={fee.label}
                      readOnly={dldFee}
                      onChange={(e) => {
                        const next = [...fees]
                        next[i] = { ...fee, label: e.target.value }
                        setFees(next)
                      }}
                      className={`rounded-md border border-[var(--color-surface-2,#E8E8E5)] px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30 ${
                        dldFee ? 'bg-[var(--color-surface-1,#F4F4F2)] text-[var(--color-text-2,#5C5C57)]' : 'bg-white'
                      }`}
                    />
                    <input
                      type="number"
                      aria-label="Fee amount AED"
                      placeholder="Amount AED"
                      value={fee.amount_aed ?? ''}
                      readOnly={dldFee}
                      onChange={(e) => {
                        const next = [...fees]
                        next[i] = {
                          ...fee,
                          amount_aed: e.target.value === '' ? null : Number(e.target.value),
                        }
                        setFees(next)
                      }}
                      className={`rounded-md border border-[var(--color-surface-2,#E8E8E5)] px-3 py-2 text-sm focus:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30 ${
                        dldFee ? 'bg-[var(--color-surface-1,#F4F4F2)] text-[var(--color-text-2,#5C5C57)]' : 'bg-white'
                      }`}
                    />
                    {dldFee ? (
                      <div className="rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] px-3 py-2 text-sm text-[var(--color-text-2,#5C5C57)]">
                        Buyer
                      </div>
                    ) : (
                      <SelectField
                        label="Paid by"
                        value={fee.paid_by}
                        onChange={(paidBy) => {
                          const next = [...fees]
                          next[i] = { ...fee, paid_by: paidBy }
                          setFees(next)
                        }}
                        options={[
                          { value: 'buyer', label: 'Buyer' },
                          { value: 'seller', label: 'Seller' },
                          { value: 'either', label: 'Either' },
                        ]}
                      />
                    )}
                  </div>
                )
              })}
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

function ChoiceCard({
  title,
  body,
  selected,
  onClick,
}: {
  title: string
  body: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30 ${
        selected
          ? 'border-[var(--color-brand-500,#3D5A80)] bg-[var(--color-brand-wash,#EEF2F7)]'
          : 'border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] hover:border-[var(--color-brand-500,#3D5A80)] hover:bg-white'
      }`}
      aria-pressed={selected}
    >
      <span className="block text-sm font-semibold text-[var(--color-text-1,#3D3D39)]">{title}</span>
      <span className="mt-1 block text-xs leading-5 text-[var(--color-text-3,#7B7B76)]">{body}</span>
    </button>
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
  placeholder = 'Select',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: ReadonlyArray<SelectOption>
  placeholder?: string
}) {
  const [open, setOpen] = useState(false)
  const selectedOption = options.find((option) => option.value === value)
  const displayValue = selectedOption?.value ? selectedOption.label : placeholder

  function handleBlur(event: FocusEvent<HTMLDivElement>) {
    if (event.relatedTarget instanceof Node && event.currentTarget.contains(event.relatedTarget)) return
    setOpen(false)
  }

  return (
    <div className="relative block text-sm" onBlur={handleBlur}>
      <span className="block text-xs text-[var(--color-text-3,#7B7B76)]">{label}</span>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`mt-1 flex min-h-10 w-full items-center justify-between gap-3 rounded-md border bg-white px-3 py-2 text-left text-sm transition focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30 ${
          open
            ? 'border-[var(--color-brand-500,#3D5A80)] shadow-[0_1px_2px_0_rgba(35,35,32,.06)]'
            : 'border-[var(--color-surface-2,#E8E8E5)] hover:border-[var(--color-border-default,#D6D6D2)]'
        }`}
      >
        <span className={value ? 'truncate text-[var(--color-text-1,#3D3D39)]' : 'truncate text-[var(--color-text-3,#7B7B76)]'}>
          {displayValue}
        </span>
        <span
          className={`material-symbols-outlined shrink-0 text-[18px] text-[var(--color-text-3,#7B7B76)] transition-transform ${
            open ? 'rotate-180' : ''
          }`}
          aria-hidden="true"
        >
          keyboard_arrow_down
        </span>
      </button>
      {open && (
        <div className="absolute z-30 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white p-1 shadow-[0_12px_24px_-6px_rgba(35,35,32,.10),0_4px_8px_-2px_rgba(35,35,32,.06)]">
          <div role="listbox" aria-label={label} className="space-y-0.5">
            {options.map((option) => {
              const selected = option.value === value
              return (
                <button
                  key={option.value || '__empty'}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    onChange(option.value)
                    setOpen(false)
                  }}
                  className={`flex w-full items-center justify-between gap-2 rounded px-2.5 py-2 text-left text-sm transition focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30 ${
                    selected
                      ? 'bg-[var(--color-brand-wash,#EEF2F7)] text-[var(--color-brand-700,#283C56)]'
                      : 'text-[var(--color-text-1,#3D3D39)] hover:bg-[var(--color-surface-1,#F4F4F2)]'
                  }`}
                >
                  <span className={option.value ? 'truncate' : 'truncate text-[var(--color-text-3,#7B7B76)]'}>
                    {option.label}
                  </span>
                  {selected && (
                    <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                      check
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function SegmentedField({
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
    <div className="block text-sm">
      <span className="block text-xs text-[var(--color-text-3,#7B7B76)]">{label}</span>
      <div className="mt-1 grid grid-cols-3 gap-1 rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] p-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded px-2 py-1.5 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30 ${
              value === option.value
                ? 'bg-white text-[var(--color-brand-700,#283C56)] shadow-[0_1px_2px_0_rgba(35,35,32,.06)]'
                : 'text-[var(--color-text-2,#5C5C57)] hover:bg-white/70'
            }`}
            aria-pressed={value === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function SupportingDocumentRow({
  document,
  onChange,
  onRemove,
}: {
  document: SupportingDocumentItem
  onChange: (patch: Partial<SupportingDocumentItem>) => void
  onRemove: () => void
}) {
  const extractionLabel = document.extractionStatus === 'parsed'
    ? 'Text ready for parser'
    : document.extractionStatus === 'metadata_only'
      ? 'Metadata only'
      : 'Text extraction failed'

  return (
    <div className="rounded-lg border border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-[var(--color-text-1,#3D3D39)]">{document.fileName}</p>
          <p className="mt-0.5 text-xs text-[var(--color-text-3,#7B7B76)]">
            {formatFileSize(document.sizeBytes)} · {extractionLabel}
          </p>
        </div>
        <button
          type="button"
          onClick={onRemove}
          className="shrink-0 rounded px-2 py-1 text-xs font-medium text-[var(--color-error-500,#B84838)] hover:bg-[color:var(--color-error-500,#B84838)]/10"
        >
          Remove
        </button>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <DocumentTypeSelectField
          value={document.documentType}
          onChange={(nextType) => onChange({
            documentType: nextType,
            label: document.label === documentLabelForType(document.documentType)
              ? documentLabelForType(nextType)
              : document.label,
          })}
        />
        <Field
          label="Document label"
          value={document.label}
          onChange={(label) => onChange({ label })}
          placeholder="e.g. Q2 2026 service charges"
        />
        {document.documentType === OTHER_DOCUMENT_TYPE_VALUE && (
          <Field
            label="Other document type"
            value={document.customDocumentType}
            onChange={(customDocumentType) => onChange({ customDocumentType })}
            placeholder="e.g. Chiller invoice"
          />
        )}
      </div>
      <div className="mt-3">
        <TextArea
          label="Document text"
          value={document.contentText}
          onChange={(contentText) => onChange({
            contentText,
            extractionStatus: contentText.trim() ? 'parsed' : 'metadata_only',
          })}
          rows={3}
        />
      </div>
    </div>
  )
}

function DeveloperSelectField({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  const valueIsKnownDeveloper = DEVELOPER_OPTIONS.some((option) => option === value)
  const [selectedOther, setSelectedOther] = useState(false)
  const customMode = selectedOther || Boolean(value && !valueIsKnownDeveloper)
  const customDeveloperValue = customMode && !valueIsKnownDeveloper ? value : ''
  const selectValue = customMode ? OTHER_DEVELOPER_VALUE : value

  function handleSelect(nextValue: string) {
    if (nextValue === OTHER_DEVELOPER_VALUE) {
      setSelectedOther(true)
      if (valueIsKnownDeveloper) onChange('')
      return
    }
    setSelectedOther(false)
    onChange(nextValue)
  }

  return (
    <div className="space-y-2">
      <SelectField
        label="Developer"
        value={selectValue}
        onChange={handleSelect}
        placeholder="Select developer"
        options={[
          { value: '', label: 'Select developer' },
          ...DEVELOPER_OPTIONS.map((developerName) => ({ value: developerName, label: developerName })),
          { value: OTHER_DEVELOPER_VALUE, label: 'Other' },
        ]}
      />
      {customMode && (
        <label className="block text-sm">
          <span className="sr-only">Other developer name</span>
          <div className="flex min-h-10 items-center gap-2 rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 transition focus-within:border-[var(--color-brand-500,#3D5A80)] focus-within:ring-2 focus-within:ring-[var(--color-brand-500,#3D5A80)]/30">
            <span className="material-symbols-outlined text-[17px] text-[var(--color-text-3,#7B7B76)]" aria-hidden="true">
              edit
            </span>
            <input
              type="text"
              value={customDeveloperValue}
              onChange={(event) => onChange(event.target.value)}
              placeholder="Enter developer name"
              className="min-w-0 flex-1 bg-transparent text-sm text-[var(--color-text-1,#3D3D39)] outline-none placeholder:text-[var(--color-text-3,#7B7B76)]"
            />
          </div>
        </label>
      )}
    </div>
  )
}

function PaymentScheduleTable({ schedule }: { schedule: PaymentInstalment[] }) {
  const totalPct = schedule.reduce((sum, item) => sum + (item.percentage || 0), 0)
  const totalAmount = schedule.reduce((sum, item) => sum + (item.amount_incl_vat_aed ?? item.amount_aed ?? 0), 0)
  return (
    <div className="overflow-hidden rounded-md border border-[var(--color-surface-2,#E8E8E5)]">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-3,#7B7B76)]">
            <th className="px-3 py-2 font-semibold">Milestone</th>
            <th className="px-3 py-2 text-right font-semibold">%</th>
            <th className="px-3 py-2 text-right font-semibold">Amount (AED)</th>
            <th className="px-3 py-2 font-semibold">Due</th>
            <th className="px-3 py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-surface-2,#E8E8E5)]">
          {schedule.map((item, index) => (
            <tr key={`${item.instalment_number ?? index}-${item.milestone}`}>
              <td className="px-3 py-2 text-[var(--color-text-1,#3D3D39)]">{item.milestone || `Installment ${index + 1}`}</td>
              <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-2,#5C5C57)]">
                {item.percentage != null ? `${item.percentage}%` : '—'}
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-1,#3D3D39)]">
                {formatMoney(item.amount_incl_vat_aed ?? item.amount_aed ?? 0)}
              </td>
              <td className="px-3 py-2 tabular-nums text-[var(--color-text-2,#5C5C57)]">{item.due_date || '—'}</td>
              <td className="px-3 py-2">
                {(() => {
                  const completed = isInstalmentCompleted(item)
                  return (
                    <span
                      className={`rounded-sm px-2 py-0.5 text-[11px] font-semibold ${
                        completed ? 'bg-sage/15 text-sage' : 'bg-[var(--color-surface-2,#E8E8E5)] text-[var(--color-text-2,#5C5C57)]'
                      }`}
                    >
                      {completed ? 'Completed' : 'Upcoming'}
                    </span>
                  )
                })()}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] font-semibold">
            <td className="px-3 py-2 text-[var(--color-text-1,#3D3D39)]">Total</td>
            <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-1,#3D3D39)]">{Math.round(totalPct)}%</td>
            <td className="px-3 py-2 text-right tabular-nums text-[var(--color-text-1,#3D3D39)]">{formatMoney(totalAmount)}</td>
            <td className="px-3 py-2" />
            <td className="px-3 py-2" />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

function PropertyCategorySelectField({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  const valueIsKnown = PROPERTY_CATEGORY_OPTIONS.some((option) => option === value)
  const [selectedOther, setSelectedOther] = useState(false)
  const customMode = selectedOther || Boolean(value && !valueIsKnown)
  const customValue = customMode && !valueIsKnown ? value : ''
  const selectValue = customMode ? OTHER_PROPERTY_CATEGORY_VALUE : value

  function handleSelect(nextValue: string) {
    if (nextValue === OTHER_PROPERTY_CATEGORY_VALUE) {
      setSelectedOther(true)
      if (valueIsKnown) onChange('')
      return
    }
    setSelectedOther(false)
    onChange(nextValue)
  }

  return (
    <div className="space-y-2">
      <SelectField
        label="Property type"
        value={selectValue}
        onChange={handleSelect}
        placeholder="Select property type"
        options={[
          { value: '', label: 'Select property type' },
          ...PROPERTY_CATEGORY_OPTIONS.map((category) => ({ value: category, label: category })),
          { value: OTHER_PROPERTY_CATEGORY_VALUE, label: 'Other' },
        ]}
      />
      {customMode && (
        <label className="block text-sm">
          <span className="sr-only">Other property type</span>
          <div className="flex min-h-10 items-center gap-2 rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 transition focus-within:border-[var(--color-brand-500,#3D5A80)] focus-within:ring-2 focus-within:ring-[var(--color-brand-500,#3D5A80)]/30">
            <span className="material-symbols-outlined text-[17px] text-[var(--color-text-3,#7B7B76)]" aria-hidden="true">
              edit
            </span>
            <input
              type="text"
              value={customValue}
              onChange={(event) => onChange(event.target.value)}
              placeholder="Enter property type"
              className="min-w-0 flex-1 bg-transparent text-sm text-[var(--color-text-1,#3D3D39)] outline-none placeholder:text-[var(--color-text-3,#7B7B76)]"
            />
          </div>
        </label>
      )}
    </div>
  )
}

function DocumentTypeSelectField({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  return (
    <SelectField
      label="Document type"
      value={value}
      onChange={onChange}
      placeholder="Select document type"
      options={DOCUMENT_TYPE_OPTIONS}
    />
  )
}

function MonthField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <SelectField
      label={label}
      value={value}
      onChange={onChange}
      placeholder="Select"
      options={[
        { value: '', label: 'Select' },
        ...HANDOVER_MONTH_OPTIONS,
      ]}
    />
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

function ReadOnlyCurrencyField({
  label,
  value,
  tooltip,
}: {
  label: string
  value: number | null
  tooltip: string
}) {
  return (
    <div className="block text-sm">
      <FieldLabel label={label} tooltip={tooltip} />
      <div className="mt-1 w-full rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] px-3 py-2 font-mono text-sm tabular-nums text-[var(--color-text-1,#3D3D39)]">
        {value === null ? 'Enter price and built-up area' : formatNumber(value)}
      </div>
    </div>
  )
}

function FieldLabel({ label, tooltip }: { label: string; tooltip?: string }) {
  return (
    <span className="flex items-center gap-1 text-xs text-[var(--color-text-3,#7B7B76)]">
      {label}
      {tooltip && (
        <span className="group relative inline-flex">
          <button
            type="button"
            className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-[var(--color-surface-2,#E8E8E5)] bg-white text-[10px] font-semibold text-[var(--color-brand-500,#3D5A80)] transition hover:border-[var(--color-brand-500,#3D5A80)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand-500,#3D5A80)]/30"
            aria-label={tooltip}
          >
            i
          </button>
          <span
            role="tooltip"
            className="pointer-events-none absolute left-1/2 top-6 z-20 w-64 -translate-x-1/2 rounded-md border border-[var(--color-surface-2,#E8E8E5)] bg-white px-3 py-2 text-xs leading-5 text-[var(--color-text-2,#5C5C57)] opacity-0 shadow-[0_4px_8px_-2px_rgba(35,35,32,.08),0_2px_4px_-2px_rgba(35,35,32,.06)] transition group-hover:opacity-100 group-focus-within:opacity-100"
          >
            {tooltip}
          </span>
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

function normalizeDeveloper(value: string | null): string {
  if (!value) return ''
  const normalized = value.trim().toLowerCase()
  const match = DEVELOPER_OPTIONS.find((option) => option.toLowerCase() === normalized)
  return match ?? value
}

function isInstalmentCompleted(item: PaymentInstalment): boolean {
  // Explicit override wins; otherwise a milestone whose due date is in the past is completed.
  if (item.actually_paid === true) return true
  if (item.actually_paid === false) return false
  if (!item.due_date) return false
  const due = Date.parse(item.due_date)
  return Number.isFinite(due) && due <= Date.now()
}

function normalizePropertyCategory(value: string | null | undefined): string {
  if (!value) return ''
  const normalized = value.trim().toLowerCase()
  // Map the free-text PF/Bayut category onto our canonical options. Ready/off_plan
  // are listing-type values that leak into the scraper's property_type — ignore those.
  if (['ready', 'off_plan', 'off-plan'].includes(normalized)) return ''
  if (normalized.includes('penthouse')) return 'Penthouse'
  if (normalized.includes('town')) return 'Townhouse'
  if (normalized.includes('villa')) return 'Villa'
  if (normalized.includes('apartment') || normalized.includes('flat')) return 'Apartment'
  const match = PROPERTY_CATEGORY_OPTIONS.find((option) => option.toLowerCase() === normalized)
  return match ?? value.trim()
}

function toMonthValue(value: string | null): string {
  if (!value) return ''
  const match = value.match(/^(\d{4})-(\d{2})/)
  return match ? `${match[1]}-${match[2]}` : ''
}

function buildHandoverMonthOptions(): SelectOption[] {
  const startYear = new Date().getFullYear()
  const options: SelectOption[] = []
  for (let year = startYear; year <= startYear + 7; year += 1) {
    for (let month = 0; month < 12; month += 1) {
      const value = `${year}-${String(month + 1).padStart(2, '0')}`
      const label = new Intl.DateTimeFormat('en-US', {
        month: 'short',
        year: 'numeric',
      }).format(new Date(year, month, 1))
      options.push({ value, label })
    }
  }
  return options
}

function calculatePricePerSqft(asking: number | '', sizeSqft: number | ''): number | null {
  if (asking === '' || sizeSqft === '' || sizeSqft <= 0) return null
  return Math.round(asking / sizeSqft)
}

function calculatePercentageFee(amount: number | '', rate: number): number | null {
  if (amount === '' || amount <= 0) return null
  return Math.round(amount * rate)
}

async function toSupportingDocument(file: File): Promise<SupportingDocumentItem> {
  const contentText = await extractReadableDocumentText(file)
  const extractionStatus: SupportingDocumentItem['extractionStatus'] = contentText
    ? 'parsed'
    : isPotentiallyTextReadable(file)
      ? 'metadata_only'
      : 'metadata_only'
  const documentType = inferDocumentType(file.name)
  return {
    id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
    documentType,
    customDocumentType: '',
    label: documentLabelForType(documentType),
    fileName: file.name,
    mimeType: file.type || 'application/octet-stream',
    sizeBytes: file.size,
    file,
    contentText,
    extractionStatus,
  }
}

async function extractReadableDocumentText(file: File): Promise<string> {
  if (!isPotentiallyTextReadable(file)) return ''
  try {
    const text = await file.text()
    return normalizeDocumentText(text).slice(0, MAX_DOCUMENT_TEXT_CHARS)
  } catch (err) {
    if (err instanceof Error) return ''
    throw err
  }
}

function normalizeDocumentText(value: string): string {
  return value
    .replace(/[^\t\n\r -~]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function isPotentiallyTextReadable(file: File): boolean {
  const lowerName = file.name.toLowerCase()
  return (
    file.type.startsWith('text/')
    || file.type === 'application/pdf'
    || lowerName.endsWith('.txt')
    || lowerName.endsWith('.csv')
    || lowerName.endsWith('.pdf')
  )
}

function inferDocumentType(fileName: string): string {
  const normalized = fileName.toLowerCase()
  if (normalized.includes('dewa') || normalized.includes('utility')) return 'dewa_utility_info'
  if (normalized.includes('title') || normalized.includes('deed')) return 'title_deed'
  if (normalized.includes('service') || normalized.includes('charge') || normalized.includes('oa')) return 'service_charge_statement'
  if (normalized.includes('ejari')) return 'ejari'
  if (normalized.includes('tenancy') || normalized.includes('lease')) return 'tenancy_contract'
  if (normalized.includes('noc')) return 'noc'
  if (normalized.includes('valuation')) return 'valuation_report'
  if (normalized.includes('mortgage') || normalized.includes('liability')) return 'mortgage_liability_letter'
  if (normalized.includes('floor')) return 'floor_plan'
  if (normalized.includes('snag')) return 'snagging_report'
  return 'title_deed'
}

function documentTypeForParser(documentType: string): string {
  return documentType === OTHER_DOCUMENT_TYPE_VALUE ? FALLBACK_OTHER_DOCUMENT_TYPE : documentType
}

function documentLabelForType(documentType: string): string {
  const option = DOCUMENT_TYPE_OPTIONS.find((item) => item.value === documentType)
  return option?.label ?? 'Document'
}

function labelForSupportingDocument(document: SupportingDocumentItem): string {
  const baseLabel = document.label.trim()
  if (document.documentType !== OTHER_DOCUMENT_TYPE_VALUE) return baseLabel || documentLabelForType(document.documentType)
  const customType = document.customDocumentType.trim()
  if (baseLabel && customType) return `${customType}: ${baseLabel}`
  return baseLabel || customType || 'Other document'
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`
  if (sizeBytes < 1024 * 1024) return `${Math.round(sizeBytes / 1024)} KB`
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
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
