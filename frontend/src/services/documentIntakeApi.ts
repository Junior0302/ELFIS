export type IntakeStatus =
  | 'uploaded'
  | 'validating'
  | 'validated'
  | 'quarantined'
  | 'duplicate'
  | 'ready_for_analysis'
  | 'rejected'
  | 'failed'
  | 'cancelled'
  | string

export type IntakeItem = {
  id: string
  intake_token: string
  universal_document_id?: string | null
  organization_id: number
  migration_session_id?: string | null
  upload_session_id?: string | null
  batch_id?: string | null
  original_filename: string
  normalized_filename: string
  relative_path?: string | null
  extension: string
  format_id: string
  mime: string
  detected_mime?: string | null
  size_bytes: number
  checksum_sha256: string
  status: IntakeStatus
  lifecycle_status?: string | null
  origin: string
  storage_provider?: string | null
  is_duplicate: boolean
  duplicate_of_id?: string | null
  duplicate_type?: string | null
  duplicate_of_item_id?: string | null
  duplicate_confidence?: number | null
  quarantine_reason?: string | null
  reject_reason?: string | null
  extract_later: boolean
  preview_allowed: boolean
  uploaded_at?: string | null
}

export type FormatCatalogItem = {
  id: string
  label: string
  extensions: string[]
  mime_types: string[]
  max_bytes: number
  upload_allowed: boolean
  preview_allowed: boolean
  analysis_allowed: boolean
  extract_later: boolean
}

export type UploadSession = {
  id: string
  organization_id: number
  migration_session_id: string
  created_by_user_id: number
  status: string
  source_type: string
  display_label?: string | null
  expected_file_count: number
  received_file_count: number
  validated_file_count: number
  duplicate_file_count: number
  rejected_file_count: number
  cancelled_file_count: number
  quarantined_file_count: number
  expected_total_bytes: number
  received_total_bytes: number
  version: number
  internal_reference?: string | null
  started_at?: string | null
  last_activity_at?: string | null
  completed_at?: string | null
  expires_at?: string | null
}

