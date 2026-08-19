/** Client API Document Registry (RC2.4) — distinct de ComptaPilot /documents. */

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

export type RegistryDocument = {
  id: string
  document_type: string
  title: string
  status: string
  organization_id: number
  product?: string | null
  current_storage_object_id?: string | null
  current_version_id?: string | null
  version_count?: number | null
  legal_hold_active?: boolean | null
  source: string
  created_at: string
  updated_at: string
  archived_at?: string | null
  deleted_at?: string | null
  metadata?: Record<string, unknown> | null
  metadata_json?: Record<string, unknown> | null
  storage_object?: {
    id: string
    original_filename: string
    safe_filename: string
    size_bytes: number
    mime_type_declared?: string | null
    mime_type_detected?: string | null
    checksum_sha256?: string | null
    status: string
  } | null
}

export type RegistryVersion = {
  id: string
  document_id: string
  version_number: number
  storage_object_id: string
  status: string
  created_at: string
  change_reason?: string | null
  original_filename: string
  size_bytes: number
  mime_type?: string | null
}

export type RegistryLegalHold = {
  id: string
  document_id: string
  reason: string
  reference?: string | null
  active: boolean
  placed_at: string
  released_at?: string | null
}

export type RegistryListResponse = {
  items: RegistryDocument[]
  total: number
  limit: number
  offset: number
}

function authHeaders(token: string, orgId?: number | null): Headers {
  const headers = new Headers()
  headers.set('Authorization', `Bearer ${token}`)
  if (orgId) headers.set('X-Organization-Id', String(orgId))
  return headers
}

async function parseError(res: Response, fallback: string): Promise<never> {
  let message = fallback
  try {
    const body = await res.json()
    message = body?.detail?.message || body?.detail || fallback
  } catch {
    /* ignore */
  }
  throw new Error(typeof message === 'string' ? message : fallback)
}

export async function uploadRegistryDocument(opts: {
  file: File
  token: string
  orgId?: number | null
  title?: string
  documentType?: string
  source?: string
  onProgress?: (pct: number) => void
  signal?: AbortSignal
}): Promise<RegistryDocument> {
  const form = new FormData()
  form.append('file', opts.file)
  if (opts.title) form.append('title', opts.title)
  form.append('document_type', opts.documentType || 'file')
  form.append('source', opts.source || 'upload')

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${apiRoot()}/document-registry/upload`)
    xhr.setRequestHeader('Authorization', `Bearer ${opts.token}`)
    if (opts.orgId) xhr.setRequestHeader('X-Organization-Id', String(opts.orgId))
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable && opts.onProgress) {
        opts.onProgress(Math.round((ev.loaded / ev.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as RegistryDocument)
        } catch (e) {
          reject(e)
        }
      } else {
        let message = 'Échec upload'
        try {
          const body = JSON.parse(xhr.responseText)
          message = body?.detail?.message || body?.detail || message
        } catch {
          /* ignore */
        }
        reject(new Error(typeof message === 'string' ? message : 'Échec upload'))
      }
    }
    xhr.onerror = () => reject(new Error('Réseau indisponible'))
    xhr.onabort = () => reject(new Error('Upload annulé'))
    if (opts.signal) {
      opts.signal.addEventListener('abort', () => xhr.abort())
    }
    xhr.send(form)
  })
}

export async function listRegistryDocuments(
  token: string,
  orgId: number | null | undefined,
  params?: { limit?: number; offset?: number },
): Promise<RegistryListResponse> {
  const q = new URLSearchParams()
  q.set('limit', String(params?.limit ?? 50))
  q.set('offset', String(params?.offset ?? 0))
  const res = await fetch(`${apiRoot()}/document-registry?${q}`, {
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) throw new Error('Liste documents indisponible')
  return res.json()
}

export async function downloadRegistryDocument(
  documentId: string,
  token: string,
  orgId?: number | null,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/download`, {
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) throw new Error('Téléchargement refusé')
  const cd = res.headers.get('content-disposition') || ''
  const match = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i.exec(cd)
  const filename = decodeURIComponent(match?.[1] || match?.[2] || 'document')
  return { blob: await res.blob(), filename }
}

