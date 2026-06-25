import { redirect } from 'next/navigation'

type LegacyListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function LegacyListingSpaPage({ params }: LegacyListingRouteProps) {
  const { id } = await params

  redirect(`/listings/${id}/documents`)
}
