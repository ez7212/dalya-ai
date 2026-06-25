import { ListingCommunityWorkspace } from '@/components/listings/ListingCommunityWorkspace'

type ListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function ListingCommunityPage({ params }: ListingRouteProps) {
  const { id } = await params

  return <ListingCommunityWorkspace id={id} />
}
