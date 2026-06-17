import Link from 'next/link'

type CampaignStatus = 'Draft' | 'Review' | 'Scheduled' | 'Live'
type StepStatus = 'Done' | 'Current' | 'Waiting'

const campaigns = [
  {
    name: 'JVC 1BR owner outreach',
    audience: 'Owners in JVC with likely resale intent',
    status: 'Live' as CampaignStatus,
    channel: 'Manual WhatsApp + one-pager',
    owner: 'Noura',
    launch: '15 May',
    leads: '42',
    conversion: '31 drafts',
  },
  {
    name: 'Downtown seller valuation',
    audience: 'Owners asking for current market value',
    status: 'Scheduled' as CampaignStatus,
    channel: 'Call script + one-pager',
    owner: 'Adeel',
    launch: '19 May',
    leads: '18',
    conversion: '7 pages',
  },
  {
    name: 'Agent viewing follow-up',
    audience: 'Warm leads after completed viewing',
    status: 'Review' as CampaignStatus,
    channel: 'WhatsApp sequence',
    owner: 'Maya',
    launch: 'Needs approval',
    leads: '9',
    conversion: 'Draft',
  },
]

const wizardSteps = [
  {
    title: 'Audience',
    status: 'Done' as StepStatus,
    detail: 'Owner segment, property type, source, and outreach intent selected.',
  },
  {
    title: 'Message',
    status: 'Current' as StepStatus,
    detail: 'Personalized opener, follow-up, call script, and review requirements are being shaped.',
  },
  {
    title: 'Page',
    status: 'Waiting' as StepStatus,
    detail: 'Seller one-pager block order and preview link will be generated from the campaign.',
  },
  {
    title: 'Distribution',
    status: 'Waiting' as StepStatus,
    detail: 'WhatsApp, email, agent task queue, and handoff status remain disabled for now.',
  },
]

const checklist = [
  { label: 'Owner source captured for every uploaded lead', state: 'Done' },
  { label: 'Missing consent/source blockers are visible before launch', state: 'Done' },
  { label: 'Agent reviews drafts before any manual send', state: 'Done' },
  { label: 'Seller one-pager copy reviewed', state: 'Review' },
  { label: 'No autonomous bulk send wired', state: 'Static' },
]

