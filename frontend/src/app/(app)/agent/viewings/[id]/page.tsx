'use client'

import { use } from 'react'
import { ViewingDetail } from '@/components/viewings/ViewingDetail'

export default function AgentViewingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  return <ViewingDetail viewingId={id} />
}
