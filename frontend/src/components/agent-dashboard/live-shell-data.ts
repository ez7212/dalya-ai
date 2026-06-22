import type { AgentDashboardData } from './types'

export const liveAgentDashboardShellData: AgentDashboardData = {
  agent: {
    name: 'Agent',
    brokerage: 'Your brokerage',
    market: 'Dubai agent desk',
    lastUpdated: 'just now',
  },
  summary: {
    openTasks: 0,
    qualifiedBuyers: 0,
    viewingsToday: 0,
    offersAtRisk: 0,
    openEscalations: 0,
  },
  performance: {
    scope: 'agent',
    agentUserId: null,
    generatedAt: null,
    primary: {
      key: 'today',
      label: 'Today',
      metrics: {
        newBuyerConversations: 0,
        escalationsHandled: 0,
        avgResponseMinutes: null,
        followUpsSent: 0,
        viewingsProposed: 0,
        viewingsConfirmed: 0,
        viewingsCompleted: 0,
        offersDetected: 0,
        hotLeadsActive: 0,
        tasksOverdue: 0,
      },
    },
    windows: [],
  },
  conversationInbox: [],
  morningQueue: [],
  escalationInbox: [],
  drafts: {
    replyDrafts: [],
    outreachDrafts: [],
  },
  campaignSnapshot: {
    headline: 'No owner outreach campaigns are active yet.',
    activeCampaigns: 0,
    newLeads: 0,
    qualifiedLeads: 0,
    responseRate: '0%',
    costPerQualifiedLead: 'AED 0',
    campaigns: [],
  },
  overnightBuyerDigest: [],
  todaysViewings: [],
  personalMomentum: {
    weekLabel: 'This week',
    focus: 'Live workspace activity will appear here after the dashboard loads.',
    stats: [],
    streaks: [],
  },
}
