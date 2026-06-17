import { FinishedListingFlow } from '@/components/listings/FinishedListingFlow'

export default function ManualFinishedListingPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-[var(--color-text-1,#3D3D39)]">Finished property</h1>
      <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
        Fill the listing details manually, then publish when the property record is complete.
      </p>
      <div className="mt-8">
        <FinishedListingFlow startManual />
      </div>
    </div>
  )
}
