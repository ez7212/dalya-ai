'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/agent', icon: 'dashboard' },
  { label: 'Drafts', href: '/agent/drafts', icon: 'edit_note' },
  { label: 'Calendar', href: '/agent/calendar', icon: 'calendar_month' },
  { label: 'Campaigns', href: '/campaigns', icon: 'campaign' },
  { label: 'Inbox', href: '/inbox', icon: 'inbox' },
  { label: 'Listings', href: '/listings', icon: 'real_estate_agent' },
  { label: 'Pages', href: '/pages', icon: 'article' },
  { label: 'Settings', href: '/settings', icon: 'settings' },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-neutral-200 bg-white">
      <div className="flex h-16 items-center border-b border-neutral-200 px-5">
        <Link
          href="/agent"
          className="flex items-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
        >
          <Image
            src="/logo-dalya.png"
            alt="Dalya AI"
            height={52}
            width={538}
            style={{ width: 'auto', maxHeight: '48px' }}
            className="object-contain"
            priority
          />
        </Link>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
        <nav className="flex flex-col gap-1" aria-label="Agent navigation">
          {NAV_ITEMS.map((item) => {
            const active = item.href === '/agent'
              ? pathname === '/agent'
              : pathname === item.href || pathname.startsWith(`${item.href}/`)

            return (
              <Link
                key={item.label}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-800'
                }`}
              >
                <span className="material-symbols-outlined text-[19px]" aria-hidden="true">
                  {item.icon}
                </span>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </aside>
  )
}

export function BackButton() {
  const router = useRouter()

  return (
    <button
      type="button"
      onClick={() => router.back()}
      className="inline-flex items-center gap-1.5 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
    >
      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
        arrow_back
      </span>
      Back
    </button>
  )
}
