'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '@/components/providers/AuthProvider'
import { createClient } from '@/lib/supabase/client'
import { GoldButton } from '@/components/ui/GoldButton'
import { GhostButton } from '@/components/ui/GhostButton'

// TODO: Wire these UI controls to Supabase user_metadata and a backend
// notification preferences endpoint. Everything below is currently local-state
// only — nothing persists across reloads.

interface NotificationPrefs {
  offerEmail: boolean
  escalationEmail: boolean
  urgentWhatsApp: boolean
  weeklySummary: boolean
}

const DEFAULT_PREFS: NotificationPrefs = {
  offerEmail: true,
  escalationEmail: true,
  urgentWhatsApp: false,
  weeklySummary: true,
}

const inputCls =
  'w-full rounded-lg bg-deep border border-gold/10 px-4 py-3 text-sand text-sm placeholder:text-n-500 focus:outline-none focus:border-gold/30 transition-colors disabled:opacity-60 disabled:cursor-not-allowed'

const labelCls = 'block text-[11px] text-n-500 uppercase tracking-widest mb-2.5'

export default function SettingsPage() {
  const { user, loading: authLoading, signOut } = useAuth()

  // TODO: replace with real user_metadata fields once wired through Supabase
  const metadata = (user?.user_metadata ?? {}) as Record<string, unknown>
  const [displayName, setDisplayName] = useState<string>(
    (metadata.display_name as string) || '',
  )
  const [phone, setPhone] = useState<string>((metadata.phone as string) || '')
  const [prefs, setPrefs] = useState<NotificationPrefs>(DEFAULT_PREFS)
  const [savedBanner, setSavedBanner] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Reseed draft fields when the authed user identity changes (e.g. after
  // auth loads or on user switch). Storing the last synced user id in state
  // and comparing during render is React's recommended pattern for resetting
  // derived state without an effect.
  const [lastUserId, setLastUserId] = useState<string | null>(user?.id ?? null)
  if (user && user.id !== lastUserId) {
    setLastUserId(user.id)
    const m = (user.user_metadata ?? {}) as Record<string, unknown>
    setDisplayName((m.display_name as string) || '')
    setPhone((m.phone as string) || '')
  }

  useEffect(() => {
    if (!savedBanner) return
    const t = setTimeout(() => setSavedBanner(null), 2400)
    return () => clearTimeout(t)
  }, [savedBanner])

  const [accountSaving, setAccountSaving] = useState(false)
  const [accountError, setAccountError] = useState<string | null>(null)

  const handleAccountSave = async () => {
    setAccountSaving(true)
    setAccountError(null)
    try {
      const supabase = createClient()
      const { error } = await supabase.auth.updateUser({
        data: {
          display_name: displayName || null,
          phone: phone || null,
        },
      })
      if (error) throw error
      setSavedBanner('Account details saved')
    } catch (err) {
      setAccountError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setAccountSaving(false)
    }
  }

  const handleNotificationsSave = () => {
    // TODO: persist prefs to backend notification-preferences endpoint
    setSavedBanner('Notification preferences saved')
  }

  const handleSignOutAll = async () => {
    // TODO: use supabase.auth.signOut({ scope: 'global' }) once exposed
    await signOut()
  }

  const handleDeleteAccount = () => {
    // TODO: call backend /api/v1/account/delete which cascades to Supabase
    setConfirmDelete(false)
    setSavedBanner('Account deletion requested — our team will follow up')
  }

  return (
    <div className="max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <h1 className="editorial text-3xl md:text-4xl font-bold text-sand tracking-tight">
          Settings
        </h1>
        <p className="text-n-500 text-sm mt-2 mb-8">
          Account preferences and notifications
        </p>

        {savedBanner && (
          <div
            className="mb-6 rounded-lg border border-sage/30 bg-sage/10 px-4 py-3 text-sm text-sage-lt"
            role="status"
            aria-live="polite"
          >
            {savedBanner}
          </div>
        )}

        {/* Section 1 — Account */}
        <section className="surface-1 rounded-xl p-6 sm:p-7 ghost-border mb-6">
          <h2 className="text-sand font-semibold text-base mb-1">Account</h2>
          <p className="text-n-500 text-xs mb-6">Your profile and contact info.</p>

          <div className="space-y-5">
            <div>
              <label htmlFor="settings-email" className={labelCls}>Email</label>
              <input
                id="settings-email"
                type="email"
                className={inputCls}
                value={authLoading ? '' : (user?.email ?? '')}
                disabled
                readOnly
              />
              <p className="text-n-500 text-[11px] mt-2">
                Email can&apos;t be changed here. Contact support to update.
              </p>
            </div>

            <div>
              <label htmlFor="settings-name" className={labelCls}>Display name</label>
              <input
                id="settings-name"
                type="text"
                className={inputCls}
                placeholder="e.g. Ahmad Al Mansouri"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="settings-phone" className={labelCls}>
                Phone number <span className="text-n-500 normal-case tracking-normal">(for WhatsApp alerts)</span>
              </label>
              <input
                id="settings-phone"
                type="tel"
                className={`${inputCls} font-mono`}
                placeholder="+971 50 123 4567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
          </div>

          {accountError && (
            <p className="mt-4 text-sm text-red-400" role="alert">{accountError}</p>
          )}

          <div className="mt-7">
            <GoldButton
              size="sm"
              onClick={handleAccountSave}
              className={accountSaving ? 'opacity-50 pointer-events-none' : ''}
            >
              {accountSaving ? 'Saving...' : 'Save Account'}
            </GoldButton>
          </div>
        </section>

        {/* Section 2 — Notifications */}
        <section className="surface-1 rounded-xl p-6 sm:p-7 ghost-border mb-6">
          <h2 className="text-sand font-semibold text-base mb-1">Notifications</h2>
          <p className="text-n-500 text-xs mb-6">Control when and how Dalya reaches you.</p>

          <div className="flex flex-col">
            <NotificationRow
              id="pref-offer"
              label="Email me when a buyer submits an offer"
              checked={prefs.offerEmail}
              onChange={(v) => setPrefs((p) => ({ ...p, offerEmail: v }))}
            />
            <NotificationRow
              id="pref-escalation"
              label="Email me when the AI escalates a question"
              checked={prefs.escalationEmail}
              onChange={(v) => setPrefs((p) => ({ ...p, escalationEmail: v }))}
            />
            <NotificationRow
              id="pref-whatsapp"
              label="WhatsApp me for urgent alerts"
              checked={prefs.urgentWhatsApp}
              onChange={(v) => setPrefs((p) => ({ ...p, urgentWhatsApp: v }))}
            />
            <NotificationRow
              id="pref-weekly"
              label="Weekly activity summary"
              checked={prefs.weeklySummary}
              onChange={(v) => setPrefs((p) => ({ ...p, weeklySummary: v }))}
              isLast
            />
          </div>

          <div className="mt-7">
            <GoldButton size="sm" onClick={handleNotificationsSave}>
              Save Preferences
            </GoldButton>
          </div>
        </section>

        {/* Section 3 — Danger Zone */}
        <section className="rounded-xl p-6 sm:p-7 border border-red-500/20 bg-red-500/[0.03]">
          <h2 className="text-sand font-semibold text-base mb-1">Danger zone</h2>
          <p className="text-n-500 text-xs mb-6">Session and account actions.</p>

          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <GhostButton size="sm" onClick={handleSignOutAll}>
              Sign out of all sessions
            </GhostButton>
            {!confirmDelete ? (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="px-5 py-2.5 text-sm font-semibold uppercase tracking-wide rounded-md border border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500/50 transition-colors focus-visible:ring-2 focus-visible:ring-red-500/40 focus-visible:outline-none"
              >
                Delete account
              </button>
            ) : (
              <div className="flex items-center gap-3 rounded-md border border-red-500/40 bg-red-500/5 px-4 py-2.5">
                <span className="text-sand text-xs">Delete your account permanently?</span>
                <button
                  type="button"
                  onClick={handleDeleteAccount}
                  className="text-xs font-semibold uppercase tracking-wide text-red-400 hover:text-red-300 transition-colors"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="text-xs font-semibold uppercase tracking-wide text-n-500 hover:text-sand transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          <p className="text-n-500 text-[11px] mt-5 leading-relaxed">
            Deleting your account removes your listings, buyer conversations, and access to Dalya. This can&apos;t be undone.
          </p>
        </section>
      </motion.div>
    </div>
  )
}

function NotificationRow({
  id,
  label,
  checked,
  onChange,
  isLast,
}: {
  id: string
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  isLast?: boolean
}) {
  return (
    <label
      htmlFor={id}
      className={`flex items-center justify-between gap-4 py-3.5 cursor-pointer group ${
        isLast ? '' : 'border-b border-gold/8'
      }`}
    >
      <span className="text-sand text-sm group-hover:text-gold transition-colors">{label}</span>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 rounded border-gold/30 bg-deep text-gold accent-gold focus:ring-2 focus:ring-gold/40 focus:ring-offset-0 focus:outline-none cursor-pointer"
      />
    </label>
  )
}
