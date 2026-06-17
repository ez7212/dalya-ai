import { AgentDashboard } from '@/components/agent-dashboard/AgentDashboard'
import { fallbackAgentDashboardData } from '@/components/agent-dashboard/fallback-data'

export default function AgentPage() {
  return <AgentDashboard data={fallbackAgentDashboardData} />
}
