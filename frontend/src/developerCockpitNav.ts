/** Navigation Platform Developer Cockpit V1 */

export type DevNavItem = { to: string; label: string; end?: boolean; available?: boolean }

export type DevNavSection = { title: string; items: DevNavItem[] }

export const developerCockpitSections: DevNavSection[] = [
  {
    title: 'Supervision',
    items: [
      { to: '/elfadmin/developer', label: 'Vue technique', end: true },
      { to: '/elfadmin/developer/services', label: 'Services' },
      { to: '/elfadmin/developer/api', label: 'API' },
      { to: '/elfadmin/developer/workers', label: 'Workers', available: false },
      { to: '/elfadmin/developer/jobs', label: 'Jobs & Queues' },
      { to: '/elfadmin/developer/events', label: 'Event Bus' },
      { to: '/elfadmin/developer/logs', label: 'Logs' },
      { to: '/elfadmin/developer/traces', label: 'Traces' },
    ],
  },
  {
    title: 'Infrastructure',
    items: [
      { to: '/elfadmin/developer/database', label: 'Base de données' },
      { to: '/elfadmin/developer/cache', label: 'Cache', available: false },
      { to: '/elfadmin/developer/storage', label: 'Storage' },
      { to: '/elfadmin/developer/search', label: 'Search' },
      { to: '/elfadmin/developer/ai', label: 'IA' },
      { to: '/elfadmin/developer/notifications', label: 'Notifications' },
    ],
  },
  {
    title: 'Contrôle',
    items: [
      { to: '/elfadmin/developer/feature-flags', label: 'Feature Flags', available: false },
      { to: '/elfadmin/developer/config', label: 'Configurations' },
      { to: '/elfadmin/developer/diagnostics', label: 'Diagnostics' },
      { to: '/elfadmin/developer/audit', label: 'Audit technique' },
    ],
  },
]

export const DEVELOPER_COCKPIT_PERMISSIONS = [
  'platform.admin',
  'platform.developer',
  'platform.engineer',
  'platform.sre',
  'platform.cto',
] as const

export function canAccessDeveloperCockpit(opts: {
  isPlatformAdmin?: boolean
  permissions?: string[]
}): boolean {
  if (opts.isPlatformAdmin) return true
  const perms = opts.permissions || []
  return DEVELOPER_COCKPIT_PERMISSIONS.some((p) => perms.includes(p))
}
