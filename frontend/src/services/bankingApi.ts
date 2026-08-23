export type BankingProvider = {
  provider: string
  display_name: string
  configured: boolean
  status: string
  message: string
  latency_ms?: number | null
  requires_user_consent?: boolean
  fictional?: boolean
}

export type BankConnection = {
  id: number
  provider: string
  bank_name: string
  status: string
  error_message?: string | null
  last_sync_at?: string | null
  next_sync_at?: string | null
  sync_interval_minutes: number
  created_at: string
}

export type BankAccount = {
  id: number
  connection_id?: number | null
  provider: string
  external_id: string
  label: string
  bank_name: string
  iban_masked: string
  iban_last4?: string | null
  account_type: string
  currency: string
  balance: number
  available_balance?: number | null
  connected: boolean
  last_sync_at?: string | null
  balance_updated_at?: string | null
}

export type BankTransaction = {
  id: number
  account_id: number
  external_id: string
  booked_at: string
  value_date?: string | null
  label: string
  amount: number
  currency: string
  category: string
  status: string
  source: string
  counterparty_name?: string | null
  reference?: string | null
  is_duplicate: boolean
  is_anomaly: boolean
  reconciled: boolean
}

export type SyncRun = {
  id: string
  connection_id: number
  provider: string
  sync_type: string
  trigger: string
  status: string
  accounts_synced: number
  transactions_created: number
  transactions_updated: number
  duplicates_skipped: number
  attempt_count: number
  max_attempts: number
  cursor?: string | null
  resumed_from_cursor: boolean
  error_message?: string | null
  started_at: string
  finished_at?: string | null
  duration_ms?: number | null
}

export type BankingStatus = {
  connections_total: number
  connections_connected: number
  connections_error: number
  accounts_total: number
  transactions_total: number
  balances_by_currency: Record<string, number>
  last_sync_at?: string | null
  last_sync_status?: string | null
  next_sync_at?: string | null
}

export type ConnectionHealth = {
  connection_id: number
  provider: string
  bank_name: string
  status: string
  error_message?: string | null
  last_sync_at?: string | null
  next_sync_at?: string | null
  provider_health?: BankingProvider | null
  runs_total: number
  runs_failed: number
  failure_rate: number
  avg_duration_ms?: number | null
  last_error?: string | null
}

export type BankingHealth = {
  connections: ConnectionHealth[]
  providers: BankingProvider[]
  summary: {
    runs_total: number
    runs_failed: number
    failure_rate: number
    avg_duration_ms?: number | null
    last_error?: string | null
  }
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

export const syncStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    running: 'En cours',
    completed: 'Terminée',
    failed: 'Échec',
  }
  return map[status] || status
}

export const accountTypeLabel = (accountType: string): string => {
  const map: Record<string, string> = {
    checking: 'Compte courant',
    savings: 'Épargne',
    card: 'Carte',
    loan: 'Crédit',
    investment: 'Investissement',
    other: 'Autre',
  }
  return map[accountType] || map.other
}

export const connectionStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    preparing: 'Connexion en préparation',
    awaiting_consent: 'En attente du consentement',
    connected: 'Connectée',
    disconnected: 'Déconnectée',
    error: 'Erreur',
  }
  return map[status] || status
}

export const bankingApi = {
  async listConnectors(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/banking/connectors`, {
      headers: headers(token, orgId),
    })
    return parse<{ providers: BankingProvider[]; connections: BankConnection[] }>(res)
  },

  async connect(token: string, orgId: number, provider: string, bankName = '') {
    const res = await fetch(`${apiRoot()}/banking/connectors/connect`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ provider, bank_name: bankName }),
    })
    return parse<{
      ok: boolean
      redirect_url?: string
      connection: BankConnection
      accounts: BankAccount[]
      message: string
    }>(res)
  },

  async disconnect(token: string, orgId: number, connectionId: number) {
    const res = await fetch(
      `${apiRoot()}/banking/connectors/${connectionId}/disconnect`,
      { method: 'POST', headers: headers(token, orgId, true), body: '{}' },
    )
    return parse<{ ok: boolean; connection: BankConnection; message: string }>(res)
  },

  async listAccounts(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/banking/accounts`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: BankAccount[]; total: number }>(res)
  },

  async listTransactions(
    token: string,
    orgId: number,
    filters: {
      account_id?: number
      category?: string
      status?: string
      source?: string
      q?: string
      limit?: number
      offset?: number
    } = {},
  ) {
    const q = new URLSearchParams()
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null && value !== '') q.set(key, String(value))
    }
    const suffix = q.toString() ? `?${q.toString()}` : ''
    const res = await fetch(`${apiRoot()}/banking/transactions${suffix}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: BankTransaction[]; total: number; limit: number; offset: number }>(res)
  },

  async triggerSync(token: string, orgId: number, connectionId?: number) {
    const res = await fetch(`${apiRoot()}/banking/sync`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify(connectionId != null ? { connection_id: connectionId } : {}),
    })
    return parse<{ ok: boolean; runs: SyncRun[] }>(res)
  },

  async listSyncRuns(token: string, orgId: number, connectionId?: number) {
    const q = connectionId != null ? `?connection_id=${connectionId}` : ''
    const res = await fetch(`${apiRoot()}/banking/sync${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{ items: SyncRun[]; total: number }>(res)
  },

  async status(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/banking/status`, {
      headers: headers(token, orgId),
    })
    return parse<BankingStatus>(res)
  },

  async health(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/banking/health`, {
      headers: headers(token, orgId),
    })
    return parse<BankingHealth>(res)
  },

  async platformOverview(token: string) {
    const res = await fetch(`${apiRoot()}/platform/banking/overview`, {
      headers: headers(token),
    })
    return parse<{
      connections_total: number
      connections_active: number
      connections_error: number
      by_provider: Array<{ provider: string; connections: number; connected: number; errors: number }>
      recent_errors: Array<Record<string, unknown>>
      runs_total: number
      runs_failed: number
      failure_rate: number
      avg_duration_ms?: number | null
      last_error?: string | null
    }>(res)
  },
}
