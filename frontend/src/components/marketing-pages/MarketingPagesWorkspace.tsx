import Link from 'next/link'

type PageStatus = 'Draft' | 'Review' | 'Published'
type NocStatus = 'eligible' | 'approaching' | 'not-yet'

const pages = [
  {
    id: 'jvc-seller-plan',
    slug: 'jvc-1br-seller-plan',
    title: 'JVC 1BR seller plan',
    audience: 'Owners considering a sale in JVC',
    status: 'Published' as PageStatus,
    campaign: 'JVC 1BR owner outreach',
    updated: '15 May',
    cta: 'Discuss selling plan',
  },
  {
    id: 'downtown-valuation',
    slug: 'downtown-seller-valuation',
    title: 'Downtown valuation plan',
    audience: 'Owners asking what their property could achieve now',
    status: 'Review' as PageStatus,
    campaign: 'Downtown seller valuation',
    updated: '14 May',
    cta: 'Request valuation',
  },
  {
    id: 'post-viewing-follow-up',
    slug: 'post-viewing-follow-up',
    title: 'Post-viewing follow-up',
    audience: 'Warm buyers after viewing completion',
    status: 'Draft' as PageStatus,
    campaign: 'Agent viewing follow-up',
    updated: '12 May',
    cta: 'Ask Dalya',
  },
]

const previewBlocks = [
  { label: 'Hero', status: 'Ready', detail: 'Property, community, agent, brokerage, and CTA.' },
  { label: 'Market rationale', status: 'Ready', detail: 'Demand angle, likely buyer profile, and recent activity.' },
  { label: 'Marketing plan', status: 'Ready', detail: 'Portal strategy, media plan, buyer targeting, and viewing approach.' },
  { label: 'Lead attribution', status: 'Static', detail: 'View and CTA tracking are reserved for the next pass.' },
]

const pageById = new Map(pages.map((page) => [page.id, page]))
const pageBySlug = new Map(pages.map((page) => [page.slug, page]))

