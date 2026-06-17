import { PublicMarketingPage } from '@/components/marketing-pages/MarketingPagesWorkspace'

export default async function PublicCampaignPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params

  return <PublicMarketingPage slug={slug} />
}
