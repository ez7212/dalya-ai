'use client'

import { ListingLogisticsForm } from '@/components/viewings/ListingLogisticsForm'

type ListingLogisticsWorkspaceProps = {
  readonly id: string
}

export function ListingLogisticsWorkspace({ id }: ListingLogisticsWorkspaceProps) {
  return (
    <div className="space-y-5" data-listing-workspace-route="logistics" data-listing-id={id}>
      <section className="rounded-lg border border-neutral-200 bg-white p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Viewing logistics</p>
            <h2 className="mt-1 text-lg font-semibold text-neutral-900">Access, keys, tenant notice, and owner permissions</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-neutral-600">
              Set the operational details agents need before proposing slots or confirming a viewing.
            </p>
          </div>
          <span className="w-fit rounded-sm bg-brand-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-700">
            Set logistics
          </span>
        </div>
      </section>

      <ListingLogisticsForm listingId={id} />
    </div>
  )
}
