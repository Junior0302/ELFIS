import { describe, expect, it } from 'vitest'
import { isPublicProductPath, isWelcomePath } from '../productPhase'

describe('Welcome routing helpers — Sprint 2.3', () => {
  it('autorise les surfaces publiques sans entitlement', () => {
    expect(isPublicProductPath('/welcome')).toBe(true)
    expect(isPublicProductPath('/abonnement')).toBe(true)
    expect(isPublicProductPath('/compte')).toBe(true)
  })

  it('refuse les routes métier comme surfaces publiques', () => {
    expect(isPublicProductPath('/dashboard')).toBe(false)
    expect(isPublicProductPath('/finance')).toBe(false)
    expect(isPublicProductPath('/facturation')).toBe(false)
    expect(isPublicProductPath('/onboarding/entreprise')).toBe(false)
    expect(isWelcomePath('/welcome')).toBe(true)
  })
})
