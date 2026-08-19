/** Client API Platform Developer Cockpit — agrégateurs techniques. */

function apiRoot(): string {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL as string
  if (import.meta.env.DEV) return '/api'
  return '/api'
}

async function getJson<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${apiRoot()}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Erreur ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const developerApi = {
  meta: (token: string) => getJson<Record<string, unknown>>('/platform/developer/meta', token),
  overview: (token: string) => getJson<Record<string, unknown>>('/platform/developer/overview', token),
  services: (token: string) =>
    getJson<{ services: Array<Record<string, unknown>>; total: number }>(
      '/platform/developer/services',
      token,
    ),
  configStatus: (token: string) =>
    getJson<Record<string, unknown>>('/platform/developer/config-status', token),
  diagnostics: (token: string) =>
    getJson<{ checks: Array<Record<string, unknown>>; mutable: boolean }>(
      '/platform/developer/diagnostics',
      token,
    ),
  databaseSummary: (token: string) =>
    getJson<Record<string, unknown>>('/platform/developer/database-summary', token),
  indexCollisions: (token: string) =>
    getJson<Record<string, unknown>>('/platform/developer/index-collisions', token),
  routes: (token: string) =>
    getJson<{ routes: Array<Record<string, unknown>>; total: number }>(
      '/platform/developer/routes',
      token,
    ),
  capabilities: (token: string) =>
    getJson<Record<string, unknown>>('/platform/developer/capabilities', token),
}
