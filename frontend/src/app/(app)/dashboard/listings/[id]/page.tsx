import { redirect } from 'next/navigation'

type LegacyListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function LegacyListingOverviewPage({ params }: LegacyListingRouteProps) {
  const { id } = await params

  redirect(`/listings/${id}`)
}
