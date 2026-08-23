import {
  API_REQUEST_TIMEOUT_MS,
  authDevLog,
  checkBackendHealth,
  getApiRoot,
  isAbortError,
} from './authNetwork'

export { checkBackendHealth, getApiRoot }
export type { BackendHealthStatus } from './authNetwork'

export type AccountingLine = {
  account: string
  label: string
  debit: number
  credit: number
}

export type AccountingEntry = {
  journal: string
  journal_lib?: string
  label: string
  piece_ref?: string
  piece_date?: string
  lines: AccountingLine[]
  explanation: string
  imputation?: string
}

export type ContactExtractedData = {
  company_name?: string | null
  trade_name?: string | null
  first_name?: string | null
  last_name?: string | null
  siren?: string | null
  siret?: string | null
  vat_number?: string | null
  email?: string | null
  phone?: string | null
  address_line_1?: string | null
  address_line_2?: string | null
  postal_code?: string | null
  city?: string | null
  country?: string | null
  iban?: string | null
  bic?: string | null
  payment_terms?: string | null
  payment_method?: string | null
}

export type ContactDuplicateMatch = {
  contact_id: number
  company_name: string
  contact_type?: string
  siret?: string
  match_type: string
  match_score: number
}

export type ContactSuggestion = {
  id: number
  document_id: number
  role: string
  status: string
  suggested_contact_type: string
  suggested_action: string
  confidence: number
  requires_user_confirmation: boolean
  extracted_data: ContactExtractedData
  possible_duplicates: ContactDuplicateMatch[]
  matched_contact_id?: number | null
  new_fields?: Record<string, string>
  iban_alert?: boolean
}

export type Contact = {
  id: number
  organization_id: number
  contact_type: string
  status: string
  company_name: string
  trade_name?: string
  first_name?: string
  last_name?: string
  siren?: string
  siret?: string
  vat_number?: string
  email?: string
  phone?: string
  address_line_1?: string
  address_line_2?: string
  postal_code?: string
  city?: string
  country?: string
  iban?: string
  bic?: string
  payment_terms?: string
  payment_method?: string
  source?: string
  source_document_id?: number | null
  extraction_confidence?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export type Invoice = {
  id: number
  filename: string
  mime_type?: string | null
  supplier: string | null
  invoice_date: string | null
  invoice_number: string | null
  amount_ht: number | null
  amount_tva: number | null
  amount_ttc: number | null
  vat_rate: number | null
  document_type: string | null
  confidence_score: number | null
  status: string
  needs_review: boolean
  anomalies: string[]
  missing_fields: string[]
  accounting_entry: AccountingEntry | null
  supplier_contact_id?: number | null
  customer_contact_id?: number | null
  contact_suggestions?: ContactSuggestion[]
  created_at: string
  updated_at: string
}

export type VaultDocumentType =
  | 'customer_invoice'
  | 'supplier_invoice'
  | 'quote'
  | 'credit_note'
  | 'expense_report'
  | 'bank_statement'
  | 'contract'
  | 'other'

export type VaultArchiveMeta = {
  document_type: VaultDocumentType
  document_number?: string
  invoice_date?: string
  due_date?: string
  amount_ht?: string
  amount_vat?: string
  amount_ttc?: string
  currency?: string
}

export type VaultDocument = {
  id: string
  tenant_id: number
  document_type: VaultDocumentType
  document_number: string | null
  original_filename: string
  storage_path: string
  mime_type: string
  file_size: number
  checksum_sha256: string
  archive_status: string
  accounting_status: string
  email_status: string
  version: number
  archived_at: string
  created_at: string
}

export type VaultDocumentListItem = {
  id: string
  tenant_id: number
  document_type: VaultDocumentType
  document_number: string | null
  original_filename: string
  mime_type: string
  file_size: number
  invoice_date: string | null
  due_date: string | null
  amount_ht: number | string | null
  amount_vat: number | string | null
  amount_ttc: number | string | null
  currency: string
  archive_status: string
  accounting_status: string
  email_status: string
  version: number
  archived_at: string
  created_at: string
}

export type VaultDocumentDetail = VaultDocumentListItem & {
  is_locked: boolean
  updated_at: string
}

export type VaultDocumentsListResponse = {
  items: VaultDocumentListItem[]
  pagination: {
    page: number
    page_size: number
    total_items: number
    total_pages: number
  }
}

export type VaultDownloadUrlResponse = {
  document_id: string
  download_url: string
  expires_in: number
  expires_at: string
}

export type VaultDocumentsQuery = {
  page?: number
  page_size?: number
  document_type?: VaultDocumentType | ''
  search?: string
  sort_by?: 'created_at' | 'invoice_date' | 'document_number' | 'amount_ttc'
  sort_order?: 'asc' | 'desc'
}

/** @deprecated Legacy `/dashboard/stats` — surfaces client migrées vers Financial Engine. */
export type DashboardStats = {
  invoice_count: number
  total_ht: number
  recoverable_vat: number
  to_review: number
  recent: Invoice[]
}

export type CompanySettings = {
  id: number
  company_name: string
  siret: string
  vat_number: string
  default_vat_rate: number
  expense_account: string
  vat_account: string
  supplier_account: string
  accountant_firm: string
  accountant_email: string
  confidence_threshold: number
}

/**
 * Base API adaptée au réseau local :
 * - avec VITE_API_URL : URL forcée
 * - en dev Vite : "/api" (proxy same-origin → accessible via IP LAN)
 * - sinon : http(s)://{hostname}:8000/api
 */
function apiRoot(): string {
  return getApiRoot()
}

async function parseError(res: Response): Promise<string> {
  const text = await res.text()
  try {
    const data = JSON.parse(text) as {
      detail?: unknown
      existing_document_id?: string
    }
    if (typeof data.detail === 'string') {
      if (data.existing_document_id) {
        return `${data.detail} (réf. ${data.existing_document_id})`
      }
      return data.detail
    }
    if (
      typeof data.detail === 'object' &&
      data.detail &&
      'message' in data.detail &&
      typeof (data.detail as { message?: unknown }).message === 'string'
    ) {
      return (data.detail as { message: string }).message
    }
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
        .join(' · ')
    }
  } catch {
    /* raw text */
  }
  return text || `Erreur ${res.status}`
}

function friendlyError(status: number, message: string, path?: string): string {
  const isLocalApi =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  if (status === 409) {
    return message || 'Ce document est déjà présent dans ELFIS Vault.'
  }
  if (status === 404 || message.toLowerCase().includes('not found')) {
    if (path?.includes('/billing/documents/') && path.includes('/pdf')) {
      return isLocalApi
        ? 'PDF indisponible. Vérifiez que le backend local est démarré (start-backend.bat).'
        : 'PDF indisponible pour le moment. Réessayez dans quelques minutes.'
    }
    if (isLocalApi) {
      return 'Service API introuvable. Lancez le backend : start-backend.bat (port 8000)'
    }
    return 'Cette ressource est indisponible pour le moment.'
  }
  if (status === 401) return message || 'Votre session a expiré. Reconnectez-vous pour continuer.'
  if (status === 402) {
    return 'Cette fonctionnalité nécessite un essai ou un abonnement actif.'
  }
  if (status === 403) return 'Vous n’avez pas l’autorisation d’accéder à cette ressource.'
  if (status === 429) return 'Trop de demandes. Réessayez dans quelques instants.'
  if (status === 500 || status === 502 || status === 503) {
    return 'Le service est temporairement indisponible. Réessayez plus tard.'
  }
  if (/^erreur\s*api\s*\d+/i.test(message)) {
    return 'Une erreur est survenue. Réessayez ou contactez le support.'
  }
  return message
}

async function request<T>(
  path: string,
  init?: RequestInit,
  auth?: { token?: string | null; orgId?: number | null },
): Promise<T> {
  const headers = new Headers(init?.headers || {})
  if (auth?.token) headers.set('Authorization', `Bearer ${auth.token}`)
  if (auth?.orgId) headers.set('X-Organization-Id', String(auth.orgId))

  const controller = new AbortController()
  const externalSignal = init?.signal
  const onExternalAbort = () => controller.abort()
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort()
    else externalSignal.addEventListener('abort', onExternalAbort, { once: true })
  }
  const timer = setTimeout(() => controller.abort(), API_REQUEST_TIMEOUT_MS)
  const started = Date.now()
  const url = `${apiRoot()}${path}`

  try {
    const res = await fetch(url, { ...init, headers, signal: controller.signal })
    if (import.meta.env.DEV && path.startsWith('/auth/')) {
      authDevLog(res.ok ? 'request ok' : 'request failed', {
        path,
        status: res.status,
        ms: Date.now() - started,
        requestId: res.headers.get('x-request-id') || undefined,
        apiRoot: apiRoot(),
      })
    }
    if (!res.ok) throw new Error(friendlyError(res.status, await parseError(res), path))
    if (res.status === 204) return undefined as T
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) return res.json() as Promise<T>
    return undefined as T
  } catch (err) {
    if (isAbortError(err)) {
      authDevLog('request timeout', { path, ms: Date.now() - started, apiRoot: apiRoot() })
      throw new Error('Le serveur ELFIS Core ne répond pas. Vérifiez que le backend est démarré.')
    }
    if (err instanceof TypeError) {
      authDevLog('request network', { path, ms: Date.now() - started, apiRoot: apiRoot() })
      throw new Error('Le serveur ELFIS Core ne répond pas. Vérifiez que le backend est démarré.')
    }
    throw err
  } finally {
    clearTimeout(timer)
    if (externalSignal) externalSignal.removeEventListener('abort', onExternalAbort)
  }
}

