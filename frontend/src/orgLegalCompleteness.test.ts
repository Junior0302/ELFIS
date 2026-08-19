import { describe, expect, it } from 'vitest'
import { orgLegalGaps, orgLegalIsReadyForSend } from './orgLegalCompleteness'

describe('orgLegalCompleteness', () => {
  it('signale SIRET et adresse manquants', () => {
    const gaps = orgLegalGaps({ name: 'Demo', siren: '', address: '', postal_code: '', city: '' })
    expect(gaps.map((g) => g.code)).toEqual(expect.arrayContaining(['siren', 'address']))
    expect(orgLegalIsReadyForSend({ name: 'Demo' })).toBe(false)
  })

  it('accepte org complète (mentions libres optionnelles soft)', () => {
    const org = {
      legal_name: 'Demo SAS',
      siren: '12345678900012',
      address: '1 rue Test',
      postal_code: '75001',
      city: 'Paris',
      legal_mentions: '',
    }
    expect(orgLegalIsReadyForSend(org)).toBe(true)
    expect(orgLegalGaps(org).some((g) => g.code === 'legal_mentions')).toBe(true)
  })
})
