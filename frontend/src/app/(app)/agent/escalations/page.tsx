import { EscalationInbox } from '@/components/escalations/EscalationInbox'

interface AgentEscalationsPageProps {
  readonly searchParams?: Promise<{
    readonly thread?: string | readonly string[]
  }>
}

export default async function AgentEscalationsPage({ searchParams }: AgentEscalationsPageProps) {
  const params = searchParams ? await searchParams : {}
  const threadValue = params.thread
  const selectedThreadId = Array.isArray(threadValue) ? threadValue[0] ?? null : threadValue ?? null

  return <EscalationInbox selectedThreadId={selectedThreadId} />
}
