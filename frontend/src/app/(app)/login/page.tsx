'use client'

import { Suspense, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}

function LoginForm() {
  const searchParams = useSearchParams()
  const redirectTo = searchParams.get('redirect') || '/agent'

  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const supabase = createClient()

  const handleGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin + '/auth/callback?redirect=' + encodeURIComponent(redirectTo) },
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (mode === 'signin') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      } else {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
      }
      window.location.assign(mode === 'signin' ? redirectTo : '/onboarding/agent')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const inputCls =
    'w-full rounded-md border border-neutral-300 bg-white px-3.5 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 outline-none transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

  return (
    <div className="marketing-surface min-h-screen bg-neutral-50">
      <div className="mx-auto grid min-h-screen w-full max-w-[1120px] grid-cols-1 px-6 py-8 lg:grid-cols-[1fr_420px] lg:items-center lg:gap-16 lg:px-8">
        <section className="hidden lg:block">
          <Link
            href="/"
            className="text-xl font-bold tracking-tight text-brand-500"
            style={{ letterSpacing: '-0.015em' }}
          >
            dalya
          </Link>
          <div className="mt-20 max-w-[560px]">
            <div className="t-eyebrow mb-4">Agent workspace</div>
            <h1 className="t-display mb-5 max-w-[560px]">
              Start the day with the right buyer work in front of you.
            </h1>
            <p className="t-large max-w-[520px]">
              Open your hot list, buyer context, viewings, and serious offer follow-ups from one working surface.
            </p>
          </div>

          <div
            className="mt-12 max-w-[520px] rounded-xl border p-5 shadow-card-md"
            style={{
              background: 'var(--color-surface-0)',
              borderColor: 'var(--color-border-hairline)',
            }}
          >
            <div className="flex items-center justify-between border-b pb-4" style={{ borderColor: 'var(--color-border-hairline)' }}>
              <div>
                <div className="t-eyebrow mb-1">Morning queue</div>
                <p className="text-sm font-semibold text-neutral-800">What needs agent judgment first</p>
              </div>
              <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">Live</span>
            </div>
            <div className="mt-4 space-y-3">
              <LoginPreviewRow label="Hot buyer" value="Cash offer · AED 5.2M" />
              <LoginPreviewRow label="Viewing" value="Downtown townhouse · 11:30" />
              <LoginPreviewRow label="Owner" value="Seller page viewed twice" />
            </div>
          </div>
        </section>

        <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center lg:min-h-0">
          <div className="w-full max-w-[420px]">
            <div className="mb-8 flex items-center justify-between lg:hidden">
              <Link href="/" className="text-xl font-bold tracking-tight text-brand-500">
                dalya
              </Link>
              <Link href="/" className="text-sm font-medium text-neutral-500 hover:text-brand-600">
                Website
              </Link>
            </div>

            <div
              className="rounded-xl border bg-white p-6 shadow-card-md sm:p-8"
              style={{ borderColor: 'var(--color-border-hairline)' }}
            >
              <div className="mb-7">
                <div className="t-eyebrow mb-2">Dalya workspace</div>
                <h1 className="text-2xl font-semibold tracking-tight text-neutral-800">
                  {mode === 'signin' ? 'Sign in' : 'Create your account'}
                </h1>
                <p className="mt-2 text-sm leading-relaxed text-neutral-600">
                  {mode === 'signin'
                    ? 'Open your agent dashboard and daily work queue.'
                    : 'Create your profile, then complete agent onboarding.'}
                </p>
              </div>

              <button
                type="button"
                onClick={handleGoogle}
                className="flex w-full items-center justify-center gap-3 rounded-md border border-neutral-300 bg-white px-4 py-3 text-sm font-medium text-neutral-800 transition-colors hover:border-brand-300 hover:bg-brand-50"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
                  <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>

              <div className="my-6 flex items-center gap-4">
                <div className="h-px flex-1 bg-neutral-200" />
                <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">or</span>
                <div className="h-px flex-1 bg-neutral-200" />
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    className={inputCls}
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div>
                  <label htmlFor="password" className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    required
                    minLength={6}
                    className={inputCls}
                    placeholder="At least 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                {error && (
                  <p className="rounded-md bg-error-50 px-3 py-2 text-sm text-error-700" role="alert">{error}</p>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className={`btn-brand w-full justify-center rounded-lg px-5 py-3 text-sm ${loading ? 'opacity-60 pointer-events-none' : ''}`}
                >
                  {loading ? 'Please wait...' : mode === 'signin' ? 'Sign in' : 'Create account'}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-neutral-600">
                {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
                <button
                  type="button"
                  onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(null) }}
                  className="font-medium text-brand-600 hover:text-brand-700 hover:underline underline-offset-2"
                >
                  {mode === 'signin' ? 'Sign up' : 'Sign in'}
                </button>
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function LoginPreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md bg-neutral-50 px-3 py-2">
      <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</span>
      <span className="text-right text-sm font-medium text-neutral-800">{value}</span>
    </div>
  )
}
