import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/api'

export interface ProcessingStage {
  key: string
  label: string
  description: string
  status: 'pending' | 'in_progress' | 'complete' | 'blocked'
  at: string | null
  note: string | null
}

export interface ListingDetail {
  id: string
  property_name: string
  unit_number: string
  developer: string
  sub_community?: string | null
  property_type?: string | null
  property_status?: string | null
  bedrooms?: number | null
  bathrooms?: number | null
  bua_sqft?: number | null
  plot_sqft?: number | null
  total_price?: number | null
  asking_price?: number | null
  negotiation_threshold?: number | null
  seller_notes?: string | null
  unit_profile?: Record<string, string[] | string | null>
  unit_profile_history?: Array<Record<string, unknown>>
  noc_eligible?: boolean
  total_paid_percent?: number
  handover_date?: string | null
  payment_schedule?: Array<Record<string, unknown>>
  status: string
  lead_count: number
  escalated_count: number
  leads: Array<{ last_message_at?: string; last_active?: string; [k: string]: unknown }>
  processing_stages?: ProcessingStage[]
}

export interface BuyerListingMatch {
  match_id: string
  buyer_id: string
  buyer_profile_id: string
  match_score: number
  aligned_preferences: string[]
  traced_inquiry_listing_ids: string[]
  outreach_draft: string
  status: 'draft' | 'copied' | 'dismissed' | 'sent_external'
  created_at: string | null
}

export interface BuyerListingMatchesResponse {
  listing_id: string
  matches: BuyerListingMatch[]
}

export interface SellerListingsResponse {
  listings: Array<{
    id: string
    property_name: string
    unit_number: string
    asking_price: number | null
    status: string
    lead_count: number
    escalated_count: number
    last_activity: string | null
  }>
  total_conversations: number
  total_escalated: number
}

export type AgentListingPropertyType = 'ready' | 'off_plan' | null
export type AgentListingStatus = 'live' | 'draft'
export type AgentListingReadinessStatus = 'ready' | 'needs_attention' | 'empty'
export type AgentListingLogisticsStatus = 'ready' | 'needs_attention' | 'not_required'
export type AgentListingPrimaryNextAction =
  | 'review_knowledge'
  | 'set_logistics'
  | 'manage_viewings'
  | 'review_offers'
  | 'review_documents'
  | 'upload_documents'
  | 'follow_up_buyers'
  | 'open_listing'

export interface AgentListingSummary {
  readonly id: string
  readonly title: string
  readonly property_type: AgentListingPropertyType
  readonly community: string | null
  readonly subcommunity: string | null
  readonly building_or_project: string | null
  readonly unit_number: string | null
  readonly bedrooms: number | null
  readonly bathrooms: number | null
  readonly size_sqft: number | null
  readonly asking_price_aed: number | null
  readonly price_per_sqft_aed: number | null
  readonly status: AgentListingStatus
  readonly lead_count: number
  readonly escalated_count: number
  readonly source_url: string | null
  readonly first_image_url: string | null
  readonly reference_document_count: number
  readonly created_at: string | null
  readonly last_activity_at: string | null
  readonly assigned_agent_name: string | null
  readonly knowledge_status: AgentListingReadinessStatus
  readonly missing_fact_count: number
  readonly active_viewing_count: number
  readonly open_offer_count: number
  readonly buyer_conversation_count: number
  readonly logistics_status: AgentListingLogisticsStatus
  readonly primary_next_action: AgentListingPrimaryNextAction
}

export interface AgentListingsResponse {
  readonly listings: readonly AgentListingSummary[]
  readonly total_listings: number
  readonly total_conversations: number
  readonly total_escalated: number
}

export interface ListingLogisticsPayload {
  logistics_id?: string
  listing_id: string
  building_id?: string | null
  agent_user_id?: string | null
  access: Record<string, unknown>
  keys: Record<string, unknown>
  tenant: Record<string, unknown>
  owner_permissions: Record<string, unknown>
  confirmed_at?: string | null
  updated_at?: string | null
}

export interface ListingLogisticsResponse {
  listing_id: string
  logistics: ListingLogisticsPayload | null
  prefill: {
    building_id: string
    building_key: string
    display_name: string
    community_key: string | null
    contributor_count: number
    confidence: number
    draft: {
      access: Record<string, unknown>
      keys: Record<string, unknown>
      tenant: Record<string, unknown>
      owner_permissions: Record<string, unknown>
    }
    source: string
  }
}

