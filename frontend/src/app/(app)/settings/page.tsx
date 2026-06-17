import { ModulePlaceholder } from '@/components/agent-modules/ModulePlaceholder'
import { NotificationPreferences } from '@/components/settings/NotificationPreferences'

export default function SettingsPage() {
  return (
    <>
    <NotificationPreferences />
    <ModulePlaceholder
      eyebrow="Workspace controls"
      title="Settings"
      description="Settings will hold agent profile details, brokerage context, languages, handoff routing, and future integration statuses."
      primaryHref="/agent"
      primaryLabel="Back to dashboard"
      items={[
        {
          icon: 'badge',
          title: 'Agent profile',
          body: 'Show the RERA-verified profile, display name, WhatsApp number, languages, and editable service areas after signup.',
        },
        {
          icon: 'account_tree',
          title: 'Brokerage routing',
          body: 'Keep every agent tied to the registered brokerage number matched from DLD records.',
        },
        {
          icon: 'settings_input_component',
          title: 'Integrations',
          body: 'Prepare placeholders for Property Finder, Bayut, CRM, and WhatsApp connection status without blocking V1.',
        },
      ]}
    />
    </>
  )
}
