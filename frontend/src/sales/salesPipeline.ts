/** SalesPilot Pipeline Engine V1 — types (mirrors backend board). */

export type PipelineCard = {
  id: number
  name: string
  company_id?: number | null
  company_name?: string | null
  estimated_amount?: string | number | null
  person_id?: number | null
  contact_name?: string | null
  owner_user_id?: number | null
  owner_label?: string | null
  probability: number
  priority: string
  source?: string | null
  status: string
  stage_id: number
  stage_entered_at?: string | null
  days_in_stage: number
  aging_label: string
  last_activity_at?: string | null
  last_activity_subject?: string | null
  next_activity_at?: string | null
  next_activity_subject?: string | null
  health_score: number
  health_label: string
  risk_level: string
  risk_label: string
  expected_close_date?: string | null
  badges: string[]
  updated_at: string
}

export type PipelineColumn = {
  stage_id: number
  code: string
  name: string
  position: number
  probability: number
  is_won: boolean
  is_lost: boolean
  opportunity_count: number
  amount_total: string | number
  weighted_amount: string | number
  average_probability: number
  average_days_in_stage: number
  cards: PipelineCard[]
}

export type PipelineBoard = {
  pipeline_id: number
  pipeline_name: string
  pipeline_code: string
  stages: PipelineColumn[]
  summary: {
    open_opportunities: number
    pipeline_value: string | number
    weighted_pipeline_value: string | number
    won_count: number
    lost_count: number
    critical_count: number
  }
  generated_at: string
}

export type PipelineDrawer = {
  opportunity: PipelineCard
  company_name?: string | null
  contacts: Array<{
    id: number
    first_name: string
    last_name: string
    email?: string | null
    phone?: string | null
    job_title?: string | null
  }>
  activities: Array<{
    id: number
    activity_type: string
    subject: string
    activity_at: string
    result?: string | null
  }>
  tasks: Array<{
    id: number
    title: string
    status: string
    priority: string
    due_at?: string | null
  }>
  notes: Array<{
    id: number
    body_markdown: string
    author_user_id?: number | null
    created_at: string
  }>
  stage_id: number
  stage_name: string
  amount?: string | number | null
  probability: number
  quick_actions: Array<{ id: string; label: string; href: string }>
}
