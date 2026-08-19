import type {
  SystemAlertsResponse,
  SystemHealthSummary,
  SystemLogsFilters,
  SystemLogsResponse,
  SystemMetricsResponse,
} from '../types/systemHealth'

function apiRoot(): string {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL as string
  if (import.meta.env.DEV) return '/api'
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    const productionHosts = new Set([
      'elfis-core.web.app',
      'elfis-core.firebaseapp.com',
      'elfis-core.com',
      'www.elfis-core.com',
    ])
    if (productionHosts.has(host)) {
      return 'https://elfis-core-api.onrender.com/api'
    }
  }
  return '/api'
}

async function request<T>(path: string, token: string): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' })
  headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`${apiRoot()}${path}`, { headers })
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) message = typeof body.detail === 'string' ? body.detail : message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  return (await res.json()) as T
}

export function getSystemHealth(token: string): Promise<SystemHealthSummary> {
  return request('/admin/system/health', token)
}

export function getSystemMetrics(token: string, period = '24h'): Promise<SystemMetricsResponse> {
  return request(`/admin/system/metrics?period=${encodeURIComponent(period)}`, token)
}

export function getSystemAlerts(token: string): Promise<SystemAlertsResponse> {
  return request('/admin/system/alerts', token)
}

export function getSystemLogs(token: string, filters: SystemLogsFilters = {}): Promise<SystemLogsResponse> {
  const params = new URLSearchParams()
  if (filters.limit != null) params.set('limit', String(filters.limit))
  if (filters.level) params.set('level', filters.level)
  if (filters.service_id) params.set('service_id', filters.service_id)
  const qs = params.toString()
  return request(`/admin/system/logs${qs ? `?${qs}` : ''}`, token)
}
