import type { ReactNode } from 'react'

type LegacyListingLayoutProps = {
  readonly children: ReactNode
}

export default function LegacyListingLayout({ children }: LegacyListingLayoutProps) {
  return children
}
