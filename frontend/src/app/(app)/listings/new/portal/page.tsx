import { FinishedListingFlow } from '@/components/listings/FinishedListingFlow'

export default function PortalListingPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-[var(--color-text-1,#3D3D39)]">
        Add a listing
      </h1>
      <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
        Choose finished or off-plan, then start from a portal link or the manual flow.
      </p>
      <div className="mt-8">
        <FinishedListingFlow />
      </div>
    </div>
  )
}
