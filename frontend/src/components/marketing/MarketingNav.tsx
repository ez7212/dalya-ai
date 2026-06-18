'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'

const NAV_LINKS = [
  { label: 'For brokerages', href: '/brokerages' },
  { label: 'For agents', href: '/agents' },
  { label: 'Workflow', href: '/how-it-works' },
  { label: 'About', href: '/about' },
]

export function MarketingNav() {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  const isActive = (href: string) => pathname === href

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <nav
      className="sticky top-0 z-50 border-b"
      style={{
        background: 'rgba(250, 250, 249, 0.85)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderColor: 'var(--color-border-hairline)',
      }}
    >
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 h-14 flex items-center gap-6">
        <Link
          href="/"
          className="text-lg font-bold tracking-tight"
          style={{ color: 'var(--color-brand-500)', letterSpacing: '-0.015em' }}
        >
          dalya
        </Link>

        <div className="hidden md:flex flex-1 gap-1">
          {NAV_LINKS.map(l => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={isActive(l.href) ? 'page' : undefined}
              className="px-2.5 py-1.5 text-[13px] font-medium rounded-md transition-colors"
              style={{
                color: isActive(l.href) ? 'var(--color-text-1)' : 'var(--color-text-2)',
                background: isActive(l.href) ? 'var(--color-surface-1)' : 'transparent',
              }}
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="ml-auto md:ml-0 flex items-center gap-3">
          <Link
            href="/login"
            className="inline-block text-[13px] font-medium"
            style={{ color: 'var(--color-text-2)' }}
          >
            Sign in
          </Link>
          <Link
            href="/contact"
            className="btn-brand px-3.5 py-1.5 rounded-lg text-[13px]"
          >
            Book a demo
          </Link>
        </div>

        <button
          type="button"
          className="md:hidden ml-2 w-9 h-9 flex flex-col items-center justify-center gap-1"
          onClick={() => setOpen(v => !v)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
        >
          <span className="block w-5 h-px" style={{ background: 'var(--color-text-1)' }} />
          <span className="block w-5 h-px" style={{ background: 'var(--color-text-1)' }} />
          <span className="block w-5 h-px" style={{ background: 'var(--color-text-1)' }} />
        </button>
      </div>

      {open && (
        <div
          id="mobile-menu"
          className="md:hidden fixed inset-0 top-14 z-50 px-6 pt-8 pb-8 flex flex-col"
          style={{ background: 'var(--color-surface-0)' }}
        >
          <nav className="flex flex-col gap-5 flex-1" aria-label="Mobile navigation">
            {NAV_LINKS.map(l => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="text-2xl font-semibold tracking-tight"
                style={{
                  color: isActive(l.href) ? 'var(--color-brand-500)' : 'var(--color-text-1)',
                  letterSpacing: '-0.015em',
                }}
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <div
            className="flex flex-col gap-3 pt-6 border-t"
            style={{ borderColor: 'var(--color-border-hairline)' }}
          >
            <Link
              href="/contact"
              onClick={() => setOpen(false)}
              className="btn-brand rounded-lg px-6 py-3 text-sm w-full text-center"
            >
              Book a demo
            </Link>
            <Link
              href="/login"
              onClick={() => setOpen(false)}
              className="text-center text-sm py-2"
              style={{ color: 'var(--color-text-2)' }}
            >
              Sign in
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}
