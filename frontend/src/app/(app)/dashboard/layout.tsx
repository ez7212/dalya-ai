'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface NavItem {
  label: string
  href: string
  icon: string
  matchPrefix?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'My Listings', href: '/dashboard', icon: 'home_work' },
  { label: 'Upload SPA', href: '/dashboard/listings/new', icon: 'upload_file', matchPrefix: true },
  { label: 'Activity', href: '/dashboard/activity', icon: 'chat', matchPrefix: true },
  { label: 'Settings', href: '/dashboard/settings', icon: 'settings', matchPrefix: true },
]

function isActive(pathname: string, item: NavItem): boolean {
  if (item.href === '/dashboard') {
    // My Listings: active on /dashboard and /dashboard/listings/[id], but NOT /dashboard/listings/new
    if (pathname === '/dashboard') return true
    if (pathname.startsWith('/dashboard/listings/') && !pathname.startsWith('/dashboard/listings/new')) {
      return true
    }
    return false
  }
  return item.matchPrefix ? pathname.startsWith(item.href) : pathname === item.href
}

function NavLink({ item, active, onNavigate }: { item: NavItem; active: boolean; onNavigate?: () => void }) {
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={`group flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors border-l-2 ${
        active
          ? 'text-gold bg-gold/10 border-gold font-medium'
          : 'text-n-500 border-transparent hover:text-sand hover:bg-ink/40'
      }`}
      aria-current={active ? 'page' : undefined}
    >
      <span
        className="material-symbols-outlined"
        aria-hidden="true"
        style={{ fontSize: '20px', fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}
      >
        {item.icon}
      </span>
      <span>{item.label}</span>
    </Link>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  const closeMobile = () => setMobileOpen(false)

  return (
    <div className="md:pl-60 lg:pl-64 bg-deep">
      {/* Desktop sidebar — fixed position */}
      <aside className="hidden md:flex md:w-60 lg:w-64 fixed top-16 left-0 bottom-0 flex-col border-r border-gold/10 bg-ink/30 px-4 py-6 z-30">
        <nav className="flex flex-col gap-1" aria-label="Dashboard navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.href} item={item} active={isActive(pathname, item)} />
          ))}
        </nav>
      </aside>

      {/* Mobile hamburger trigger — positioned above the top bar */}
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-3 left-3 z-[60] w-10 h-10 flex items-center justify-center rounded-md text-sand hover:text-gold transition-colors"
        aria-label="Open navigation"
        aria-expanded={mobileOpen}
        aria-controls="mobile-nav"
      >
        <span className="material-symbols-outlined" style={{ fontSize: '22px' }} aria-hidden="true">
          menu
        </span>
      </button>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50" role="dialog" aria-modal="true" id="mobile-nav">
          <div
            className="absolute inset-0 bg-deep/80 backdrop-blur-sm"
            onClick={closeMobile}
            aria-hidden="true"
          />
          <aside className="absolute inset-y-0 left-0 w-64 bg-ink border-r border-gold/10 px-4 py-6 flex flex-col">
            <div className="flex items-center justify-between px-3 mb-4">
              <p className="text-[11px] tracking-[0.14em] uppercase text-n-500 font-medium">Dashboard</p>
              <button
                type="button"
                onClick={closeMobile}
                className="w-8 h-8 flex items-center justify-center rounded-md text-n-500 hover:text-sand transition-colors"
                aria-label="Close navigation"
              >
                <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">
                  close
                </span>
              </button>
            </div>
            <nav className="flex flex-col gap-1" aria-label="Dashboard navigation">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  active={isActive(pathname, item)}
                  onNavigate={closeMobile}
                />
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* Main content — scrolls independently of fixed sidebar */}
      <main className="min-w-0 px-6 md:px-8 py-8">{children}</main>
    </div>
  )
}
