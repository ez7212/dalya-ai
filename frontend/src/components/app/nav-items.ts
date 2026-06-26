export interface AppNavItem {
  readonly label: string
  readonly href: string
  readonly icon: string
}

const CORE_NAV_ITEMS = [
  { label: 'Dashboard', href: '/agent', icon: 'dashboard' },
  { label: 'Inbox', href: '/agent/inbox', icon: 'forum' },
  { label: 'Listings', href: '/listings', icon: 'real_estate_agent' },
  { label: 'Buyers', href: '/agent/buyers', icon: 'groups' },
  { label: 'Drafts', href: '/agent/drafts', icon: 'edit_note' },
  { label: 'Viewings', href: '/agent/viewings', icon: 'event_available' },
  { label: 'Escalations', href: '/agent/escalations', icon: 'support_agent' },
  { label: 'Calendar', href: '/agent/calendar', icon: 'calendar_month' },
] as const satisfies readonly AppNavItem[]

const OWNER_SURFACE_NAV_ITEMS = [
  { label: 'Campaigns', href: '/campaigns', icon: 'campaign' },
  { label: 'Inbox', href: '/inbox', icon: 'inbox' },
  { label: 'Pages', href: '/pages', icon: 'article' },
] as const satisfies readonly AppNavItem[]

const SETTINGS_NAV_ITEM = { label: 'Settings', href: '/settings', icon: 'settings' } as const satisfies AppNavItem
const FULL_NAV_ROLES = new Set(['admin', 'owner', 'team_lead'])

export const PILOT_NAV_ITEMS = [
  ...CORE_NAV_ITEMS,
  SETTINGS_NAV_ITEM,
] as const satisfies readonly AppNavItem[]

export const FULL_NAV_ITEMS = [
  ...CORE_NAV_ITEMS,
  ...OWNER_SURFACE_NAV_ITEMS,
  SETTINGS_NAV_ITEM,
] as const satisfies readonly AppNavItem[]

export function getAppNavItems({
  ownerSurfacesEnabled,
  role,
}: {
  readonly ownerSurfacesEnabled: boolean
  readonly role?: string | null
}): readonly AppNavItem[] {
  return ownerSurfacesEnabled || roleCanUseFullNav(role) ? FULL_NAV_ITEMS : PILOT_NAV_ITEMS
}

function roleCanUseFullNav(role: string | null | undefined): boolean {
  if (!role) return false
  return FULL_NAV_ROLES.has(role)
}
