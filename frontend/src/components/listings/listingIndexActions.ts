import type { AgentListingPrimaryNextAction, AgentListingSummary } from '@/lib/queries'

export const SUPPORTED_INDEX_ACTIONS: readonly AgentListingPrimaryNextAction[] = [
  'review_knowledge',
  'set_logistics',
  'manage_viewings',
  'review_offers',
  'review_documents',
  'upload_documents',
  'follow_up_buyers',
  'open_listing',
]

export interface ListingNextAction {
  readonly href: string
  readonly label: string
  readonly icon: string
}

type ListingActionInput = Pick<AgentListingSummary, 'id' | 'primary_next_action'>

export function nextActionForListing(listing: ListingActionInput): ListingNextAction {
  switch (listing.primary_next_action) {
    case 'review_knowledge':
      return { href: `/listings/${listing.id}/knowledge`, label: 'Review knowledge', icon: 'fact_check' }
    case 'set_logistics':
      return { href: `/listings/${listing.id}/logistics`, label: 'Set logistics', icon: 'event_available' }
    case 'manage_viewings':
      return { href: `/listings/${listing.id}/logistics`, label: 'Manage viewings', icon: 'event_available' }
    case 'review_offers':
      return { href: `/listings/${listing.id}/offers`, label: 'View offers', icon: 'handshake' }
    case 'review_documents':
      return { href: `/listings/${listing.id}/documents`, label: 'Review documents', icon: 'description' }
    case 'upload_documents':
      return { href: `/listings/${listing.id}/documents`, label: 'Upload documents', icon: 'upload_file' }
    case 'follow_up_buyers':
      return { href: `/listings/${listing.id}`, label: 'Follow up buyers', icon: 'forum' }
    case 'open_listing':
      return { href: `/listings/${listing.id}`, label: 'Open listing', icon: 'open_in_new' }
    default:
      return assertNever(listing.primary_next_action)
  }
}

function assertNever(value: never): never {
  throw new Error(`Unsupported listing index action: ${value}`)
}
