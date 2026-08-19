import { describe, expect, it } from 'vitest'
import { detectProvenance, mapOverviewToHome } from './dashboardHome'
import type { FinancialOverview } from './services/financialApi'

function sampleOverview(over: Partial<FinancialOverview> = {}): FinancialOverview {
  return {
    computed_at: '2026-07-26T10:00:00Z',
    has_data: true,
    kpis: [
      {
        id: 'tresorerie',
        label: 'Trésorerie',
        value: 12000,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 12000 },
        hint: '',
      },
      {
        id: 'revenus',
        label: 'Revenus',
        value: 14000,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'up', delta: 1000, delta_pct: 7, previous: 13000 },
        hint: '',
      },
      {
        id: 'depenses',
        label: 'Dépenses',
        value: 4000,
        unit: 'EUR',
        format: 'currency',
        status: 'neutral',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 4000 },
        hint: '',
      },
      {
        id: 'resultat',
        label: 'Résultat',
        value: 8500,
        unit: 'EUR',
        format: 'currency',
        status: 'ok',
        trend: { direction: 'up', delta: 500, delta_pct: 6, previous: 8000 },
        hint: '',
      },
      {
        id: 'tva_estimee',
        label: 'TVA estimée',
        value: 2560,
        unit: 'EUR',
        format: 'currency',
        status: 'neutral',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        hint: '',
      },
      {
        id: 'factures_impayees',
        label: 'Factures impayées',
        value: 1,
        unit: 'count',
        format: 'integer',
        status: 'warning',
        trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
        hint: '3600 €',
      },
    ],
    alerts: [
      {
        id: '1-overdue',
        code: 'INVOICE_OVERDUE',
        severity: 'warning',
        title: 'Factures clients impayées',
        message: '1 facture',
        action: 'Relancer',
        source: 'financial_engine',
        value: 3600,
        created_at: '2026-07-26T10:00:00Z',
      },
    ],
    health: {
      score: 82,
      grade: 'A',
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
      last_sync_at: '2026-07-26T08:00:00Z',
      age_hours: 2,
      failed_runs_7d: 0,
      ok_runs_7d: 1,
      status: 'fresh',
    },
    documents_to_process: 1,
    recent_activity: [
      {
        type: 'transaction',
        label: 'LOYER',
        amount: -2000,
        date: '2026-07-05',
        meta: 'loyer',
        created_at: '2026-07-05T00:00:00Z',
      },
    ],
    recommendations: ['Maintenir le suivi'],
    ...over,
  }
}

describe('dashboardHome ← Financial Engine', () => {
  it('mappe les KPI moteur sans valeurs codées en dur', () => {
    const view = mapOverviewToHome(sampleOverview())
    const tresorerie = view.kpis.find((k) => k.id === 'tresorerie')
    const revenus = view.kpis.find((k) => k.id === 'revenus')
    expect(tresorerie?.display).toContain('12')
    expect(revenus?.display).toContain('14')
    // Pas de CA magique type 205000
    expect(view.kpis.every((k) => !k.display.includes('205'))).toBe(true)
  })

  it('expose Health Score et alertes du moteur', () => {
    const view = mapOverviewToHome(sampleOverview())
    expect(view.healthScore).toBe(82)
    expect(view.healthGrade).toBe('A')
    expect(view.alerts[0].code).toBe('INVOICE_OVERDUE')
    expect(view.syncStatus).toBe('fresh')
    expect(view.documentsToProcess).toBe(1)
  })

  it('détecte provenance incomplete / unsynced / real', () => {
    expect(detectProvenance(sampleOverview({ has_data: false }))).toBe('incomplete')
    expect(
      detectProvenance(
        sampleOverview({
          sync: {
            connections: 1,
            errors: 0,
            last_sync_at: null,
            age_hours: null,
            failed_runs_7d: 0,
            ok_runs_7d: 0,
            status: 'stale',
          },
        }),
      ),
    ).toBe('unsynced')
    expect(detectProvenance(sampleOverview())).toBe('real')
  })

  it('ne duplique pas toute la page finance (vue synthétique bornée)', () => {
    const view = mapOverviewToHome(sampleOverview())
    expect(view.kpis).toHaveLength(6)
    expect(view.alerts.length).toBeLessThanOrEqual(5)
    expect(view.recentActivity.length).toBeLessThanOrEqual(6)
  })
})
