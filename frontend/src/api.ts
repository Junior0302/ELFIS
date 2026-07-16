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
  // Production Firebase Hosting → API Render
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host === 'elfis-core.web.app' || host === 'elfis-core.firebaseapp.com') {
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

function friendlyError(status: number, message: string): string {
  if (status === 404 || message.toLowerCase().includes('not found')) {
    return 'Service API introuvable. Lancez le backend : start-backend.bat (port 8001)'
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
  if (!res.ok) throw new Error(friendlyError(res.status, await parseError(res)))
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
  if (!res.ok) throw new Error(friendlyError(res.status, await parseError(res)))
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
    }>('/auth/me', undefined, { token, orgId }),
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
  aiSuggestions: () =>
    request<{ agent: string; suggestions: string[] }>('/ai/suggestions'),
  aiConversations: (token: string, orgId?: number | null) =>
    request<{ conversations: { id: number; question: string; answer: string; created_at: string | null }[] }>(
      '/ai/conversations',
      undefined,
      { token, orgId },
    ),
  billingOverview: (token?: string | null, orgId?: number | null) =>
    request<BillingOverview>('/billing/overview', undefined, { token, orgId }),
  createSalesDoc: (
    payload: {
      doc_type: string
      customer_name: string
      amount_ht: number
      vat_rate?: number
      notes?: string
    },
    token?: string | null,
    orgId?: number | null,
  ) =>
    request<SalesDoc>('/billing/documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }, { token, orgId }),
  billingAction: (docId: number, action: string, token?: string | null, orgId?: number | null, body?: object) =>
    request<unknown>(`/billing/documents/${docId}/${action}`, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }, { token, orgId }),
  orgDetail: (organizationId: number, token?: string | null) =>
    request<OrgDetail>(`/org/${organizationId}`, undefined, { token, orgId: organizationId }),
  orgMembers: (organizationId: number, token: string) =>
    request<{ members: OrgMember[]; can_manage: boolean; roles: string[] }>(
      `/org/${organizationId}/members`,
      undefined,
      { token, orgId: organizationId },
    ),
  addOrgMember: (
    organizationId: number,
    payload: { email: string; role: string },
    token: string,
  ) =>
    request<{ ok: boolean; member: OrgMember }>(
      `/org/${organizationId}/members`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      { token, orgId: organizationId },
    ),
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
  currentSubscription: async (token: string, orgId?: number | null) => {
    const result = await request<{ subscription: SubscriptionInfo }>(
      '/subscriptions/current',
      undefined,
      { token, orgId },
    )
    return result.subscription
  },
  createSubscriptionCheckout: (token: string, orgId?: number | null) =>
    request<{ url: string }>('/subscriptions/checkout', { method: 'POST' }, { token, orgId }),
  createSubscriptionPortal: (token: string, orgId?: number | null) =>
    request<{ url: string }>('/subscriptions/portal', { method: 'POST' }, { token, orgId }),
  platformOverview: (token: string) =>
    request<PlatformOverview>('/platform/overview', undefined, { token }),
  platformOrganizations: (token: string) =>
    request<{ organizations: PlatformOrganization[] }>('/platform/organizations', undefined, { token }),
  platformUsers: (token: string) =>
    request<{ users: PlatformUser[] }>('/platform/users', undefined, { token }),
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

export type SubscriptionInfo = {
  id?: number
  plan: string
  status: SubscriptionStatus
  price_eur: number
  configured: boolean
  stripe_price_id?: string | null
  trial_start?: string | null
  trial_end: string | null
  current_period_start?: string | null
  current_period_end: string | null
  past_due_since?: string | null
  cancel_at_period_end: boolean
  canceled_at?: string | null
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
  role: string
  permissions: string[]
  plan: string
  country: string
}

export type SalesDoc = {
  id: number
  doc_type: string
  number: string
  issue_date: string
  due_date: string
  status: string
  customer_name: string
  amount_ht: number
  amount_tva: number
  amount_ttc: number
  vat_rate: number
  paid_amount: number
  signature_status: string
  notes: string
}

export type BillingOverview = {
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
  customers: { id: number; name: string; email: string }[]
}

export type OrgDetail = {
  organization: {
    id: number
    name: string
    legal_name: string
    siren: string
    country: string
    currency: string
    subscription_plan: string
  }
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
  permissions: string[]
  status: string
  joined_at: string
}


export function formatEuro(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(value)
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}
