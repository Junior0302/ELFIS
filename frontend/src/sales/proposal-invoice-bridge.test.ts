/** ProposalConversionPanel — S1.6.1 smoke + helpers */
import { describe, expect, it } from 'vitest'
import { invoiceFromProposalPath } from './salesProposals'

describe('Proposal invoice bridge helpers', () => {
  it('construit le lien ComptaPilot facture', () => {
    expect(invoiceFromProposalPath(42)).toBe('/facturation?doc=42')
  })
})
