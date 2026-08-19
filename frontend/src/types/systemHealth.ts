/** Types System Health Center — alignés sur les schémas backend RC2.1 */

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown' | 'disabled'
export type AlertSeverity = 'info' | 'warning' | 'critical'

export interface HealthMetric {
  key: string
  label: string
  value: number | string | null
  unit: string | null
  status: string | null
  description: string | null
  timestamp: string
}

export interface HealthCheckResult {
  service_id: string
  service_name: string
  category: string
  status: HealthStatus
  summary: string
  latency_ms: number | null
  checked_at: string
  version: string | null
  metrics: HealthMetric[]
  metadata: Record<string, unknown>
  error_code: string | null
  error_message: string | null
}

export interface SystemHealthSummary {
  overall_status: HealthStatus
  generated_at: string
  environment: string
  platform_version: string | null
  healthy_count: number
  degraded_count: number
  unhealthy_count: number
  unknown_count: number
  services: HealthCheckResult[]
}

export interface SystemAlert {
  alert_id: string
  severity: AlertSeverity
  service_id: string | null
  title: string
  message: string
  impact: string | null
  recommendation: string | null
  started_at: string
  last_seen_at: string
  resolved_at: string | null
  is_active: boolean
}

export interface SystemLogEntry {
  log_id: string
  timestamp: string
  level: string
  service_id: string | null
  event_type: string
  message: string
  correlation_id: string | null
  metadata: Record<string, unknown>
}

export interface SystemMetricsResponse {
  generated_at: string
  period: string
  metrics: HealthMetric[]
}

export interface SystemAlertsResponse {
  generated_at: string
  active_count: number
  critical_count: number
  warning_count: number
  alerts: SystemAlert[]
}

export interface SystemLogsResponse {
  generated_at: string
  total: number
  entries: SystemLogEntry[]
}

export interface SystemLogsFilters {
  limit?: number
  level?: string
  service_id?: string
}
