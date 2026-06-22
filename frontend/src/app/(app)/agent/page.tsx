import { AgentDashboard } from '@/components/agent-dashboard/AgentDashboard'
import { liveAgentDashboardShellData } from '@/components/agent-dashboard/live-shell-data'

export default function AgentPage() {
  return <AgentDashboard data={liveAgentDashboardShellData} />
}
