export type ImportRun = {
  id: string
  document_id: string
  universal_document_id?: string | null
  validation_session_id: string
  validation_version: number
  migration_session_id?: string | null
  schema_name?: string | null
  status: string
  fingerprint: string
  progress_percent: number
  error_code?: string | null
  error_message?: string | null
  warnings: unknown[]
  created_objects: Array<Record<string, unknown>>
  linked_objects: Array<Record<string, unknown>>
  report_id?: string | null
  duration_ms?: number | null
  started_at?: string | null
  completed_at?: string | null
  rolled_back_at?: string | null
  rollback_reason?: string | null
  actor_user_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export type ImportReport = {
  id: string
  import_run_id: string
  version: number
  documents: unknown[]
  created_objects: unknown[]
  linked_objects: unknown[]
  warnings: unknown[]
  duration_ms?: number | null
  actor_user_id?: number | null
  report: Record<string, unknown>
  created_at?: string | null
}

export type ReadyDocument = {
  document_id: string
  universal_document_id?: string | null
  validation_session_id: string
  validation_version: number
  schema_name?: string | null
  status: string
  already_imported: boolean
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

function headers(token: string, orgId?: number | null, json = false): HeadersInit {
  const h: Record<string, string> = { Authorization: `Bearer ${token}` }
  if (json) h['Content-Type'] = 'application/json'
  if (orgId != null) h['X-Organization-Id'] = String(orgId)
  return h
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = text
  }
  if (!res.ok) {
    const detail = (body as { detail?: unknown })?.detail
    const msg =
      typeof detail === 'string'
        ? detail
        : detail && typeof detail === 'object' && 'message' in (detail as object)
          ? String((detail as { message: string }).message)
          : `Erreur API ${res.status}`
    const err = new Error(msg) as Error & { code?: string; status?: number }
    if (detail && typeof detail === 'object' && 'code' in (detail as object)) {
      err.code = String((detail as { code: string }).code)
    }
    err.status = res.status
    throw err
  }
  return body as T
}

export const importStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    pending: 'En attente',
    mapping: 'Mapping',
    transaction_started: 'Transaction',
    committing: 'Commit',
    completed: 'Terminé',
    failed: 'Échec',
    rolling_back: 'Rollback…',
    rollback_completed: 'Rollback terminé',
    cancelled: 'Annulé',
  }
  return map[status] || status
}

export const importApi = {
  async listReady(token: string, orgId: number, migrationSessionId: string) {
    const q = new URLSearchParams({ migration_session_id: migrationSessionId })
    const res = await fetch(`${apiRoot()}/import/ready?${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: ReadyDocument[]; total: number }>(res)
  },

  async listImports(token: string, orgId: number, migrationSessionId: string) {
    const q = new URLSearchParams({ migration_session_id: migrationSessionId })
    const res = await fetch(`${apiRoot()}/import/imports?${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: ImportRun[]; total: number }>(res)
  },

  async getReport(token: string, orgId: number, importId: string) {
    const res = await fetch(`${apiRoot()}/import/imports/${importId}/report`, {
      headers: headers(token, orgId),
    })
    return parse<ImportReport>(res)
  },

  async runImport(token: string, orgId: number, documentId: string) {
    const res = await fetch(`${apiRoot()}/import/documents/${documentId}/import`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<ImportRun>(res)
  },

  async retry(token: string, orgId: number, importId: string) {
    const res = await fetch(`${apiRoot()}/import/imports/${importId}/retry`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<ImportRun>(res)
  },

  async rollback(token: string, orgId: number, importId: string, reason = 'manual') {
    const res = await fetch(`${apiRoot()}/import/imports/${importId}/rollback`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ reason }),
    })
    return parse<ImportRun>(res)
  },
}
