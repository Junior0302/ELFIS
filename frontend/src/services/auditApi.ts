import type {
  AuditEvent,
  AuditEventListResponse,
  AuditExportFormat,
  AuditFilters,
  AuditStatistics,
} from '../types/audit'

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
      if (body?.detail) {
        message =
          typeof body.detail === 'string'
            ? body.detail
            : body.detail?.message || body.detail?.code || message
      }
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  return (await res.json()) as T
}

export function buildAuditQuery(filters: AuditFilters = {}): string {
  const params = new URLSearchParams()
  if (filters.hours != null) params.set('hours', String(filters.hours))
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.severity) params.set('severity', filters.severity)
  if (filters.category) params.set('category', filters.category)
  if (filters.action) params.set('action', filters.action)
  if (filters.status) params.set('status', filters.status)
  if (filters.actor_user_id != null) params.set('actor_user_id', String(filters.actor_user_id))
  if (filters.actor_email) params.set('actor_email', filters.actor_email)
  if (filters.organization_id != null) params.set('organization_id', String(filters.organization_id))
  if (filters.service) params.set('service', filters.service)
  if (filters.product) params.set('product', filters.product)
  if (filters.success != null) params.set('success', String(filters.success))
  if (filters.target_type) params.set('target_type', filters.target_type)
  if (filters.target_id) params.set('target_id', filters.target_id)
  if (filters.correlation_id) params.set('correlation_id', filters.correlation_id)
  if (filters.request_id) params.set('request_id', filters.request_id)
  if (filters.q) params.set('q', filters.q)
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.limit != null) params.set('limit', String(filters.limit))
  if (filters.offset != null) params.set('offset', String(filters.offset))
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export function getAuditEvents(token: string, filters: AuditFilters = {}): Promise<AuditEventListResponse> {
  return request(`/admin/audit/events${buildAuditQuery(filters)}`, token)
}

export function getAuditEventById(token: string, id: string): Promise<AuditEvent> {
  return request(`/admin/audit/events/${encodeURIComponent(id)}`, token)
}

export function getAuditStatistics(
  token: string,
  filters: { hours?: number } = {},
): Promise<AuditStatistics> {
  const params = new URLSearchParams()
  if (filters.hours != null) params.set('hours', String(filters.hours))
  const qs = params.toString()
  return request(`/admin/audit/statistics${qs ? `?${qs}` : ''}`, token)
}

export async function downloadAuditExport(
  token: string,
  filters: AuditFilters,
  format: AuditExportFormat = 'csv',
): Promise<void> {
  const qs = buildAuditQuery({ ...filters, limit: undefined, offset: undefined })
  const sep = qs ? '&' : '?'
  const path = `/admin/audit/export${qs}${sep}format=${encodeURIComponent(format)}`
  const headers = new Headers({ Authorization: `Bearer ${token}` })
  const res = await fetch(`${apiRoot()}${path}`, { headers })
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) {
        message =
          typeof body.detail === 'string'
            ? body.detail
            : body.detail?.message || body.detail?.code || message
      }
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  const disposition = res.headers.get('content-disposition') || ''
  const filename = disposition.match(/filename="?([^"]+)"?/i)?.[1] || `audit-export.${format}`
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
