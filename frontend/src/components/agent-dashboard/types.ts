export type QueuePriority = 'critical' | 'high' | 'normal'
export type CampaignStatus = 'live' | 'warming' | 'needs_action'
export type BuyerIntent = 'offer_ready' | 'viewing_ready' | 'financing' | 'researching'
export type ViewingStatus = 'confirmed' | 'pending' | 'follow_up'
export type MomentumTrend = 'up' | 'flat' | 'down'
export type EscalationUrgency = 'critical' | 'high' | 'normal'
export type EscalationState = 'debouncing' | 'open' | 'updated' | 'resolved' | 'timed_out' | 'opt_out_closed'

export interface AgentDashboardData {
  agent: {
    name: string
    brokerage: string
    market: string
    lastUpdated: string
  }
  hotListRefresh?: {
    status: string
    trigger?: string | null
    lastRefreshAt?: string | null
    completedAt?: string | null
    assignmentCount: number
    taskCount: number
    draftCount: number
    error?: string | null
  }
  emptyState?: {
    reason: string
    message: string
  }
  summary: {
    openTasks: number
    qualifiedBuyers: number
    viewingsToday: number
    offersAtRisk: number
    openEscalations: number
  }
  performance: AgentPerformance
  conversationInbox: ConversationInboxItem[]
  morningQueue: QueueItem[]
  escalationInbox: EscalationThreadItem[]
  drafts: AgentDrafts
  campaignSnapshot: CampaignSnapshot
  overnightBuyerDigest: BuyerDigestItem[]
  todaysViewings: ViewingItem[]
  personalMomentum: PersonalMomentum
}

export interface AgentDrafts {
  replyDrafts: ReplyDraftItem[]
  outreachDrafts: OutreachDraftItem[]
}

export interface ReplyDraftItem {
  id: string
  conversationId?: string | null
  buyerName: string
  buyerPhone?: string | null
  listingName: string
  unitNumber?: string | null
  category: string
  intent?: string | null
  body: string
}

export interface OutreachDraftItem {
  id: string
  subject: string
  audience: string
  body: string
}

export interface AgentPerformanceWindow {
  key: 'today' | '7d' | '30d' | string
  label: string
  startAt?: string | null
  endAt?: string | null
  metrics: {
    newBuyerConversations: number
    escalationsHandled: number
    avgResponseMinutes?: number | null
    followUpsSent: number
    viewingsProposed: number
    viewingsConfirmed: number
    viewingsCompleted: number
    offersDetected: number
    hotLeadsActive: number
    tasksOverdue: number
  }
}

export interface AgentPerformance {
  scope: string
  agentUserId?: string | null
  generatedAt?: string | null
  primary: AgentPerformanceWindow
  windows: AgentPerformanceWindow[]
}

export interface ConversationInboxItem {
  id: string
  buyerName: string
  buyerPhone: string
  listingName: string
  unitNumber?: string | null
  summary: string
  nextStep: string
  lastMessage: string
  lastSeen: string
  messageCount: number
  offerCount: number
  openEscalationCount: number
  interestLevel?: string | null
  needsReply: boolean
  needsReplyReason?: string | null
  hasPendingDraft?: boolean
  lastBuyerMessageAt?: string | null
  lastAgentResponseAt?: string | null
}

export interface EscalationThreadQuestion {
  id: string
  text: string
  addedAt: string
  resolvedAt?: string | null
}

export interface EscalationThreadItem {
  id: string
  token?: string | null
  conversationId?: string | null
  aiMode?: string
  category: string
  state: EscalationState
  urgency: EscalationUrgency
  buyerName: string
  buyerPhone: string
  listingName: string
  unitNumber?: string | null
  latestQuestion: string
  questionCount: number
  lastBuyerMessageAt: string
  openedAt: string
  routeExpiresAt?: string | null
  questions: EscalationThreadQuestion[]
}

export interface QueueItem {
  id: string
  priority: QueuePriority
  title: string
  context: string
  buyerName: string
  listingName: string
  nextAction: string
  due: string
}

export interface CampaignSnapshot {
  headline: string
  activeCampaigns: number
  newLeads: number
  qualifiedLeads: number
  responseRate: string
  costPerQualifiedLead: string
  campaigns: CampaignItem[]
}

export interface CampaignItem {
  id: string
  name: string
  audience: string
  status: CampaignStatus
  spend: string
  leads: number
  qualified: number
  insight: string
}

export interface BuyerDigestItem {
  id: string
  buyerName: string
  intent: BuyerIntent
  message: string
  budget: string
  target: string
  recommendedAction: string
  lastSeen: string
}

export interface ViewingItem {
  id: string
  time: string
  buyerName: string
  property: string
  location: string
  status: ViewingStatus
  preparation: string
}

export interface PersonalMomentum {
  weekLabel: string
  stats: MomentumStat[]
  focus: string
  streaks: MomentumStreak[]
}

export interface MomentumStat {
  label: string
  value: string
  helper: string
  trend: MomentumTrend
}

export interface MomentumStreak {
  label: string
  value: string
  tone: 'brand' | 'success' | 'warning'
}