export function CampaignsOverview() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-700">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
                Campaign builder
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-800">
                Owner campaigns
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
                Plan owner outreach, review personalized drafts, and attach seller one-pagers while keeping the agent in control.
              </p>
            </div>
            <Link
              href="/campaigns/new"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              <Icon name="add" />
              New campaign
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[minmax(0,1fr)_340px] lg:px-8">
        <section className="rounded-lg border border-neutral-200 bg-white">
          <div className="flex flex-col gap-3 border-b border-neutral-200 px-5 py-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-neutral-800">Campaign pipeline</h2>
              <p className="mt-1 text-xs text-neutral-500">Seeded owner-acquisition records for the first dashboard pass.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {['Draft', 'Review', 'Scheduled', 'Live'].map((status) => (
                <StatusPill key={status} status={status as CampaignStatus} />
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="border-b border-neutral-200 bg-neutral-50 text-[11px] uppercase tracking-[0.12em] text-neutral-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Campaign</th>
                  <th className="px-5 py-3 font-semibold">Audience</th>
                  <th className="px-5 py-3 font-semibold">Status</th>
                  <th className="px-5 py-3 font-semibold">Owner</th>
                  <th className="px-5 py-3 font-semibold">Launch</th>
                  <th className="px-5 py-3 text-right font-semibold">Leads</th>
                  <th className="px-5 py-3 text-right font-semibold">Conversion</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {campaigns.map((campaign) => (
                  <tr key={campaign.name} className="align-top hover:bg-neutral-50">
                    <td className="px-5 py-4">
                      <p className="font-medium text-neutral-800">{campaign.name}</p>
                      <p className="mt-1 text-xs text-neutral-500">{campaign.channel}</p>
                    </td>
                    <td className="max-w-[260px] px-5 py-4 text-neutral-600">{campaign.audience}</td>
                    <td className="px-5 py-4">
                      <StatusPill status={campaign.status} />
                    </td>
                    <td className="px-5 py-4 text-neutral-600">{campaign.owner}</td>
                    <td className="px-5 py-4 font-mono text-xs text-neutral-600">{campaign.launch}</td>
                    <td className="px-5 py-4 text-right font-mono text-neutral-800">{campaign.leads}</td>
                    <td className="px-5 py-4 text-right font-mono text-neutral-800">{campaign.conversion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="space-y-4">
          <MetricCard label="Ready pages" value="4" detail="Seller one-pagers ready for review" />
          <MetricCard label="Pending review" value="2" detail="Copy and compliance approval" tone="warning" />
          <MetricCard label="Active audiences" value="3" detail="Owner lists under review" tone="success" />
          <div className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">Module status</h2>
            <div className="mt-4 space-y-3">
              <SideStatus icon="dataset" label="Data source" value="Seed data" />
              <SideStatus icon="public" label="Bulk send" value="Not wired" />
              <SideStatus icon="rule" label="Compliance" value="Visible checks" />
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

export function CampaignBuilder() {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-700">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <Link href="/campaigns" className="text-sm font-medium text-brand-600 hover:text-brand-700">
                Back to campaigns
              </Link>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-800">
                New campaign
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">
                Build a controlled owner-outreach workflow: upload a list, map fields, define the message, generate drafts, then review manually.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="rounded-md border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
                Save draft
              </button>
              <button className="rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700">
                Request review
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 sm:px-6 lg:grid-cols-[320px_minmax(0,1fr)_340px] lg:px-8">
        <section className="rounded-lg border border-neutral-200 bg-white">
          <div className="border-b border-neutral-200 px-5 py-4">
            <h2 className="text-sm font-semibold text-neutral-800">Wizard steps</h2>
            <p className="mt-1 text-xs text-neutral-500">V1 campaign flow reserved for upload, mapping, draft generation, and review.</p>
          </div>
          <div className="p-5">
            <ol className="space-y-4">
              {wizardSteps.map((step, index) => (
                <li key={step.title} className="flex gap-3">
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${
                      step.status === 'Done'
                        ? 'border-success-500 bg-success-50 text-success-700'
                        : step.status === 'Current'
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-neutral-300 bg-white text-neutral-500'
                    }`}
                  >
                    {index + 1}
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-neutral-800">{step.title}</p>
                      <StepPill status={step.status} />
                    </div>
                    <p className="mt-1 text-xs leading-5 text-neutral-500">{step.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="space-y-4">
          <Panel title="Campaign brief" icon="edit_note">
            <div className="grid gap-3 sm:grid-cols-2">
              <FieldPreview label="Campaign name" value="JVC 1BR owner outreach" />
              <FieldPreview label="Audience" value="Owners with source and property fields mapped" />
              <FieldPreview label="Primary CTA" value="Discuss your selling plan" />
              <FieldPreview label="Distribution" value="Manual WhatsApp, call script, agent queue" />
            </div>
          </Panel>

          <Panel title="Offer and compliance" icon="verified">
            <div className="grid gap-3 xl:grid-cols-3">
              <ProofPoint title="Source check" value="Owner source and consent status visible before review" />
              <ProofPoint title="Agent control" value="Drafts are edited, approved, copied, or rejected manually" />
              <ProofPoint title="Page proof" value="Seller one-pager explains the marketing plan for the property" />
            </div>
          </Panel>

          <Panel title="Page block plan" icon="view_quilt">
            <div className="divide-y divide-neutral-200">
              {[
                ['1', 'Property positioning', 'Community, building, property type, and agent contact context.'],
                ['2', 'Marketing plan', 'Portal strategy, media plan, buyer targeting, and viewing approach.'],
                ['3', 'Pricing intelligence', 'Indicative range, comparable summary, caveat, and next-step CTA.'],
              ].map(([order, title, detail]) => (
                <div key={title} className="grid gap-3 py-3 sm:grid-cols-[48px_minmax(0,1fr)_110px] sm:items-center">
                  <span className="font-mono text-sm text-brand-600">{order}</span>
                  <div>
                    <p className="text-sm font-medium text-neutral-800">{title}</p>
                    <p className="mt-1 text-xs text-neutral-500">{detail}</p>
                  </div>
                  <span className="rounded-full bg-neutral-100 px-3 py-1 text-center text-xs font-medium text-neutral-600">
                    Static
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        <aside className="space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">Readiness checks</h2>
            <div className="mt-4 space-y-3">
              {checklist.map((item) => (
                <div key={item.label} className="flex items-start justify-between gap-3">
                  <p className="text-sm leading-5 text-neutral-700">{item.label}</p>
                  <span className="shrink-0 rounded-full bg-neutral-100 px-2.5 py-1 text-[11px] font-medium text-neutral-600">
                    {item.state}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-neutral-800">Sample launch card</h2>
            <div className="mt-4 rounded-md border border-neutral-200 bg-neutral-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-600">
                Owner campaign
              </p>
              <p className="mt-2 text-lg font-semibold tracking-tight text-neutral-800">
                Show how you would market the property
              </p>
              <p className="mt-2 text-sm leading-6 text-neutral-600">
                Give an owner a concrete selling plan, then let the agent decide when and how to follow up.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full bg-success-50 px-3 py-1 text-xs font-medium text-success-700">
                  Draft ready
                </span>
                <span className="rounded-full bg-warning-50 px-3 py-1 text-xs font-medium text-warning-700">
                  Consent review
                </span>
              </div>
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

function Panel({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-neutral-200 bg-white">
      <div className="flex items-center gap-2 border-b border-neutral-200 px-5 py-4">
        <Icon name={icon} className="text-brand-600" />
        <h2 className="text-sm font-semibold text-neutral-800">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </section>
  )
}

function MetricCard({
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

function FieldPreview({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-neutral-800">{value}</p>
    </div>
  )
}

function ProofPoint({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-md border border-neutral-200 bg-white p-4">
      <p className="text-sm font-semibold text-neutral-800">{title}</p>
      <p className="mt-2 text-sm leading-6 text-neutral-600">{value}</p>
    </div>
  )
}

function SideStatus({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <Icon name={icon} className="text-brand-600" />
        <span className="text-sm text-neutral-600">{label}</span>
      </div>
      <span className="text-sm font-medium text-neutral-800">{value}</span>
    </div>
  )
}

function StatusPill({ status }: { status: CampaignStatus }) {
  const classes = {
    Draft: 'bg-neutral-100 text-neutral-600',
    Review: 'bg-warning-50 text-warning-700',
    Scheduled: 'bg-brand-50 text-brand-700',
    Live: 'bg-success-50 text-success-700',
  }

  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${classes[status]}`}>{status}</span>
}

function StepPill({ status }: { status: StepStatus }) {
  const classes = {
    Done: 'bg-success-50 text-success-700',
    Current: 'bg-brand-50 text-brand-700',
    Waiting: 'bg-neutral-100 text-neutral-600',
  }

  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${classes[status]}`}>{status}</span>
}

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className}`} style={{ fontSize: 18 }} aria-hidden="true">
      {name}
    </span>
  )
}