async function requestBlob(
  path: string,
  token: string,
  orgId?: number | null,
): Promise<{ blob: Blob; filename: string }> {
  const headers = new Headers({ Authorization: `Bearer ${token}` })
  if (orgId) headers.set('X-Organization-Id', String(orgId))
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), API_REQUEST_TIMEOUT_MS)
  try {
    const res = await fetch(`${apiRoot()}${path}`, { headers, signal: controller.signal })
    if (!res.ok) throw new Error(friendlyError(res.status, await parseError(res), path))
    const disposition = res.headers.get('content-disposition') || ''
    const filename = disposition.match(/filename="?([^"]+)"?/i)?.[1] || 'export'
    return { blob: await res.blob(), filename }
  } catch (err) {
    if (isAbortError(err) || err instanceof TypeError) {
      throw new Error('Le serveur ELFIS Core ne répond pas. Vérifiez que le backend est démarré.')
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export async function downloadApiFile(
  path: string,
  token: string,
  orgId?: number | null,
  preferredFilename?: string,
): Promise<void> {
  const { blob, filename } = await requestBlob(path, token, orgId)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = preferredFilename?.trim() || filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}


export type WorkspaceProvisionStatus = {
  status: 'pending' | 'running' | 'completed' | 'failed'
  current_step: string
  progress: number
  setup_completed: boolean
  error_code?: string | null
  error_message?: string | null
  started_at?: string | null
  completed_at?: string | null
  provisioning_version?: number
}

export const api = {
  health: () =>
    request<{ status: string; ai_mode: string; product: string; details?: { version?: string } }>('/health'),
  // Legacy retirés du client : api.dashboard (/dashboard/stats) et api.dashboardPilot
  // (/dashboard/pilot). Source de vérité = financialApi → /api/financial/*.
  // Endpoints backend encore présents mais deprecated (voir app/routers/dashboard.py).
  listDocuments: (
    params: { q?: string; status?: string; needs_review?: boolean } | undefined,
    token: string,
    orgId?: number | null,
  ) => {
    const sp = new URLSearchParams()
    if (params?.q) sp.set('q', params.q)
    if (params?.status) sp.set('status', params.status)
    if (params?.needs_review !== undefined) sp.set('needs_review', String(params.needs_review))
    const qs = sp.toString()
    return request<Invoice[]>(`/documents${qs ? `?${qs}` : ''}`, undefined, { token, orgId })
  },
  getDocument: (id: number, token: string, orgId?: number | null) =>
    request<Invoice>(`/documents/${id}`, undefined, { token, orgId }),
  uploadDocument: async (file: File, token: string, orgId?: number | null) => {
    const form = new FormData()
    form.append('file', file)
    return request<Invoice>('/documents/upload', { method: 'POST', body: form }, { token, orgId })
  },
  archiveVaultDocument: async (
    file: File,
    meta: VaultArchiveMeta,
    token: string,
    orgId?: number | null,
  ) => {
    if (!orgId) throw new Error('Organisation requise')
    const form = new FormData()
    form.append('file', file)
    form.append('tenant_id', String(orgId))
    form.append('document_type', meta.document_type)
    form.append('currency', meta.currency || 'EUR')
    if (meta.document_number) form.append('document_number', meta.document_number)
    if (meta.invoice_date) form.append('invoice_date', meta.invoice_date)
    if (meta.due_date) form.append('due_date', meta.due_date)
    if (meta.amount_ht != null && meta.amount_ht !== '') form.append('amount_ht', String(meta.amount_ht))
    if (meta.amount_vat != null && meta.amount_vat !== '') form.append('amount_vat', String(meta.amount_vat))
    if (meta.amount_ttc != null && meta.amount_ttc !== '') form.append('amount_ttc', String(meta.amount_ttc))
    return request<VaultDocument>('/vault/documents/archive', { method: 'POST', body: form }, { token, orgId })
  },
  getVaultDocuments: (params: VaultDocumentsQuery, token: string, orgId?: number | null) => {
    const sp = new URLSearchParams()
    if (params.page) sp.set('page', String(params.page))
    if (params.page_size) sp.set('page_size', String(params.page_size))
    if (params.document_type) sp.set('document_type', params.document_type)
    if (params.search) sp.set('search', params.search)
    if (params.sort_by) sp.set('sort_by', params.sort_by)
    if (params.sort_order) sp.set('sort_order', params.sort_order)
    const qs = sp.toString()
    return request<VaultDocumentsListResponse>(
      `/vault/documents${qs ? `?${qs}` : ''}`,
      undefined,
      { token, orgId },
    )
  },
  getVaultDocument: (documentId: string, token: string, orgId?: number | null) =>
    request<VaultDocumentDetail>(`/vault/documents/${documentId}`, undefined, { token, orgId }),
  getVaultDocumentDownloadUrl: (documentId: string, token: string, orgId?: number | null) =>
    request<VaultDownloadUrlResponse>(
      `/vault/documents/${documentId}/download-url`,
      { method: 'POST' },
      { token, orgId },
    ),
  updateDocument: (
    id: number,
    payload: Partial<Invoice>,
    token: string,
    orgId?: number | null,
  ) =>
    request<Invoice>(`/documents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  reprocessDocument: (id: number, token: string, orgId?: number | null) =>
    request<Invoice>(`/documents/${id}/reprocess`, { method: 'POST' }, { token, orgId }),
  getContactSuggestions: (documentId: number, token: string, orgId?: number | null) =>
    request<{
      document_id: number
      supplier_contact_id?: number | null
      customer_contact_id?: number | null
      suggestions: ContactSuggestion[]
    }>(`/documents/${documentId}/contact-suggestions`, undefined, { token, orgId }),
  createContactFromDocument: (
    payload: {
      document_id: number
      role: string
      contact_type: string
      suggestion_id?: number | null
      confirmed_data: ContactExtractedData
    },
    token: string,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; contact: Contact; document_id: number }>(
      '/contacts/from-document',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  linkDocumentContact: (
    documentId: number,
    payload: { contact_id: number; role: string; suggestion_id?: number | null },
    token: string,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; contact: Contact; document_id: number }>(
      `/documents/${documentId}/link-contact`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  ignoreContactSuggestion: (
    documentId: number,
    payload: { role: string; suggestion_id?: number | null },
    token: string,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; ignored_count: number }>(
      `/documents/${documentId}/contact-suggestions/ignore`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  enrichContactFromDocument: (
    contactId: number,
    payload: {
      document_id: number
      accepted_fields: string[]
      field_values?: Record<string, string>
      suggestion_id?: number | null
      confirm_iban?: boolean
    },
    token: string,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; contact: Contact }>(
      `/contacts/${contactId}/enrich-from-document`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  listContacts: (
    token?: string | null,
    orgId?: number | null,
    params?: { contact_type?: string; q?: string },
  ) => {
    const search = new URLSearchParams()
    if (params?.contact_type) search.set('contact_type', params.contact_type)
    if (params?.q) search.set('q', params.q)
    const qs = search.toString()
    return request<{ contacts: Contact[] }>(
      `/contacts${qs ? `?${qs}` : ''}`,
      undefined,
      { token, orgId },
    )
  },
  createContact: (
    payload: {
      contact_type?: string
      company_name?: string
      email?: string
      phone?: string
      vat_number?: string
      address_line_1?: string
      postal_code?: string
      city?: string
      siret?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; contact: Contact }>(
      '/contacts',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  updateContact: (
    contactId: number,
    payload: Partial<{
      contact_type: string
      status: string
      company_name: string
      email: string
      phone: string
      vat_number: string
      address_line_1: string
      postal_code: string
      city: string
      siret: string
      allow_iban_replace: boolean
    }>,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; contact: Contact }>(
      `/contacts/${contactId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  deleteContact: (contactId: number, token?: string | null, orgId?: number | null) =>
    request<{ ok: boolean; contact: Contact }>(
      `/contacts/${contactId}`,
      { method: 'DELETE' },
      { token, orgId },
    ),
  listFiscalPeriods: (token?: string | null, orgId?: number | null) =>
    request<{
      periods: Array<{
        id: number
        period_key: string
        kind: string
        status: string
        notes: string
        closed_at: string | null
      }>
    }>('/fiscal/periods', undefined, { token, orgId }),
  closeFiscalPeriod: (
    payload: { period_key: string; kind: string; notes?: string },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{
      period: {
        id: number
        period_key: string
        kind: string
        status: string
        notes: string
        closed_at: string | null
      }
    }>(
      '/fiscal/periods/close',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  reopenFiscalPeriod: (
    periodId: number,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean }>(
      `/fiscal/periods/${periodId}/reopen`,
      { method: 'POST' },
      { token, orgId },
    ),
  getElfisReport: (id: number, token: string, orgId?: number | null) =>
    request<{ report: import('./elfisTypes').ElfisReport; history: import('./elfisTypes').ElfisAnalysisHistoryItem[] }>(
      `/elfis-ai/documents/${id}/report`,
      undefined,
      { token, orgId },
    ),
  reanalyzeElfis: (id: number, token: string, orgId?: number | null) =>
    request<{ report: import('./elfisTypes').ElfisReport }>(
      `/elfis-ai/documents/${id}/reanalyze`,
      { method: 'POST' },
      { token, orgId },
    ),
  exportElfisJson: (id: number, token: string, orgId?: number | null) =>
    downloadApiFile(`/elfis-ai/documents/${id}/export.json`, token, orgId),
  getIntelligence: (period: string, token: string, orgId?: number | null) =>
    request<import('./elfisTypes').IntelligenceOverview>(
      `/elfis-ai/intelligence?period=${encodeURIComponent(period)}`,
      undefined,
      { token, orgId },
    ),
  elfisChat: (question: string, token: string, orgId?: number | null) =>
    request<{
      ok: boolean
      answer: string
      citations: string[]
      status: string
    }>(
      '/elfis-ai/chat',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      },
      { token, orgId },
    ),
  deleteDocument: (id: number, token: string, orgId?: number | null) =>
    request<{ ok: boolean }>(`/documents/${id}`, { method: 'DELETE' }, { token, orgId }),
  getSettings: (token: string, orgId?: number | null) =>
    request<CompanySettings>('/settings', undefined, { token, orgId }),
  saveSettings: (
    payload: Omit<CompanySettings, 'id'>,
    token: string,
    orgId?: number | null,
  ) =>
    request<CompanySettings>('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  fileUrl: (id: number) => `${apiRoot()}/documents/${id}/file`,
  documentFile: (id: number, token: string, orgId?: number | null) =>
    requestBlob(`/documents/${id}/file`, token, orgId),
  exportExcelUrl: (id: number) => `${apiRoot()}/exports/${id}/excel`,
  exportPdfUrl: (id: number) => `${apiRoot()}/exports/${id}/pdf`,
  exportSoftwareUrl: (id: number, target: string) => `${apiRoot()}/exports/${id}/${target}`,
  historyExcelUrl: () => `${apiRoot()}/exports/history/excel`,
  historySoftwareUrl: (target: string) => `${apiRoot()}/exports/history/${target}`,
  exportFormats: () =>
    request<{ formats: { id: string; label: string; ext: string }[] }>('/exports/formats'),
  listModules: () =>
    request<{ product: string; vision: string; modules: ModuleInfo[] }>('/modules'),
  firebaseSession: (payload: {
    id_token: string
    first_name?: string
    last_name?: string
    organization_name?: string
  }) =>
    request<{ access_token: string; user: AuthUser; memberships: Membership[] }>('/auth/firebase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  register: (payload: {
    first_name: string
    last_name: string
    email: string
    password: string
    organization_name?: string
  }) =>
    request<{ access_token: string; user: AuthUser; memberships: Membership[] }>('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  me: (token: string, orgId?: number | null) =>
    request<{
      user: AuthUser
      memberships: Membership[]
      current_organization_id: number | null
      role: string | null
      permissions: string[]
      pending_invitations: OrgInvitation[]
      unread_notifications: number
      role_labels: Record<string, string>
    }>('/auth/me', undefined, { token, orgId }),
  myInvitations: (token: string, orgId?: number | null) =>
    request<{ invitations: OrgInvitation[] }>('/auth/invitations', undefined, { token, orgId }),
  acceptInvitation: (
    payload: { token?: string; invitation_id?: number },
    token: string,
    orgId?: number | null,
  ) =>
    request<{
      ok: boolean
      organization_id: number
      memberships: Membership[]
      pending_invitations: OrgInvitation[]
    }>('/auth/invitations/accept', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  refuseInvitation: (
    payload: { token?: string; invitation_id?: number },
    token: string,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; pending_invitations: OrgInvitation[] }>('/auth/invitations/refuse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  leaveOrganization: (organizationId: number, token: string, orgId?: number | null) =>
    request<{ ok: boolean; memberships: Membership[] }>(
      `/auth/organizations/${organizationId}/leave`,
      { method: 'POST' },
      { token, orgId },
    ),
  setActiveOrganization: (organizationId: number, token: string, orgId?: number | null) =>
    request<{
      ok: boolean
      access_token: string
      organization_id: number
      role: string
      permissions: string[]
      memberships: Membership[]
    }>('/auth/active-organization', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ organization_id: organizationId }),
    }, { token, orgId }),
  myNotifications: (token: string, orgId?: number | null) =>
    request<{ notifications: TeamNotificationItem[] }>('/auth/notifications', undefined, {
      token,
      orgId,
    }),
  markNotificationRead: (notificationId: number, token: string, orgId?: number | null) =>
    request<{ ok: boolean; notification: TeamNotificationItem }>(
      `/auth/notifications/${notificationId}/read`,
      { method: 'POST' },
      { token, orgId },
    ),
  planCatalog: () =>
    request<{
      features: Record<string, string[]>
      seat_limits: Record<string, number>
      role_labels: Record<string, string>
    }>('/auth/plan-catalog'),
  updateProfile: (
    payload: { first_name?: string; last_name?: string; phone?: string; avatar?: string },
    token: string,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; user: AuthUser }>('/auth/me', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  uploadAvatar: async (file: File, token: string, orgId?: number | null) => {
    const form = new FormData()
    form.append('file', file)
    return request<{ ok: boolean; user: AuthUser }>(
      '/auth/me/avatar',
      { method: 'POST', body: form },
      { token, orgId },
    )
  },
  aiChat: (question: string, token?: string | null, orgId?: number | null) =>
    request<{
      ok: boolean
      answer: string
      agent: string
      conversation_id: number | null
      snapshot: { ca: number; marge_pct: number; balance: number; unpaid: number }
    }>('/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }, { token, orgId }),
  aiSuggestions: (token?: string | null, orgId?: number | null) =>
    request<{ agent: string; suggestions: string[] }>(
      '/ai/suggestions',
      undefined,
      { token, orgId },
    ),
  aiConversations: (token: string, orgId?: number | null) =>
    request<{ conversations: { id: number; question: string; answer: string; created_at: string | null }[] }>(
      '/ai/conversations',
      undefined,
      { token, orgId },
    ),
  billingOverview: (
    token?: string | null,
    orgId?: number | null,
    params?: { doc_type?: string; q?: string; status?: string },
  ) => {
    const search = new URLSearchParams()
    if (params?.doc_type) search.set('doc_type', params.doc_type)
    if (params?.q) search.set('q', params.q)
    if (params?.status) search.set('status', params.status)
    const qs = search.toString()
    return request<BillingOverview>(`/billing/sales-overview${qs ? `?${qs}` : ''}`, undefined, {
      token,
      orgId,
    })
  },
  /** Billing System V2 — Entitlement Engine (abonnements / quotas). */
  saasBillingOverview: (token?: string | null, orgId?: number | null) =>
    request<{
      overview: Record<string, unknown>
      plans: Array<Record<string, unknown>>
      history_preview: Array<Record<string, unknown>>
    }>('/billing/overview', undefined, { token, orgId }),
  saasBillingPlans: (token?: string | null, orgId?: number | null) =>
    request<{ plans: Array<Record<string, unknown>> }>('/billing/plans', undefined, {
      token,
      orgId,
    }),
  saasBillingSubscription: (token?: string | null, orgId?: number | null) =>
    request<Record<string, unknown>>('/billing/subscription', undefined, { token, orgId }),
  saasBillingUsage: (token?: string | null, orgId?: number | null) =>
    request<{ usage: unknown }>('/billing/usage', undefined, { token, orgId }),
  saasBillingQuotas: (token?: string | null, orgId?: number | null) =>
    request<{ quotas: Record<string, unknown> }>('/billing/quotas', undefined, { token, orgId }),
  saasBillingHistory: (token?: string | null, orgId?: number | null) =>
    request<{ events: Array<Record<string, unknown>> }>('/billing/history', undefined, {
      token,
      orgId,
    }),
  saasBillingCheckout: (
    payload: {
      plan_code?: string
      automatic_renewal_accepted: boolean
      terms_accepted: boolean
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{ url: string }>('/billing/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  saasBillingPortal: (token?: string | null, orgId?: number | null) =>
    request<{ url: string }>('/billing/customer-portal', { method: 'POST' }, { token, orgId }),
  platformBillingOverview: (token: string) =>
    request<{
      mrr_eur: number
      arr_eur: number
      subscriptions: Record<string, number>
      subscriptions_total: number
      churn_cancelled_ratio_pct: number
      past_due: number
      trials: number
      note?: string
      source?: string
      generated_at?: string
    }>('/platform/billing/overview', undefined, { token }),
  platformBillingSubscriptionsList: (
    token: string,
    params?: { status?: string; limit?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.limit) q.set('limit', String(params.limit))
    const qs = q.toString()
    return request<{ subscriptions: Array<Record<string, unknown>> }>(
      `/platform/billing/subscriptions${qs ? `?${qs}` : ''}`,
      undefined,
      { token },
    )
  },
  platformBillingSuspend: (subscriptionId: string, token: string) =>
    request<{ ok: boolean; status: string }>(
      `/platform/billing/subscriptions/${subscriptionId}/suspend`,
      { method: 'POST' },
      { token },
    ),
  platformBillingRestore: (subscriptionId: string, token: string) =>
    request<{ ok: boolean; status: string }>(
      `/platform/billing/subscriptions/${subscriptionId}/restore`,
      { method: 'POST' },
      { token },
    ),
  listCustomers: (token?: string | null, orgId?: number | null, q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : ''
    return request<{ customers: CustomerRecord[] }>(`/billing/customers${qs}`, undefined, {
      token,
      orgId,
    })
  },
  listSharedRelations: (
    token: string,
    orgId?: number | null,
    params?: {
      q?: string
      role?: string
      source?: string
      status?: string
      page?: number
      page_size?: number
    },
  ) => {
    const sp = new URLSearchParams()
    if (params?.q) sp.set('q', params.q)
    if (params?.role) sp.set('role', params.role)
    if (params?.source) sp.set('source', params.source)
    if (params?.status) sp.set('status', params.status)
    if (params?.page) sp.set('page', String(params.page))
    if (params?.page_size) sp.set('page_size', String(params.page_size))
    const qs = sp.toString()
    return request<SharedRelationListResponse>(
      `/shared/relations${qs ? `?${qs}` : ''}`,
      undefined,
      { token, orgId },
    )
  },
  searchSharedRelations: (
    token: string,
    orgId: number | null | undefined,
    q: string,
    page = 1,
    pageSize = 20,
  ) =>
    request<SharedRelationListResponse>(
      `/shared/relations/search?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`,
      undefined,
      { token, orgId },
    ),
  getSharedRelation: (token: string, orgId: number | null | undefined, relationId: string) =>
    request<SharedRelationDetailResponse>(
      `/shared/relations/${encodeURIComponent(relationId)}`,
      undefined,
      { token, orgId },
    ),
  listSharedRelationDuplicates: (
    token: string,
    orgId?: number | null,
    relationId?: string,
  ) => {
    const qs = relationId ? `?relation_id=${encodeURIComponent(relationId)}` : ''
    return request<{
      items: SharedRelationDuplicate[]
      auto_merge: boolean
      note?: string
    }>(`/shared/relations/duplicates${qs}`, undefined, { token, orgId })
  },
  createCustomer: (
    payload: {
      name: string
      email?: string
      phone?: string
      address?: string
      vat_number?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<CustomerRecord>('/billing/customers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  getCustomer: (id: number, token?: string | null, orgId?: number | null) =>
    request<CustomerRecord>(`/billing/customers/${id}`, undefined, { token, orgId }),
  updateCustomer: (
    id: number,
    payload: Partial<{
      name: string
      email: string
      phone: string
      address: string
      vat_number: string
    }>,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<CustomerRecord>(`/billing/customers/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  deleteCustomer: (id: number, token?: string | null, orgId?: number | null) =>
    request<{ ok: boolean }>(`/billing/customers/${id}`, { method: 'DELETE' }, { token, orgId }),
  listCatalog: (token?: string | null, orgId?: number | null, activeOnly?: boolean) => {
    const qs = activeOnly ? '?active_only=true' : ''
    return request<{ items: CatalogItem[] }>(`/billing/catalog${qs}`, undefined, { token, orgId })
  },
  createCatalogItem: (
    payload: {
      name: string
      kind?: string
      unit?: string
      unit_price_ht?: number
      vat_rate?: number
      active?: boolean
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<CatalogItem>('/billing/catalog', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  updateCatalogItem: (
    id: number,
    payload: Partial<{
      name: string
      kind: string
      unit: string
      unit_price_ht: number
      vat_rate: number
      active: boolean
    }>,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<CatalogItem>(`/billing/catalog/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  deleteCatalogItem: (id: number, token?: string | null, orgId?: number | null) =>
    request<{ ok: boolean }>(`/billing/catalog/${id}`, { method: 'DELETE' }, { token, orgId }),
  listActivities: (
    token?: string | null,
    orgId?: number | null,
    params?: { status?: string; kind?: string },
  ) => {
    const search = new URLSearchParams()
    if (params?.status) search.set('status', params.status)
    if (params?.kind) search.set('kind', params.kind)
    const qs = search.toString()
    return request<{ activities: CommercialActivity[] }>(
      `/billing/activities${qs ? `?${qs}` : ''}`,
      undefined,
      { token, orgId },
    )
  },
  createActivity: (
    payload: {
      title: string
      kind?: string
      customer_id?: number | null
      scheduled_at?: string | null
      status?: string
      notes?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<CommercialActivity>('/billing/activities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  updateActivity: (
    id: number,
    payload: Partial<{
      title: string
      kind: string
      customer_id: number | null
      scheduled_at: string | null
      status: string
      notes: string
    }>,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<CommercialActivity>(`/billing/activities/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  deleteActivity: (id: number, token?: string | null, orgId?: number | null) =>
    request<{ ok: boolean }>(`/billing/activities/${id}`, { method: 'DELETE' }, { token, orgId }),
  createSalesDoc: (
    payload: {
      doc_type: string
      customer_name: string
      customer_email?: string
      customer_id?: number | null
      amount_ht: number
      vat_rate?: number
      notes?: string
      due_days?: number
      branding?: { showLogo?: boolean; template?: string }
      lines?: Array<{
        label: string
        quantity: number
        unit_price: number
        catalog_item_id?: number | null
      }>
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<SalesDoc>('/billing/documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  getSalesDoc: (docId: number, token?: string | null, orgId?: number | null) =>
    request<{ document: SalesDoc; email_logs: DocumentEmailLog[] }>(
      `/billing/documents/${docId}`,
      undefined,
      { token, orgId },
    ),
  updateSalesDoc: (
    docId: number,
    payload: {
      customer_name?: string
      customer_email?: string
      customer_id?: number | null
      amount_ht?: number
      vat_rate?: number
      notes?: string
      due_days?: number
      branding?: { showLogo?: boolean; template?: string }
      lines?: Array<{
        label: string
        quantity: number
        unit_price: number
        catalog_item_id?: number | null
      }>
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<SalesDoc>(`/billing/documents/${docId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  deleteSalesDoc: (docId: number, token?: string | null, orgId?: number | null) =>
    request<{ ok: boolean }>(`/billing/documents/${docId}`, { method: 'DELETE' }, { token, orgId }),
  salesDocPdfUrl: (docId: number) => `${apiRoot()}/billing/documents/${docId}/pdf`,
  downloadSalesDocPdf: (
    docId: number,
    token: string,
    orgId?: number | null,
    preferredFilename?: string,
  ) => downloadApiFile(`/billing/documents/${docId}/pdf`, token, orgId, preferredFilename),
  openSalesDocPdfBlob: async (docId: number, token: string, orgId?: number | null) => {
    const { blob } = await requestBlob(`/billing/documents/${docId}/pdf`, token, orgId)
    return URL.createObjectURL(blob)
  },
  emailSalesDoc: (
    docId: number,
    payload: {
      recipient?: string
      message?: string
      subject?: string
      cc?: string
      bcc?: string
      is_test?: boolean
      idempotency_key?: string
      connection_id?: number | null
      send_mode?: 'mailto' | 'server' | string
      sender_acknowledged?: boolean
      preferred_from_email?: string
      preferred_from_label?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{
      document: SalesDoc
      email_log: DocumentEmailLog | null
      smtp_configured: boolean
      email_configured?: boolean
      send_mode?: string
      sender_email?: string
      can_send_direct?: boolean
      mailer_provider?: string
      mailer_reason_code?: string
      mailer_sender_configured?: boolean
      status?: string
      business_document_id?: string
      business_document_type?: string
      vault_document_id?: string | null
      vault_archive_status?: string | null
      email_status?: string
      recipient?: string
      sent_at?: string | null
      reused_existing_archive?: boolean
      already_processed?: boolean
      message?: string
    }>(
      `/billing/documents/${docId}/email`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  salesDocEmails: (docId: number, token?: string | null, orgId?: number | null) =>
    request<{
      email_logs: DocumentEmailLog[]
      smtp_configured?: boolean
      email_configured?: boolean
      preview?: EmailSendPreview
      connections?: EmailConnection[]
      default_connection_id?: number | null
      can_send_direct?: boolean
      mailer_provider?: string
      mailer_reason_code?: string
      mailer_sender_configured?: boolean
    }>(`/billing/documents/${docId}/emails`, undefined, { token, orgId }),
  listEmailConnections: (token?: string | null, orgId?: number | null) =>
    request<{
      connections: EmailConnection[]
      sendable: EmailConnection[]
      platform_configured: boolean
      google_oauth_configured: boolean
      microsoft_oauth_configured: boolean
      can_manage: boolean
    }>('/email-connections', undefined, { token, orgId }),
  activatePlatformEmail: (token?: string | null, orgId?: number | null) =>
    request<{ connection: EmailConnection }>(
      '/email-connections/platform/activate',
      { method: 'POST' },
      { token, orgId },
    ),
  startGoogleEmailOAuth: (token?: string | null, orgId?: number | null, connectionId?: number) =>
    request<{ redirect_url: string; provider: string }>(
      `/email-connections/google/start${connectionId ? `?connection_id=${connectionId}` : ''}`,
      { method: 'POST' },
      { token, orgId },
    ),
  startMicrosoftEmailOAuth: (token?: string | null, orgId?: number | null, connectionId?: number) =>
    request<{ redirect_url: string; provider: string }>(
      `/email-connections/microsoft/start${connectionId ? `?connection_id=${connectionId}` : ''}`,
      { method: 'POST' },
      { token, orgId },
    ),
  upsertCustomSmtp: (
    payload: {
      email_address: string
      display_name?: string
      smtp_host: string
      smtp_port?: number
      smtp_username?: string
      smtp_password?: string | null
      smtp_security?: string
      connection_id?: number | null
      make_default?: boolean
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{ connection: EmailConnection }>(
      '/email-connections/custom-smtp',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  testCustomSmtp: (
    payload: {
      email_address: string
      smtp_host: string
      smtp_port?: number
      smtp_username?: string
      smtp_password?: string
      smtp_security?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{ ok: boolean; message: string }>(
      '/email-connections/custom-smtp/test',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId },
    ),
  setDefaultEmailConnection: (connectionId: number, token?: string | null, orgId?: number | null) =>
    request<{ connection: EmailConnection }>(
      `/email-connections/${connectionId}/set-default`,
      { method: 'POST' },
      { token, orgId },
    ),
  disconnectEmailConnection: (connectionId: number, token?: string | null, orgId?: number | null) =>
    request<{ connection: EmailConnection }>(
      `/email-connections/${connectionId}/disconnect`,
      { method: 'POST' },
      { token, orgId },
    ),
  reconnectEmailConnection: (connectionId: number, token?: string | null, orgId?: number | null) =>
    request<{ redirect_url?: string; provider?: string; connection?: EmailConnection }>(
      `/email-connections/${connectionId}/reconnect`,
      { method: 'POST' },
      { token, orgId },
    ),
  testEmailConnection: (
    connectionId: number,
    toEmail: string,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{
      ok: boolean
      provider: string
      sender_email: string
      sender_name: string
      provider_message_id: string
    }>(
      `/email-connections/${connectionId}/test`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_email: toEmail }),
      },
      { token, orgId },
    ),
  getOrgEmailSettings: (token?: string | null, orgId?: number | null) =>
    request<OrgEmailSettings>('/org/email-settings', undefined, { token, orgId }),
  updateOrgEmailSettings: (
    payload: Partial<OrgEmailSettingsUpdate>,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<OrgEmailSettings>('/org/email-settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  testOrgEmailSettings: (token?: string | null, orgId?: number | null) =>
    request<{
      ok: boolean
      status: string
      recipient: string
      subject: string
      sender_name: string
      sender_email: string
      reply_to_email: string
      error_message: string
    }>('/org/email-settings/test', { method: 'POST' }, { token, orgId }),
  billingAction: (docId: number, action: string, token?: string | null, orgId?: number | null, body?: object) =>
    request<unknown>(`/billing/documents/${docId}/${action}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }, { token, orgId }),
  orgDetail: (organizationId: number, token?: string | null) =>
    request<OrgDetail>(`/org/${organizationId}`, undefined, { token, orgId: organizationId }),
  updateOrganization: (
    organizationId: number,
    payload: Partial<{
      name: string
      legal_name: string
      siren: string
      vat_number: string
      address: string
      postal_code: string
      city: string
      phone: string
      email: string
      website: string
      iban: string
      bic: string
      share_capital: string
      legal_form: string
      legal_mentions: string
      logo: string
      industry: string
      country: string
      currency: string
      primary_color: string
      secondary_color: string
      documents_show_logo: boolean | null
    }>,
    token: string,
  ) =>
    request<{ organization: OrgDetail['organization'] }>(
      `/org/${organizationId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId: organizationId },
    ),
  uploadOrganizationLogo: (organizationId: number, file: File, token: string) => {
    const body = new FormData()
    body.append('file', file)
    return request<{ ok: boolean; organization: OrgDetail['organization'] }>(
      `/org/${organizationId}/logo`,
      { method: 'POST', body },
      { token, orgId: organizationId },
    )
  },
  deleteOrganizationLogo: (organizationId: number, token: string) =>
    request<{ ok: boolean; organization: OrgDetail['organization'] }>(
      `/org/${organizationId}/logo`,
      { method: 'DELETE' },
      { token, orgId: organizationId },
    ),
  orgMembers: (organizationId: number, token: string) =>
    request<{
      members: OrgMember[]
      can_manage: boolean
      roles: string[]
      role_labels?: Record<string, string>
      plan?: string
      subscription_status?: string
      seats?: { active: number; pending_invites: number; used: number }
      can_invite?: boolean
      seat_limit_message?: string
    }>(`/org/${organizationId}/members`, undefined, { token, orgId: organizationId }),
  inviteOrgMember: (
    organizationId: number,
    payload: { email: string; role: string },
    token: string,
  ) =>
    request<{
      ok: boolean
      invitation: OrgInvitation
      invite_token: string
      email_warning: string | null
      message: string
    }>(`/org/${organizationId}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId: organizationId }),
  orgInvitations: (organizationId: number, token: string) =>
    request<{ invitations: OrgInvitation[] }>(`/org/${organizationId}/invitations`, undefined, {
      token,
      orgId: organizationId,
    }),
  resendOrgInvitation: (organizationId: number, invitationId: number, token: string) =>
    request<{
      ok: boolean
      invitation: OrgInvitation
      invite_token: string
      email_warning: string | null
    }>(`/org/${organizationId}/invitations/${invitationId}/resend`, { method: 'POST' }, {
      token,
      orgId: organizationId,
    }),
  cancelOrgInvitation: (organizationId: number, invitationId: number, token: string) =>
    request<{ ok: boolean }>(`/org/${organizationId}/invitations/${invitationId}`, {
      method: 'DELETE',
    }, { token, orgId: organizationId }),
  updateOrgMember: (
    organizationId: number,
    membershipId: number,
    payload: { role?: string; status?: string },
    token: string,
  ) =>
    request<{ ok: boolean; member: OrgMember }>(
      `/org/${organizationId}/members/${membershipId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId: organizationId },
    ),
  deleteOrgMember: (organizationId: number, membershipId: number, token: string) =>
    request<{ ok: boolean; uid: string; email: string }>(
      `/org/${organizationId}/members/${membershipId}`,
      { method: 'DELETE' },
      { token, orgId: organizationId },
    ),
  currentSubscription: async (token: string, orgId?: number | null) => {
    const result = await request<{ subscription: SubscriptionInfo }>(
      '/subscriptions/current',
      undefined,
      { token, orgId },
    )
    return result.subscription
  },
  createSubscriptionCheckout: (
    token: string,
    orgId?: number | null,
    consents?: { automatic_renewal_accepted: boolean; terms_accepted: boolean },
  ) =>
    request<{ url: string; session_id?: string }>(
      '/subscriptions/checkout',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          consents || { automatic_renewal_accepted: false, terms_accepted: false },
        ),
      },
      { token, orgId },
    ),
  subscriptionPlan: () =>
    request<{
      plan_code: string
      name: string
      price_amount_cents: number
      currency: string
      trial_days: number
      feature_labels: string[]
      terms_version: string
    }>('/subscriptions/plan'),
  createSubscriptionPortal: (token: string, orgId?: number | null) =>
    request<{ url: string }>('/subscriptions/portal', { method: 'POST' }, { token, orgId }),
  syncSubscription: (token: string, orgId?: number | null, sessionId?: string | null) =>
    request<{ subscription: SubscriptionInfo }>(
      '/subscriptions/sync',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId || null }),
      },
      { token, orgId },
    ).then((result) => result.subscription),
  /** Disponibilité backend de l’essai local (GET /api/dev/trial-status). */
  getDevTrialStatus: async (token: string, orgId?: number | null) => {
    const headers = new Headers({ Authorization: `Bearer ${token}` })
    if (orgId != null) headers.set('X-Organization-Id', String(orgId))
    const res = await fetch(`${apiRoot()}/dev/trial-status`, {
      method: 'GET',
      headers,
    })
    if (!res.ok) {
      const err = new Error('DEV_TRIAL_STATUS_FAILED') as Error & {
        status: number
        code: string
        requestId?: string | null
      }
      err.status = res.status
      err.code = 'DEV_TRIAL_STATUS_FAILED'
      err.requestId =
        res.headers.get('x-request-id') || res.headers.get('x-correlation-id')
      throw err
    }
    return res.json() as Promise<{
      allowed: boolean
      environment: string
      flag_enabled: boolean
      reason: string | null
      already_active: boolean
    }>
  },
  /** Développement uniquement (backend: ELFIS_DEV_TRIAL_ENABLED). */
  /** C1.11 — démarrer / reprendre le provisioning workspace. */
  provisionWorkspace: (
    token: string,
    orgId: number | null | undefined,
    draft: {
      company_name: string
      industry: string
      industry_other?: string | null
      country: string
      currency: string
      vat_status: string
      vat_number?: string | null
    },
  ) =>
    request<WorkspaceProvisionStatus>('/workspace/provision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: draft.company_name,
        industry: draft.industry,
        industry_other: draft.industry_other ?? null,
        country: draft.country,
        currency: draft.currency,
        vat_status: draft.vat_status,
        vat_number: draft.vat_number ?? null,
      }),
    }, { token, orgId }),
  getWorkspaceProvisionStatus: (token: string, orgId?: number | null) =>
    request<WorkspaceProvisionStatus>('/workspace/provision/status', undefined, {
      token,
      orgId,
    }),
  getLaunchDashboard: (token: string, orgId?: number | null) =>
    request<import('./launchDashboard').LaunchDashboardData>('/dashboard/launch', undefined, {
      token,
      orgId,
    }),
  getCommandCenter: (token: string, orgId?: number | null) =>
    request<import('./commandCenter').CommandCenterData>('/dashboard/command-center', undefined, {
      token,
      orgId,
    }),
  getSalesDashboard: (token: string, orgId?: number | null) =>
    request<import('./sales/salesDashboard').SalesDashboardData>('/sales/dashboard', undefined, {
      token,
      orgId,
    }),
  listSalesLeads: (token: string, orgId?: number | null, params?: { page?: number; q?: string }) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set('page', String(params.page))
    if (params?.q) qs.set('q', params.q)
    const s = qs.toString() ? `?${qs}` : ''
    return request<import('./sales/salesOps').SalesListResponse<import('./sales/salesOps').SalesLead>>(
      `/sales/leads${s}`,
      undefined,
      { token, orgId },
    )
  },
  createSalesLead: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<import('./sales/salesOps').SalesLead>('/sales/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  updateSalesLead: (
    token: string,
    orgId: number | null | undefined,
    id: number,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesLead>(`/sales/leads/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  deleteSalesLead: (token: string, orgId: number | null | undefined, id: number) =>
    request<void>(`/sales/leads/${id}`, { method: 'DELETE' }, { token, orgId }),
  listSalesCompanies: (
    token: string,
    orgId?: number | null,
    params?: { page?: number; q?: string },
  ) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set('page', String(params.page))
    if (params?.q) qs.set('q', params.q)
    const s = qs.toString() ? `?${qs}` : ''
    return request<
      import('./sales/salesOps').SalesListResponse<import('./sales/salesOps').SalesCompany>
    >(`/sales/companies${s}`, undefined, { token, orgId })
  },
  createSalesCompany: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesCompany>('/sales/companies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  updateSalesCompany: (
    token: string,
    orgId: number | null | undefined,
    id: number,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesCompany>(`/sales/companies/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  deleteSalesCompany: (token: string, orgId: number | null | undefined, id: number) =>
    request<void>(`/sales/companies/${id}`, { method: 'DELETE' }, { token, orgId }),
  listSalesPeople: (token: string, orgId?: number | null, params?: { page?: number; q?: string }) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set('page', String(params.page))
    if (params?.q) qs.set('q', params.q)
    const s = qs.toString() ? `?${qs}` : ''
    return request<
      import('./sales/salesOps').SalesListResponse<import('./sales/salesOps').SalesPerson>
    >(`/sales/people${s}`, undefined, { token, orgId })
  },
  createSalesPerson: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesPerson>('/sales/people', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  updateSalesPerson: (
    token: string,
    orgId: number | null | undefined,
    id: number,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesPerson>(`/sales/people/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  deleteSalesPerson: (token: string, orgId: number | null | undefined, id: number) =>
    request<void>(`/sales/people/${id}`, { method: 'DELETE' }, { token, orgId }),
  createSalesOpportunity: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<{ id: number; name: string }>('/sales/opportunities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  listSalesTasks: (token: string, orgId?: number | null, params?: { page?: number; q?: string; status?: string }) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set('page', String(params.page))
    if (params?.q) qs.set('q', params.q)
    if (params?.status) qs.set('status', params.status)
    const s = qs.toString() ? `?${qs}` : ''
    return request<
      import('./sales/salesOps').SalesListResponse<import('./sales/salesOps').SalesTaskRow>
    >(`/sales/tasks${s}`, undefined, { token, orgId })
  },
  createSalesTask: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<import('./sales/salesOps').SalesTaskRow>('/sales/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  updateSalesTask: (
    token: string,
    orgId: number | null | undefined,
    id: number,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesTaskRow>(`/sales/tasks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  deleteSalesTask: (token: string, orgId: number | null | undefined, id: number) =>
    request<void>(`/sales/tasks/${id}`, { method: 'DELETE' }, { token, orgId }),
  listSalesActivities: (
    token: string,
    orgId?: number | null,
    params?: { page?: number; q?: string },
  ) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.set('page', String(params.page))
    if (params?.q) qs.set('q', params.q)
    const s = qs.toString() ? `?${qs}` : ''
    return request<
      import('./sales/salesOps').SalesListResponse<import('./sales/salesOps').SalesActivityRow>
    >(`/sales/activities${s}`, undefined, { token, orgId })
  },
  createSalesActivity: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesOps').SalesActivityRow>('/sales/activities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  createSalesNote: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<{ id: number }>('/sales/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  updateSalesNote: (
    token: string,
    orgId: number | null | undefined,
    id: number,
    body: Record<string, unknown>,
  ) =>
    request<{ id: number }>(`/sales/notes/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  getSalesCalendar: (
    token: string,
    orgId: number | null | undefined,
    fromDate: string,
    toDate: string,
  ) =>
    request<{ events: import('./sales/salesOps').CalendarEvent[]; from_date: string; to_date: string }>(
      `/sales/ops/calendar?from_date=${fromDate}&to_date=${toDate}`,
      undefined,
      { token, orgId },
    ),
  previewSalesImport: (
    token: string,
    orgId: number | null | undefined,
    body: { resource: string; csv_text: string; delimiter?: string },
  ) =>
    request<Record<string, unknown>>('/sales/ops/import/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  commitSalesImport: (
    token: string,
    orgId: number | null | undefined,
    body: { resource: string; rows: Record<string, unknown>[]; skip_duplicates?: boolean },
  ) =>
    request<{ created: number; skipped: number; errors: string[] }>('/sales/ops/import/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  scanSalesDuplicates: (token: string, orgId: number | null | undefined, resource: string) =>
    request<Record<string, unknown>>(`/sales/ops/duplicates/${resource}`, undefined, { token, orgId }),
  resolveSalesDuplicate: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<Record<string, unknown>>('/sales/ops/duplicates/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  bulkSalesAction: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<{ updated: number; skipped: number; errors: string[] }>('/sales/ops/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  getSalesJournal: (token: string, orgId?: number | null, limit = 50) =>
    request<{ items: import('./sales/salesOps').JournalItem[]; generated_at: string }>(
      `/sales/ops/journal?limit=${limit}`,
      undefined,
      { token, orgId },
    ),
  listSalesSavedViews: (token: string, orgId?: number | null, resource?: string) => {
    const qs = resource ? `?resource=${resource}` : ''
    return request<Array<Record<string, unknown>>>(`/sales/ops/saved-views${qs}`, undefined, {
      token,
      orgId,
    })
  },
  createSalesSavedView: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<Record<string, unknown>>('/sales/ops/saved-views', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  updateSalesSavedView: (
    token: string,
    orgId: number | null | undefined,
    id: number,
    body: Record<string, unknown>,
  ) =>
    request<Record<string, unknown>>(`/sales/ops/saved-views/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  deleteSalesSavedView: (token: string, orgId: number | null | undefined, id: number) =>
    request<void>(`/sales/ops/saved-views/${id}`, { method: 'DELETE' }, { token, orgId }),

  // Sales Collaboration S1.9
  listSalesTeams: (token: string, orgId?: number | null) =>
    request<import('./sales/salesCollab').SalesTeam[]>(`/sales/collab/teams`, undefined, { token, orgId }),
  createSalesTeam: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<import('./sales/salesCollab').SalesTeam>('/sales/collab/teams', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  addSalesTeamMember: (
    token: string,
    orgId: number | null | undefined,
    teamId: number,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesCollab').SalesTeamMember>(`/sales/collab/teams/${teamId}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  getSalesTeamDashboard: (token: string, orgId?: number | null, teamId?: number | null) => {
    const qs = teamId != null ? `?team_id=${teamId}` : ''
    return request<import('./sales/salesCollab').TeamDashboard>(
      `/sales/collab/team-dashboard${qs}`,
      undefined,
      { token, orgId },
    )
  },
  assignSalesResource: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<Record<string, unknown>>('/sales/collab/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  transferSalesOwnership: (
    token: string,
    orgId: number | null | undefined,
    body: Record<string, unknown>,
  ) =>
    request<Record<string, unknown>>('/sales/collab/transfer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  listSalesComments: (
    token: string,
    orgId: number | null | undefined,
    entityType: string,
    entityId: number,
  ) =>
    request<import('./sales/salesCollab').SalesComment[]>(
      `/sales/collab/comments?entity_type=${entityType}&entity_id=${entityId}`,
      undefined,
      { token, orgId },
    ),
  createSalesComment: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<import('./sales/salesCollab').SalesComment>('/sales/collab/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  deleteSalesComment: (token: string, orgId: number | null | undefined, id: number) =>
    request<void>(`/sales/collab/comments/${id}`, { method: 'DELETE' }, { token, orgId }),
  listSalesMentionCandidates: (token: string, orgId?: number | null, q = '') =>
    request<import('./sales/salesCollab').MentionCandidate[]>(
      `/sales/collab/mentions/candidates?q=${encodeURIComponent(q)}`,
      undefined,
      { token, orgId },
    ),
  listSalesFollowers: (
    token: string,
    orgId: number | null | undefined,
    entityType: string,
    entityId: number,
  ) =>
    request<import('./sales/salesCollab').SalesFollower[]>(
      `/sales/collab/followers?entity_type=${entityType}&entity_id=${entityId}`,
      undefined,
      { token, orgId },
    ),
  followSalesResource: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<import('./sales/salesCollab').SalesFollower>('/sales/collab/followers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  unfollowSalesResource: (
    token: string,
    orgId: number | null | undefined,
    entityType: string,
    entityId: number,
  ) =>
    request<void>(
      `/sales/collab/followers?entity_type=${entityType}&entity_id=${entityId}`,
      { method: 'DELETE' },
      { token, orgId },
    ),
  listSalesReviews: (
    token: string,
    orgId?: number | null,
    params?: { status?: string; mine?: boolean },
  ) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.mine) qs.set('mine', 'true')
    const s = qs.toString() ? `?${qs}` : ''
    return request<import('./sales/salesCollab').SalesReview[]>(`/sales/collab/reviews${s}`, undefined, {
      token,
      orgId,
    })
  },
  createSalesReview: (token: string, orgId: number | null | undefined, body: Record<string, unknown>) =>
    request<import('./sales/salesCollab').SalesReview>('/sales/collab/reviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  decideSalesReview: (
    token: string,
    orgId: number | null | undefined,
    reviewId: number,
    body: Record<string, unknown>,
  ) =>
    request<import('./sales/salesCollab').SalesReview>(`/sales/collab/reviews/${reviewId}/decide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  getSalesCollabView: (
    token: string,
    orgId: number | null | undefined,
    params: { view: string; resource: string; team_id?: number; page?: number },
  ) => {
    const qs = new URLSearchParams()
    qs.set('view', params.view)
    qs.set('resource', params.resource)
    if (params.team_id != null) qs.set('team_id', String(params.team_id))
    if (params.page) qs.set('page', String(params.page))
    return request<{ items: Record<string, unknown>[]; pagination: Record<string, number> }>(
      `/sales/collab/views?${qs}`,
      undefined,
      { token, orgId },
    )
  },

  getSalesIntelligence: (token: string, orgId?: number | null, sync = true) =>
    request<import('./sales/salesIntelligence').IntelligenceOverview>(
      `/sales/intelligence?sync=${sync ? 'true' : 'false'}`,
      undefined,
      { token, orgId },
    ),
  listSalesInsights: (
    token: string,
    orgId?: number | null,
    params?: {
      category?: string
      severity?: string
      status?: string
      source_type?: string
      source_id?: string
      page?: number
      limit?: number
      sort?: string
    },
  ) => {
    const qs = new URLSearchParams()
    if (params?.category) qs.set('category', params.category)
    if (params?.severity) qs.set('severity', params.severity)
    if (params?.status) qs.set('status', params.status)
    if (params?.source_type) qs.set('source_type', params.source_type)
    if (params?.source_id) qs.set('source_id', params.source_id)
    if (params?.page) qs.set('page', String(params.page))
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.sort) qs.set('sort', params.sort)
    const suffix = qs.toString() ? `?${qs}` : ''
    return request<{
      items: import('./sales/salesIntelligence').SalesInsight[]
      total: number
      page: number
      limit: number
    }>(`/sales/intelligence/insights${suffix}`, undefined, { token, orgId })
  },
  getSalesInsight: (token: string, orgId: number | null | undefined, insightId: number) =>
    request<import('./sales/salesIntelligence').SalesInsight>(
      `/sales/intelligence/insights/${insightId}`,
      undefined,
      { token, orgId },
    ),
  acknowledgeSalesInsight: (token: string, orgId: number | null | undefined, insightId: number) =>
    request<import('./sales/salesIntelligence').SalesInsight>(
      `/sales/intelligence/insights/${insightId}/acknowledge`,
      { method: 'POST' },
      { token, orgId },
    ),
  dismissSalesInsight: (
    token: string,
    orgId: number | null | undefined,
    insightId: number,
    reason?: string,
  ) =>
    request<import('./sales/salesIntelligence').SalesInsight>(
      `/sales/intelligence/insights/${insightId}/dismiss`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason || null }),
      },
      { token, orgId },
    ),
  syncSalesIntelligence: (token: string, orgId?: number | null) =>
    request<Record<string, number>>('/sales/intelligence/sync', { method: 'POST' }, { token, orgId }),
  getSalesPipeline: (token: string, orgId?: number | null, pipelineId?: number | null) => {
    const qs = pipelineId != null ? `?pipeline_id=${pipelineId}` : ''
    return request<import('./sales/salesPipeline').PipelineBoard>(`/sales/pipeline${qs}`, undefined, {
      token,
      orgId,
    })
  },
  moveSalesOpportunityStage: (
    token: string,
    orgId: number | null | undefined,
    opportunityId: number,
    body: { stage_id: number; expected_stage_id?: number | null },
  ) =>
    request<import('./sales/salesPipeline').PipelineCard>(
      `/sales/pipeline/opportunities/${opportunityId}/move`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      { token, orgId },
    ),
  getSalesPipelineDrawer: (token: string, orgId: number | null | undefined, opportunityId: number) =>
    request<import('./sales/salesPipeline').PipelineDrawer>(
      `/sales/pipeline/opportunities/${opportunityId}/drawer`,
      undefined,
      { token, orgId },
    ),
  getSalesWorkspace: (
    token: string,
    orgId: number | null | undefined,
    entity: string,
    entityId: number,
  ) =>
    request<import('./sales/salesWorkspace').RelationshipWorkspace>(
      `/sales/workspace/${entity}/${entityId}`,
      undefined,
      { token, orgId },
    ),
  getSalesDealWorkspace: (token: string, orgId: number | null | undefined, opportunityId: number) =>
    request<import('./sales/salesDeal').DealWorkspace>(
      `/sales/opportunities/${opportunityId}/workspace`,
      undefined,
      { token, orgId },
    ),
  addSalesDealProduct: (
    token: string,
    orgId: number | null | undefined,
    opportunityId: number,
    body: {
      name: string
      description?: string | null
      quantity?: string | number
      unit_price?: string | number
      discount_percent?: string | number
      position?: number
    },
  ) =>
    request<import('./sales/salesDeal').DealWorkspace['products'][number]>(
      `/sales/opportunities/${opportunityId}/products`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      { token, orgId },
    ),
  removeSalesDealProduct: (
    token: string,
    orgId: number | null | undefined,
    opportunityId: number,
    productId: number,
  ) =>
    request<void>(`/sales/opportunities/${opportunityId}/products/${productId}`, { method: 'DELETE' }, {
      token,
      orgId,
    }),
  listSalesProposals: (token: string, orgId?: number | null) =>
    request<{ items: import('./sales/salesProposals').ProposalListItem[]; pagination: unknown }>(
      '/sales/proposals',
      undefined,
      { token, orgId },
    ),
  createSalesProposal: (
    token: string,
    orgId: number | null | undefined,
    body: {
      opportunity_id?: number | null
      sales_company_id?: number | null
      person_id?: number | null
      proposal_type?: string
      title?: string
      currency?: string
      seed_from_opportunity_products?: boolean
      amount_source?: 'calculated' | 'final'
    },
  ) =>
    request<import('./sales/salesProposals').ProposalListItem>('/sales/proposals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, { token, orgId }),
  getSalesProposalWorkspace: (token: string, orgId: number | null | undefined, proposalId: number) =>
    request<import('./sales/salesProposals').ProposalWorkspace>(
      `/sales/proposals/${proposalId}/workspace`,
      undefined,
      { token, orgId },
    ),
  runSalesProposalAction: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
    action: string,
    body?: Record<string, unknown>,
  ) =>
    request<import('./sales/salesProposals').ProposalListItem>(
      `/sales/proposals/${proposalId}/${action}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body ?? {}),
      },
      { token, orgId },
    ),
  generateSalesProposalPdf: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
  ) =>
    request<unknown>(`/sales/proposals/${proposalId}/generate-pdf`, { method: 'POST' }, {
      token,
      orgId,
    }),
  prepareSalesProposalConversion: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
  ) =>
    request<Record<string, unknown>>(`/sales/proposals/${proposalId}/prepare-conversion`, {
      method: 'POST',
    }, { token, orgId }),
  getSalesProposalConversionState: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
  ) =>
    request<import('./sales/salesProposals').ProposalConversionState>(
      `/sales/proposals/${proposalId}/conversion-state`,
      undefined,
      { token, orgId },
    ),
  getSalesProposalConversionPreview: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
    customerId?: number | null,
  ) => {
    const qs = customerId != null ? `?customer_id=${customerId}` : ''
    return request<import('./sales/salesProposals').InvoiceConversionPreview>(
      `/sales/proposals/${proposalId}/conversion-preview${qs}`,
      { method: 'POST' },
      { token, orgId },
    )
  },
  resolveSalesProposalConversionCustomer: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
    body: {
      customer_resolution_mode: import('./sales/salesProposals').CustomerResolutionMode
      customer_id?: number | null
      customer_payload?: Record<string, unknown> | null
      confirm_possible_match?: boolean
      force_create?: boolean
    },
  ) =>
    request<{ customer: { id: number; name: string }; created: boolean }>(
      `/sales/proposals/${proposalId}/conversion/customer`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      { token, orgId },
    ),
  convertSalesProposalToInvoice: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
    body: {
      customer_resolution_mode: import('./sales/salesProposals').CustomerResolutionMode
      customer_id?: number | null
      customer_payload?: Record<string, unknown> | null
      accepted_version_id?: number | null
      expected_proposal_updated_at?: string | null
      idempotency_key?: string | null
      confirm_possible_match?: boolean
    },
  ) =>
    request<import('./sales/salesProposals').ConvertToInvoiceResult>(
      `/sales/proposals/${proposalId}/convert-to-invoice`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      { token, orgId },
    ),
  compareSalesProposalVersions: (
    token: string,
    orgId: number | null | undefined,
    proposalId: number,
    fromVersionId: number,
    toVersionId: number,
  ) =>
    request<Record<string, unknown>>(
      `/sales/proposals/${proposalId}/versions/compare?from_version_id=${fromVersionId}&to_version_id=${toVersionId}`,
      undefined,
      { token, orgId },
    ),
  listDecisions: (
    token: string,
    orgId?: number | null,
    params?: { status?: string; severity?: string; page?: number; page_size?: number; sync?: boolean },
  ) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.severity) qs.set('severity', params.severity)
    if (params?.page) qs.set('page', String(params.page))
    if (params?.page_size) qs.set('page_size', String(params.page_size))
    if (params?.sync === false) qs.set('sync', 'false')
    const suffix = qs.toString() ? `?${qs}` : ''
    return request<import('./decisionCenter').DecisionListResponse>(`/decisions${suffix}`, undefined, {
      token,
      orgId,
    })
  },
  getWorkQueue: (
    token: string,
    orgId?: number | null,
    params?: {
      bucket?: string
      severity?: string
      decision_type?: string
      source_type?: string
      search?: string
      sort?: string
      page?: number
      page_size?: number
      sync?: boolean
    },
  ) => {
    const qs = new URLSearchParams()
    if (params?.bucket) qs.set('bucket', params.bucket)
    if (params?.severity) qs.set('severity', params.severity)
    if (params?.decision_type) qs.set('decision_type', params.decision_type)
    if (params?.source_type) qs.set('source_type', params.source_type)
    if (params?.search) qs.set('search', params.search)
    if (params?.sort) qs.set('sort', params.sort)
    if (params?.page) qs.set('page', String(params.page))
    if (params?.page_size) qs.set('page_size', String(params.page_size))
    if (params?.sync) qs.set('sync', 'true')
    const suffix = qs.toString() ? `?${qs}` : ''
    return request<import('./workQueue').WorkQueueResponse>(`/work-queue${suffix}`, undefined, {
      token,
      orgId,
    })
  },
  startDecision: (decisionId: string, token: string, orgId?: number | null) =>
    request<import('./decisionCenter').DecisionDetail>(`/decisions/${decisionId}/start`, { method: 'POST' }, {
      token,
      orgId,
    }),
  reopenDecision: (decisionId: string, token: string, orgId?: number | null) =>
    request<import('./decisionCenter').DecisionDetail>(`/decisions/${decisionId}/reopen`, { method: 'POST' }, {
      token,
      orgId,
    }),
  dismissDecision: (decisionId: string, token: string, orgId?: number | null) =>
    request<{ ok: boolean; decision: import('./decisionCenter').DecisionItem }>(
      `/decisions/${decisionId}/dismiss`,
      { method: 'POST' },
      { token, orgId },
    ),
  getDecision: (
    decisionId: string,
    token: string,
    orgId?: number | null,
    params?: { sync?: boolean },
  ) => {
    const qs = params?.sync === false ? '?sync=false' : ''
    return request<import('./decisionCenter').DecisionDetail>(`/decisions/${decisionId}${qs}`, undefined, {
      token,
      orgId,
    })
  },
  executeDecisionAction: (
    decisionId: string,
    actionType: string,
    token: string,
    orgId?: number | null,
    body?: {
      idempotency_key?: string
      comment?: string
      confirm_balanced_entry?: boolean
      confirm_document_reviewed?: boolean
    },
  ) =>
    request<import('./decisionCenter').DecisionExecuteResponse>(
      `/decisions/${decisionId}/actions/${encodeURIComponent(actionType)}`,
      { method: 'POST', body: JSON.stringify(body || {}) },
      { token, orgId },
    ),
  markAccountingDiscovered: (token: string, orgId?: number | null) =>
    request<{ ok: boolean; accounting_discovery_completed: boolean }>(
      '/dashboard/launch/accounting-discovered',
      { method: 'POST' },
      { token, orgId },
    ),
  activateDevTrial: async (token: string, orgId?: number | null) => {
    const headers = new Headers({ Authorization: `Bearer ${token}` })
    if (orgId != null) headers.set('X-Organization-Id', String(orgId))
    const res = await fetch(`${apiRoot()}/dev/activate-trial`, {
      method: 'POST',
      headers,
    })
    if (!res.ok) {
      const text = await res.text()
      let code = ''
      try {
        const data = JSON.parse(text) as { detail?: { code?: string; message?: string } | string }
        if (typeof data.detail === 'object' && data.detail && 'code' in data.detail) {
          code = String(data.detail.code || '')
        }
      } catch {
        /* ignore */
      }
      const err = new Error(
        code === 'dev_trial_disabled' || code === 'dev_trial_environment_forbidden'
          ? 'DEV_TRIAL_DISABLED'
          : res.status === 401
            ? 'DEV_TRIAL_UNAUTHORIZED'
            : res.status === 404
              ? 'DEV_TRIAL_NOT_FOUND'
              : res.status === 409
                ? 'DEV_TRIAL_CONFLICT'
                : res.status >= 500
                  ? 'DEV_TRIAL_SERVER'
                  : 'DEV_TRIAL_FAILED',
      ) as Error & { status: number; code: string; requestId?: string | null }
      err.status = res.status
      err.code = code || err.message
      err.requestId =
        res.headers.get('x-request-id') || res.headers.get('x-correlation-id')
      throw err
    }
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      return res.json() as Promise<{
        subscription: SubscriptionInfo
        outcome: 'created' | 'already_active'
        environment: string
      }>
    }
    return {
      subscription: null as unknown as SubscriptionInfo,
      outcome: 'created' as const,
      environment: 'development',
    }
  },
  platformOverview: (token: string) =>
    request<PlatformOverview>('/platform/overview', undefined, { token }),
  platformDashboard: (token: string, period: '24h' | '7d' | '30d' = '24h') =>
    request<PlatformDashboard>(`/platform/dashboard?period=${period}`, undefined, { token }),
  platformHealthServices: (token: string) =>
    request<{ checked_at: string; services: PlatformServiceHealth[] }>(
      '/platform/health/services',
      undefined,
      { token },
    ),
  platformOrgOpsDetail: (organizationId: number, token: string) =>
    request<PlatformOrgOpsDetail>(`/platform/organizations/${organizationId}/ops-detail`, undefined, {
      token,
    }),
  platformSuspendOrganization: (organizationId: number, reason: string, token: string) =>
    request<{ ok: boolean; platform_status: string }>(
      `/platform/organizations/${organizationId}/suspend`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      },
      { token },
    ),
  platformRestoreOrganization: (organizationId: number, reason: string, token: string) =>
    request<{ ok: boolean; platform_status: string }>(
      `/platform/organizations/${organizationId}/restore`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      },
      { token },
    ),
  platformIncidents: (token: string, params?: { status?: string; organization_id?: number }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.organization_id) q.set('organization_id', String(params.organization_id))
    const suffix = q.toString() ? `?${q}` : ''
    return request<{ incidents: PlatformIncident[]; total: number }>(
      `/platform/incidents${suffix}`,
      undefined,
      { token },
    )
  },
  platformIncidentAction: (
    incidentId: string,
    action: 'acknowledge' | 'resolve' | 'ignore',
    note: string,
    token: string,
  ) =>
    request<PlatformIncident>(`/platform/incidents/${incidentId}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    }, { token }),
  platformAudit: (token: string) =>
    request<{ audits: PlatformAuditRow[]; total: number }>('/platform/audit', undefined, { token }),
  platformSecurityEvents: (token: string) =>
    request<{ events: Array<Record<string, unknown>> }>('/platform/security/events', undefined, { token }),
  platformSecurityConfiguration: (token: string) =>
    request<Record<string, unknown>>('/platform/security/configuration', undefined, { token }),
  platformObservabilityMetrics: (token: string) =>
    request<{ format: string; metrics: Record<string, unknown> }>(
      '/platform/observability/metrics',
      undefined,
      { token },
    ),
  platformObservabilityHealth: (token: string) =>
    request<Record<string, unknown>>('/platform/observability/health', undefined, { token }),
  platformReliabilityRetention: (token: string) =>
    request<{ policies: Array<Record<string, unknown>> }>('/platform/reliability/retention', undefined, {
      token,
    }),
  platformReliabilityCleanupDryRun: (token: string) =>
    request<Record<string, unknown>>(
      '/platform/reliability/cleanup/dry-run',
      { method: 'POST' },
      { token },
    ),
  platformReliabilityReadiness: (token: string) =>
    request<Record<string, unknown>>('/platform/reliability/readiness', undefined, { token }),
  platformReliabilityBackupPolicy: (token: string) =>
    request<Record<string, unknown>>('/platform/reliability/backup-policy', undefined, { token }),
  platformGlobalSearch: (token: string, q: string) =>
    request<{ query: string; results: Record<string, unknown[]> }>(
      `/platform/global-search?q=${encodeURIComponent(q)}`,
      undefined,
      { token },
    ),
  platformOrganizations: (token: string) =>
    request<{ organizations: PlatformOrganization[] }>('/platform/organizations', undefined, { token }),
  platformUsers: (token: string) =>
    request<{ users: PlatformUser[] }>('/platform/users', undefined, { token }),
  platformAccountingProposals: (
    token: string,
    params?: {
      organization_id?: number
      status?: string
      page?: number
      page_size?: number
      requires_review?: boolean
    },
  ) => {
    const q = new URLSearchParams()
    if (params?.organization_id != null) q.set('organization_id', String(params.organization_id))
    if (params?.status) q.set('status', params.status)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.requires_review != null) q.set('requires_review', String(params.requires_review))
    const qs = q.toString()
    return request<{
      total: number
      page: number
      page_size: number
      proposals: Array<{
        proposal_id: string
        organization_id: number
        vault_document_id: string
        document_type: string
        status: string
        requires_review: boolean
        confidence?: number | null
        amount_ttc?: number | null
        created_at: string
      }>
    }>(`/platform/accounting/proposals${qs ? `?${qs}` : ''}`, undefined, { token })
  },
  platformAccountingReviews: (
    token: string,
    params?: { organization_id?: number; page?: number; page_size?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.organization_id != null) q.set('organization_id', String(params.organization_id))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{ total: number; reviews: Array<Record<string, unknown>> }>(
      `/platform/accounting/reviews${qs ? `?${qs}` : ''}`,
      undefined,
      { token },
    )
  },
  platformAiUsage: (
    token: string,
    params?: { organization_id?: number; page?: number; page_size?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.organization_id != null) q.set('organization_id', String(params.organization_id))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{
      total: number
      usage: Array<{
        execution_id: string
        organization_id: number
        task_name: string
        provider: string
        model: string
        input_tokens?: number | null
        output_tokens?: number | null
        total_tokens?: number | null
        estimated_cost?: number | null
        currency?: string | null
        created_at: string
      }>
    }>(`/platform/ai/usage${qs ? `?${qs}` : ''}`, undefined, { token })
  },
  platformAiExecutions: (
    token: string,
    params?: { organization_id?: number; status?: string; page?: number; page_size?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.organization_id != null) q.set('organization_id', String(params.organization_id))
    if (params?.status) q.set('status', params.status)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{
      total: number
      executions: Array<Record<string, unknown>>
    }>(`/platform/ai/executions${qs ? `?${qs}` : ''}`, undefined, { token })
  },
  platformNotificationsAdmin: (
    token: string,
    params?: { organization_id?: number; page?: number; page_size?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.organization_id != null) q.set('organization_id', String(params.organization_id))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{
      total: number
      notifications: Array<Record<string, unknown>>
    }>(`/platform/notifications${qs ? `?${qs}` : ''}`, undefined, { token })
  },
  platformJobs: (
    token: string,
    params?: { status?: string; page?: number; page_size?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{ total: number; jobs: Array<Record<string, unknown>> }>(
      `/platform/jobs${qs ? `?${qs}` : ''}`,
      undefined,
      { token },
    )
  },
  platformJobRetry: (jobId: string, token: string) =>
    request<Record<string, unknown>>(`/platform/jobs/${jobId}/retry`, { method: 'POST' }, { token }),
  platformJobCancel: (jobId: string, token: string) =>
    request<Record<string, unknown>>(`/platform/jobs/${jobId}/cancel`, { method: 'POST' }, { token }),
  platformJobManualRetry: (jobId: string, reason: string, token: string) =>
    request<Record<string, unknown>>(
      `/platform/jobs/${jobId}/manual-retry`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }) },
      { token },
    ),
  platformJobManualCancel: (jobId: string, reason: string, token: string) =>
    request<Record<string, unknown>>(
      `/platform/jobs/${jobId}/manual-cancel`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }) },
      { token },
    ),
  platformEvents: (token: string, params?: { status?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{ total: number; events: Array<Record<string, unknown>> }>(
      `/platform/events${qs ? `?${qs}` : ''}`,
      undefined,
      { token },
    )
  },
  platformVaultDocuments: (
    token: string,
    params?: { organization_id?: number; page?: number; page_size?: number },
  ) => {
    const q = new URLSearchParams()
    if (params?.organization_id != null) q.set('organization_id', String(params.organization_id))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<Record<string, unknown>>(
      `/platform/vault-documents${qs ? `?${qs}` : ''}`,
      undefined,
      { token },
    )
  },
  platformBillingPlans: (token: string) =>
    request<{ plans: Array<Record<string, unknown>> }>('/platform/billing/plans', undefined, {
      token,
    }),
  platformEmailStatus: (token: string) =>
    request<Record<string, unknown>>('/platform/email-status', undefined, { token }),
  updatePlatformUser: (
    userId: number,
    payload: { status: 'active' | 'suspended' | 'banned' },
    token: string,
  ) =>
    request<{ ok: boolean; user: PlatformUser }>(`/platform/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token }),
  platformSyncSubscription: (organizationId: number, token: string) =>
    request<{ subscription: SubscriptionInfo }>(
      `/platform/organizations/${organizationId}/subscriptions/sync`,
      { method: 'POST' },
      { token },
    ),
  platformRevokeSubscription: (
    organizationId: number,
    payload: { reason_public: string; reason_internal?: string },
    token: string,
  ) =>
    request<{ subscription: SubscriptionInfo }>(
      `/platform/organizations/${organizationId}/subscriptions/revoke`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token },
    ),
  platformRestoreSubscription: (
    organizationId: number,
    payload: { reason?: string },
    token: string,
  ) =>
    request<{ subscription: SubscriptionInfo }>(
      `/platform/organizations/${organizationId}/subscriptions/restore`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token },
    ),
  platformGrantTrial: (
    organizationId: number,
    payload: { reason: string },
    token: string,
  ) =>
    request<{ subscription: SubscriptionInfo }>(
      `/platform/organizations/${organizationId}/subscriptions/grant-trial`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token },
    ),
  platformOrphanSubscriptions: (token: string) =>
    request<{
      orphans: {
        subscription_id: number
        organization_id: number
        stripe_subscription_id: string | null
        status: string
      }[]
    }>('/platform/subscriptions/orphans', undefined, { token }),
  platformAiSubscriptionSummary: (organizationId: number, token: string) =>
    request<{
      summary: string
      suggestions: string[]
      requires_human_confirmation: boolean
    }>(
      '/platform/subscriptions/ai-summary',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ organization_id: organizationId }),
      },
      { token },
    ),
  listNotifications: (
    params: {
      page?: number
      page_size?: number
      status?: string
      category?: string
      severity?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) => {
    const q = new URLSearchParams()
    if (params.page) q.set('page', String(params.page))
    if (params.page_size) q.set('page_size', String(params.page_size))
    if (params.status) q.set('status', params.status)
    if (params.category) q.set('category', params.category)
    if (params.severity) q.set('severity', params.severity)
    const qs = q.toString()
    return request<{
      total: number
      page: number
      page_size: number
      notifications: import('./notificationFormat').AppNotification[]
    }>(`/notifications${qs ? `?${qs}` : ''}`, undefined, { token, orgId })
  },
  notificationsUnreadCount: (token?: string | null, orgId?: number | null) =>
    request<{ count: number }>('/notifications/unread-count', undefined, { token, orgId }),
  markElfisNotificationRead: (notificationId: string, token?: string | null, orgId?: number | null) =>
    request<{ notification: import('./notificationFormat').AppNotification }>(
      `/notifications/${notificationId}/read`,
      { method: 'POST' },
      { token, orgId },
    ),
  markAllElfisNotificationsRead: (token?: string | null, orgId?: number | null) =>
    request<{ updated: number }>('/notifications/read-all', { method: 'POST' }, { token, orgId }),
  archiveElfisNotification: (notificationId: string, token?: string | null, orgId?: number | null) =>
    request<{ notification: import('./notificationFormat').AppNotification }>(
      `/notifications/${notificationId}/archive`,
      { method: 'POST' },
      { token, orgId },
    ),
  getJobStatus: (jobId: string, token?: string | null, orgId?: number | null) =>
    request<{
      job_id: string
      job_name: string
      status: string
      progress: number
      progress_message?: string | null
      attempt_count: number
      max_attempts: number
      created_at: string
      started_at?: string | null
      completed_at?: string | null
      failed_at?: string | null
    }>(`/jobs/${jobId}`, undefined, { token, orgId }),
  cancelJob: (jobId: string, token?: string | null, orgId?: number | null) =>
    request<{
      job_id: string
      job_name: string
      status: string
      progress: number
      progress_message?: string | null
      attempt_count: number
      max_attempts: number
      created_at: string
      started_at?: string | null
      completed_at?: string | null
      failed_at?: string | null
    }>(`/jobs/${jobId}/cancel`, { method: 'POST' }, { token, orgId }),
  startDocumentAnalysis: (
    vaultDocumentId: string,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<{
      analysis_id: string
      vault_document_id: string
      status: string
      current_stage?: string | null
      job_id?: string | null
      reused_existing_analysis: boolean
    }>(
      `/ai/documents/${vaultDocumentId}/analyze`,
      { method: 'POST', body: JSON.stringify({}) },
      { token, orgId },
    ),
  getDocumentAnalysis: (vaultDocumentId: string, token?: string | null, orgId?: number | null) =>
    request<{
      analysis_id: string
      status: string
      current_stage?: string | null
      document_type?: string | null
      confidence?: number | null
      requires_review: boolean
      quality_summary?: Record<string, unknown> | null
      created_at: string
      updated_at: string
      completed_at?: string | null
    }>(`/ai/documents/${vaultDocumentId}/analysis`, undefined, { token, orgId }),
  /** Étapes d'affichage pour le suivi d'analyse documentaire. */
  documentAnalysisStageLabel: (stage?: string | null, status?: string | null): string => {
    if (status === 'blocked' || stage === 'awaiting_ocr') return 'En attente OCR'
    if (status === 'failed') return 'Erreur'
    switch (stage) {
      case 'text_extraction':
        return 'Extraction du texte'
      case 'classification':
        return 'Classification'
      case 'extraction':
        return 'Extraction des données'
      case 'validation':
        return 'Contrôle qualité'
      case 'completed':
        return 'Terminé'
      default:
        return 'Préparation du document'
    }
  },
  listAccountingProposals: (
    params?: { status?: string; requires_review?: boolean; page?: number; page_size?: number },
    token?: string | null,
    orgId?: number | null,
  ) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.requires_review != null) q.set('requires_review', String(params.requires_review))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return request<{
      total: number
      page: number
      page_size: number
      proposals: Array<{
        proposal_id: string
        vault_document_id: string
        document_type: string
        document_number?: string | null
        supplier_name?: string | null
        customer_name?: string | null
        amount_ttc?: number | null
        currency: string
        status: string
        confidence?: number | null
        requires_review: boolean
        created_at: string
      }>
    }>(`/accounting/proposals${qs ? `?${qs}` : ''}`, undefined, { token, orgId })
  },
  getAccountingProposal: (proposalId: string, token?: string | null, orgId?: number | null) =>
    request<{
      proposal_id: string
      status: string
      current_stage: string
      document_type: string
      document_number?: string | null
      supplier_name?: string | null
      customer_name?: string | null
      amount_ht?: number | null
      amount_vat?: number | null
      amount_ttc?: number | null
      currency: string
      confidence?: number | null
      requires_review: boolean
      review_reasons?: string[]
      document_validation?: Record<string, unknown>
      financial_validation?: Record<string, unknown>
      accounting_mapping?: Record<string, unknown>
      quality_summary?: Record<string, unknown>
      entry?: Record<string, unknown> | null
      lines?: Array<Record<string, unknown>>
      reviews?: Array<Record<string, unknown>>
      allowed_actions?: string[]
      disclaimer?: string
      [key: string]: unknown
    }>(`/accounting/proposals/${proposalId}`, undefined, {
      token,
      orgId,
    }),
  updateAccountingProposal: (
    proposalId: string,
    body: Record<string, unknown>,
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<Record<string, unknown>>(
      `/accounting/proposals/${proposalId}`,
      { method: 'PUT', body: JSON.stringify(body) },
      { token, orgId },
    ),
  validateAccountingProposal: (
    proposalId: string,
    body: { comment?: string; confirm_balanced_entry: boolean; confirm_document_reviewed: boolean },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<Record<string, unknown>>(
      `/accounting/proposals/${proposalId}/validate`,
      { method: 'POST', body: JSON.stringify(body) },
      { token, orgId },
    ),
  rejectAccountingProposal: (
    proposalId: string,
    body: { reason: string; comment?: string },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<Record<string, unknown>>(
      `/accounting/proposals/${proposalId}/reject`,
      { method: 'POST', body: JSON.stringify(body) },
      { token, orgId },
    ),
  reopenAccountingProposal: (proposalId: string, token?: string | null, orgId?: number | null) =>
    request<Record<string, unknown>>(
      `/accounting/proposals/${proposalId}/reopen`,
      { method: 'POST' },
      { token, orgId },
    ),
  buildAccountingProposal: (vaultDocumentId: string, token?: string | null, orgId?: number | null) =>
    request<{
      proposal_id?: string | null
      job_id?: string | null
      status: string
      reused_existing?: boolean
    }>(
      `/accounting/documents/${vaultDocumentId}/build-proposal`,
      { method: 'POST' },
      { token, orgId },
    ),
  searchElfis: (
    params?: {
      q?: string
      resource_type?: string
      status?: string
      category?: string
      sort?: string
      page?: number
      page_size?: number
      amount_min?: number
      amount_max?: number
      currency?: string
      requires_review?: boolean
    },
    token?: string | null,
    orgId?: number | null,
  ) => {
    const q = new URLSearchParams()
    if (params?.q) q.set('q', params.q)
    if (params?.resource_type) q.set('resource_type', params.resource_type)
    if (params?.status) q.set('status', params.status)
    if (params?.category) q.set('category', params.category)
    if (params?.sort) q.set('sort', params.sort)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.amount_min != null) q.set('amount_min', String(params.amount_min))
    if (params?.amount_max != null) q.set('amount_max', String(params.amount_max))
    if (params?.currency) q.set('currency', params.currency)
    if (params?.requires_review != null) q.set('requires_review', String(params.requires_review))
    const qs = q.toString()
    return request<{
      items: Array<{
        search_document_id: string
        resource_type: string
        resource_id: string
        title: string
        subtitle?: string | null
        snippet: string
        status?: string | null
        category?: string | null
        document_date?: string | null
        amount?: number | null
        currency?: string | null
        action_url?: string | null
        score: number
        metadata?: Record<string, unknown>
      }>
      page: number
      page_size: number
      total: number
      total_pages: number
      query?: string | null
      execution_time_ms: number
    }>(`/search${qs ? `?${qs}` : ''}`, undefined, { token, orgId })
  },
  searchSuggestions: (q: string, limit = 10, token?: string | null, orgId?: number | null) =>
    request<{
      suggestions: Array<{
        title: string
        resource_type: string
        resource_id: string
        action_url?: string | null
      }>
    }>(`/search/suggestions?q=${encodeURIComponent(q)}&limit=${limit}`, undefined, { token, orgId }),
}


export type ModuleInfo = {
  id: number
  slug: string
  name: string
  status: 'live' | 'setup'
  summary: string
  capabilities: string[]
  route: string | null
}

export type AuthUser = {
  id: number
  first_name: string
  last_name: string
  email: string
  phone?: string
  avatar?: string
  status: string
  last_login?: string | null
  is_platform_admin: boolean
}

export type SubscriptionStatus =
  | 'trialing'
  | 'active'
  | 'past_due'
  | 'unpaid'
  | 'canceled'
  | 'expired'
  | 'incomplete'
  | 'incomplete_expired'
  | 'paused'
  | 'none'
  | 'checkout_pending'
  | 'cancel_scheduled'
  | 'admin_revoked'

export type SubscriptionInfo = {
  id?: number | null
  plan: string
  plan_code?: string
  status: SubscriptionStatus
  price_eur: number
  configured: boolean
  stripe_price_id?: string | null
  trial_start?: string | null
  trial_end: string | null
  current_period_start?: string | null
  current_period_end: string | null
  past_due_since?: string | null
  grace_until?: string | null
  cancel_at_period_end: boolean
  canceled_at?: string | null
  access_ends_at?: string | null
  next_billing_at?: string | null
  next_billing_amount_cents?: number | null
  platform_bypass?: boolean
  access_granted?: boolean
  read_only?: boolean
  is_trial?: boolean
  access_reason?: string
  label?: string
  trial_used?: boolean
  trial_eligibility_status?: string
  admin_revoked?: boolean
  admin_revoked_reason_public?: string
  raw_status?: string
}

export type PlatformOverview = {
  organizations: number
  organizations_suspended?: number
  users: number
  active_memberships: number
  subscriptions_by_status: Partial<Record<SubscriptionStatus, number>>
}

export type PlatformDashboard = {
  period: string
  computed_at: string
  organizations_total: number
  organizations_active: number
  organizations_suspended: number
  users_total: number
  subscriptions_trialing: number
  subscriptions_active: number
  subscriptions_past_due: number
  subscriptions_cancelled: number
  documents_processed_today: number
  ai_analyses_today: number
  accounting_proposals_today: number
  jobs_pending: number
  jobs_running: number
  jobs_failed: number
  jobs_dead_letter: number
  events_dead_letter: number
  email_deliveries_failed: number
  extractions_awaiting_ocr: number
  proposals_requires_review: number
  incidents_open: number
}

export type PlatformServiceHealth = {
  service: string
  status: string
  message: string
  checked_at: string
  metrics: Record<string, unknown>
}

export type PlatformOrgOpsDetail = {
  organization: {
    id: number
    name: string
    platform_status: string
    platform_suspend_reason?: string
  }
  users: Array<{ user_id: number; email: string; role: string; status: string }>
  counts: Record<string, number>
  billing: Record<string, unknown>
  support_links: Record<string, string>
}

export type PlatformIncident = {
  incident_id: string
  organization_id: number | null
  incident_type: string
  severity: string
  status: string
  title: string
  summary: string | null
  last_seen_at: string
}

export type PlatformAuditRow = {
  audit_id: string
  actor_email: string | null
  organization_id: number | null
  action: string
  target_type: string
  target_id: string | null
  reason: string | null
  status: string
  created_at: string
}

export type PlatformOrganization = {
  id: number
  name: string
  legal_name: string
  country: string
  platform_status?: string
  member_count: number
  subscription: SubscriptionInfo
  created_at: string | null
}

export type PlatformUser = {
  id: number
  display_name: string
  email: string
  status: string
  is_platform_admin: boolean
  organization_count: number
  last_login: string | null
  created_at: string | null
}

/** @deprecated Legacy `/dashboard/pilot` — remplacé par Financial Engine overview. */
export type PilotOverview = {
  health: 'ok' | 'attention' | 'critique' | 'setup'
  ca: number
  benefice: number
  marge_pct: number
  tresorerie: number | null
  depenses: number
  unpaid: number
  forecast_30: number
  alerts: string[]
  recommendations: string[]
}

export type Membership = {
  membership_id: number
  organization_id: number
  organization_name: string
  organization_logo?: string
  role: string
  status?: string
  permissions: string[]
  plan: string
  subscription_status?: string
  country: string
  joined_at?: string | null
}

export type OrgInvitation = {
  id: number
  organization_id: number
  organization_name: string | null
  email: string
  role: string
  status: string
  invited_by: number | null
  expires_at: string | null
  accepted_at: string | null
  created_at: string | null
}

export type TeamNotificationItem = {
  id: number
  organization_id: number | null
  kind: string
  title: string
  body: string
  payload: Record<string, unknown>
  is_read: boolean
  created_at: string | null
}

export type SalesDoc = {
  id: number
  doc_type: string
  number: string
  issue_date: string
  due_date: string
  status: string
  customer_id?: number | null
  customer_name: string
  customer_email: string
  amount_ht: number
  amount_tva: number
  amount_ttc: number
  vat_rate: number
  paid_amount: number
  signature_status: string
  notes: string
  branding?: { showLogo?: boolean; template?: string }
  lines?: {
    label?: string
    quantity?: number
    unit_price?: number
    catalog_item_id?: number | null
  }[]
}

export type DocumentEmailLog = {
  id: number
  sales_document_id: number | null
  organization_id?: number
  document_type?: string
  sent_by_user_id?: number | null
  sent_by_email?: string
  sent_by_name?: string
  recipient: string
  recipient_email?: string
  cc_email?: string
  bcc_email?: string
  sender_name?: string
  sender_email?: string
  reply_to_email?: string
  subject: string
  provider?: string
  provider_message_id?: string
  status: 'preparing' | 'queued' | 'sent' | 'delivered' | 'opened' | 'bounced' | 'blocked' | 'failed' | string
  error_code?: string
  error_message: string
  sent_at: string
  delivered_at?: string | null
  opened_at?: string | null
  bounced_at?: string | null
  updated_at?: string | null
}

export type EmailSendPreview = {
  recipient: string
  cc: string
  bcc: string
  subject: string
  message: string
  pdf_filename: string
  sender_name: string
  sender_email: string
  reply_to_email: string
  sender_mode: string
  connection_id?: number | null
  user_email?: string
  org_email?: string
  preferred_send_mode?: string
}

export type EmailConnection = {
  id: number
  organization_id: number
  provider: 'platform' | 'google' | 'microsoft' | 'custom_smtp' | string
  email_address: string
  display_name: string
  status: string
  is_default: boolean
  connected_by_user_id?: number | null
  provider_account_id?: string
  smtp_host?: string
  smtp_port?: number | null
  smtp_username?: string
  smtp_security?: string
  has_smtp_password?: boolean
  token_expires_at?: string | null
  last_used_at?: string | null
  last_error_code?: string
  last_error_message?: string
  created_at?: string | null
  updated_at?: string | null
  from_preview?: string
}

export type OrgEmailSettings = {
  organization_id: number
  sender_mode: 'platform' | 'custom_sender' | string
  sender_name: string
  reply_to_email: string
  reply_to_name: string
  cc_email: string
  bcc_email: string
  invoice_default_subject: string
  invoice_default_message: string
  quote_default_subject: string
  quote_default_message: string
  email_signature: string
  send_copy_to_organization: boolean
  custom_sender_email: string
  custom_sender_status: string
  custom_domain: string
  custom_domain_status: string
  platform_configured: boolean
  configuration_state: string
  effective_from_preview: string
  updated_at: string | null
}

export type OrgEmailSettingsUpdate = {
  sender_mode: string
  sender_name: string
  reply_to_email: string
  reply_to_name: string
  cc_email: string
  bcc_email: string
  invoice_default_subject: string
  invoice_default_message: string
  quote_default_subject: string
  quote_default_message: string
  email_signature: string
  send_copy_to_organization: boolean
  custom_sender_email: string
  custom_domain: string
}

export type BillingOverview = {
  module?: string
  smtp_configured?: boolean
  stats: {
    documents: number
    customers: number
    unpaid: number
    unpaid_amount: number
    quotes: number
    invoices: number
    credits: number
  }
  documents: SalesDoc[]
  customers: { id: number; name: string; email: string; phone?: string; address?: string }[]
}

export type CustomerRecord = {
  id: number
  organization_id?: number
  name: string
  email: string
  phone: string
  address: string
  vat_number: string
  created_at?: string
}

export type SharedRelationRole =
  | 'customer'
  | 'supplier'
  | 'prospect'
  | 'partner'
  | 'employee'
  | 'commercial_account'
  | 'billing_contact'

export type SharedRelation = {
  id: string
  organization_id: number
  party_type: 'person' | 'organization' | 'unknown'
  display_name: string
  legal_name: string
  first_name: string
  last_name: string
  emails: string[]
  phones: string[]
  addresses: Array<{
    line1: string
    line2: string
    postal_code: string
    city: string
    country: string
  }>
  tax_number: string
  siren: string
  siret: string
  roles: SharedRelationRole[]
  status: string
  source_system: 'customer' | 'contact' | 'sales_company'
  source_entity_id: number
  created_at?: string | null
  updated_at?: string | null
  links?: Record<string, string>
}

export type SharedRelationDuplicate = {
  possible_duplicate: boolean
  confidence: number
  matching_fields: string[]
  related_entity_ids: string[]
  left_id: string
  right_id: string
}

export type SharedRelationListResponse = {
  items: SharedRelation[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type SharedRelationDetailResponse = {
  relation: SharedRelation
  roles: SharedRelationRole[]
  usages: Record<string, unknown>
  duplicates: SharedRelationDuplicate[]
}

export type CatalogItem = {
  id: number
  name: string
  kind: string
  unit: string
  unit_price_ht: number
  vat_rate: number
  active: boolean
  created_at?: string
  updated_at?: string
}

export type CommercialActivity = {
  id: number
  title: string
  kind: string
  customer_id: number | null
  customer_name?: string
  scheduled_at: string | null
  status: string
  notes: string
  created_at?: string
  updated_at?: string
}

export type OrgDetail = {
  organization: {
    id: number
    name: string
    legal_name: string
    siren: string
    vat_number: string
    country: string
    currency: string
    industry: string
    address: string
    postal_code: string
    city: string
    phone: string
    email: string
    website: string
    iban: string
    bic: string
    share_capital: string
    legal_form: string
    legal_mentions: string
    logo: string
    primary_color: string
    secondary_color: string
    documents_show_logo?: boolean | null
    subscription_plan: string
  }
  can_edit?: boolean
  subscription: { plan: string; status: string; price: number } | null
  companies: { id: number; name: string; country: string; parent_company_id: number | null }[]
  teams: { id: number; name: string }[]
  ai_agents: { id: number; name: string; type: string; status: string }[]
}

export type OrgMember = {
  membership_id: number
  uid: string
  user_id: number
  first_name: string
  last_name: string
  display_name: string
  email: string
  avatar: string
  role: string
  role_label?: string
  permissions: string[]
  status: string
  invited_by?: number | null
  joined_at: string | null
}


export function formatEuro(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value)
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}
