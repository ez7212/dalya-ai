import { ModulePlaceholder } from '@/components/agent-modules/ModulePlaceholder'

export default function ListingsPage() {
  return (
    <ModulePlaceholder
      eyebrow="Inventory workspace"
      title="Listings"
      description="Add an off-plan resale from an SPA or start from a finished-property portal URL, then connect the listing to buyer conversations, viewings, seller one-pagers, and owner outreach."
      primaryHref="/listings/new"
      primaryLabel="Add listing"
      primaryIcon="add"
      items={[
        {
          icon: 'upload_file',
          title: 'Off-plan SPA upload',
          body: 'Upload the SPA and review Dalya-parsed contract facts, payment plan, NOC status, handover, and developer details before publishing.',
        },
        {
          icon: 'link',
          title: 'Finished property import',
          body: 'Paste a Property Finder or Bayut URL and let Dalya prefill the listing form from available portal details.',
        },
        {
          icon: 'article',
          title: 'Listing workspace',
          body: 'Use listing facts for buyer briefs, viewing notes, seller one-pagers, and clean follow-up drafts once inventory is added.',
        },
      ]}
    />
  )
}
