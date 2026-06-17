import { Hero } from '@/components/marketing/Hero'
import {
  Frame,
  StatsRow,
  Surfaces,
  Pillars,
  HowWeShip,
  TrustStrip,
  ClosingCTA,
} from '@/components/marketing/Sections'

export default function Home() {
  return (
    <>
      <Hero />
      <Frame />
      <StatsRow />
      <Surfaces />
      <Pillars />
      <HowWeShip />
      <TrustStrip />
      <ClosingCTA />
    </>
  )
}
