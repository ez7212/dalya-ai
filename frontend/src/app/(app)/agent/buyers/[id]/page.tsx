import { BuyerCard } from '@/components/buyers/BuyerCard'

export default async function BuyerCardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <BuyerCard profileId={id} />
}
