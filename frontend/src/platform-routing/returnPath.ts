/**
 * Chemins de retour post-auth / post-welcome — F1.3.2.3.
 * Jamais de secrets ; pathname + search (+ hash optionnel) uniquement.
 */

const AUTH_ONLY = new Set(['/login', '/register', '/forgot-password'])

/** Valide un chemin SPA interne pour restauration après login / welcome. */
export function sanitizeReturnPath(from: unknown, fallback = '/home'): string {
  if (typeof from !== 'string' || !from.startsWith('/')) return fallback
  const pathOnly = from.split('?')[0].split('#')[0] || '/'
  if (AUTH_ONLY.has(pathOnly)) return fallback
  if (pathOnly === '/welcome' || pathOnly.startsWith('/welcome/')) return fallback
  return from
}

/** Clé location complète pour state.from (RequireAuth). */
export function locationReturnKey(location: {
  pathname: string
  search?: string
  hash?: string
}): string {
  return `${location.pathname}${location.search ?? ''}${location.hash ?? ''}`
}
