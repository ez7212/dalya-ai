'use client'

import Link from 'next/link'

export function NewListingFlow() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-[var(--color-text-1,#3D3D39)]">Add a listing</h1>
      <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
        Choose how you want to bring this listing into Dalya.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <FlowCard
          href="/listings/new/portal"
          title="Paste from Property Finder / Bayut"
          body="Paste a listing URL and Dalya prefills property details, pricing, amenities, photos, agent, brokerage, and permit fields where available."
        />
        <FlowCard
          href="/listings/new/manual"
          title="Upload manually"
          body="Start from an SPA for off-plan inventory or fill a finished-property listing form yourself."
        />
      </div>
    </div>
  )
}

export function ManualListingChoice() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-[var(--color-text-1,#3D3D39)]">Upload manually</h1>
      <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
        Choose the listing type you want to create manually.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <FlowCard
          href="/listings/new/manual/off-plan"
          title="Off-plan"
          body="Upload the SPA. Dalya parses the contract and prefills payment plan, NOC status, handover, and developer details."
        />
        <FlowCard
          href="/listings/new/manual/finished"
          title="Finished property"
          body="Fill the listing form manually, including location, size, bedrooms, bathrooms, pricing, amenities, photos, and permit details."
        />
      </div>
    </div>
  )
}

function FlowCard({ href, title, body }: { href: string; title: string; body: string }) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-[var(--color-surface-2,#E8E8E5)] bg-[var(--color-surface-1,#F4F4F2)] p-5 text-left transition hover:border-[var(--color-brand-500,#3D5A80)] hover:bg-white"
    >
      <div className="text-sm font-medium text-[var(--color-text-1,#3D3D39)]">{title}</div>
      <p className="mt-1 text-xs text-[var(--color-text-3,#7B7B76)]">{body}</p>
    </Link>
  )
}
