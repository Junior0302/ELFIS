/** Navigation Platform Cockpit — permissions IAM pour filtrage UI (V1/V2). */

export type PlatformNavItem = {
  to: string
  label: string
  end?: boolean
  /** Permissions plateforme acceptées (OR). Admin voit tout. */
  permissions: string[]
  /** Support mode : visible pour platform.support */
  supportSafe?: boolean
}

export type PlatformNavSection = { title: string; items: PlatformNavItem[] }

export const PLATFORM_COCKPIT_PERMISSIONS = {
  admin: 'platform.admin',
  support: 'platform.support',
  finance: 'platform.finance',
  operations: 'platform.operations',
  dashboard: 'platform.dashboard.read',
} as const

export const platformCockpitSections: PlatformNavSection[] = [
  {
    title: 'Plateforme',
    items: [
      {
        to: '/elfadmin',
        label: 'Vue globale',
        end: true,
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
          PLATFORM_COCKPIT_PERMISSIONS.support,
          PLATFORM_COCKPIT_PERMISSIONS.finance,
          PLATFORM_COCKPIT_PERMISSIONS.dashboard,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/organisations',
        label: 'Organisations',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.support,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/utilisateurs',
        label: 'Utilisateurs',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.support,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/abonnements',
        label: 'Abonnements',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.finance,
          PLATFORM_COCKPIT_PERMISSIONS.support,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/documents',
        label: 'Documents',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
        ],
      },
      {
        to: '/elfadmin/migration',
        label: 'Migration',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
        ],
      },
      {
        to: '/elfadmin/comptabilite',
        label: 'Comptabilité',
        permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin, PLATFORM_COCKPIT_PERMISSIONS.finance],
      },
      {
        to: '/elfadmin/finance',
        label: 'Finance',
        permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin, PLATFORM_COCKPIT_PERMISSIONS.finance],
      },
      {
        to: '/elfadmin/banque',
        label: 'Banking',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.finance,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
        ],
      },
      {
        to: '/elfadmin/ia',
        label: 'IA',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
          PLATFORM_COCKPIT_PERMISSIONS.finance,
        ],
      },
      {
        to: '/elfadmin/notifications',
        label: 'Notifications',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
          PLATFORM_COCKPIT_PERMISSIONS.support,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/rapports',
        label: 'Rapports',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.finance,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
        ],
      },
      {
        to: '/elfadmin/system-health',
        label: 'Santé système',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
          PLATFORM_COCKPIT_PERMISSIONS.support,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/logs',
        label: 'Logs',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.operations,
          PLATFORM_COCKPIT_PERMISSIONS.support,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/support',
        label: 'Support',
        permissions: [
          PLATFORM_COCKPIT_PERMISSIONS.admin,
          PLATFORM_COCKPIT_PERMISSIONS.support,
        ],
        supportSafe: true,
      },
      {
        to: '/elfadmin/configuration',
        label: 'Configuration',
        permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin],
      },
    ],
  },
  {
    title: 'Ops avancées',
    items: [
      { to: '/elfadmin/activity', label: 'Activity Center', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin] },
      { to: '/elfadmin/processing', label: 'Processing', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin, PLATFORM_COCKPIT_PERMISSIONS.operations] },
      { to: '/elfadmin/storage', label: 'Storage', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin, PLATFORM_COCKPIT_PERMISSIONS.operations] },
      { to: '/elfadmin/incidents', label: 'Incidents', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin, PLATFORM_COCKPIT_PERMISSIONS.operations] },
      { to: '/elfadmin/audit', label: 'Audit', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin] },
      { to: '/elfadmin/securite', label: 'Sécurité', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin] },
      { to: '/elfadmin/observabilite', label: 'Observabilité', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin, PLATFORM_COCKPIT_PERMISSIONS.operations] },
      { to: '/elfadmin/fiabilite', label: 'Fiabilité', permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin] },
      {
        to: '/elfadmin/developer',
        label: 'Dev Cockpit',
        permissions: [PLATFORM_COCKPIT_PERMISSIONS.admin],
      },
    ],
  },
]

/** Permissions effectives cockpit (flag admin = toutes). */
export function resolvePlatformPermissions(opts: {
  isPlatformAdmin?: boolean
  permissions?: string[]
}): string[] {
  if (opts.isPlatformAdmin) {
    return [
      PLATFORM_COCKPIT_PERMISSIONS.admin,
      PLATFORM_COCKPIT_PERMISSIONS.support,
      PLATFORM_COCKPIT_PERMISSIONS.finance,
      PLATFORM_COCKPIT_PERMISSIONS.operations,
      PLATFORM_COCKPIT_PERMISSIONS.dashboard,
      '*',
    ]
  }
  return opts.permissions || []
}

export function canSeePlatformNavItem(
  item: PlatformNavItem,
  effective: string[],
): boolean {
  if (effective.includes('*') || effective.includes(PLATFORM_COCKPIT_PERMISSIONS.admin)) {
    return true
  }
  return item.permissions.some((p) => effective.includes(p))
}
