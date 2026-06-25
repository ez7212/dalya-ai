import { ListingOverviewWorkspace } from '@/components/listings/ListingOverviewWorkspace'

type ListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function ListingOverviewPage({ params }: ListingRouteProps) {
  const { id } = await params

  return <ListingOverviewWorkspace id={id} />
}
