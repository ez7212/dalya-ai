'use client'

import { usePathname } from 'next/navigation'
import { AppSidebar, BackButton } from '@/components/app/AppSidebar'
import { BrokerageGate, BrokerageProvider, BrokerageSelector } from '@/components/providers/BrokerageProvider'
import { useAuth } from '@/components/providers/AuthProvider'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { user, signOut } = useAuth()

  const isLoginPage = pathname === '/login' || pathname.startsWith('/auth/')
  const isOnboardingPage = pathname.startsWith('/onboarding')
  const isAdminPage = pathname.startsWith('/admin')
  const requiresBrokerageContext = !isLoginPage && !isOnboardingPage && !isAdminPage
  const displayName = (user?.user_metadata?.display_name as string) || user?.email || ''
  const initial = displayName ? displayName.charAt(0).toUpperCase() : null

  // Login and auth callback pages: no app shell at all
  if (isLoginPage) {
    return <>{children}</>
  }

  // All other app pages: always render the same structure
  return (
    <BrokerageProvider>
    <div className="min-h-screen bg-neutral-50">
      <AppSidebar />

      <div className="min-h-screen pl-64">
        <header className="fixed left-64 right-0 top-0 z-40 border-b border-neutral-200 bg-white/90 backdrop-blur-sm">
          <div className="flex h-16 items-center justify-between gap-4 px-4 md:px-6 lg:px-8">
            <BackButton />
          {/* Right side — user menu */}
          <div className="flex items-center justify-end gap-4">
            {user && !isOnboardingPage && !isAdminPage && <BrokerageSelector />}
            {user && (
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex flex-col items-end leading-tight">
                  <span className="text-[12px] text-neutral-800 font-medium truncate max-w-[200px]">
                    {displayName}
                  </span>
                  <button
                    onClick={() => signOut()}
                    className="text-[11px] text-neutral-500 hover:text-brand-600 transition-colors"
                  >
                    Sign out
                  </button>
                </div>
                <button
                  onClick={() => signOut()}
                  className="sm:hidden w-9 h-9 rounded-full bg-brand-50 flex items-center justify-center text-brand-700 text-xs font-semibold hover:bg-brand-100 transition-colors"
                  aria-label="Sign out"
                  title={displayName || 'Sign out'}
                >
                  {initial}
                </button>
                <span className="hidden sm:flex w-9 h-9 rounded-full bg-brand-50 items-center justify-center text-brand-700 text-xs font-semibold">
                  {initial}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>
        <main id="main-content" className="pt-16">
          {requiresBrokerageContext ? <BrokerageGate>{children}</BrokerageGate> : children}
        </main>
      </div>
    </div>
    </BrokerageProvider>
  )
}
