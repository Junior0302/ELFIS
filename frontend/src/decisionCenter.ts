/** Types Decision Center C1.15 + Execution Layer C1.16. */

export type DecisionAction = {
  action_type?: string
  type: string
  label: string
  description?: string | null
  method?: 'NAVIGATE' | 'POST'
  endpoint?: string | null
  action_path?: string | null
  path?: string | null
  requires_confirmation?: boolean
  destructive?: boolean
  required_permission?: string | null
  enabled: boolean
  disabled_reason?: string | null
  idempotency_supported?: boolean
  opens_external_page?: boolean
  opens_source?: boolean
  expected_resolution_behavior?: string | null
}

export type DecisionEvidence = {
  type: string
  label: string
  value?: string | null
  description?: string | null
}

export type DecisionHistoryItem = {
  id: string
  kind: string
  label: string
  status?: string | null
  action_type?: string | null
  at: string
  user_id?: number | null
  error_message?: string | null
}

export type DecisionItem = {
  id: string
  organization_id: number
  decision_type: string
  source_type: string
  source_id: string
  status: string
  severity: string
  confidence?: number | null
  title: string
  summary: string
  explanation: string
  recommended_action_type: string
  recommended_action_path?: string | null
  required_permission?: string | null
  created_by_rule: string
  rule_version: string
  created_at: string
  updated_at: string
  resolved_at?: string | null
  dismissed_at?: string | null
  available_actions: DecisionAction[]
  metadata?: Record<string, unknown> | null
  execution_status?: string
  last_action_type?: string | null
  last_execution_error_code?: string | null
  last_execution_error_message?: string | null
  execution_attempts?: number
  last_source_refresh_at?: string | null
}

export type DecisionDetail = DecisionItem & {
  evidence: DecisionEvidence[]
  history: DecisionHistoryItem[]
  source_label?: string | null
  what_was_detected?: string | null
  why_it_matters?: string | null
  what_to_do?: string | null
  what_happens_after?: string | null
}

export type DecisionListResponse = {
  items: DecisionItem[]
  total: number
  page: number
  page_size: number
}

export type DecisionExecuteResult = {
  execution_id?: string | null
  action_type: string
  status: string
  navigation_path?: string | null
  message?: string | null
  error_code?: string | null
  source_status?: string | null
}

export type DecisionExecuteResponse = {
  ok: boolean
  decision: DecisionDetail
  result: DecisionExecuteResult
}

export type CommandDecisionInsight = {
  decision_id: string
  title: string
  summary: string
  severity: string
  action_label: string
  action_path?: string | null
}

export const DECISIONS_REFRESH_KEY = 'elfis.decisions.refresh'
export const COMMAND_CENTER_REFRESH_KEY = 'elfis.command_center.refresh'

export function markDecisionsStale(): void {
  try {
    sessionStorage.setItem(DECISIONS_REFRESH_KEY, String(Date.now()))
    sessionStorage.setItem(COMMAND_CENTER_REFRESH_KEY, String(Date.now()))
    sessionStorage.setItem('elfis.work_queue.refresh', String(Date.now()))
  } catch {
    /* ignore */
  }
}

export function consumeDecisionsStale(): boolean {
  try {
    const value = sessionStorage.getItem(DECISIONS_REFRESH_KEY)
    if (!value) return false
    sessionStorage.removeItem(DECISIONS_REFRESH_KEY)
    return true
  } catch {
    return false
  }
}

export function consumeCommandCenterStale(): boolean {
  try {
    const value = sessionStorage.getItem(COMMAND_CENTER_REFRESH_KEY)
    if (!value) return false
    sessionStorage.removeItem(COMMAND_CENTER_REFRESH_KEY)
    return true
  } catch {
    return false
  }
}

export function decisionSeverityLabel(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'Critique'
    case 'high':
      return 'Élevée'
    case 'medium':
      return 'Moyenne'
    case 'low':
      return 'Faible'
    case 'info':
      return 'Info'
    default:
      return severity
  }
}

export function decisionStatusLabel(status: string): string {
  switch (status) {
    case 'open':
      return 'Ouverte'
    case 'in_progress':
      return 'En cours'
    case 'resolved':
      return 'Résolue'
    case 'dismissed':
      return 'Ignorée'
    case 'expired':
      return 'Expirée'
    default:
      return status
  }
}

export function executionStatusLabel(status: string): string {
  switch (status) {
    case 'idle':
      return 'Inactive'
    case 'pending':
      return 'En attente'
    case 'running':
      return 'En cours'
    case 'succeeded':
      return 'Réussie'
    case 'failed':
      return 'Échouée'
    case 'cancelled':
      return 'Annulée'
    default:
      return status
  }
}

export function actionTypeOf(action: DecisionAction): string {
  return action.action_type || action.type
}

export function actionPathOf(action: DecisionAction): string | null {
  return action.action_path || action.path || null
}
