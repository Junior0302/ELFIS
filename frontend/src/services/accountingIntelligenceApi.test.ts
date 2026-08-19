import { describe, expect, it, vi, beforeEach } from 'vitest'
import { accountingIntelligenceApi } from '../services/accountingIntelligenceApi'

describe('accounting intelligence API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('génère une recommandation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            data: {
              recommendation_id: 'r1',
              recommendation: {
                account_code: '606',
                journal_code: 'ACH',
                vat_rate: 20,
                score: 0.8,
                primary_source: 'rules',
                reason: 'ok',
              },
              explanation: { narrative: 'Compte 606 via règles.' },
              confidence: { score: 0.82, detail: { similarity: 0.5 } },
            },
          }),
      }),
    )
    const r = await accountingIntelligenceApi.recommendations('tok', 1, {
      payload: { amount_ht: 100 },
    })
    expect(r.recommendation?.journal_code).toBe('ACH')
    expect(r.confidence?.score).toBeGreaterThan(0.5)
  })
})
