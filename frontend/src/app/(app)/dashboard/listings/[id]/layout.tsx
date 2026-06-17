'use client'

import { use } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/components/providers/AuthProvider'
import { useListingDetail } from '@/lib/queries'

interface Tab {
  label: string
  href: (id: string) => string
  match: (pathname: string, id: string) => boolean
}

const TABS: Tab[] = [
  {
    label: 'Overview',
    href: (id) => `/dashboard/listings/${id}`,
    match: (pathname, id) => pathname === `/dashboard/listings/${id}`,
  },
  {
    label: 'Offers',
    href: (id) => `/dashboard/listings/${id}/offers`,
    match: (pathname, id) => pathname.startsWith(`/dashboard/listings/${id}/offers`),
  },
  {
    label: 'SPA Data',
    href: (id) => `/dashboard/listings/${id}/spa`,
    match: (pathname, id) => pathname.startsWith(`/dashboard/listings/${id}/spa`),
  },
  {
    label: 'Ready Knowledge',
    href: (id) => `/dashboard/listings/${id}/knowledge`,
    match: (pathname, id) => pathname.startsWith(`/dashboard/listings/${id}/knowledge`),
  },
  {
    label: 'Logistics',
    href: (id) => `/dashboard/listings/${id}/logistics`,
    match: (pathname, id) => pathname.startsWith(`/dashboard/listings/${id}/logistics`),
  },
]

export default function ListingDetailLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const { loading: authLoading } = useAuth()
  const pathname = usePathname()
  const { data: header, error: headerError } = useListingDetail(id, !authLoading)

  return (
    <div className="max-w-5xl mx-auto">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-n-500 text-xs hover:text-sand transition-colors mb-5"
      >
        <span className="material-symbols-outlined" aria-hidden="true" style={{ fontSize: '16px' }}>arrow_back</span>
        Back to My Listings
      </Link>

      {/* Title */}
      <div className="mb-6">
        {header ? (
          <h1 className="editorial text-2xl md:text-3xl font-bold text-sand tracking-tight">
            {header.property_name} <span className="text-n-500 font-normal">·</span>{' '}
            <span className="text-n-500 font-normal">Unit {header.unit_number}</span>
          </h1>
        ) : headerError ? (
          <h1 className="text-sand text-xl font-semibold">Listing</h1>
        ) : (
          <div className="h-8 w-80 rounded bg-ink/50 animate-pulse" aria-hidden="true" />
        )}
      </div>

      {/* Tab nav */}
      <nav
        className="flex items-center gap-1 border-b border-gold/10 mb-8 -mx-1 overflow-x-auto"
        aria-label="Listing sections"
      >
        {TABS.map((tab) => {
          const active = tab.match(pathname, id)
          return (
            <Link
              key={tab.label}
              href={tab.href(id)}
              aria-current={active ? 'page' : undefined}
              className={`relative px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                active ? 'text-gold' : 'text-n-500 hover:text-sand'
              }`}
            >
              {tab.label}
              {active && (
                <span
                  className="absolute left-3 right-3 -bottom-px h-0.5 bg-gold rounded-full"
                  aria-hidden="true"
                />
              )}
            </Link>
          )
        })}
      </nav>

      {children}
    </div>
  )
}
