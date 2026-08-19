import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  extractCanonicalFinancialFacts,
  mapOverviewToHome,
} from './dashboardHome'
import type { FinancialOverview } from './services/financialApi'
import { financialApi } from './services/financialApi'

function sampleOverview(): FinancialOverview {
  return {
    computed_at: '2026-07-26T12:00:00Z',
    has_data: true,
    kpis: [
      {
        id: 'tresorerie',
        label: 'Trésorerie',
        value: 15000,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 15000 },
        hint: '',
      },
      {
        id: 'revenus',
        label: 'Revenus',
        value: 42000,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'up', delta: 2000, delta_pct: 5, previous: 40000 },
        hint: '',
      },
      {
        id: 'depenses',
        label: 'Dépenses',
        value: 8000,
        unit: 'EUR',
        format: 'currency',
        status: 'neutral',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 8000 },
        hint: '',
      },
      {
        id: 'resultat',
        label: 'Résultat',
        value: 12000,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        hint: '',
      },
      {
        id: 'tva_estimee',
        label: 'TVA',
        value: 3000,
        unit: 'EUR',
        format: 'currency',
        status: 'neutral',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        hint: '',
      },
      {
        id: 'factures_impayees',
        label: 'Impayées',
        value: 2,
        unit: 'count',
        format: 'integer',
        status: 'warning',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        hint: '4800 €',
      },
    ],
    alerts: [
      {
        id: 'a1',
        code: 'INVOICE_OVERDUE',
        severity: 'warning',
        title: 'Impayés',
        message: '2 factures',
        action: 'Relancer',
        source: 'financial_engine',
        value: 4800,
        created_at: '2026-07-26T12:00:00Z',
      },
    ],
    health: {
      score: 77,
      grade: 'B',
      state: 'active',
      components: [],
      message: null,
    },
    charts: {
      revenue_vs_expenses: [],
      treasury: [],
      expense_breakdown: [],
      categories: [],
      ca_evolution: [],
    },
    trends: {
      monthly: {
        points: [],
        comparison: {
          revenue: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          expenses: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          result: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        },
      },
      weekly: {
        points: [],
        comparison: {
          revenue: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          expenses: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          result: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        },
      },
      yearly: {
        points: [],
        comparison: {
          revenue: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          expenses: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
          result: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        },
      },
    },
    sync: {
      connections: 1,
      errors: 0,
      last_sync_at: '2026-07-26T10:00:00Z',
      age_hours: 2,
      failed_runs_7d: 0,
      ok_runs_7d: 1,
      status: 'fresh',
    },
    documents_to_process: 4,
    recent_activity: [],
    recommendations: [],
  }
}

describe('surfaces client — même source de vérité Financial Engine', () => {
  it('Accueil et Cockpit dérivent les mêmes faits d’un même overview', () => {
    const overview = sampleOverview()
    const facts = extractCanonicalFinancialFacts(overview)
    const home = mapOverviewToHome(overview)
    // Cockpit réutilise mapOverviewToHome — mêmes KPI / score / alertes
    expect(facts.tresorerie).toBe(15000)
    expect(facts.revenus).toBe(42000)
    expect(facts.factures_impayees).toBe(2)
    expect(facts.healthScore).toBe(77)
    expect(facts.alertCodes).toEqual(['INVOICE_OVERDUE'])

    expect(home.kpis.find((k) => k.id === 'tresorerie')?.display).toContain('15')
    expect(home.kpis.find((k) => k.id === 'revenus')?.display).toContain('42')
    expect(home.kpis.find((k) => k.id === 'factures_impayees')?.display).toBe('2')
    expect(home.healthScore).toBe(facts.healthScore)
    expect(home.alerts.map((a) => a.code).sort()).toEqual(facts.alertCodes)
  })

  it('financialApi.overview est le contrat Accueil + Cockpit (pas /dashboard/*)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () => JSON.stringify(sampleOverview()),
      }),
    )
    await financialApi.overview('tok', 7)
    const url = String((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0])
    expect(url).toContain('/financial/overview')
    expect(url).not.toMatch(/\/dashboard\/(stats|pilot)/)
  })
})

describe('api legacy dashboard absente du client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('api.dashboard et api.dashboardPilot ne sont plus exportés comme méthodes actives', async () => {
    const { api } = await import('./api')
    expect('dashboard' in api).toBe(false)
    expect('dashboardPilot' in api).toBe(false)
  })
})