export function MarketingPagesOverview() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-700">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
                Marketing pages
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-800">
                Page library
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
                Seller one-pagers that show owners how the agent would market their property before a follow-up call.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/campaigns/new"
                className="rounded-md border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Build from campaign
              </Link>
              <Link
                href="/p/jvc-1br-seller-plan"
                className="rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
              >
                Open sample page
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:px-8">
        <section className="rounded-lg border border-neutral-200 bg-white">
          <div className="border-b border-neutral-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-neutral-800">Pages</h2>
            <p className="mt-1 text-xs text-neutral-500">Seeded routes and review states for owner-outreach one-pagers.</p>
          </div>
          <div className="divide-y divide-neutral-200">
            {pages.map((page) => (
              <article key={page.id} className="grid gap-4 px-5 py-4 lg:grid-cols-[minmax(0,1fr)_180px_160px] lg:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold tracking-tight text-neutral-800">{page.title}</h3>
                    <PageStatusPill status={page.status} />
                  </div>
                  <p className="mt-1 text-sm leading-6 text-neutral-600">{page.audience}</p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-neutral-500">
                    <span>Campaign: {page.campaign}</span>
                    <span>Slug: /p/{page.slug}</span>
                    <span>CTA: {page.cta}</span>
                  </div>
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Updated</p>
                  <p className="mt-1 font-mono text-sm text-neutral-800">{page.updated}</p>
                </div>
                <div className="flex flex-wrap gap-2 lg:justify-end">
                  <Link
                    href={`/pages/${page.id}/preview`}
                    className="rounded-md border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
                  >
                    Preview
                  </Link>
                  <Link
                    href={`/p/${page.slug}`}
                    className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
                  >
                    Public
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="space-y-4">
          <ScoreCard label="Published" value="1" detail="Public sample route is available" tone="success" />
          <ScoreCard label="Needs review" value="1" detail="Compliance copy and NOC language" tone="warning" />
          <div className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">Page requirements</h2>
            <div className="mt-4 space-y-3">
              {[
                'Agent and brokerage visible on every public page',
                'Property marketing plan written for the owner',
                'Indicative pricing caveat included',
                'No private owner data in public URL or page body',
              ].map((item) => (
                <div key={item} className="flex items-start gap-2">
                  <Icon name="check_circle" className="text-success-500" />
                  <p className="text-sm leading-5 text-neutral-700">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

export function MarketingPagePreview({ id }: { id: string }) {
  const page = pageById.get(id) ?? pages[0]

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-700">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <Link href="/pages" className="text-sm font-medium text-brand-600 hover:text-brand-700">
                Back to page library
              </Link>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight text-neutral-800">{page.title}</h1>
                <PageStatusPill status={page.status} />
              </div>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">{page.audience}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href={`/p/${page.slug}`}
                className="rounded-md border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Public route
              </Link>
              <button className="rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700">
                Mark ready
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[320px_minmax(0,1fr)] lg:px-8">
        <aside className="space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">Preview status</h2>
            <div className="mt-4 space-y-3">
              {previewBlocks.map((block) => (
                <div key={block.label} className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-neutral-800">{block.label}</p>
                    <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-neutral-600">
                      {block.status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-neutral-500">{block.detail}</p>
                </div>
              ))}
            </div>
          </div>
          <ScoreCard label="Route" value={`/p/${page.slug}`} detail="Next app route scaffold" />
        </aside>

        <section className="overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-card-sm">
          <div className="border-b border-neutral-200 bg-neutral-50 px-4 py-3">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-error-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-warning-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-success-500" />
              <span className="ml-3 rounded bg-white px-3 py-1 font-mono text-xs text-neutral-500">
                dalya.ai/p/{page.slug}
              </span>
            </div>
          </div>
          <PublicMarketingPage slug={page.slug} embedded />
        </section>
      </main>
    </div>
  )
}

export function PublicMarketingPage({ slug, embedded = false }: { slug: string; embedded?: boolean }) {
  const page = pageBySlug.get(slug) ?? pages[0]
  const shellClass = embedded ? 'bg-white' : 'marketing-surface bg-neutral-50'

  return (
    <div className={shellClass}>
      <section className="border-b border-neutral-200 bg-white">
        <div className="mx-auto grid max-w-[1180px] gap-8 px-5 py-12 md:grid-cols-[minmax(0,1fr)_360px] md:items-center lg:px-8">
          <div>
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
                RERA Licensed
              </span>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
                Trakheesi Partner
              </span>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
                DLD Registered
              </span>
            </div>
            <h1 className="mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-neutral-800 md:text-5xl">
              Here is how I would market your property
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-600">
              A focused seller plan with market rationale, buyer targeting, pricing context, and a clear next step with the agent.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button className="rounded-md bg-brand-600 px-5 py-3 text-sm font-medium text-white hover:bg-brand-700">
                {page.cta}
              </button>
              <button className="rounded-md border border-neutral-300 px-5 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
                WhatsApp agent
              </button>
            </div>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Seller plan</p>
            <div className="mt-4 space-y-3">
              <PlanRow label="Buyer profile" value="End users and yield-focused investors" />
              <PlanRow label="Media plan" value="Photos, short video, portal copy, agent network" />
              <PlanRow label="Next action" value="Review valuation range with agent" />
            </div>
            <p className="mt-4 text-xs leading-5 text-neutral-500">
              Pricing context is indicative and should be confirmed with the assigned agent before any owner decision.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-12 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <ListingProofCard />
          <div className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-base font-semibold tracking-tight text-neutral-800">Lead capture status</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              This public page is static for now. WhatsApp routing, CTA tracking, and campaign attribution are not connected.
            </p>
            <div className="mt-5 space-y-3">
              <InputPreview label="Owner intent" value="Valuation, listing, or market check" />
              <InputPreview label="Property value" value="AED range" />
              <InputPreview label="Preferred contact" value="WhatsApp" />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

function ListingProofCard() {
  return (
    <article className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-success-50 px-3 py-1 text-xs font-medium text-success-700">
              Marketing plan
            </span>
            <NocPill status="eligible" />
          </div>
          <h2 className="mt-4 text-xl font-semibold tracking-tight text-neutral-800">
            JVC 1BR seller acquisition plan
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
            Sample page proof model showing marketability, buyer profile, viewing strategy, pricing intelligence, and
            agent follow-up.
          </p>
        </div>
        <div className="rounded-md bg-neutral-50 px-4 py-3 text-right">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Ask price</p>
          <p className="mt-1 font-mono text-2xl font-semibold text-neutral-800">AED 5.95M</p>
        </div>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <ProofMetric label="Community demand" value="High" />
        <ProofMetric label="Likely buyers" value="2 groups" />
        <ProofMetric label="Follow-up" value="2 hours" />
      </div>
    </article>
  )
}

function PlanRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-neutral-200 bg-white px-4 py-3">
      <span className="text-sm text-neutral-600">{label}</span>
      <span className="max-w-[180px] text-right text-sm font-semibold text-brand-700">{value}</span>
    </div>
  )
}

function InputPreview({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-xs font-medium text-neutral-600">{label}</label>
      <div className="mt-1 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500">
        {value}
      </div>
    </div>
  )
}

function ProofMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className="mt-1 font-mono text-lg font-semibold text-neutral-800">{value}</p>
    </div>
  )
}

function ScoreCard({
  label,
  value,
  detail,
  tone = 'default',
}: {
  label: string
  value: string
  detail: string
  tone?: 'default' | 'warning' | 'success'
}) {
  const valueClass =
    tone === 'warning' ? 'text-warning-700' : tone === 'success' ? 'text-success-700' : 'text-neutral-800'

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className={`mt-2 font-mono text-3xl font-semibold ${valueClass}`}>{value}</p>
      <p className="mt-2 text-sm text-neutral-500">{detail}</p>
    </div>
  )
}

function PageStatusPill({ status }: { status: PageStatus }) {
  const classes = {
    Draft: 'bg-neutral-100 text-neutral-600',
    Review: 'bg-warning-50 text-warning-700',
    Published: 'bg-success-50 text-success-700',
  }

  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${classes[status]}`}>{status}</span>
}

function NocPill({ status }: { status: NocStatus }) {
  const labels = {
    eligible: 'NOC eligible',
    approaching: 'NOC approaching',
    'not-yet': 'NOC not yet',
  }
  const classes = {
    eligible: 'bg-success-50 text-success-700',
    approaching: 'bg-warning-50 text-warning-700',
    'not-yet': 'bg-neutral-100 text-neutral-600',
  }

  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${classes[status]}`}>{labels[status]}</span>
}

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={{ fontSize: 18 }} aria-hidden="true">
      {name}
    </span>
  )
}