export type UploadAnalytics = {
  schema_version: number
  file_count: number
  total_bytes: number
  received_bytes: number
  validated_count: number
  duplicate_count: number
  rejected_count: number
  quarantined_count: number
  cancelled_count: number
  average_upload_speed_bps: number | null
  duration_ms: number | null
  dominant_format: string | null
  format_distribution: Record<string, number>
  error_distribution: Record<string, number>
  completion_percent: number
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

const UPLOAD_SESSION_KEY = (migrationSessionId: string) =>
  `elfis.upload_session.${migrationSessionId}`

export const documentIntakeApi = {
  sessionStorageKey: UPLOAD_SESSION_KEY,

  async formats(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/document-intake/formats`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: FormatCatalogItem[] }>(res)
  },

  async listItems(
    token: string,
    orgId: number,
    params?: {
      migration_session_id?: string
      upload_session_id?: string
      limit?: number
    },
  ) {
    const q = new URLSearchParams()
    if (params?.migration_session_id) q.set('migration_session_id', params.migration_session_id)
    if (params?.upload_session_id) q.set('upload_session_id', params.upload_session_id)
    if (params?.limit) q.set('limit', String(params.limit))
    const qs = q.toString()
    const res = await fetch(`${apiRoot()}/document-intake/items${qs ? `?${qs}` : ''}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: IntakeItem[]; total: number; summary: Record<string, unknown> }>(res)
  },

  async createUploadSession(
    token: string,
    orgId: number,
    body: {
      migration_session_id: string
      expected_file_count?: number
      expected_total_bytes?: number
      display_label?: string
    },
  ) {
    const res = await fetch(`${apiRoot()}/document-intake/upload-sessions`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify(body),
    })
    return parse<UploadSession>(res)
  },

  async listUploadSessions(token: string, orgId: number, migrationSessionId: string) {
    const q = new URLSearchParams({ migration_session_id: migrationSessionId })
    const res = await fetch(`${apiRoot()}/document-intake/upload-sessions?${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: UploadSession[]; total: number }>(res)
  },

  async getUploadSession(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/document-intake/upload-sessions/${sessionId}`, {
      headers: headers(token, orgId),
    })
    return parse<UploadSession>(res)
  },

  async pauseUploadSession(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/document-intake/upload-sessions/${sessionId}/pause`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<UploadSession>(res)
  },

  async resumeUploadSession(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/document-intake/upload-sessions/${sessionId}/resume`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<UploadSession>(res)
  },

  async cancelUploadSession(token: string, orgId: number, sessionId: string) {
    const res = await fetch(`${apiRoot()}/document-intake/upload-sessions/${sessionId}/cancel`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<UploadSession>(res)
  },

  async getAnalytics(token: string, orgId: number, sessionId: string) {
    const res = await fetch(
      `${apiRoot()}/document-intake/upload-sessions/${sessionId}/analytics`,
      { headers: headers(token, orgId) },
    )
    return parse<UploadAnalytics>(res)
  },

  async uploadOne(
    token: string,
    orgId: number,
    file: File,
    opts?: {
      migration_session_id?: string
      upload_session_id?: string
      relative_path?: string
      idempotency_key?: string
      client_upload_id?: string
    },
  ) {
    const fd = new FormData()
    fd.append('file', file)
    if (opts?.migration_session_id) fd.append('migration_session_id', opts.migration_session_id)
    if (opts?.upload_session_id) fd.append('upload_session_id', opts.upload_session_id)
    if (opts?.relative_path) fd.append('relative_path', opts.relative_path)
    if (opts?.idempotency_key) fd.append('idempotency_key', opts.idempotency_key)
    if (opts?.client_upload_id) fd.append('client_upload_id', opts.client_upload_id)
    const res = await fetch(`${apiRoot()}/document-intake/uploads`, {
      method: 'POST',
      headers: headers(token, orgId),
      body: fd,
    })
    return parse<{ item: IntakeItem }>(res)
  },

  async uploadBatch(
    token: string,
    orgId: number,
    files: File[],
    opts?: {
      migration_session_id?: string
      upload_session_id?: string
      relative_paths?: string[]
      idempotency_keys?: string[]
    },
  ) {
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    if (opts?.migration_session_id) fd.append('migration_session_id', opts.migration_session_id)
    if (opts?.upload_session_id) fd.append('upload_session_id', opts.upload_session_id)
    if (opts?.relative_paths) fd.append('relative_paths', JSON.stringify(opts.relative_paths))
    if (opts?.idempotency_keys) fd.append('idempotency_keys', JSON.stringify(opts.idempotency_keys))
    const res = await fetch(`${apiRoot()}/document-intake/uploads/batch`, {
      method: 'POST',
      headers: headers(token, orgId),
      body: fd,
    })
    return parse<{
      batch_id: string
      items: IntakeItem[]
      accepted: number
      rejected: number
      duplicates: number
      quarantined: number
    }>(res)
  },

  async cancel(token: string, orgId: number, itemId: string) {
    const res = await fetch(`${apiRoot()}/document-intake/items/${itemId}/cancel`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<IntakeItem>(res)
  },
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}

export function intakeStatusLabel(status: string): string {
  const map: Record<string, string> = {
    uploaded: 'Déposé',
    validating: 'Validation des fichiers',
    validated: 'Validé',
    quarantined: 'Quarantaine',
    duplicate: 'Doublon exact détecté',
    ready_for_analysis: 'Prêt pour analyse',
    rejected: 'Fichier rejeté',
    failed: 'Échec',
    cancelled: 'Annulé',
  }
  return map[status] || status
}

export function uploadSessionStatusLabel(status: string): string {
  const map: Record<string, string> = {
    created: 'Prêt',
    uploading: 'Dépôt en cours',
    paused: 'Dépôt interrompu',
    validating: 'Validation des fichiers',
    completed: 'Dépôt terminé',
    partially_completed: 'Dépôt terminé avec avertissements',
    failed: 'Échec',
    cancelled: 'Annulé',
    expired: 'Expiré',
  }
  return map[status] || status
}

export function intakeIcon(formatId: string): string {
  const map: Record<string, string> = {
    pdf: 'PDF',
    csv: 'CSV',
    xls: 'XLS',
    xlsx: 'XLS',
    ods: 'ODS',
    xml: 'XML',
    json: 'JSON',
    zip: 'ZIP',
    jpeg: 'IMG',
    png: 'IMG',
    tiff: 'IMG',
    txt: 'TXT',
  }
  return map[formatId] || 'DOC'
}
