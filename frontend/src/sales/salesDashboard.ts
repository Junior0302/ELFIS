/**
 * SalesPilot Dashboard API types — mirrors backend SalesDashboardOut.
 * No KPI calculation on the frontend.
 */

export type SalesDashboardSummary = {
  open_leads: number
  open_opportunities: number
  pipeline_value: string | number
  weighted_pipeline_value: string | number
  won_opportunities: number
  lost_opportunities: number
  overdue_tasks: number
  activities_today: number
}

export type SalesPipelineStageOverview = {
  stage_id: number
  code: string
  name: string
  position: number
  probability: number
  is_won: boolean
  is_lost: boolean
  opportunity_count: number
  amount_total: string | number
  average_probability: number
}

export type SalesPipelineOverview = {
  pipeline_id: number
  pipeline_name: string
  stages: SalesPipelineStageOverview[]
}

export type SalesDashboardActivity = {
  id: number
  activity_type: string
  subject: string
  activity_at: string
  bucket: 'today' | 'tomorrow' | 'this_week' | string
  result?: string | null
  opportunity_id?: number | null
  company_id?: number | null
  owner_user_id?: number | null
}

export type SalesDashboardTask = {
  id: number
  title: string
  status: string
  priority: string
  due_at?: string | null
  bucket: 'overdue' | 'today' | 'upcoming' | string
  assignee_user_id?: number | null
  opportunity_id?: number | null
  company_id?: number | null
}

export type SalesDashboardOpportunity = {
  id: number
  name: string
  estimated_amount?: string | number | null
  probability: number
  stage_id: number
  stage_name?: string | null
  status: string
  owner_user_id?: number | null
  company_id?: number | null
  company_name?: string | null
  updated_at: string
}

export type SalesQuickAction = {
  id: string
  label: string
  description: string
  href: string
}

export type SalesDashboardData = {
  summary: SalesDashboardSummary
  pipeline: SalesPipelineOverview | null
  activities: {
    today: SalesDashboardActivity[]
    tomorrow: SalesDashboardActivity[]
    this_week: SalesDashboardActivity[]
  }
  tasks: {
    overdue: SalesDashboardTask[]
    today: SalesDashboardTask[]
    upcoming: SalesDashboardTask[]
  }
  recent_opportunities: SalesDashboardOpportunity[]
  quick_actions: SalesQuickAction[]
  generated_at: string
}

export function formatSalesMoney(value: string | number | null | undefined): string {
  if (value == null || value === '') return '—'
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return String(value)
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(n)
}

export function activityTypeLabel(type: string): string {
  switch (type) {
    case 'call':
      return 'Appel'
    case 'email':
      return 'Email'
    case 'meeting':
      return 'Réunion'
    case 'visit':
      return 'Visite'
    default:
      return type
  }
}
