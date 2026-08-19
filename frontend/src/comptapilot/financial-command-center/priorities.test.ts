import { describe, expect, it } from 'vitest'
import { buildDayPriorities, mapAlertSeverityToHierarchy } from './priorities'
import type { FinancialOverview } from '../../services/financialApi'

function overview(over: Partial<FinancialOverview> = {}): FinancialOverview {
  return {
    computed_at: '2026-08-02T10:00:00Z',
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
    ...over,
  }
}

describe('buildDayPriorities', () => {
  it('mappe la sévérité des alertes', () => {
    expect(mapAlertSeverityToHierarchy('critical')).toBe('critical')
    expect(mapAlertSeverityToHierarchy('warning')).toBe('high')
    expect(mapAlertSeverityToHierarchy('info')).toBe('info')
  })

  it('dérive priorités depuis alertes, impayés, docs et sync', () => {
    const list = buildDayPriorities(
      overview({
        alerts: [
          {
            id: 'a1',
            code: 'INVOICE_OVERDUE',
            severity: 'critical',
            title: 'Impayés critiques',
            message: '3 factures',
            action: 'Relancer',
            source: 'engine',
            value: 1200,
            created_at: '2026-08-02T10:00:00Z',
          },
        ],
        kpis: [
          {
            id: 'factures_impayees',
            label: 'Impayées',
            value: 2,
            unit: 'count',
            format: 'integer',
            status: 'warning',
            trend: { direction: 'flat', delta: 0, delta_pct: null, previous: 0 },
            hint: '',
          },
        ],
        documents_to_process: 4,
        sync: {
          connections: 1,
          errors: 2,
          last_sync_at: null,
          age_hours: null,
          failed_runs_7d: 1,
          ok_runs_7d: 0,
          status: 'error',
        },
      }),
    )
    expect(list[0]?.level).toBe('critical')
    expect(list.some((p) => p.id === 'docs:to_process')).toBe(true)
    expect(list.some((p) => p.id === 'bank:sync_error')).toBe(true)
    expect(list.every((p) => p.href.startsWith('/'))).toBe(true)
  })

  it('retourne vide si aucun signal', () => {
    expect(buildDayPriorities(overview())).toEqual([])
  })
})
