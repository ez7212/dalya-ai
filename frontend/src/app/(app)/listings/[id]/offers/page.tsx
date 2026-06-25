import { ListingOffersWorkspace } from '@/components/listings/ListingOffersWorkspace'

type ListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function ListingOffersPage({ params }: ListingRouteProps) {
  const { id } = await params

  return <ListingOffersWorkspace id={id} />
}
