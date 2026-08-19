import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  financialApi,
  formatEuro,
  formatKpiValue,
  severityLabel,
  type Kpi,
} from '../services/financialApi'

function mockFetch(payload: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status,
      url: 'http://localhost/api/financial/overview',
      headers: { get: () => null },
      text: async () => JSON.stringify(payload),
    }),
  )
}

const kpi = (over: Partial<Kpi> = {}): Kpi => ({
  id: 'tresorerie',
  label: 'Trésorerie',
  value: 12000,
  unit: 'EUR',
  format: 'currency',
  status: 'ok',
  trend: { direction: 'up', delta: 2500, delta_pct: 26.3, previous: 9500 },
  hint: '',
  ...over,
})

describe('financial API', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('charge la vue d’ensemble complète', async () => {
    mockFetch({
      computed_at: '2026-07-26T10:00:00Z',
      has_data: true,
      kpis: [kpi()],
      alerts: [],
      health: { score: 82.9, grade: 'A', state: 'active', components: [], message: null },
      charts: {
        revenue_vs_expenses: [],
        treasury: [],
        expense_breakdown: [],
        categories: [],
        ca_evolution: [],
      },
      trends: {},
      sync: { connections: 1, errors: 0, last_sync_at: null, age_hours: 2, failed_runs_7d: 0, ok_runs_7d: 1, status: 'fresh' },
      documents_to_process: 1,
      recent_activity: [],
      recommendations: [],
    })
    const data = await financialApi.overview('tok', 1)
    expect(data.health.grade).toBe('A')
    expect(data.kpis[0].id).toBe('tresorerie')
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(String(call[0])).toContain('/financial/overview')
    expect(call[1].headers['X-Organization-Id']).toBe('1')
  })

  it('demande un recalcul avec refresh=true', async () => {
    mockFetch({ kpis: [] })
    await financialApi.kpis('tok', 1, true)
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(String(call[0])).toContain('/financial/kpis?refresh=true')
  })

  it('charge tendances, graphiques, alertes et score', async () => {
    mockFetch({ monthly: { points: [], comparison: {} }, weekly: {}, yearly: {} })
    const trends = await financialApi.trends('tok', 1)
    expect(trends.monthly.points).toEqual([])

    mockFetch({ score: 55, grade: 'C', state: 'active', components: [], message: null })
    const health = await financialApi.healthScore('tok', 1)
    expect(health.grade).toBe('C')

    mockFetch({ alerts: [{ id: '1-treasury_low', code: 'TREASURY_LOW', severity: 'warning', title: 'Trésorerie faible', message: '', action: '', source: 'financial_engine', value: 3000, created_at: '2026-07-26' }] })
    const alerts = await financialApi.alerts('tok', 1)
    expect(alerts.alerts[0].code).toBe('TREASURY_LOW')
  })

  it('charge la vue plateforme', async () => {
    mockFetch({
      organizations_total: 3,
      organizations_active: 2,
      organizations_setup: 1,
      average_score: 71.5,
      organizations_without_sync: 1,
      sync_errors: 0,
      critical_alerts: 1,
      warning_alerts: 2,
      organizations: [],
    })
    const data = await financialApi.platformOverview('tok')
    expect(data.average_score).toBe(71.5)
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(String(call[0])).toContain('/platform/financial/overview')
  })

  it('remonte les erreurs API avec le message backend', async () => {
    mockFetch({ detail: 'Organisation requise' }, false, 400)
    await expect(financialApi.overview('tok', 1)).rejects.toThrow('Organisation requise')
  })

  it('traduit le 402 sans exposer le code HTTP', async () => {
    mockFetch({ detail: 'Payment Required' }, false, 402)
    const err = await financialApi.overview('tok', 1).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(Error)
    expect((err as Error).message).toMatch(/essai ou un abonnement/i)
    expect((err as Error).message).not.toMatch(/402/)
    expect((err as Error & { status: number }).status).toBe(402)
  })

  it('formate les valeurs sans calculer (affichage uniquement)', () => {
    expect(formatEuro(12000)).toContain('12')
    expect(formatKpiValue(kpi())).toContain('€')
    expect(formatKpiValue(kpi({ format: 'integer', unit: 'count', value: 3 }))).toBe('3')
    expect(severityLabel('critical')).toBe('Critique')
    expect(severityLabel('warning')).toBe('Vigilance')
  })
})
