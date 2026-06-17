import { ModulePlaceholder } from '@/components/agent-modules/ModulePlaceholder'

export default function InboxPage() {
  return (
    <ModulePlaceholder
      eyebrow="Buyer conversations"
      title="Inbox"
      description="The inbox will collect buyer messages, AI reply drafts, low-confidence replies, and conversations that need agent takeover."
      primaryHref="/agent"
      primaryLabel="Back to dashboard"
      items={[
        {
          icon: 'mark_chat_unread',
          title: 'Priority threads',
          body: 'Surface hot buyers, viewing requests, offer-like messages, and buyers who went quiet after a strong signal.',
        },
        {
          icon: 'rate_review',
          title: 'Draft review',
          body: 'Keep agents in control with editable replies, approval states, and manual send or copy actions.',
        },
        {
          icon: 'person_pin',
          title: 'Agent handoff',
          body: 'Route each Property Advisor handoff to the assigned agent for that brokerage and profile.',
        },
      ]}
    />
  )
}