export interface AgentViewing {
  viewing_id: string
  conversation_id: string
  listing_id: string
  buyer_phone: string
  buyer_name?: string | null
  scheduled_for?: string | null
  status: string
  tenant_notice_required: boolean
  listing: {
    project?: string | null
    unit_number?: string | null
    property_type?: string | null
  }
  confirmation_status: Record<string, string>
  notification_drafts: ViewingNotificationDraft[]
  post_viewing?: PostViewingCapture | null
  proposed_slots: Array<Record<string, unknown>>
  logistics_summary: Record<string, unknown>
}

export interface ViewingNotificationDraft {
  draft_id: string
  type: string
  channel: string
  status: string
  recipient_type: string
  recipient?: string | null
  body: string
  created_at?: string | null
  sent_at?: string | null
  transport_message_id?: string | null
}

export interface TenantViewingConfirmation {
  confirmation_id: string
  viewing_id: string
  listing_id: string
  status: string
  tenant_contact_key: string
  tenant_phone?: string | null
  notice_body?: string | null
  outbound_message_id?: string | null
  last_inbound_body?: string | null
  metadata_json?: Record<string, unknown>
  sent_at?: string | null
  responded_at?: string | null
}

export interface ViewingFeedback {
  feedback_id: string
  participant_type: string
  status: string
  score?: number | null
  sentiment?: string | null
  temperature?: string | null
  financing_status?: string | null
  next_action?: string | null
  summary?: string | null
  structured?: Record<string, unknown>
  source?: string | null
  requested_at?: string | null
  responded_at?: string | null
  metadata?: Record<string, unknown>
}

export interface PostViewingCapture {
  status: string
  due_at?: string | null
  requested_at?: string | null
  buyer?: ViewingFeedback | null
  agent?: ViewingFeedback | null
  metadata?: Record<string, unknown>
}

export interface AgentViewingDetail extends AgentViewing {
  buyer: {
    name?: string | null
    phone: string
    budget_aed?: number | null
    summary?: Record<string, unknown>
  }
  logistics: ListingLogisticsPayload | null
  tenant_confirmation?: TenantViewingConfirmation | null
}

export interface ViewingBrief {
  viewing_id: string
  scheduled_for?: string | null
  buyer_profile: {
    name?: string | null
    phone: string
    budget_aed?: number | null
    summary?: string | null
    stated_priorities?: string[]
  }
  property: Record<string, unknown>
  property_highlights: string[]
  likely_objections: Array<{ objection: string; response: string }>
  comparable_units_already_viewed: string[]
  logistics: Record<string, unknown>
  confirmation_status: Record<string, string>
}

/**
 * Fetch details for a single listing. Shared across all tabs on the listing detail page —
 * first tab fetches, subsequent tabs read from cache instantly.
 */
