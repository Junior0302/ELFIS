export type SmartDashboard = {
  migration_id: string
  smart_run_id?: string | null
  status: string
  documents_total: number
  documents_completed: number
  documents_pending: number
  documents_failed: number
  documents_imported: number
  documents_awaiting?: number
  progress_percent: number
  eta_seconds?: number | null
  throughput_per_min: number
  avg_duration_ms: number
  active_batches: number
  active_workers: number
  estimated_cost: number
  actual_cost: number
  batches: Array<{
    batch_id: string
    batch_index: number
    status: string
    documents: number
    completed: number
    failed: number
    progress_percent: number
  }>
  chart: { labels: string[]; values: number[] }
  computed_at?: string
  correlation_id?: string | null
}

export type SmartReport = {
  id: string
  version: number
  format: string
  summary: Record<string, unknown>
  stats: Record<string, unknown>
  created_objects: unknown[]
  linked_objects: unknown[]
  errors: unknown[]
  warnings: unknown[]
  csv?: string
  pdf_base64?: string
  created_at?: string | null
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
    throw new Error(msg)
  }
  return body as T
}

export const smartMigrationApi = {
  async status(token: string, orgId: number, migrationId: string) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/status?${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{
      migration_id: string
      smart_run_id?: string | null
      status: string
      progress: Record<string, unknown>
      correlation_id?: string | null
    }>(res)
  },

  async dashboard(token: string, orgId: number, migrationId: string) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/dashboard?${q}`, {
      headers: headers(token, orgId),
    })
    const body = await parse<{ data: SmartDashboard }>(res)
    return body.data
  },

  async metrics(token: string, orgId: number, migrationId: string) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/metrics?${q}`, {
      headers: headers(token, orgId),
    })
    const body = await parse<{ data: Record<string, unknown> }>(res)
    return body.data
  },

  async report(token: string, orgId: number, migrationId: string, format = 'json') {
    const q = new URLSearchParams({ migration_id: migrationId, format })
    const res = await fetch(`${apiRoot()}/migration/report?${q}`, {
      headers: headers(token, orgId),
    })
    const body = await parse<{ data: SmartReport }>(res)
    return body.data
  },

  async start(
    token: string,
    orgId: number,
    migrationId: string,
    opts: { batch_size?: number; max_workers?: number; parallel?: boolean; run_now?: boolean } = {},
  ) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/start?${q}`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({
        batch_size: opts.batch_size ?? 25,
        max_workers: opts.max_workers ?? 4,
        parallel: opts.parallel ?? false,
        run_now: opts.run_now ?? true,
      }),
    })
    return parse<{ smart_run_id: string; status: string; progress_percent: number }>(res)
  },

  async resume(token: string, orgId: number, migrationId: string) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/resume?${q}`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<{ smart_run_id: string; status: string; progress_percent: number }>(res)
  },

  async cancel(token: string, orgId: number, migrationId: string) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/cancel?${q}`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<{ smart_run_id: string; status: string }>(res)
  },

  async retryFailed(token: string, orgId: number, migrationId: string) {
    const q = new URLSearchParams({ migration_id: migrationId })
    const res = await fetch(`${apiRoot()}/migration/retry_failed?${q}`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: '{}',
    })
    return parse<{ smart_run_id: string; status: string }>(res)
  },
}
