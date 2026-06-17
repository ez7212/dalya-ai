'use client'

import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  ConversationView,
  DraftMessageCard,
  InspectionAudioInput,
  InspectionAudioReady,
  InterestedBuyersPanel,
  UnitProfileView,
} from '@/components/shared-ui'
import type { ConversationTurn, InterestedBuyerMatch } from '@/components/shared-ui'

const now = new Date('2026-05-28T10:15:00+04:00').toISOString()

const conversationTurns: ConversationTurn[] = [
  {
    id: 't1',
    role: 'buyer',
    content: 'Hi, is Marina Gate 2304 still available?',
    timestamp: now,
  },
  {
    id: 't2',
    role: 'property_advisor',
    content: 'Yes, Marina Gate 2304 is available. The asking price is AED 2,850,000.',
    timestamp: now,
  },
  {
    id: 't3',
    role: 'buyer',
    origin: 'voice',
    content: 'I was thinking maybe 2.2 or 2.3',
    correctedTranscript: 'I was thinking maybe 2.2 or 2.3.',
    timestamp: now,
    lowConfidenceSegments: [
      {
        source_phrase: '2.2 or 2.3',
        reason: 'Ambiguous spoken amount with background noise',
        candidates: ['AED 2,200,000', 'AED 2,300,000'],
      },
    ],
    priceExtractions: [
      {
        confidence: 'low',
        source_phrase: '2.2 or 2.3',
        candidate_amounts: [2_200_000, 2_300_000],
      },
    ],
  },
  {
    id: 't4',
    role: 'agent',
    content: 'I can verify the amount and come back with viewing slots.',
    timestamp: now,
  },
]

const matches: InterestedBuyerMatch[] = [
  {
    id: 'm1',
    buyerLabel: 'Ahmed · +971 **** 1842',
    matchScore: 93,
    matchReasons: ['Marina', '2BR', 'AED 2.5M to 3M'],
    tracedInquiries: ['Marina Gate 2304', 'JBR 2BR'],
    outreachDraft: 'Hi Ahmed, we just listed a Marina 2BR at AED 2.8M that fits the range you asked about earlier. Happy to send details or arrange a viewing.',
    status: 'draft',
  },
  {
    id: 'm2',
    buyerLabel: 'Buyer · +971 **** 5520',
    matchScore: 81,
    matchReasons: ['High floor', 'Marina', 'Investment'],
    tracedInquiries: ['Marina resale inquiry'],
    outreachDraft: 'Hi, I have a new Marina unit that may fit your high-floor investment search. I can send the numbers if you want to compare it.',
    status: 'draft',
  },
  {
    id: 'm3',
    buyerLabel: 'Sara · +971 **** 0091',
    matchScore: 74,
    matchReasons: ['2BR', 'Ready property'],
    tracedInquiries: ['Ready 2BR request'],
    outreachDraft: 'Hi Sara, a ready 2BR just came in that matches the type of unit you asked for. I can send the floor plan and viewing options.',
    status: 'draft',
  },
]

const profile = {
  layout: ['Master bedroom has west-facing windows.'],
  condition: ['Kitchen was upgraded in 2024 with quartz counters.'],
  view: ['Afternoon sun reaches the master bedroom.'],
  building_community_quirks: ['South-side elevator breaks down often.'],
  ac_utilities: ['AC is the older Daikin system.'],
  parking: ['Two assigned parking spots in basement level B2.'],
  neighbor_situation: ['Neighbor situation not captured yet.'],
  agent_subjective_notes: ['Best buyer fit is someone who values afternoon light.'],
}

const history = [
  {
    timestamp: '2026-05-28T09:10:00+04:00',
    provenance: 'Agent-recorded',
    transcript: 'Master bedroom has west-facing windows, AC is older Daikin, two parking spots in B2.',
  },
  {
    timestamp: '2026-05-28T09:22:00+04:00',
    provenance: 'Agent-recorded',
    transcript: 'Kitchen was upgraded in 2024 with quartz counters and the south elevator has issues.',
  },
]

export default function ComponentShowcasePage() {
  const [audioStatus, setAudioStatus] = useState('No audio captured yet.')
  const [copiedDraft, setCopiedDraft] = useState('')

  const handleAudio = (audio: InspectionAudioReady) => {
    setAudioStatus(`${audio.source} ready: ${audio.file.name} (${audio.contentType})`)
  }

  return (
    <main className="min-h-screen bg-surface-0 px-4 py-8 text-text-1 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <header>
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3">Internal fixture</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-800">Shared UI component showcase</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-2">
            Permanent fixture for inspection notes, transcript review, and outreach components. Check this page at desktop and around 380px width.
          </p>
        </header>

        <ShowcaseSection title="InspectionAudioInput" note={audioStatus}>
          <InspectionAudioInput onAudioReady={handleAudio} maxLengthSeconds={600} />
        </ShowcaseSection>

        <ShowcaseSection title="ConversationView">
          <ConversationView
            summary={{
              title: 'Marina buyer, amount needs verification',
              buyerGoal: 'Ready 2BR in Marina',
              budgetSignal: 'Possible AED 2.2M or AED 2.3M voice offer',
              objections: ['Amount unclear', 'Needs viewing slots'],
              status: 'Possible offer, not confirmed',
              nextStep: 'Ask buyer to confirm exact AED amount',
            }}
            turns={conversationTurns}
          />
        </ShowcaseSection>

        <ShowcaseSection title="DraftMessageCard" note={copiedDraft ? `Copied: ${copiedDraft.slice(0, 42)}...` : undefined}>
          <DraftMessageCard
            contextLine="For Ahmed, inquired about Marina 2BRs in March"
            draft="Hi Ahmed, we just listed a Marina 2BR at AED 2.8M that fits the range you asked about earlier. Happy to send details or arrange a viewing."
            onCopy={(draft) => setCopiedDraft(draft)}
          />
        </ShowcaseSection>

        <ShowcaseSection title="InterestedBuyersPanel">
          <InterestedBuyersPanel matches={matches} defaultLimit={2} onCopyDraft={(_, draft) => setCopiedDraft(draft)} />
          <div className="mt-4">
            <InterestedBuyersPanel matches={[]} />
          </div>
        </ShowcaseSection>

        <ShowcaseSection title="UnitProfileView">
          <UnitProfileView
            profile={profile}
            history={history}
            onAudioReady={handleAudio}
            onEditCategory={(category) => setAudioStatus(`Edit requested for ${category}`)}
          />
          <div className="mt-4">
            <UnitProfileView profile={{}} history={[]} onAudioReady={handleAudio} />
          </div>
        </ShowcaseSection>
      </div>
    </main>
  )
}

function ShowcaseSection({
  title,
  note,
  children,
}: {
  title: string
  note?: string
  children: ReactNode
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="text-lg font-semibold text-neutral-800">{title}</h2>
        {note && <p className="text-xs text-text-3">{note}</p>}
      </div>
      {children}
    </section>
  )
}
