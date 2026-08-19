/**
 * SalesPilot Commercial Proposal Engine — routing helpers (S1.6).
 */
import { describe, expect, it } from 'vitest'
import { SALES_NAV_ITEMS } from './salesNavModel'
import { proposalNewPath, proposalPath } from './salesProposals'

describe('SalesPilot proposals', () => {
  it('expose la navigation Proposals', () => {
    expect(SALES_NAV_ITEMS.some((i) => i.to === '/sales/proposals')).toBe(true)
  })

  it('construit les chemins proposition', () => {
    expect(proposalPath(12)).toBe('/sales/proposals/12')
    expect(proposalNewPath(5)).toBe('/sales/proposals/new?opportunity_id=5')
    expect(proposalNewPath()).toBe('/sales/proposals/new')
  })
})
