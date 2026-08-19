/** SalesPilot Collaboration V1 — types. */

export type SalesTeamMember = {
  id: number
  team_id: number
  user_id: number
  role: string
  permissions: Record<string, unknown>
  sort_order: number
  status: string
  user_label?: string | null
}

export type SalesTeam = {
  id: number
  name: string
  description?: string | null
  lead_user_id?: number | null
  status: string
  created_at: string
  updated_at: string
  members: SalesTeamMember[]
}

export type SalesComment = {
  id: number
  entity_type: string
  entity_id: number
  author_user_id?: number | null
  author_label?: string | null
  body: string
  mentions: Array<{ user_id: number; label: string }>
  vault_document_ids: number[]
  edited_at?: string | null
  created_at: string
  updated_at: string
}

export type SalesFollower = {
  id: number
  entity_type: string
  entity_id: number
  user_id: number
  user_label?: string | null
  created_at: string
}

export type SalesReview = {
  id: number
  entity_type: string
  entity_id: number
  requester_user_id?: number | null
  reviewer_user_id: number
  status: string
  message?: string | null
  decision_comment?: string | null
  decided_at?: string | null
  created_at: string
  route?: string | null
}

export type TeamDashboard = {
  team_id?: number | null
  team_name?: string | null
  open_opportunities: number
  pipeline_value: number
  overdue_tasks: number
  open_tasks: number
  pending_reviews: number
  members: SalesTeamMember[]
  load_by_member: Array<{
    user_id: number
    label?: string | null
    open_opportunities: number
    open_tasks: number
    overdue_tasks: number
  }>
  insights: Array<{ severity: string; title: string; summary: string }>
  generated_at: string
}

export type MentionCandidate = {
  user_id: number
  label: string
  email?: string | null
}

/** Format mention token resolved by backend: @[userId:Label] */
export function formatMention(userId: number, label: string): string {
  return `@[${userId}:${label}]`
}
