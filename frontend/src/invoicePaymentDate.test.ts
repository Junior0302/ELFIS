import { describe, expect, it } from 'vitest'
import { isoDateToPaidAt } from './components/invoicePaymentDate'

describe('isoDateToPaidAt', () => {
  it('convertit ISO vers DD-MM-YYYY', () => {
    expect(isoDateToPaidAt('2026-07-15')).toBe('15-07-2026')
  })
})
