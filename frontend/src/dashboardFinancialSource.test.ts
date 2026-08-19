import { describe, expect, it, vi, beforeEach } from 'vitest'
import { financialApi } from './services/financialApi'

/**
 * Preuve que l’accueil doit appeler le Financial Engine
 * (et non /dashboard/stats ou /dashboard/pilot).
 */
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

describe('dashboard data source contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('charge /financial/overview (pas /dashboard/pilot)', async () => {
    mockFetch({
      computed_at: '2026-07-26T10:00:00Z',
      has_data: true,
      kpis: [],
      alerts: [],
      health: { score: 70, grade: 'B', state: 'active', components: [], message: null },
      charts: {
        revenue_vs_expenses: [],
        treasury: [],
        expense_breakdown: [],
        categories: [],
        ca_evolution: [],
      },
      trends: {},
      sync: {
        connections: 0,
        errors: 0,
        last_sync_at: null,
        age_hours: null,
        failed_runs_7d: 0,
        ok_runs_7d: 0,
        status: 'none',
      },
      documents_to_process: 0,
      recent_activity: [],
      recommendations: [],
    })
    await financialApi.overview('tok', 42)
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const url = String(call[0])
    expect(url).toContain('/financial/overview')
    expect(url).not.toContain('/dashboard/stats')
    expect(url).not.toContain('/dashboard/pilot')
    expect(call[1].headers['X-Organization-Id']).toBe('42')
  })
})
