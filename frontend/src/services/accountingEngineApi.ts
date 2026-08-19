export type AccountingEngineProposal = {
  id: string
  status: string
  direction: string
  document_type: string
  source_document_id?: string | null
  version: number
  journal_code?: string | null
  journal_label?: string | null
  currency: string
  amount_ht?: number | null
  amount_vat?: number | null
  amount_ttc?: number | null
  vat_rate?: number | null
  lines: Array<{
    line_number: number
    account_code: string
    account_label?: string
    debit: number
    credit: number
  }>
  warnings: string[]
  errors: string[]
  comments: string[]
  explanations: string[]
  consistency: Record<string, unknown>
  confidence_score?: number | null
  confidence_detail: Record<string, unknown>
  previous_snapshot?: Record<string, unknown> | null
  disclaimer?: string
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

export const accountingEngineApi = {
  async getProposal(token: string, orgId: number, proposalId: string) {
    const q = new URLSearchParams({ proposal_id: proposalId })
    const res = await fetch(`${apiRoot()}/accounting/proposal?${q}`, {
      headers: headers(token, orgId),
    })
    const body = await parse<{ data: AccountingEngineProposal }>(res)
    return body.data
  },

  async generate(
    token: string,
    orgId: number,
    body: {
      payload?: Record<string, unknown>
      invoice_id?: number
      source_document_id?: string
      source_kind?: string
    },
  ) {
    const res = await fetch(`${apiRoot()}/accounting/generate`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify(body),
    })
    const out = await parse<{ data: AccountingEngineProposal }>(res)
    return out.data
  },

  async regenerate(
    token: string,
    orgId: number,
    proposalId: string,
    payloadOverrides?: Record<string, unknown>,
  ) {
    const res = await fetch(`${apiRoot()}/accounting/regenerate`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({
        proposal_id: proposalId,
        payload_overrides: payloadOverrides,
      }),
    })
    const out = await parse<{ data: AccountingEngineProposal }>(res)
    return out.data
  },

  async confidence(token: string, orgId: number, proposalId: string) {
    const q = new URLSearchParams({ proposal_id: proposalId })
    const res = await fetch(`${apiRoot()}/accounting/confidence?${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{ proposal_id: string; score: number | null; detail: Record<string, unknown> }>(
      res,
    )
  },

  async explanation(token: string, orgId: number, proposalId: string) {
    const q = new URLSearchParams({ proposal_id: proposalId })
    const res = await fetch(`${apiRoot()}/accounting/explanation?${q}`, {
      headers: headers(token, orgId),
    })
    const body = await parse<{ data: Record<string, unknown> }>(res)
    return body.data
  },
}
