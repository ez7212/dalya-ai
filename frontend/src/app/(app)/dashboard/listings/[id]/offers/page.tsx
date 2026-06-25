import { redirect } from 'next/navigation'

type LegacyListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function LegacyListingOffersPage({ params }: LegacyListingRouteProps) {
  const { id } = await params

  redirect(`/listings/${id}/offers`)
}
