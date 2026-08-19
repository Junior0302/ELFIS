/** SalesPilot Operations — shared CRM types & helpers (S1.8). */

export type SalesListResponse<T> = {
  items: T[]
  pagination: { page: number; page_size: number; total: number; total_pages?: number }
}

export type SalesLead = {
  id: number
  title: string
  status: string
  priority: string
  email?: string | null
  phone?: string | null
  company_name?: string | null
  estimated_amount?: string | number | null
  created_at: string
  updated_at: string
}

export type SalesCompany = {
  id: number
  name: string
  email?: string | null
  phone?: string | null
  city?: string | null
  status: string
  created_at: string
  updated_at: string
}

export type SalesPerson = {
  id: number
  first_name: string
  last_name: string
  email?: string | null
  phone?: string | null
  job_title?: string | null
  company_id?: number | null
  status: string
  created_at: string
  updated_at: string
}

export type SalesTaskRow = {
  id: number
  title: string
  status: string
  priority: string
  due_at?: string | null
  opportunity_id?: number | null
  created_at: string
  updated_at: string
}

export type SalesActivityRow = {
  id: number
  activity_type: string
  subject: string
  activity_at: string
  opportunity_id?: number | null
  result?: string | null
  created_at: string
  updated_at: string
}

export type QuickCreateKind =
  | 'lead'
  | 'company'
  | 'person'
  | 'opportunity'
  | 'task'
  | 'activity'
  | 'note'

export type CalendarEvent = {
  id: string
  event_type: string
  title: string
  starts_at: string
  ends_at?: string | null
  source_type: string
  source_id: number
  route: string
  severity?: string | null
}

export type JournalItem = {
  id: string
  kind: string
  title: string
  summary?: string | null
  occurred_at: string
  source_type: string
  source_id?: number | null
  route?: string | null
}

export function personLabel(p: SalesPerson): string {
  return `${p.first_name} ${p.last_name}`.trim()
}
