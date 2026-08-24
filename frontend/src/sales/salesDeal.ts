/** SalesPilot Deal Workspace V1 — types + routing helpers (no business logic). */

export const DEAL_TABS = [
  { id: 'overview', label: 'Vue générale' },
  { id: 'participants', label: 'Participants' },
  { id: 'products', label: 'Produits' },
  { id: 'activities', label: 'Activités' },
  { id: 'tasks', label: 'Tâches' },
  { id: 'notes', label: 'Notes' },
  { id: 'documents', label: 'Documents' },
  { id: 'timeline', label: 'Timeline' },
] as const

export type DealTabId = (typeof DEAL_TABS)[number]['id']

export type DealWorkspace = {
  header: {
    opportunity_id: number
    name: string
    company_id?: number | null
    company_name?: string | null
    amount?: string | number | null
    pipeline_id?: number | null
    pipeline_name?: string | null
    stage_id?: number | null
    stage_name?: string | null
    owner_label?: string | null
    probability: number
    status: string
    health_score: number
    health_label: string
    health_explanation: string
    relationship_score: number
    relationship_label: string
    risk_level: string
    risk_label: string
    forecast_amount: string | number
    forecast_label: string
    last_activity_at?: string | null
    expected_close_date?: string | null
    created_at?: string | null
  }
  summary: {
    participants_count: number
    products_count: number
    products_total: string | number
    activities_count: number
    open_tasks_count: number
    notes_count: number
    documents_count: number
    forecast_amount: string | number
  }
  participants: Array<{
    id?: number | null
    person_id: number
    first_name: string
    last_name: string
    email?: string | null
    phone?: string | null
    job_title?: string | null
    role: string
    role_label: string
    is_primary: boolean
    href: string
  }>
  products: Array<{
    id: number
    name: string
    description?: string | null
    quantity: string | number
    unit_price: string | number
    discount_percent: string | number
    line_total: string | number
    position: number
  }>
  activities: Array<{
    id: number
    activity_type: string
    subject: string
    activity_at: string
    result?: string | null
    owner_label?: string | null
  }>
  tasks: Array<{
    id: number
    title: string
    status: string
    priority: string
    due_at?: string | null
    bucket: string
  }>
  notes: Array<{
    id: number
    body_markdown: string
    author_user_id?: number | null
    author_label?: string | null
    created_at: string
  }>
  attachments: Array<{
    id: number
    vault_document_id: string
    label?: string | null
    filename?: string | null
    preview_url?: string | null
    open_url?: string | null
  }>
  timeline: Array<{
    id: string
    event_type: string
    title: string
    occurred_at: string
    meta: Record<string, string>
  }>
  health: {
    score: number
    label: string
    explanation: string
    risk_level: string
    risk_label: string
  }
  relationship: {
    score: number
    label: string
    explanation: string
    factors: string[]
  }
  forecast: {
    amount: string | number
    probability: number
    weighted_amount: string | number
    label: string
    formula: string
  }
  quick_actions: Array<{ id: string; label: string; href: string }>
  generated_at: string
}

export function parseDealTab(value: string | null | undefined): DealTabId {
  const found = DEAL_TABS.find((t) => t.id === value)
  return found?.id ?? 'overview'
}

export function dealPath(id: number | string, tab?: DealTabId): string {
  const base = `/sales/deals/${id}`
  return tab && tab !== 'overview' ? `${base}?tab=${tab}` : base
}
