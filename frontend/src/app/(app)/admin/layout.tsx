'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { label: 'Listings', href: '/admin' },
  { label: 'CRM', href: '/admin/crm' },
  { label: 'Knowledge Base', href: '/admin/knowledge-base' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-deep">
      <nav className="border-b border-gold/10 bg-ink/60 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex items-center gap-1 h-11">
          {navItems.map((item) => {
            const isActive =
              item.href === '/admin'
                ? pathname === '/admin'
                : pathname.startsWith(item.href)
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-gold bg-gold/10'
                    : 'text-n-500 hover:text-sand hover:bg-white/5'
                }`}
              >
                {item.label}
              </Link>
            )
          })}
        </div>
      </nav>
      <div className="max-w-7xl mx-auto px-6 lg:px-10 pt-8 pb-16">
        {children}
      </div>
    </div>
  )
}
