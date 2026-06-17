import { Suspense } from 'react'
import { SellerUpload } from '@/components/sections/SellerUpload'

export default function ManualOffPlanListingPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-[var(--color-text-1,#3D3D39)]">Off-plan listing</h1>
      <p className="mt-1 text-sm text-[var(--color-text-2,#5C5C57)]">
        Upload the SPA and review the parsed listing details before publishing.
      </p>
      <div className="mt-8">
        <Suspense fallback={null}>
          <SellerUpload />
        </Suspense>
      </div>
    </div>
  )
}
