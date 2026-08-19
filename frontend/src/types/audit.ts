/** Types Audit Engine — alignés sur /api/admin/audit */

export type AuditSeverity = 'TRACE' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

export type AuditStatus = 'SUCCESS' | 'FAILURE' | 'PARTIAL'

export type AuditCategory =
  | 'AUTH'
  | 'IAM'
  | 'SYSTEM'
  | 'SECURITY'
  | 'BILLING'
  | 'PRODUCT'
  | 'ORGANIZATION'
  | 'COMPTAPILOT'
  | 'AI'
  | 'OCR'
  | 'NOTIFICATION'
  | 'EVENT'
  | 'JOB'
  | 'PLATFORM'
  | 'SUPPORT'
  | 'VAULT'
  | 'SEARCH'
  | 'OTHER'

export type AuditPeriodHours = 1 | 24 | 168 | 720

export interface AuditEvent {
  id: string
  occurred_at: string
  severity: AuditSeverity | string
  category: AuditCategory | string
  action: string
  status: AuditStatus | string
  actor_user_id: number | null
  actor_email: string | null
  organization_id: number | null
  product: string | null
  service: string | null
  target_type: string | null
  target_id: string | null
  target_display: string | null
  request_id: string | null
  correlation_id: string | null
  ip_address?: string | null
  user_agent?: string | null
  message: string | null
  duration_ms: number | null
  success: boolean
  metadata: Record<string, unknown> | null
}

export interface AuditEventListResponse {
  total: number
  limit: number
  offset: number
  items: AuditEvent[]
}

export interface AuditStatistics {
  since: string
  hours: number
  total: number
  success: number
  failure: number
  by_severity: Record<string, number>
  by_category: Record<string, number>
  by_action: Record<string, number>
  by_service?: Record<string, number>
  by_day?: Record<string, number>
  permission_denied: number
  login_failure: number
  iam_changes: number
  warnings_errors: number
}

export interface AuditFilters {
  hours?: AuditPeriodHours | number
  date_from?: string
  date_to?: string
  severity?: string
  category?: string
  action?: string
  status?: string
  actor_user_id?: number
  actor_email?: string
  organization_id?: number
  service?: string
  product?: string
  success?: boolean
  target_type?: string
  target_id?: string
  correlation_id?: string
  request_id?: string
  q?: string
  sort?: string
  limit?: number
  offset?: number
}

export interface AuditPagination {
  total: number
  limit: number
  offset: number
  page: number
  pageCount: number
}

export type AuditExportFormat = 'csv' | 'jsonl'
