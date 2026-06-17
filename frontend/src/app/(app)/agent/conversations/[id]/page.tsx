import { ConversationDetail } from '@/components/conversations/ConversationDetail'

export default async function AgentConversationPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <ConversationDetail conversationId={id} />
}
