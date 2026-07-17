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
  created_at: string
  updated_at: string
}

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
 * - sinon : http(s)://{hostname}:8001/api
 */
function apiRoot(): string {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL as string
  if (import.meta.env.DEV) return '/api'
  // Production Firebase Hosting / domaine custom → API Render
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    const productionHosts = new Set([
      'elfis-core.web.app',
      'elfis-core.firebaseapp.com',
      'elfis-core.com',
      'www.elfis-core.com',
    ])
    if (productionHosts.has(host)) {
      return 'https://elfis-core-api.onrender.com/api'
    }
  }
  const { protocol, hostname } = window.location
  const port = (import.meta.env.VITE_API_PORT as string) || '8001'
  return `${protocol}//${hostname}:${port}/api`
}

async function parseError(res: Response): Promise<string> {
  const text = await res.text()
  try {
    const data = JSON.parse(text) as { detail?: unknown }
    if (typeof data.detail === 'string') return data.detail
    if (
      typeof data.detail === 'object' &&
      data.detail &&
      'message' in data.detail &&
      typeof data.detail.message === 'string'
    ) {
      return data.detail.message
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
  if (status === 404 || message.toLowerCase().includes('not found')) {
    if (path?.includes('/billing/documents/') && path.includes('/pdf')) {
      return isLocalApi
        ? 'PDF indisponible. Vérifiez que le backend local est démarré (start-backend.bat).'
        : 'PDF indisponible pour le moment. Réessayez dans quelques minutes.'
    }
    if (isLocalApi) {
      return 'Service API introuvable. Lancez le backend : start-backend.bat (port 8001)'
    }
    return message || 'Ressource introuvable sur l’API'
  }
  if (status === 401) return message || 'Email ou mot de passe incorrect'
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
  const res = await fetch(`${apiRoot()}${path}`, { ...init, headers })
  if (!res.ok) throw new Error(friendlyError(res.status, await parseError(res), path))
  if (res.status === 204) return undefined as T
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) return res.json() as Promise<T>
  return undefined as T
}

async function requestBlob(
  path: string,
  token: string,
  orgId?: number | null,
): Promise<{ blob: Blob; filename: string }> {
  const headers = new Headers({ Authorization: `Bearer ${token}` })
  if (orgId) headers.set('X-Organization-Id', String(orgId))
  const res = await fetch(`${apiRoot()}${path}`, { headers })
  if (!res.ok) throw new Error(friendlyError(res.status, await parseError(res), path))
  const disposition = res.headers.get('content-disposition') || ''
  const filename = disposition.match(/filename="?([^"]+)"?/i)?.[1] || 'export'
  return { blob: await res.blob(), filename }
}

export async function downloadApiFile(
  path: string,
  token: string,
  orgId?: number | null,
): Promise<void> {
  const { blob, filename } = await requestBlob(path, token, orgId)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}


