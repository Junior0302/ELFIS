import type { AuditFilters, AuditPeriodHours } from '../../types/audit'

export type AuditFiltersBarValue = {
  hours: AuditPeriodHours
  useCustomRange: boolean
  date_from: string
  date_to: string
  category: string
  severity: string
  status: string
  action: string
  service: string
  product: string
  success: '' | 'true' | 'false'
  actor_email: string
  organization_id: string
  q: string
  target_type: string
  target_id: string
  correlation_id: string
  request_id: string
  actor_user_id: string
}

export const DEFAULT_AUDIT_FILTERS: AuditFiltersBarValue = {
  hours: 24,
  useCustomRange: false,
  date_from: '',
  date_to: '',
  category: '',
  severity: '',
  status: '',
  action: '',
  service: '',
  product: '',
  success: '',
  actor_email: '',
  organization_id: '',
  q: '',
  target_type: '',
  target_id: '',
  correlation_id: '',
  request_id: '',
  actor_user_id: '',
}

export function filtersBarToApi(value: AuditFiltersBarValue, page: { limit: number; offset: number }): AuditFilters {
  const org = value.organization_id.trim()
  const orgId = org ? Number(org) : undefined
  const actorIdRaw = value.actor_user_id.trim()
  const actorId = actorIdRaw ? Number(actorIdRaw) : undefined
  const base: AuditFilters = {
    category: value.category || undefined,
    severity: value.severity || undefined,
    status: value.status || undefined,
    action: value.action.trim().toUpperCase() || undefined,
    service: value.service.trim() || undefined,
    product: value.product.trim() || undefined,
    success: value.success === '' ? undefined : value.success === 'true',
    actor_email: value.actor_email.trim() || undefined,
    organization_id: orgId != null && Number.isFinite(orgId) ? orgId : undefined,
    actor_user_id: actorId != null && Number.isFinite(actorId) ? actorId : undefined,
    q: value.q.trim() || undefined,
    target_type: value.target_type.trim() || undefined,
    target_id: value.target_id.trim() || undefined,
    correlation_id: value.correlation_id.trim() || undefined,
    request_id: value.request_id.trim() || undefined,
    limit: page.limit,
    offset: page.offset,
  }
  if (value.useCustomRange && (value.date_from || value.date_to)) {
    if (value.date_from) base.date_from = new Date(value.date_from).toISOString()
    if (value.date_to) base.date_to = new Date(value.date_to).toISOString()
  } else {
    base.hours = value.hours
  }
  return base
}
