/**
 * SalesPilot Dashboard V1 — formatting helpers (no KPI math).
 */
import { describe, expect, it } from 'vitest'
import { activityTypeLabel, formatSalesMoney } from './salesDashboard'

describe('salesDashboard helpers', () => {
  it('formatSalesMoney formate en EUR', () => {
    expect(formatSalesMoney(12000)).toMatch(/12/)
    expect(formatSalesMoney(null)).toBe('—')
  })

  it('activityTypeLabel mappe les types CRM', () => {
    expect(activityTypeLabel('call')).toBe('Appel')
    expect(activityTypeLabel('meeting')).toBe('Réunion')
    expect(activityTypeLabel('email')).toBe('Email')
    expect(activityTypeLabel('visit')).toBe('Visite')
  })
})
