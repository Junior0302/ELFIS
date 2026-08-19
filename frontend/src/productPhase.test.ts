import { describe, expect, it } from 'vitest'
import type { SubscriptionInfo } from './api'
import {
  isPublicProductPath,
  isWelcomePath,
  resolveProductPhase,
} from './productPhase'

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

describe('resolveProductPhase — Sprint 2.3', () => {
  it('loading tant que l’abonnement n’est pas résolu', () => {
    expect(resolveProductPhase(null, { subscriptionLoading: true })).toBe('loading')
  })

  it('ne repasse pas en loading si un abonnement est déjà connu (focus refresh)', () => {
    expect(
      resolveProductPhase(sub({ status: 'active', access_granted: true }), {
        subscriptionLoading: true,
      }),
    ).toBe('entitled')
    expect(
      resolveProductPhase(sub({ status: 'none', access_granted: false }), {
        subscriptionLoading: true,
      }),
    ).toBe('no_entitlement')
  })

  it('no_entitlement sans accès produit', () => {
    expect(resolveProductPhase(sub({ status: 'none' }))).toBe('no_entitlement')
    expect(resolveProductPhase(sub({ status: 'expired' }))).toBe('no_entitlement')
    expect(resolveProductPhase(sub({ status: 'checkout_pending' }))).toBe('no_entitlement')
  })

  it('entitled avec access_granted ou admin', () => {
    expect(
      resolveProductPhase(sub({ status: 'trialing', access_granted: true })),
    ).toBe('entitled')
    expect(
      resolveProductPhase(sub({ status: 'active', access_granted: true })),
    ).toBe('entitled')
    expect(resolveProductPhase(sub({ status: 'none' }), { isPlatformAdmin: true })).toBe(
      'entitled',
    )
  })

  it('chemins publics', () => {
    expect(isPublicProductPath('/welcome')).toBe(true)
    expect(isPublicProductPath('/abonnement')).toBe(true)
    expect(isPublicProductPath('/compte')).toBe(true)
    expect(isPublicProductPath('/compte?x=1'.split('?')[0])).toBe(true)
    expect(isPublicProductPath('/dashboard')).toBe(false)
    expect(isPublicProductPath('/finance')).toBe(false)
    expect(isWelcomePath('/welcome')).toBe(true)
    expect(isWelcomePath('/dashboard')).toBe(false)
  })
})
