import { redirect } from 'next/navigation'

export default function LegacyNewListingPage() {
  redirect('/listings/new')
}