export function useListingDetail(id: string, enabled: boolean = true) {
  return useQuery<ListingDetail>({
    queryKey: ['listing', id],
    enabled: enabled && !!id,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/seller/listings/${id}/leads`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load listing (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useBuyerListingMatches(listingId: string, enabled: boolean = true) {
  return useQuery<BuyerListingMatchesResponse>({
    queryKey: ['buyer-listing-matches', listingId],
    enabled: enabled && !!listingId,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/agent/listings/${listingId}/buyer-matches`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load buyer matches (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useAgentListings(enabled: boolean = true) {
  return useQuery<AgentListingsResponse>({
    queryKey: ['agent-listings'],
    enabled,
    queryFn: async () => {
      const res = await apiFetch('/api/v1/listings/mine')
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load listings (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useListingLogistics(listingId: string, enabled: boolean = true) {
  return useQuery<ListingLogisticsResponse>({
    queryKey: ['listing-logistics', listingId],
    enabled: enabled && !!listingId,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/agent/listings/${listingId}/logistics`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load logistics (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useAgentViewings(enabled: boolean = true) {
  return useQuery<{ viewings: AgentViewing[] }>({
    queryKey: ['agent-viewings'],
    enabled,
    queryFn: async () => {
      const res = await apiFetch('/api/v1/agent/viewings')
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load viewings (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useAgentViewingDetail(viewingId: string, enabled: boolean = true) {
  return useQuery<AgentViewingDetail>({
    queryKey: ['agent-viewing', viewingId],
    enabled: enabled && !!viewingId,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load viewing (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useViewingBrief(viewingId: string, enabled: boolean = true) {
  return useQuery<ViewingBrief>({
    queryKey: ['agent-viewing-brief', viewingId],
    enabled: enabled && !!viewingId,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/agent/viewings/${viewingId}/brief`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load brief (${res.status})`)
      }
      return res.json()
    },
  })
}

/**
 * Fetch all listings for the authenticated seller. Shared across dashboard pages.
 */
export function useSellerListings(enabled: boolean = true) {
  return useQuery<SellerListingsResponse>({
    queryKey: ['seller-listings'],
    enabled,
    queryFn: async () => {
      const res = await apiFetch('/api/v1/seller/listings')
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load listings (${res.status})`)
      }
      return res.json()
    },
  })
}

/* ------------------------------------------------------------------ */
/*  Seller — Conversations, Offers, Activity                           */
/* ------------------------------------------------------------------ */

export interface StructuredSummary {
  topics?: string[]
  interest_level?: string | null
  sentiment?: string | null
  key_question?: string | null
  next_step_hint?: string | null
  buyer_context?: string | null
  _fallback?: string
}

export interface ConversationSummary {
  buyer_label: string
  message_count: number
  buyer_messages: number
  summary: StructuredSummary | string
  offer_made: boolean
  last_active: string
  language: string
  started_at: string
}

export interface ConversationsResponse {
  listing_id: string
  conversations: ConversationSummary[]
}

export interface OfferItem {
  buyer_label: string
  amount_aed: number
  vs_asking: string
  status: 'pending' | 'accepted' | 'rejected'
  received_at: string | null
}

export interface OffersResponse {
  listing_id: string
  asking_price: number
  threshold: number | null
  offers: OfferItem[]
}

export interface ActivityEvent {
  type: 'inquiry' | 'offer' | 'escalation' | 'milestone'
  listing_name: string
  listing_id: string
  description: string
  timestamp: string
}

export interface ActivityResponse {
  events: ActivityEvent[]
}

export function useSellerConversations(listingId: string, enabled: boolean = true) {
  return useQuery<ConversationsResponse>({
    queryKey: ['seller-conversations', listingId],
    enabled: enabled && !!listingId,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/seller/listings/${listingId}/conversations`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load conversations (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useSellerOffers(listingId: string, enabled: boolean = true) {
  return useQuery<OffersResponse>({
    queryKey: ['seller-offers', listingId],
    enabled: enabled && !!listingId,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/seller/listings/${listingId}/offers`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load offers (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useSellerActivity(enabled: boolean = true) {
  return useQuery<ActivityResponse>({
    queryKey: ['seller-activity'],
    enabled,
    queryFn: async () => {
      const res = await apiFetch('/api/v1/seller/activity')
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load activity (${res.status})`)
      }
      return res.json()
    },
  })
}

/* ------------------------------------------------------------------ */
/*  CRM — Admin buyer management                                      */
/* ------------------------------------------------------------------ */

export interface BuyerSummary {
  phone: string
  name: string | null
  lead_stage: string
  lead_source: string | null
  budget_aed: number | null
  bedroom_preferences: string | null
  area_preferences: string[] | null
  purpose: string | null
  tags: string[]
  listings_inquired: number
  total_messages: number
  last_active: string | null
  created_at: string | null
}

export interface BuyerStats {
  total_buyers: number
  new_this_week: number
  engaged: number
  qualified: number
  offers_made: number
  in_negotiation: number
}

export interface BuyerConversation {
  conversation_id: string
  listing_name: string
  message_count: number
  escalated: boolean
  last_message_preview: string | null
  last_message_at: string | null
}

export interface BuyerDetail {
  phone: string
  name: string | null
  lead_stage: string
  lead_source: string | null
  budget_aed: number | null
  bedroom_preferences: string | null
  area_preferences: string[] | null
  purpose: string | null
  tags: string[]
  admin_notes: Array<{ note: string; at: string }>
  conversations: BuyerConversation[]
  created_at: string | null
  last_active: string | null
}

export interface TranscriptMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  intent: string | null
  escalated: boolean
}

export interface TranscriptData {
  conversation_id: string
  listing_name: string
  buyer_name: string | null
  buyer_phone: string
  messages: TranscriptMessage[]
}

export function useAdminBuyers(enabled: boolean = true) {
  return useQuery<{ buyers: BuyerSummary[] }>({
    queryKey: ['admin-buyers'],
    enabled,
    queryFn: async () => {
      const res = await apiFetch('/api/v1/admin/buyers')
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load buyers (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useAdminBuyerStats(enabled: boolean = true) {
  return useQuery<BuyerStats>({
    queryKey: ['admin-buyer-stats'],
    enabled,
    queryFn: async () => {
      const res = await apiFetch('/api/v1/admin/buyers/stats')
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load stats (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useAdminBuyerDetail(phone: string, enabled: boolean = true) {
  return useQuery<BuyerDetail>({
    queryKey: ['admin-buyer', phone],
    enabled: enabled && !!phone,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/admin/buyers/${encodeURIComponent(phone)}`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load buyer (${res.status})`)
      }
      return res.json()
    },
  })
}

export function useAdminConversationMessages(
  phone: string,
  conversationId: string,
  enabled: boolean = true,
) {
  return useQuery<TranscriptData>({
    queryKey: ['admin-messages', phone, conversationId],
    enabled: enabled && !!phone && !!conversationId,
    queryFn: async () => {
      const res = await apiFetch(
        `/api/v1/admin/buyers/${encodeURIComponent(phone)}/messages/${conversationId}`,
      )
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `Failed to load messages (${res.status})`)
      }
      return res.json()
    },
  })
}

export function usePatchBuyer(phone: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const res = await apiFetch(`/api/v1/admin/buyers/${encodeURIComponent(phone)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Update failed (${res.status})`)
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-buyer', phone] })
      queryClient.invalidateQueries({ queryKey: ['admin-buyers'] })
    },
  })
}

export function useAddBuyerNote(phone: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (note: string) => {
      const res = await apiFetch(`/api/v1/admin/buyers/${encodeURIComponent(phone)}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Failed to add note (${res.status})`)
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-buyer', phone] })
    },
  })
}

// ── Community research view + agent per-field overrides ───────────────────

export interface CommunityOverride {
  readonly override_id: string
  readonly field_key: string
  readonly value_text: string
  readonly note: string | null
  readonly buyer_safe: boolean
  readonly updated_at: string | null
}

export interface CommunityField {
  readonly key: string
  readonly label: string
  readonly group: string
  readonly researched_value: string | null
  readonly override: CommunityOverride | null
}

export interface ListingCommunityResponse {
  readonly project_name: string | null
  readonly project_key: string | null
  readonly research_status: 'approved' | 'in_review' | 'in_progress' | 'none'
  readonly research_confidence: number | null
  readonly source_count: number
  readonly fields: readonly CommunityField[]
}

export function useListingCommunity(id: string, enabled: boolean = true) {
  return useQuery<ListingCommunityResponse>({
    queryKey: ['listing-community', id],
    enabled,
    queryFn: async () => {
      const res = await apiFetch(`/api/v1/listings/${id}/community`)
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Failed to load community data (${res.status})`)
      }
      return res.json()
    },
  })
}

export interface CommunityOverrideInput {
  readonly fieldKey: string
  readonly value_text: string
  readonly note?: string | null
  readonly buyer_safe: boolean
}

export function useUpsertCommunityOverride(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ fieldKey, value_text, note, buyer_safe }: CommunityOverrideInput) => {
      const res = await apiFetch(`/api/v1/listings/${id}/community/overrides/${fieldKey}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value_text, note: note ?? null, buyer_safe }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Save failed (${res.status})`)
      }
      return res.json() as Promise<ListingCommunityResponse>
    },
    onSuccess: (data) => queryClient.setQueryData(['listing-community', id], data),
  })
}

export function useDeleteCommunityOverride(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (fieldKey: string) => {
      const res = await apiFetch(`/api/v1/listings/${id}/community/overrides/${fieldKey}`, { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json().catch(() => null)
        throw new Error(err?.detail ?? `Remove failed (${res.status})`)
      }
      return res.json() as Promise<ListingCommunityResponse>
    },
    onSuccess: (data) => queryClient.setQueryData(['listing-community', id], data),
  })
}
