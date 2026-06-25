import { redirect } from 'next/navigation'

type LegacyListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function LegacyListingKnowledgePage({ params }: LegacyListingRouteProps) {
  const { id } = await params

  redirect(`/listings/${id}/knowledge`)
}
