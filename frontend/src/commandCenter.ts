/** Types Command Center (C1.14) — miroir backend, aucun calcul métier. */

import type { LaunchActivityItem, LaunchQuickAction } from './launchDashboard'

export type CommandPriority = {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  action_path: string
  permission: string
}

export type CommandSummaryMetric = {
  key: string
  label: string
  value: number
  unit?: string | null
  path?: string | null
}

export type CommandSmartSummary = {
  headline: string
  metrics: CommandSummaryMetric[]
  has_financial_data: boolean
}

export type CommandAiInsights = {
  status: 'empty' | 'ready'
  message: string
  title?: string
  work_queue_path?: string
  counts?: {
    todo: number
    in_progress: number
    waiting: number
    completed: number
  }
  insights: Array<{
    decision_id: string
    title: string
    summary: string
    severity: string
    action_label: string
    action_path?: string | null
  }>
}

export type CommandHealthService = {
  key: string
  label: string
  status: 'ok' | 'warning' | 'critical' | 'degraded'
  detail?: string | null
}

export type CommandSystemHealth = {
  services: CommandHealthService[]
}

export type CommandCenterData = {
  organization_name: string
  priorities: CommandPriority[]
  smart_summary: CommandSmartSummary
  activity_timeline: LaunchActivityItem[]
  ai_insights: CommandAiInsights
  quick_actions: LaunchQuickAction[]
  system_health: CommandSystemHealth
  generated_at: string
}

export function formatCommandMetric(metric: CommandSummaryMetric): string {
  if (metric.unit === 'EUR') {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(metric.value)
  }
  return String(metric.value)
}

export function severityLabel(severity: CommandPriority['severity']): string {
  switch (severity) {
    case 'critical':
      return 'Critique'
    case 'high':
      return 'Élevée'
    case 'medium':
      return 'Moyenne'
    default:
      return 'Faible'
  }
}

export function healthStatusLabel(status: CommandHealthService['status']): string {
  switch (status) {
    case 'ok':
      return 'Opérationnel'
    case 'warning':
      return 'Attention'
    case 'critical':
      return 'Critique'
    case 'degraded':
      return 'Dégradé'
    default:
      return status
  }
}