export async function listRegistryVersions(
  documentId: string,
  token: string,
  orgId?: number | null,
): Promise<{ items: RegistryVersion[]; total: number; current_version_id?: string | null }> {
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/versions`, {
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) await parseError(res, 'Versions indisponibles')
  return res.json()
}

export async function uploadRegistryVersion(opts: {
  documentId: string
  file: File
  token: string
  orgId?: number | null
  changeReason?: string
}): Promise<RegistryVersion> {
  const form = new FormData()
  form.append('file', opts.file)
  if (opts.changeReason) form.append('change_reason', opts.changeReason)
  const res = await fetch(`${apiRoot()}/document-registry/${opts.documentId}/versions`, {
    method: 'POST',
    headers: authHeaders(opts.token, opts.orgId),
    body: form,
  })
  if (!res.ok) await parseError(res, 'Échec nouvelle version')
  return res.json()
}

export async function downloadRegistryVersion(
  documentId: string,
  versionId: string,
  token: string,
  orgId?: number | null,
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(
    `${apiRoot()}/document-registry/${documentId}/versions/${versionId}/download`,
    { headers: authHeaders(token, orgId) },
  )
  if (!res.ok) throw new Error('Téléchargement version refusé')
  const cd = res.headers.get('content-disposition') || ''
  const match = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i.exec(cd)
  const filename = decodeURIComponent(match?.[1] || match?.[2] || 'document')
  return { blob: await res.blob(), filename }
}

export async function archiveRegistryDocument(
  documentId: string,
  token: string,
  orgId?: number | null,
): Promise<RegistryDocument> {
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/archive`, {
    method: 'POST',
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) await parseError(res, 'Archivage refusé')
  return res.json()
}

export async function unarchiveRegistryDocument(
  documentId: string,
  token: string,
  orgId?: number | null,
): Promise<RegistryDocument> {
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/unarchive`, {
    method: 'POST',
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) await parseError(res, 'Désarchivage refusé')
  return res.json()
}

export async function softDeleteRegistryDocument(
  documentId: string,
  token: string,
  orgId?: number | null,
  reason?: string,
): Promise<RegistryDocument> {
  const headers = authHeaders(token, orgId)
  headers.set('Content-Type', 'application/json')
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/delete`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason: reason || null }),
  })
  if (!res.ok) await parseError(res, 'Suppression refusée')
  return res.json()
}

export async function restoreRegistryDocument(
  documentId: string,
  token: string,
  orgId?: number | null,
): Promise<RegistryDocument> {
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/restore`, {
    method: 'POST',
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) await parseError(res, 'Restauration refusée')
  return res.json()
}

export async function listLegalHolds(
  documentId: string,
  token: string,
  orgId?: number | null,
): Promise<{ items: RegistryLegalHold[]; total: number }> {
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/legal-holds`, {
    headers: authHeaders(token, orgId),
  })
  if (!res.ok) await parseError(res, 'Legal holds indisponibles')
  return res.json()
}

export async function placeLegalHold(
  documentId: string,
  token: string,
  orgId: number | null | undefined,
  reason: string,
): Promise<RegistryLegalHold> {
  const headers = authHeaders(token, orgId)
  headers.set('Content-Type', 'application/json')
  const res = await fetch(`${apiRoot()}/document-registry/${documentId}/legal-holds`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) await parseError(res, 'Pose legal hold refusée')
  return res.json()
}

export async function releaseLegalHold(
  documentId: string,
  holdId: string,
  token: string,
  orgId?: number | null,
): Promise<RegistryLegalHold> {
  const res = await fetch(
    `${apiRoot()}/document-registry/${documentId}/legal-holds/${holdId}/release`,
    { method: 'POST', headers: authHeaders(token, orgId) },
  )
  if (!res.ok) await parseError(res, 'Levée legal hold refusée')
  return res.json()
}
