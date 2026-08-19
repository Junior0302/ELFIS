import { describe, expect, it, vi, beforeEach } from 'vitest'
import { accountingEngineApi } from '../services/accountingEngineApi'

describe('accounting engine API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('génère une proposition', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            data: {
              id: 'p1',
              status: 'generated',
              direction: 'purchase',
              document_type: 'invoice',
              version: 1,
              journal_code: 'ACH',
              journal_label: 'Achats',
              currency: 'EUR',
              amount_ht: 100,
              amount_vat: 20,
              amount_ttc: 120,
              vat_rate: 20,
              lines: [{ line_number: 1, account_code: '606', debit: 100, credit: 0 }],
              warnings: [],
              errors: [],
              comments: [],
              explanations: ['ok'],
              consistency: { balanced: true },
              confidence_score: 0.82,
              confidence_detail: {},
              disclaimer: 'Proposition uniquement',
            },
          }),
      }),
    )
    const p = await accountingEngineApi.generate('tok', 1, {
      payload: { amount_ht: 100, amount_ttc: 120 },
    })
    expect(p.journal_code).toBe('ACH')
    expect(p.confidence_score).toBeGreaterThan(0.5)
  })
})
