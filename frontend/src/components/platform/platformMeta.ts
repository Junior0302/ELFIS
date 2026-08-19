/** Métadonnées UI Platform Cockpit V2 — sans logique métier. */

export type PlatformEnvKind = 'local' | 'staging' | 'prod' | 'unknown'

export function detectPlatformEnvironment(): PlatformEnvKind {
  const forced = (import.meta.env.VITE_PLATFORM_ENV as string | undefined)?.trim().toLowerCase()
  if (forced === 'local' || forced === 'staging' || forced === 'prod') return forced
  if (typeof window === 'undefined') return 'unknown'
  const host = window.location.hostname
  if (host === 'localhost' || host === '127.0.0.1' || host.endsWith('.local')) return 'local'
  if (host.includes('staging') || host.includes('render.com')) return 'staging'
  if (
    host === 'elfis-core.web.app' ||
    host === 'elfis-core.firebaseapp.com' ||
    host === 'elfis-core.com' ||
    host === 'www.elfis-core.com'
  ) {
    return 'prod'
  }
  return 'unknown'
}

export const PLATFORM_ENV_LABEL: Record<PlatformEnvKind, string> = {
  local: 'Local',
  staging: 'Staging',
  prod: 'Production',
  unknown: 'Environnement',
}

/** Titres de page pour topbar / fil d’Ariane. */
export const PLATFORM_PAGE_TITLES: Record<string, string> = {
  '/elfadmin': 'Vue globale',
  '/elfadmin/organisations': 'Organisations',
  '/elfadmin/utilisateurs': 'Utilisateurs',
  '/elfadmin/abonnements': 'Abonnements',
  '/elfadmin/documents': 'Documents',
  '/elfadmin/migration': 'Migration',
  '/elfadmin/comptabilite': 'Comptabilité',
  '/elfadmin/banque': 'Banking',
  '/elfadmin/finance': 'Finance',
  '/elfadmin/ia': 'IA',
  '/elfadmin/notifications': 'Notifications',
  '/elfadmin/rapports': 'Rapports',
  '/elfadmin/system-health': 'Santé système',
  '/elfadmin/logs': 'Logs',
  '/elfadmin/support': 'Support',
  '/elfadmin/configuration': 'Configuration',
  '/elfadmin/activity': 'Activity Center',
  '/elfadmin/processing': 'Processing',
  '/elfadmin/storage': 'Storage',
  '/elfadmin/incidents': 'Incidents',
  '/elfadmin/audit': 'Audit',
  '/elfadmin/securite': 'Sécurité',
  '/elfadmin/observabilite': 'Observabilité',
  '/elfadmin/fiabilite': 'Fiabilité',
  '/elfadmin/integrations/documents': 'Intégrations documents',
}

export function resolvePlatformPageTitle(pathname: string): string {
  if (PLATFORM_PAGE_TITLES[pathname]) return PLATFORM_PAGE_TITLES[pathname]
  const orgMatch = pathname.match(/^\/elfadmin\/organisations\/\d+/)
  if (orgMatch) return 'Détail organisation'
  return 'Platform Cockpit'
}

export type GlobalHealthTone = 'healthy' | 'degraded' | 'critical' | 'unknown'

export function aggregateGlobalHealth(
  statuses: string[],
): { tone: GlobalHealthTone; label: string } {
  if (!statuses.length) return { tone: 'unknown', label: 'Unknown' }
  const normalized = statuses.map((s) => s.toLowerCase())
  if (normalized.some((s) => s.includes('critical') || s.includes('unhealthy') || s === 'down' || s === 'error')) {
    return { tone: 'critical', label: 'Critical' }
  }
  if (normalized.some((s) => s.includes('degraded') || s.includes('warn'))) {
    return { tone: 'degraded', label: 'Degraded' }
  }
  if (normalized.every((s) => s.includes('healthy') || s === 'ok' || s === 'up')) {
    return { tone: 'healthy', label: 'Healthy' }
  }
  return { tone: 'unknown', label: 'Unknown' }
}

export const ELFIS_FRONTEND_VERSION = '0.8.9'
