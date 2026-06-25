import { ListingLogisticsWorkspace } from '@/components/listings/ListingLogisticsWorkspace'

type ListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function ListingLogisticsPage({ params }: ListingRouteProps) {
  const { id } = await params

  return <ListingLogisticsWorkspace id={id} />
}
