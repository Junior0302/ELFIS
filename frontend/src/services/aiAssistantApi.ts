// Client API AI Financial Assistant V1 — le LLM n'est jamais la source de vérité.

export type ConfidenceLevel = 'high' | 'medium' | 'low'

export type ProposedAction = {
  id: string
  label: string
  href: string
  requires_confirmation: boolean
  description: string
}

export type Explanation = {
  why: string
  data_used: string[]
  calculation: string
  confidence: ConfidenceLevel
  data_as_of: string | null
}

export type Recommendation = {
  text: string
  explanation: Explanation
  action: ProposedAction | null
}

export type StructuredAnswer = {
  facts: string[]
  estimates: string[]
  recommendations: Recommendation[]
  missing: string[]
  summary: string
  confidence: ConfidenceLevel
  sources: string[]
  tools_used: string[]
  actions: ProposedAction[]
  data_as_of: string | null
}

export type ChatResponse = {
  ok: boolean
  agent: string
  answer: string
  structured: StructuredAnswer
  conversation_id: number | null
  message_id: string | null
  run_id: string
  confidence: ConfidenceLevel
  sources: string[]
  tools_used: string[]
  actions: ProposedAction[]
  metrics?: {
    latency_ms: number
    llm_called: boolean
    estimated_cost: number | null
    tools_called: string[]
    cache_hit: boolean
  }
  cache_hit?: boolean
}

export type HistoryItem = {
  id: string
  question: string
  answer: string
  structured: StructuredAnswer | null
  tools_used: string[]
  sources: string[]
  confidence: string
  conversation_id: number | null
  created_at: string | null
}

export type ToolSpec = {
  name: string
  description: string
  parameters: Record<string, unknown>
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
    const msg = typeof detail === 'string' ? detail : `Erreur API ${res.status}`
    const err = new Error(msg) as Error & { status?: number }
    err.status = res.status
    throw err
  }
  return body as T
}

export const confidenceLabel = (c: ConfidenceLevel | string): string => {
  const map: Record<string, string> = {
    high: 'Élevée',
    medium: 'Moyenne',
    low: 'Faible',
  }
  return map[c] || c
}

export const feedbackLabel = (kind: string): string => {
  const map: Record<string, string> = {
    useful: 'Utile',
    useless: 'Inutile',
    incorrect: 'Incorrect',
  }
  return map[kind] || kind
}

export const aiAssistantApi = {
  async chat(token: string, orgId: number, question: string) {
    const res = await fetch(`${apiRoot()}/ai/chat`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ question, stream: false }),
    })
    return parse<ChatResponse>(res)
  },

  async context(token: string, orgId: number, question = "vue d'ensemble") {
    const q = new URLSearchParams({ question })
    const res = await fetch(`${apiRoot()}/ai/context?${q}`, {
      headers: headers(token, orgId),
    })
    return parse<{ ok: boolean; context: Record<string, unknown> }>(res)
  },

  async tools(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/ai/tools`, {
      headers: headers(token, orgId),
    })
    return parse<{ ok: boolean; tools: ToolSpec[] }>(res)
  },

  async history(token: string, orgId: number, limit = 20) {
    const res = await fetch(`${apiRoot()}/ai/history?limit=${limit}`, {
      headers: headers(token, orgId),
    })
    return parse<{ ok: boolean; items: HistoryItem[] }>(res)
  },

  async feedback(
    token: string,
    orgId: number,
    messageId: string,
    kind: 'useful' | 'useless' | 'incorrect',
    comment = '',
  ) {
    const res = await fetch(`${apiRoot()}/ai/feedback`, {
      method: 'POST',
      headers: headers(token, orgId, true),
      body: JSON.stringify({ message_id: messageId, kind, comment }),
    })
    return parse<{ ok: boolean; feedback: { id: string; kind: string } }>(res)
  },

  async suggestions(token: string, orgId: number) {
    const res = await fetch(`${apiRoot()}/ai/suggestions`, {
      headers: headers(token, orgId),
    })
    return parse<{ agent: string; suggestions: string[] }>(res)
  },
}
