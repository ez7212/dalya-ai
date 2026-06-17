'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import Image from 'next/image'
import Link from 'next/link'
import { useAuth } from '@/components/providers/AuthProvider'

const NAV_LINKS = [
  { label: 'View Listings', href: '/#listings' },
  { label: 'How It Works', href: '/how-it-works' },
  { label: 'About', href: '/about' },
]

export function Navbar() {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()
  const { user } = useAuth()

  const initial = user?.email ? user.email.charAt(0).toUpperCase() : null

  const isActive = (href: string) => {
    if (href.startsWith('/#')) return pathname === '/'
    return pathname === href
  }

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
    <nav className="nav-glass fixed top-0 w-full z-50 font-sans">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center focus-visible:ring-2 focus-visible:ring-gold/50 focus-visible:outline-none rounded">
          <Image src="/logo-dalya.png" alt="Dalya AI" height={34} width={538} style={{ width: 'auto', maxHeight: '48px' }} className="object-contain" priority />
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map(l => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={isActive(l.href) ? 'page' : undefined}
              className={`text-sm font-medium transition-colors focus-visible:outline-none focus-visible:text-gold ${
                isActive(l.href)
                  ? 'text-sand underline underline-offset-4 decoration-gold/40'
                  : 'text-n-300 hover:text-sand'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              <Link href="/dashboard" className="text-sm font-medium text-n-300 hover:text-gold transition-colors px-3 py-2">Dashboard</Link>
              <span className="w-8 h-8 rounded-full bg-gold/15 flex items-center justify-center text-gold text-xs font-semibold">{initial}</span>
            </>
          ) : (
            <Link href="/login" className="text-sm font-medium text-n-300 hover:text-gold transition-colors px-3 py-2">Login</Link>
          )}
          <Link href="/dashboard/listings/new" className="btn-gold rounded-md tracking-wide uppercase font-semibold shadow-gold focus-visible:ring-2 focus-visible:ring-gold/50 focus-visible:outline-none px-5 py-2.5 text-sm">List Your Offplan</Link>
        </div>

        <button
          className="md:hidden flex flex-col justify-center gap-1.5 p-2 w-10 h-10 focus-visible:ring-2 focus-visible:ring-gold/50 focus-visible:outline-none rounded"
          onClick={() => setOpen(v => !v)}
          aria-label={open ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={open}
          aria-controls="mobile-menu"
        >
          <motion.span
            className="block w-5 h-px bg-sand origin-center"
            animate={open ? { rotate: 45, y: 6 } : { rotate: 0, y: 0 }}
            transition={{ duration: 0.2 }}
          />
          <motion.span
            className="block w-5 h-px bg-sand"
            animate={open ? { opacity: 0, scaleX: 0 } : { opacity: 1, scaleX: 1 }}
            transition={{ duration: 0.15 }}
          />
          <motion.span
            className="block w-5 h-px bg-sand origin-center"
            animate={open ? { rotate: -45, y: -6 } : { rotate: 0, y: 0 }}
            transition={{ duration: 0.2 }}
          />
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            id="mobile-menu"
            className="md:hidden fixed inset-0 top-16 z-50 flex flex-col px-6 pt-10 pb-8"
            style={{ background: 'rgba(15, 25, 35, 0.98)', backdropFilter: 'blur(24px)' }}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <nav className="flex flex-col gap-6 flex-1" aria-label="Mobile navigation">
              {NAV_LINKS.map((l, i) => (
                <motion.div
                  key={l.href}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.2 }}
                >
                  <Link
                    href={l.href}
                    aria-current={isActive(l.href) ? 'page' : undefined}
                    className={`text-2xl font-semibold editorial focus-visible:outline-none focus-visible:text-gold transition-colors ${
                      isActive(l.href) ? 'text-gold' : 'text-sand hover:text-gold'
                    }`}
                    onClick={() => setOpen(false)}
                  >
                    {l.label}
                  </Link>
                </motion.div>
              ))}
            </nav>
            <div className="flex flex-col gap-3 pt-8 border-t border-gold/10">
              <Link href="/dashboard/listings/new" className="btn-gold rounded-md tracking-wide uppercase font-semibold shadow-gold focus-visible:ring-2 focus-visible:ring-gold/50 focus-visible:outline-none px-8 py-4 text-sm w-full text-center" onClick={() => setOpen(false)}>
                List Your Offplan
              </Link>
              {user ? (
                <Link href="/dashboard" className="text-center text-sm text-n-300 hover:text-sand py-2 transition-colors" onClick={() => setOpen(false)}>Dashboard</Link>
              ) : (
                <Link href="/login" className="text-center text-sm text-n-300 hover:text-sand py-2 transition-colors" onClick={() => setOpen(false)}>Login</Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}
