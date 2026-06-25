import type { AgentListingSummary } from '@/lib/queries'

export function propertyTypeLabel(propertyType: AgentListingSummary['property_type']): string {
  switch (propertyType) {
    case 'ready':
      return 'Ready property'
    case 'off_plan':
      return 'Off-plan'
    case null:
      return 'Listing'
  }
}

export function listingStatusLabel(status: AgentListingSummary['status']): string {
  switch (status) {
    case 'live':
      return 'Live'
    case 'draft':
      return 'Draft'
  }
}

export function readinessStatusLabel(status: AgentListingSummary['knowledge_status'] | AgentListingSummary['logistics_status']): string {
  switch (status) {
    case 'ready':
      return 'ready'
    case 'needs_attention':
      return 'needs attention'
    case 'empty':
      return 'empty'
    case 'not_required':
      return 'not required'
  }
}
