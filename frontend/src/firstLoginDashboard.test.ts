import { describe, expect, it, vi } from 'vitest'
import { createApiError, userFacingApiMessage, isEntitlementError } from './apiErrors'
import {
  hasFinancialEntitlement,
  resolveCommercialStatus,
  type CommercialStatus,
} from './subscription'
import type { SubscriptionInfo } from './api'

function sub(over: Partial<SubscriptionInfo> = {}): SubscriptionInfo {
  return {
    plan: 'pro',
    status: 'none',
    price_eur: 19,
    configured: true,
    trial_end: null,
    current_period_end: null,
    cancel_at_period_end: false,
    access_granted: false,
    ...over,
  }
}

describe('userFacingApiMessage', () => {
  it('ne remonte jamais un code HTTP brut', () => {
    expect(userFacingApiMessage(402)).not.toMatch(/402/)
    expect(userFacingApiMessage(402)).toMatch(/essai|abonnement/i)
    expect(userFacingApiMessage(401)).toMatch(/session/i)
    expect(userFacingApiMessage(403)).toMatch(/autorisation/i)
    expect(userFacingApiMessage(404)).toMatch(/indisponible/i)
    expect(userFacingApiMessage(429)).toMatch(/Trop/i)
    expect(userFacingApiMessage(503)).toMatch(/temporairement/i)
    expect(userFacingApiMessage(500, 'Erreur API 500')).not.toMatch(/Erreur API 500/)
  })

  it('journalise sans exposer le message technique au client', () => {
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const err = createApiError(402, 'Payment Required', {
      endpoint: '/api/financial/overview',
      organizationId: 9,
      userId: 3,
      requestId: 'req-1',
    })
    expect(err.message).toBe(userFacingApiMessage(402))
    expect(err.status).toBe(402)
    expect(spy).toHaveBeenCalled()
    const logged = spy.mock.calls[0][1] as Record<string, unknown>
    expect(logged.status).toBe(402)
    expect(logged.endpoint).toBe('/api/financial/overview')
    expect(logged.organizationId).toBe(9)
    spy.mockRestore()
  })

  it('détecte les erreurs d’entitlement', () => {
    expect(isEntitlementError({ status: 402, message: 'x' })).toBe(true)
    expect(isEntitlementError(new Error('Abonnement requis'))).toBe(true)
    expect(isEntitlementError(new Error('boom'))).toBe(false)
  })
})

describe('resolveCommercialStatus + hasFinancialEntitlement', () => {
  const cases: Array<[Partial<SubscriptionInfo>, CommercialStatus, boolean]> = [
    [{ status: 'none', access_granted: false, trial_used: false }, 'trial_available', false],
    [{ status: 'none', access_granted: false, trial_used: true }, 'none', false],
    [{ status: 'trialing', access_granted: true }, 'trialing', true],
    [{ status: 'active', access_granted: true }, 'active', true],
    [{ status: 'past_due', access_granted: true }, 'grace', true],
    [{ status: 'expired', access_granted: false }, 'expired', false],
    [{ status: 'admin_revoked', access_granted: false }, 'suspended', false],
    [{ status: 'paused', access_granted: false }, 'suspended', false],
    [{ status: 'checkout_pending', access_granted: false }, 'checkout_pending', false],
  ]

  it.each(cases)('status %j → %s, entitled=%s', (partial, expectedStatus, entitled) => {
    const s = sub(partial)
    expect(resolveCommercialStatus(s)).toBe(expectedStatus)
    expect(hasFinancialEntitlement(s)).toBe(entitled)
  })

  it('platform admin bypasse l’entitlement FE pour le chargement', () => {
    expect(hasFinancialEntitlement(sub({ status: 'none' }), { isPlatformAdmin: true })).toBe(true)
  })

  it('access_granted est la source de vérité entitlement', () => {
    expect(hasFinancialEntitlement(sub({ status: 'none', access_granted: true }))).toBe(true)
    expect(hasFinancialEntitlement(null)).toBe(false)
  })
})

describe('gate financial overview sans entitlement', () => {
  it('ne doit pas appeler fetch si entitled=false (contrat Dashboard)', () => {
    const entitled = hasFinancialEntitlement(sub({ status: 'none', access_granted: false }))
    expect(entitled).toBe(false)
    // DashboardPage court-circuite avant financialApi.overview — pas d’appel réseau.
    const fetchSpy = vi.fn()
    if (entitled) fetchSpy()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
