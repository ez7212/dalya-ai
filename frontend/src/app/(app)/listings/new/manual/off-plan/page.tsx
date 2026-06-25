import { redirect } from 'next/navigation'

// The off-plan SPA upload now runs through the unified FinishedListingFlow review form
// (at /listings/new → Off-plan → Upload SPA), so this legacy SellerUpload route redirects.
export default function ManualOffPlanListingPage() {
  redirect('/listings/new')
}
