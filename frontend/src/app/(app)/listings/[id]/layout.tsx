import type { ReactNode } from 'react'
import { ListingWorkspaceShell } from '@/components/listings/ListingWorkspaceShell'

type ListingWorkspaceLayoutProps = {
  readonly children: ReactNode
  readonly params: Promise<unknown>
}

export default async function ListingWorkspaceLayout({ children, params }: ListingWorkspaceLayoutProps) {
  const id = listingIdFromParams(await params)

  return <ListingWorkspaceShell id={id}>{children}</ListingWorkspaceShell>
}

function listingIdFromParams(params: unknown): string {
  if (typeof params !== 'object' || params === null || !('id' in params)) {
    return ''
  }

  return typeof params.id === 'string' ? params.id : ''
}
