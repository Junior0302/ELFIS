export type ExtractionRecord = {
  id: string
  document_id: string
  universal_document_id?: string | null
  migration_session_id?: string | null
  schema_name: string
  schema_version: string
  extraction_version: string
  status: string
  strategy?: string | null
  overall_confidence?: number | null
  confidence_level?: string | null
  critical_fields_confidence?: number | null
  completeness_score?: number | null
  consistency_score?: number | null
  requires_human_review: boolean
  structured_data: Record<string, unknown>
  warnings: unknown[]
  errors: unknown[]
  progress_percent: number
  current_step?: string | null
  text_source?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

function headers(token: string, orgId?: number | null, json = false): HeadersInit {
  const h: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  }
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

export const documentExtractionApi = {
  async extractSession(token: string, orgId: number, migrationSessionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/sessions/${migrationSessionId}/extract`,
      { method: 'POST', headers: headers(token, orgId, true), body: '{}' },
    )
    return parse<{
      extracted: number
      errors: { item_id: string; code: string; message: string }[]
      items: ExtractionRecord[]
    }>(res)
  },

  async listExtractions(token: string, orgId: number, migrationSessionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/sessions/${migrationSessionId}/extractions`,
      { headers: headers(token, orgId) },
    )
    return parse<{ items: ExtractionRecord[]; total: number }>(res)
  },

  async extractDocument(
    token: string,
    orgId: number,
    documentId: string,
    forceReextract = false,
  ) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/documents/${documentId}/extract`,
      {
        method: 'POST',
        headers: headers(token, orgId, true),
        body: JSON.stringify({ force_reextract: forceReextract }),
      },
    )
    return parse<ExtractionRecord>(res)
  },

  async getExtraction(token: string, orgId: number, extractionId: string) {
    const res = await fetch(`${apiRoot()}/document-extraction/extractions/${extractionId}`, {
      headers: headers(token, orgId),
    })
    return parse<ExtractionRecord>(res)
  },

  async retry(token: string, orgId: number, extractionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/extractions/${extractionId}/retry`,
      { method: 'POST', headers: headers(token, orgId, true), body: '{}' },
    )
    return parse<ExtractionRecord>(res)
  },

  async cancel(token: string, orgId: number, extractionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/extractions/${extractionId}/cancel`,
      { method: 'POST', headers: headers(token, orgId, true), body: '{}' },
    )
    return parse<ExtractionRecord>(res)
  },

  async getProvenance(token: string, orgId: number, extractionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/extractions/${extractionId}/provenance`,
      { headers: headers(token, orgId) },
    )
    return parse<{ provenance: Record<string, unknown> }>(res)
  },

  async getFields(token: string, orgId: number, extractionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-extraction/extractions/${extractionId}/fields`,
      { headers: headers(token, orgId) },
    )
    return parse<{ fields: Record<string, unknown>; low_confidence: string[] }>(res)
  },
}

export function extractionStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: 'En attente',
    queued: 'File d’attente',
    preparing: 'Préparation',
    extracting: 'Extraction',
    normalizing: 'Normalisation',
    reconciling: 'Réconciliation',
    validating: 'Validation schéma',
    completed: 'Terminée',
    completed_with_warnings: 'Terminée (avertissements)',
    awaiting_human_validation: 'Attente validation humaine',
    failed: 'Échouée',
    cancelled: 'Annulée',
    superseded: 'Remplacée',
    ocr_pending: 'Attente OCR',
  }
  return map[status] || status
}

export function confidenceLabel(level: string | null | undefined): string {
  const map: Record<string, string> = {
    high: 'Haute',
    medium: 'Moyenne',
    low: 'Faible',
    unreliable: 'Peu fiable',
  }
  return map[level || ''] || level || '—'
}

export function fieldCount(data: Record<string, unknown> | null | undefined): number {
  if (!data) return 0
  let n = 0
  const walk = (v: unknown) => {
    if (v == null || v === '') return
    if (Array.isArray(v)) {
      if (v.length) n += 1
      return
    }
    if (typeof v === 'object') {
      Object.values(v as Record<string, unknown>).forEach(walk)
      return
    }
    n += 1
  }
  walk(data)
  return n
}
