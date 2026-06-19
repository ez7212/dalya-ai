import { Hero } from '@/components/marketing/Hero'
import {
  StatsRow,
  Surfaces,
  Pillars,
  WhatsAppBridge,
  HowWeShip,
  ClosingCTA,
} from '@/components/marketing/Sections'

function Rule() {
  return <div role="presentation" className="section-rule" />
}

export default function Home() {
  return (
    <>
      <Hero />
      <Rule />
      <StatsRow />
      <Rule />
      <Surfaces />
      <Rule />
      <Pillars />
      <Rule />
      <WhatsAppBridge />
      <Rule />
      <HowWeShip />
      <ClosingCTA />
    </>
  )
}
