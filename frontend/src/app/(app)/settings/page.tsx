import { AgentProfileForm } from '@/components/settings/AgentProfileForm'
import { NotificationPreferences } from '@/components/settings/NotificationPreferences'

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-[760px] px-5 py-8">
      <header>
        <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-500">
          Workspace controls
        </p>
        <h1 className="mt-1 text-xl font-semibold text-neutral-900">Settings</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Manage your agent profile and how Dalya notifies you. Your profile details
          autofill when you add new listings.
        </p>
      </header>

      <div className="mt-6 space-y-6">
        <AgentProfileForm />
        <NotificationPreferences />
      </div>
    </div>
  )
}
