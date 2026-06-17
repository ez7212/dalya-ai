import { MarketingPagePreview } from '@/components/marketing-pages/MarketingPagesWorkspace'

export default async function MarketingPagePreviewRoute({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  return <MarketingPagePreview id={id} />
}
