import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  aiAssistantApi,
  confidenceLabel,
  feedbackLabel,
} from '../services/aiAssistantApi'

function mockFetch(payload: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status,
      text: async () => JSON.stringify(payload),
    }),
  )
}

describe('aiAssistantApi', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('envoie une question au Decision Engine', async () => {
    mockFetch({
      ok: true,
      agent: 'AI Financial Assistant',
      answer: 'Faits vérifiés…',
      structured: {
        facts: ['Trésorerie : 12000'],
        estimates: [],
        recommendations: [],
        missing: [],
        summary: 'OK',
        confidence: 'high',
        sources: ['get_cashflow'],
        tools_used: ['get_cashflow'],
        actions: [],
        data_as_of: null,
      },
      conversation_id: 1,
      message_id: 'msg-1',
      run_id: 'run-1',
      confidence: 'high',
      sources: ['get_cashflow'],
      tools_used: ['get_cashflow'],
      actions: [],
    })
    const res = await aiAssistantApi.chat('tok', 1, 'Quelle est ma trésorerie ?')
    expect(res.structured.facts[0]).toContain('12000')
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(String(call[0])).toContain('/ai/chat')
    expect(JSON.parse(call[1].body).question).toContain('trésorerie')
  })

  it('liste les outils et le contexte', async () => {
    mockFetch({ ok: true, tools: [{ name: 'get_cashflow', description: 'x', parameters: {} }] })
    const tools = await aiAssistantApi.tools('tok', 1)
    expect(tools.tools[0].name).toBe('get_cashflow')

    mockFetch({ ok: true, context: { intent: 'overview' } })
    const ctx = await aiAssistantApi.context('tok', 1)
    expect(ctx.context.intent).toBe('overview')
  })

  it('envoie un feedback', async () => {
    mockFetch({ ok: true, feedback: { id: 'fb1', kind: 'useful' } })
    const res = await aiAssistantApi.feedback('tok', 1, 'msg-1', 'useful', 'top')
    expect(res.feedback.kind).toBe('useful')
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(String(call[0])).toContain('/ai/feedback')
  })

  it('remonte les erreurs API', async () => {
    mockFetch({ detail: 'Permission ai.analysis requise' }, false, 403)
    await expect(aiAssistantApi.chat('tok', 1, 'hello world')).rejects.toThrow('Permission')
  })

  it('traduit confiance et feedback', () => {
    expect(confidenceLabel('high')).toBe('Élevée')
    expect(feedbackLabel('incorrect')).toBe('Incorrect')
  })
})
