/** SalesPilot Relationship Workspace V1 — types + routing helpers (no business logic). */

export const WORKSPACE_ENTITIES = ['lead', 'company', 'person', 'opportunity'] as const
export type WorkspaceEntity = (typeof WORKSPACE_ENTITIES)[number]

export const WORKSPACE_TABS = [
  { id: 'overview', label: 'Vue générale' },
  { id: 'contacts', label: 'Contacts' },
  { id: 'opportunities', label: 'Opportunités' },
  { id: 'activities', label: 'Activités' },
  { id: 'tasks', label: 'Tâches' },
  { id: 'notes', label: 'Notes' },
  { id: 'documents', label: 'Documents' },
  { id: 'timeline', label: 'Timeline' },
] as const

export type WorkspaceTabId = (typeof WORKSPACE_TABS)[number]['id']

export type WorkspaceHeader = {
  entity: WorkspaceEntity
  entity_id: number
  name: string
  status?: string | null
  pipeline_name?: string | null
  stage_name?: string | null
  amount?: string | number | null
  owner_label?: string | null
  created_at?: string | null
  last_activity_at?: string | null
  health_score: number
  health_label: string
  health_explanation: string
  relationship_score: number
  relationship_label: string
  risk_level: string
  risk_label: string
}

export type RelationshipWorkspace = {
  header: WorkspaceHeader
  summary: {
    open_opportunities: number
    contacts_count: number
    activities_count: number
    open_tasks_count: number
    notes_count: number
    documents_count: number
    pipeline_value: string | number
  }
  contacts: Array<{
    id: number
    first_name: string
    last_name: string
    email?: string | null
    phone?: string | null
    job_title?: string | null
    is_primary: boolean
    linkedin_url?: string | null
  }>
  opportunities: Array<{
    id: number
    name: string
    stage_name?: string | null
    estimated_amount?: string | number | null
    probability: number
    owner_label?: string | null
    health_score: number
    health_label: string
    status: string
    href: string
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
  quick_actions: Array<{ id: string; label: string; href: string }>
  generated_at: string
}

export function isWorkspaceEntity(value: string | undefined | null): value is WorkspaceEntity {
  return !!value && (WORKSPACE_ENTITIES as readonly string[]).includes(value)
}

export function parseWorkspaceTab(value: string | null | undefined): WorkspaceTabId {
  const found = WORKSPACE_TABS.find((t) => t.id === value)
  return found?.id ?? 'overview'
}

export function workspacePath(entity: WorkspaceEntity, id: number | string, tab?: WorkspaceTabId): string {
  const base = `/sales/workspace/${entity}/${id}`
  return tab && tab !== 'overview' ? `${base}?tab=${tab}` : base
}

export function entityLabel(entity: WorkspaceEntity): string {
  switch (entity) {
    case 'lead':
      return 'Lead'
    case 'company':
      return 'Entreprise'
    case 'person':
      return 'Contact'
    case 'opportunity':
      return 'Opportunité'
  }
}