export const api = {
  health: () =>
    request<{ status: string; ai_mode: string; product: string; details?: { version?: string } }>('/health'),
  dashboard: (token?: string | null, orgId?: number | null) =>
    request<DashboardStats>('/dashboard/stats', undefined, { token, orgId }),
  dashboardPilot: (token?: string | null, orgId?: number | null) =>
    request<PilotOverview>('/dashboard/pilot', undefined, { token, orgId }),
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
    return request<BillingOverview>(`/billing/overview${qs ? `?${qs}` : ''}`, undefined, {
      token,
      orgId,
    })
  },
  listCustomers: (token?: string | null, orgId?: number | null, q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : ''
    return request<{ customers: CustomerRecord[] }>(`/billing/customers${qs}`, undefined, {
      token,
      orgId,
    })
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
  downloadSalesDocPdf: (docId: number, token: string, orgId?: number | null) =>
    downloadApiFile(`/billing/documents/${docId}/pdf`, token, orgId),
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
      email_log: DocumentEmailLog
      smtp_configured: boolean
      email_configured?: boolean
      send_mode?: string
      sender_email?: string
      can_send_direct?: boolean
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
  platformOverview: (token: string) =>
    request<PlatformOverview>('/platform/overview', undefined, { token }),
  myProfessionalEmails: (token?: string | null, orgId?: number | null) =>
    request<{
      emails: ProfessionalEmailRecord[]
      has_active: boolean
      has_pending: boolean
      can_request: boolean
    }>('/professional-emails/me', undefined, { token, orgId }),
  requestProfessionalEmail: (token?: string | null, orgId?: number | null) =>
    request<{
      ok: boolean
      message: string
      email: ProfessionalEmailRecord
      notify?: {
        admin_notified?: boolean
        user_confirmed?: boolean
        notify_to?: string
        mail_configured?: boolean
        error?: string
      }
    }>('/professional-emails/request', { method: 'POST' }, { token, orgId }),
  professionalSenderOptions: (token?: string | null, orgId?: number | null) =>
    request<{
      options: EmailSenderOption[]
      default_option_id: string | null
    }>('/professional-emails/sender-options', undefined, { token, orgId }),
  platformProfessionalEmailRequests: (token: string, status?: string) =>
    request<{
      requests: ProfessionalEmailRecord[]
      counts?: {
        all: number
        pending: number
        creating: number
        active: number
        suspended: number
        rejected: number
      }
    }>(
      `/professional-emails/admin/requests${status ? `?status=${encodeURIComponent(status)}` : ''}`,
      undefined,
      { token },
    ),
  platformActivateProfessionalEmail: (
    requestId: number,
    payload: { email?: string; notes?: string; make_default?: boolean },
    token: string,
  ) =>
    request<{ ok: boolean; email: ProfessionalEmailRecord }>(
      `/professional-emails/admin/requests/${requestId}/activate`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token },
    ),
  platformRejectProfessionalEmail: (
    requestId: number,
    payload: { notes?: string },
    token: string,
  ) =>
    request<{ ok: boolean; email: ProfessionalEmailRecord }>(
      `/professional-emails/admin/requests/${requestId}/reject`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token },
    ),
  platformSuspendProfessionalEmail: (
    requestId: number,
    payload: { notes?: string },
    token: string,
  ) =>
    request<{ ok: boolean; email: ProfessionalEmailRecord }>(
      `/professional-emails/admin/requests/${requestId}/suspend`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token },
    ),
  platformResetProfessionalEmail: (requestId: number, token: string) =>
    request<{ ok: boolean; deleted: ProfessionalEmailRecord }>(
      `/professional-emails/admin/requests/${requestId}/reset`,
      { method: 'POST' },
      { token },
    ),
  platformResendProfessionalEmail: (requestId: number, token: string) =>
    request<{
      ok: boolean
      notify: {
        admin_notified?: boolean
        user_confirmed?: boolean
        notify_to?: string
        error?: string
        mail_status?: {
          configured?: boolean
          transport?: string
          has_brevo_api_key?: boolean
          has_platform_from?: boolean
          platform_from?: string
        }
      }
    }>(`/professional-emails/admin/requests/${requestId}/resend`, { method: 'POST' }, { token }),
  platformResetAllProfessionalEmails: (token: string) =>
    request<{ ok: boolean; deleted_count: number }>(
      '/professional-emails/admin/requests/reset-all',
      { method: 'POST' },
      { token },
    ),
  platformEmailStatus: (token: string) =>
    request<{
      configured: boolean
      transport: string
      has_brevo_api_key: boolean
      has_platform_from: boolean
      platform_from: string
      platform_from_name: string
      notify_to: string
      hint: string
    }>('/platform/email-status', undefined, { token }),
  platformOrganizations: (token: string) =>
    request<{ organizations: PlatformOrganization[] }>('/platform/organizations', undefined, { token }),
  platformUsers: (token: string) =>
    request<{ users: PlatformUser[] }>('/platform/users', undefined, { token }),
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
  users: number
  active_memberships: number
  subscriptions_by_status: Partial<Record<SubscriptionStatus, number>>
}

export type PlatformOrganization = {
  id: number
  name: string
  legal_name: string
  country: string
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

export type ProfessionalEmailRecord = {
  id: number
  user_id: number
  organization_id?: number | null
  email: string
  suggested_email: string
  provider: string
  status: string
  is_default: boolean
  created_at?: string | null
  activated_at?: string | null
  activated_by?: number | null
  admin_notes?: string
  request_snapshot?: Record<string, unknown>
  user?: {
    id: number | null
    first_name: string
    last_name: string
    email: string
    status: string
  }
}

export type EmailSenderOption = {
  id: string
  kind: 'professional' | 'personal' | 'organization' | string
  email: string
  label: string
  is_default: boolean
  professional_email_id?: number | null
}

export type PilotOverview = {
  health: 'ok' | 'attention' | 'critique' | 'setup'
  ca: number
  benefice: number
  marge_pct: number
  tresorerie: number
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
  customer_name: string
  customer_email: string
  amount_ht: number
  amount_tva: number
  amount_ttc: number
  vat_rate: number
  paid_amount: number
  signature_status: string
  notes: string
  lines?: { label?: string; quantity?: number; unit_price?: number }[]
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
