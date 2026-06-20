'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/agent', icon: 'dashboard' },
  { label: 'Buyers', href: '/agent/buyers', icon: 'groups' },
  { label: 'Drafts', href: '/agent/drafts', icon: 'edit_note' },
  { label: 'Viewings', href: '/agent/viewings', icon: 'event_available' },
  { label: 'Escalations', href: '/agent/escalations', icon: 'support_agent' },
  { label: 'Calendar', href: '/agent/calendar', icon: 'calendar_month' },
  { label: 'Campaigns', href: '/campaigns', icon: 'campaign' },
  { label: 'Inbox', href: '/inbox', icon: 'inbox' },
  { label: 'Listings', href: '/listings', icon: 'real_estate_agent' },
  { label: 'Pages', href: '/pages', icon: 'article' },
  { label: 'Settings', href: '/settings', icon: 'settings' },
]

export function AppSidebar({
  mobileOpen = false,
  onClose,
}: {
  mobileOpen?: boolean
  onClose?: () => void
}) {
  const pathname = usePathname()

  return (
    <>
      {/* Mobile backdrop — only present when the drawer is open. */}
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-neutral-900/40 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 max-w-[85vw] flex-col border-r border-neutral-200 bg-white transition-transform duration-200 ease-out lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full lg:shadow-none'
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-neutral-200 px-5">
          <Link
            href="/agent"
            onClick={onClose}
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
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="-me-2 inline-flex h-9 w-9 items-center justify-center rounded-md text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-800 lg:hidden"
          >
            <span className="material-symbols-outlined text-[20px]" aria-hidden="true">close</span>
          </button>
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
                  onClick={onClose}
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
    </>
  )
}

export function MenuButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label="Open navigation"
      className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-neutral-300 bg-white text-neutral-700 transition-colors hover:bg-neutral-50 lg:hidden"
    >
      <span className="material-symbols-outlined text-[20px]" aria-hidden="true">menu</span>
    </button>
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
