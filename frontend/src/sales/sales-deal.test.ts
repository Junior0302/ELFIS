/**
 * SalesPilot Deal Workspace — routing helpers (S1.5).
 */
import { describe, expect, it } from 'vitest'
import { DEAL_TABS, dealPath, parseDealTab } from './salesDeal'

describe('SalesPilot deal workspace routing', () => {
  it('expose les onglets deal', () => {
    expect(DEAL_TABS.map((t) => t.id)).toEqual([
      'overview',
      'participants',
      'products',
      'activities',
      'tasks',
      'notes',
      'documents',
      'timeline',
    ])
    expect(parseDealTab('products')).toBe('products')
    expect(parseDealTab('x')).toBe('overview')
  })

  it('construit les chemins deal', () => {
    expect(dealPath(9)).toBe('/sales/deals/9')
    expect(dealPath(9, 'timeline')).toBe('/sales/deals/9?tab=timeline')
  })
})
