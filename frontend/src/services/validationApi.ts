export type ValidationSession = {
  id: string
  document_id: string
  universal_document_id?: string | null
  extraction_id: string
  migration_session_id?: string | null
  status: string
  validated_data: Record<string, unknown>
  field_states: Record<string, string>
  warnings: unknown[]
  errors: unknown[]
  duplicate_summary: Record<string, unknown>
  matching_summary: Record<string, unknown>
  progress_percent: number
  rejection_reason?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type ValidationField = {
  field_path: string
  ai_value: unknown
  current_value: unknown
  status: string
  confidence?: number | null
  provenance: Record<string, unknown>
  warnings: unknown[]
}

export type HistoryEntry = {
  id: string
  field_path: string
  old_value: unknown
  new_value: unknown
  action: string
  reason?: string | null
  actor_user_id?: number | null
  created_at?: string | null
}

export type DuplicateItem = {
  id: string
  other_document_id?: string | null
  other_universal_document_id?: string | null
  severity: string
  score: number
  matched_fields: string[]
  explanation?: string | null
  resolution: string
}

export type MatchItem = {
  id: string
  party_role: string
  category: string
  score: number
  contact_id?: number | null
  contact_label?: string | null
  matched_criteria: unknown[]
  explanation?: string | null
  resolution: string
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

export const validationApi = {
  async startSession(token: string, orgId: number, migrationSessionId: string) {
    const res = await fetch(
      `${apiRoot()}/validation/sessions/${migrationSessionId}/start`,
      { method: 'POST', headers: headers(token, orgId, true), body: '{}' },
    )
    return parse<{
      started: number
      errors: { item_id: string; code: string; message: string }[]
      items: ValidationSession[]
    }>(res)
  },

  async listSessions(token: string, orgId: number, migrationSessionId: string) {
    const res = await fetch(
      `${apiRoot()}/validation/sessions/${migrationSessionId}/items`,
      { headers: headers(token, orgId) },
    )
    return parse<{ items: ValidationSession[]; total: number }>(res)
  },

  async getFields(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/validation/${sessionId}/fields`, {
      headers: headers(token, orgId),
    })
    return parse<{ fields: ValidationField[] }>(res)
  },

  async editField(
    token: string,
    orgId: number,
    sessionId: string,
    fieldPath: string,
    body: { value?: unknown; action?: string; reason?: string },
  ) {
    const res = await fetch(
      `${apiRoot()}/validation/${sessionId}/fields/${encodeURIComponent(fieldPath)}`,
      {
        method: 'PATCH',
        headers: headers(token, orgId, true),
        body: JSON.stringify(body),
      },
    )
    return parse<ValidationField>(res)
  },

  async validate(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/validation/${sessionId}/validate`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ mark_ready: true }),
    })
    return parse<ValidationSession>(res)
  },

  async reject(token: string, orgId: number, sessionId: string, reason?: string) {
    const res = await fetch(`${apiRoot()}/validation/${sessionId}/reject`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ reason: reason || null }),
    })
    return parse<ValidationSession>(res)
  },

  async history(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/validation/${sessionId}/history`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: HistoryEntry[] }>(res)
  },

  async duplicates(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/validation/${sessionId}/duplicates`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: DuplicateItem[] }>(res)
  },

  async matching(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/validation/${sessionId}/matching`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: MatchItem[] }>(res)
  },

  async resolveMatch(
    token: string,
    orgId: number,
    matchId: string,
    resolution: string,
  ) {
    const res = await fetch(`${apiRoot()}/validation/matches/${matchId}/resolve`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ resolution }),
    })
    return parse<MatchItem>(res)
  },
}

export function validationStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: 'En attente',
    validating: 'En validation',
    validated: 'Validé',
    ready_for_import: 'Prêt pour import',
    rejected: 'Rejeté',
    cancelled: 'Annulé',
  }
  return map[status] || status
}

export function fieldStatusLabel(status: string): string {
  const map: Record<string, string> = {
    unknown: 'À revoir',
    accepted: 'Accepté',
    edited: 'Modifié',
    rejected: 'Rejeté',
  }
  return map[status] || status
}
