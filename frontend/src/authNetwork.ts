/**
 * Auth / réseau — helpers testables (timeout, health, messages login).
 */

export const API_REQUEST_TIMEOUT_MS = 15_000

export type BackendHealthStatus = 'available' | 'unavailable' | 'timeout'

export function resolveApiRoot(input: { viteApiUrl?: string; isDev: boolean }): string {
  const forced = input.viteApiUrl?.trim()
  if (forced) return forced
  if (input.isDev) return '/api'
  throw new Error(
    'VITE_API_URL manquant : reconstruire le frontend avec VITE_API_URL=https://<api>/api.',
  )
}

export function getApiRoot(): string {
  return resolveApiRoot({
    viteApiUrl: import.meta.env.VITE_API_URL as string | undefined,
    isDev: Boolean(import.meta.env.DEV),
  })
}

export function isAbortError(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const name = 'name' in err ? String((err as { name: unknown }).name) : ''
  return name === 'AbortError' || name === 'TimeoutError'
}

export function mapLoginFailure(err: unknown): string {
  if (isAbortError(err)) {
    return 'Le serveur ELFIS Core ne répond pas. Vérifiez que le backend est démarré.'
  }
  const code =
    typeof err === 'object' && err && 'code' in err ? String((err as { code: string }).code) : ''
  if (
    code === 'auth/invalid-credential' ||
    code === 'auth/wrong-password' ||
    code === 'auth/user-not-found'
  ) {
    return 'Email ou mot de passe incorrect.'
  }
  const msg = err instanceof Error ? err.message : ''
  if (/ne répond pas|backend|timed out|timeout|Failed to fetch|NetworkError|ECONNREFUSED|Network request failed/i.test(msg)) {
    return 'Le serveur ELFIS Core ne répond pas. Vérifiez que le backend est démarré.'
  }
  if (/incorrect|invalid-credential|wrong-password|user-not-found|Aucun compte/i.test(msg)) {
    return 'Email ou mot de passe incorrect.'
  }
  if (msg && !/firebase|vite_|firestore|identity toolkit/i.test(msg)) {
    return msg
  }
  return 'Impossible de vous connecter pour le moment.'
}

export function authDevLog(event: string, data: Record<string, unknown>): void {
  if (!import.meta.env.DEV) return
  const safe = { ...data }
  for (const key of Object.keys(safe)) {
    if (/password|token|secret|id_token|access_token/i.test(key)) {
      delete safe[key]
    }
  }
  // eslint-disable-next-line no-console
  console.info(`[ELFIS Auth] ${event}`, safe)
}

export async function checkBackendHealth(
  fetchImpl: typeof fetch = fetch,
  timeoutMs = 5_000,
): Promise<BackendHealthStatus> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const started = Date.now()
  try {
    const res = await fetchImpl(`${getApiRoot()}/health`, {
      method: 'GET',
      signal: controller.signal,
    })
    authDevLog('health', { status: res.status, ms: Date.now() - started, apiRoot: getApiRoot() })
    if (res.ok) return 'available'
    return 'unavailable'
  } catch (err) {
    authDevLog('health failed', {
      ms: Date.now() - started,
      apiRoot: getApiRoot(),
      abort: isAbortError(err),
    })
    return isAbortError(err) ? 'timeout' : 'unavailable'
  } finally {
    clearTimeout(timer)
  }
}
