/**
 * SalesPilot Collaboration V1 — helpers smoke.
 */
import { describe, expect, it } from 'vitest'
import { formatMention } from './salesCollab'
import { SALES_NAV_ITEMS } from './salesNavModel'

describe('salesCollab', () => {
  it('formatMention produit le token backend', () => {
    expect(formatMention(42, 'Ada Lovelace')).toBe('@[42:Ada Lovelace]')
  })

  it('nav collab S1.9 — routes équipe/vues hors menu principal (NAV.DOMAIN.1)', () => {
    const tos = SALES_NAV_ITEMS.map((i) => i.to)
    expect(tos).not.toContain('/sales/team')
    expect(tos).not.toContain('/sales/collab/views')
  })
})
