/** SalesPilot Sales Intelligence V1 — types + helpers (no score math). */

export type InsightSeverity = 'info' | 'low' | 'medium' | 'high' | 'critical' | string
export type InsightCategory =
  | 'focus'
  | 'opportunity'
  | 'pipeline'
  | 'activity'
  | 'task'
  | 'relationship'
  | 'proposal'
  | 'conversion'
  | 'performance'
  | string

export type InsightStatus =
  | 'active'
  | 'acknowledged'
  | 'resolved'
  | 'dismissed'
  | 'expired'
  | string

export type SalesFocus = {
  title: string
  summary: string
  reason: string
  severity: InsightSeverity
  tone: 'urgent' | 'important' | 'normal' | 'no_urgent_focus' | string
  route?: string | null
  action_label?: string | null
  source_type?: string | null
  source_id?: string | null
  evidence?: Array<Record<string, unknown>>
  insight_id?: number | null
  generated_at: string
}

export type SalesInsight = {
  id: number
  insight_type: string
  category: InsightCategory
  severity: InsightSeverity
  priority_score: number
  title: string
  summary: string
  explanation: {
    headline?: string
    observed_facts?: string[]
    rule_applied?: string
    why_it_matters?: string
    recommended_next_step?: string
    resolution_condition?: string
  }
  evidence: Array<Record<string, unknown>>
  recommended_action: Record<string, unknown>
  available_actions: Array<{
    action_type: string
    label: string
    route?: string | null
    enabled?: boolean
    disabled_reason?: string | null
    required_permission?: string | null
    requires_confirmation?: boolean
  }>
  route?: string | null
  source_type: string
  source_id?: string | null
  source_label?: string | null
  status: InsightStatus
  linked_decision_id?: string | null
  resolution_condition?: string | null
  first_detected_at: string
  last_detected_at: string
  resolved_at?: string | null
  dismissed_at?: string | null
  acknowledged_at?: string | null
}

export type IntelligenceOverview = {
  focus: SalesFocus
  summary: {
    active_count: number
    critical_count: number
    high_count: number
    opportunity_count: number
    pipeline_count: number
    proposal_count: number
    task_count: number
    acknowledged_count: number
  }
  top_insights: SalesInsight[]
  opportunity_insights: SalesInsight[]
  pipeline_insights: SalesInsight[]
  proposal_insights: SalesInsight[]
  activity_insights: SalesInsight[]
  counts: IntelligenceOverview['summary']
  generated_at: string
  stale?: boolean
}

export function intelligencePath(id?: number | string | null): string {
  if (id == null) return '/sales/intelligence'
  return `/sales/intelligence/${id}`
}

export function severityTone(
  severity: string,
): 'ok' | 'accent' | 'warn' | 'danger' | 'neutral' {
  if (severity === 'critical') return 'danger'
  if (severity === 'high') return 'warn'
  if (severity === 'medium') return 'accent'
  if (severity === 'info' || severity === 'low') return 'neutral'
  return 'neutral'
}

export function focusToneLabel(tone: string): string {
  if (tone === 'urgent') return 'Urgent'
  if (tone === 'important') return 'Important'
  if (tone === 'no_urgent_focus') return 'Aucune urgence'
  return 'Normal'
}
