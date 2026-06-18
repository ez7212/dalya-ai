import type { Metadata } from 'next'
import { ContactClient } from '@/components/marketing/ContactClient'

export const metadata: Metadata = {
  title: 'Book a Demo — Dalya',
  description:
    'Book a demo of Dalya on your own Dubai brokerage listings — see the agent hot list, smart escalation, and follow-up drafts in action.',
}

export default function ContactPage() {
  return <ContactClient />
}
