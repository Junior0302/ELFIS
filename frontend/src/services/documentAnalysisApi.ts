export type AnalysisReport = {
  id: string
  organization_id: number
  document_intake_item_id: string
  universal_document_id?: string | null
  migration_session_id?: string | null
  status: string
  schema_version: number
  analysis_version: string
  need_ocr?: boolean | null
  classification_label?: string | null
  classification_confidence?: number | null
  language_code?: string | null
  language_confidence?: number | null
  quality_score?: number | null
  orientation_degrees?: number | null
  page_count?: number | null
  detected_format?: string | null
  warnings: string[]
  error_code?: string | null
  error_message?: string | null
  processing_time_ms?: number | null
  current_step?: string | null
  steps_completed: number
  steps_total: number
  progress_percent: number
  report: Record<string, unknown>
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
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

export const documentAnalysisApi = {
  async analyzeSession(token: string, orgId: number, migrationSessionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-analysis/sessions/${migrationSessionId}/analyze`,
      { method: 'POST', headers: headers(token, orgId, true), body: '{}' },
    )
    return parse<{
      analyzed: number
      errors: { item_id: string; code: string; message: string }[]
      items: AnalysisReport[]
    }>(res)
  },

  async listReports(token: string, orgId: number, migrationSessionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-analysis/sessions/${migrationSessionId}/reports`,
      { headers: headers(token, orgId) },
    )
    return parse<{ items: AnalysisReport[]; total: number }>(res)
  },

  async analyzeItem(token: string, orgId: number, itemId: string, force = false) {
    const res = await fetch(`${apiRoot()}/document-analysis/items/${itemId}/analyze`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ force }),
    })
    return parse<AnalysisReport>(res)
  },
}

export function classificationLabel(code: string | null | undefined): string {
  const map: Record<string, string> = {
    invoice: 'Facture',
    quote: 'Devis',
    credit_note: 'Avoir',
    bank_statement: 'Relevé bancaire',
    contract: 'Contrat',
    receipt: 'Reçu',
    unknown: 'Inconnu',
  }
  return map[code || ''] || code || '—'
}

export function languageLabel(code: string | null | undefined): string {
  const map: Record<string, string> = {
    fr: 'Français',
    en: 'Anglais',
    de: 'Allemand',
    es: 'Espagnol',
    it: 'Italien',
    nl: 'Néerlandais',
    unknown: 'Inconnue',
  }
  return map[code || ''] || code || '—'
}

export function warningLabel(code: string): string {
  const map: Record<string, string> = {
    pdf_encrypted: 'PDF chiffré',
    mixed_orientation: 'Orientations mixtes',
    low_quality: 'Qualité faible',
    ocr_recommended: 'OCR recommandé',
    classification_uncertain: 'Classification incertaine',
    zip_malformed: 'Archive ZIP invalide',
  }
  return map[code] || code
}
