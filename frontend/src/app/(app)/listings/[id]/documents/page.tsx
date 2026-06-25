import { ListingDocumentsWorkspace } from '@/components/listings/ListingDocumentsWorkspace'

type ListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function ListingDocumentsPage({ params }: ListingRouteProps) {
  const { id } = await params

  return <ListingDocumentsWorkspace id={id} />
}
