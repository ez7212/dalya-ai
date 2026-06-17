import type { Metadata } from 'next'
import { ContactClient } from '@/components/marketing/ContactClient'

export const metadata: Metadata = {
  title: 'Apply for Design Partnership — Dalya',
  description:
    'Apply to run a 60-day Dalya design partnership for your Dubai real estate brokerage. Pricing waits until the agent day is sharper.',
}

export default function ContactPage() {
  return <ContactClient />
}
