import { ListingKnowledgeWorkspace } from '@/components/listings/ListingKnowledgeWorkspace'

type ListingRouteProps = {
  readonly params: Promise<{
    readonly id: string
  }>
}

export default async function ListingKnowledgePage({ params }: ListingRouteProps) {
  const { id } = await params

  return <ListingKnowledgeWorkspace id={id} />
}
