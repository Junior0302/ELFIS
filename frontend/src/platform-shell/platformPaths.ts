/**
 * Routes montées sous le shell ELFIS Core (pas Compta / Sales).
 * Source unique pour ProductAccessLayout + thème runtime.
 * /home utilise ElfisHomeLayout ; le reste → PlatformWorkspaceLayout.
 */

const PLATFORM_EXACT = new Set([
  '/organisation',
  '/compte',
  '/abonnement',
  '/modules',
  '/notifications',
  '/admin/equipe',
])

const PLATFORM_PREFIXES = ['/platform', '/admin', '/home'] as const

/** Gestion des connexions / sync bancaires — menu ELFIS Core uniquement. */
export const ELFIS_BANKING_PATH = '/platform/banking' as const

/** Aide / support tenant — menu ELFIS Core uniquement. */
export const ELFIS_HELP_PATH = '/platform/help' as const

/** Recherche globale — surface ELFIS Core. */
export const ELFIS_SEARCH_PATH = '/platform/search' as const

export function isPlatformShellPath(pathname: string): boolean {
  const path = normalize(pathname)
  if (PLATFORM_EXACT.has(path)) return true
  for (const prefix of PLATFORM_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return true
  }
  return false
}

function normalize(pathname: string): string {
  if (!pathname) return '/'
  const trimmed = pathname.split('?')[0].split('#')[0] || '/'
  if (trimmed.length > 1 && trimmed.endsWith('/')) return trimmed.slice(0, -1)
  return trimmed || '/'
}
