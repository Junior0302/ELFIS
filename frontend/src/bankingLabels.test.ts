import { describe, expect, it } from 'vitest'
import { FICTIONAL_BANK_LABEL, isFictionalBankProvider, providerPublicLabel } from './bankingLabels'

describe('bankingLabels', () => {
  it('identifie uniquement le provider demo comme fictif', () => {
    expect(isFictionalBankProvider('demo')).toBe(true)
    expect(isFictionalBankProvider('bridge')).toBe(false)
  })

  it('affiche le libellé fictif et la configuration requise Bridge', () => {
    expect(
      providerPublicLabel({
        provider: 'demo',
        display_name: 'Banque Démo ELFIS',
        status: 'ok',
        fictional: true,
      }),
    ).toBe(FICTIONAL_BANK_LABEL)
    expect(
      providerPublicLabel({
        provider: 'bridge',
        display_name: 'Bridge',
        status: 'not_configured',
      }),
    ).toBe('Bridge — configuration requise')
  })
})
