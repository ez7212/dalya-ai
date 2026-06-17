import { MarketingNav } from '@/components/marketing/MarketingNav'
import { MarketingFooter } from '@/components/marketing/Sections'

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="marketing-surface">
      <MarketingNav />
      <main id="main-content">{children}</main>
      <MarketingFooter />
    </div>
  )
}
