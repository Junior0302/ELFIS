/**
 * SalesPilot Pipeline — routing + type surface (S1.3).
 */
import { describe, expect, it } from 'vitest'
import { SALES_NAV_ITEMS } from './salesNavModel'

describe('SalesPilot pipeline shell', () => {
  it('expose la route Pipeline', () => {
    expect(SALES_NAV_ITEMS.some((i) => i.to === '/sales/pipeline')).toBe(true)
  })
})
