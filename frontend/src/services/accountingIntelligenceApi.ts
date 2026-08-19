import { accountingEngineApi } from './accountingEngineApi'

export type IntelligenceRecommendation = {
  recommendation_id?: string
  proposal_id?: string | null
  recommendation?: {
    account_code?: string | null
    journal_code?: string | null
    vat_rate?: number | null
    score?: number
    primary_source?: string
    reason?: string
    accounts?: Record<string, string>
    similarity?: Array<Record<string, unknown>>
    disclaimer?: string
  }
  explanation?: {
    narrative?: string
    why_account?: string
    why_vat?: string
    why_journal?: string
    why_score?: string
    why_confidence?: string
  }
  confidence?: {
    score?: number
    detail?: Record<string, number>
    reasons?: string[]
  }
  context?: Record<string, unknown>
  comparison?: Record<string, unknown> | null
  disclaimer?: string
  items?: Array<Record<string, unknown>>
  learned?: boolean
  learn_gate?: string
  feedback_id?: string
  action?: string
  matches?: Array<Record<string, unknown>>
  optimizations?: Record<string, unknown>
}

function apiRoot(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/$/, '')
  return '/api'
}

function headers(token: string, orgId?: number | null, json = false): HeadersInit {
  const h: Record<string, string> = { Authorization: `Bearer ${token}` }
  if (orgId != null) h['X-Organization-Id'] = String(orgId)
  if (json) h['Content-Type'] = 'application/json'
  return h
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!res.ok) {
    let msg = text
    try {
      const j = JSON.parse(text)
      msg = j?.detail?.message || j?.detail || text
    } catch {
      /* ignore */
    }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return text ? JSON.parse(text) : ({} as T)
}

export const accountingIntelligenceApi = {
  async recommendations(
    token: string,
    orgId: number,
    body?: {
      payload?: Record<string, unknown>
      proposal_id?: string
      generate_proposal?: boolean
    },
  ): Promise<IntelligenceRecommendation> {
    if (body?.payload || body?.proposal_id || body?.generate_proposal) {
      const res = await fetch(`${apiRoot()}/accounting/intelligence/recommendations`, {
        method: 'POST',
        headers: headers(token, orgId, true),
        body: JSON.stringify(body || {}),
      })
      const j = await parse<{ data: IntelligenceRecommendation }>(res)
      return j.data
    }
    const res = await fetch(`${apiRoot()}/accounting/intelligence/recommendations`, {
      headers: headers(token, orgId),
    })
    const j = await parse<{ data: IntelligenceRecommendation }>(res)
    return j.data
  },

  async explanations(
    token: string,
    orgId: number,
    params: { recommendation_id?: string; proposal_id?: string },
  ): Promise<Record<string, unknown>> {
    const q = new URLSearchParams()
    if (params.recommendation_id) q.set('recommendation_id', params.recommendation_id)
    if (params.proposal_id) q.set('proposal_id', params.proposal_id)
    const res = await fetch(
      `${apiRoot()}/accounting/intelligence/explanations?${q}`,
      { headers: headers(token, orgId) },
    )
    const j = await parse<{ data: Record<string, unknown> }>(res)
    return j.data
  },

  async learning(token: string, orgId: number): Promise<Record<string, unknown>> {
    const res = await fetch(`${apiRoot()}/accounting/intelligence/learning`, {
      headers: headers(token, orgId),
    })
    const j = await parse<{ data: Record<string, unknown> }>(res)
    return j.data
  },

  async feedback(
    token: string,
    orgId: number,
    body: {
      action: 'accept' | 'modify' | 'reject'
      recommendation_id?: string
      proposal_id?: string
      validation_seconds?: number
      comment?: string
      modifications?: Record<string, unknown>
    },
  ): Promise<IntelligenceRecommendation> {
    const res = await fetch(`${apiRoot()}/accounting/intelligence/feedback`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify(body),
    })
    const j = await parse<{ data: IntelligenceRecommendation }>(res)
    return j.data
  },

  async retrain(token: string, orgId: number): Promise<Record<string, unknown>> {
    const res = await fetch(`${apiRoot()}/accounting/intelligence/retrain`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({}),
    })
    const j = await parse<{ data: Record<string, unknown> }>(res)
    return j.data
  },

  async similarity(
    token: string,
    orgId: number,
    payload: Record<string, unknown>,
  ): Promise<IntelligenceRecommendation> {
    const res = await fetch(`${apiRoot()}/accounting/intelligence/similarity`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ payload, limit: 5 }),
    })
    const j = await parse<{ data: IntelligenceRecommendation }>(res)
    return j.data
  },
}

// Réutilise le client moteur pour comparaison éventuelle
export { accountingEngineApi }
