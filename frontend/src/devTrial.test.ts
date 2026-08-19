import { describe, expect, it, vi } from 'vitest'
import type { SubscriptionInfo } from './api'
import {
  isEntitledAfterRefresh,
  mapDevTrialError,
  resolveDevTrialPanelMode,
  shouldShowDevTrialButton,
} from './devTrial'
import { resolveProductPhase } from './productPhase'

function sub(over: Partial<SubscriptionInfo> = {}): SubscriptionInfo {
  return {
    plan: 'pro',
    status: 'none',
    price_eur: 19,
    configured: false,
    trial_end: null,
    current_period_end: null,
    cancel_at_period_end: false,
    access_granted: false,
    ...over,
  }
}

describe('shouldShowDevTrialButton — C1.3', () => {
  it('DEV + configured=false → panneau visible', () => {
    expect(shouldShowDevTrialButton(false, true)).toBe(true)
  })

  it('Production → panneau absent', () => {
    expect(shouldShowDevTrialButton(false, false)).toBe(false)
    expect(shouldShowDevTrialButton(true, false)).toBe(false)
  })

  it('DEV + configured=true → panneau absent', () => {
    expect(shouldShowDevTrialButton(true, true)).toBe(false)
  })
})

describe('resolveDevTrialPanelMode', () => {
  it('backend autorise → allowed', () => {
    expect(
      resolveDevTrialPanelMode({
        statusLoading: false,
        status: {
          allowed: true,
          environment: 'development',
          flag_enabled: true,
          reason: null,
          already_active: false,
        },
        subscription: sub(),
      }),
    ).toBe('allowed')
  })

  it('backend refuse → unavailable', () => {
    expect(
      resolveDevTrialPanelMode({
        statusLoading: false,
        status: {
          allowed: false,
          environment: 'development',
          flag_enabled: false,
          reason: 'dev_trial_disabled',
          already_active: false,
        },
        subscription: sub(),
      }),
    ).toBe('unavailable')
  })

  it('essai déjà actif → already_active', () => {
    expect(
      resolveDevTrialPanelMode({
        statusLoading: false,
        status: {
          allowed: true,
          environment: 'development',
          flag_enabled: true,
          reason: null,
          already_active: true,
        },
        subscription: sub(),
      }),
    ).toBe('already_active')
    expect(
      resolveDevTrialPanelMode({
        statusLoading: true,
        status: null,
        subscription: sub({ status: 'trialing', access_granted: true }),
      }),
    ).toBe('already_active')
  })
})

describe('mapDevTrialError', () => {
  it('403 / flag → message configuration', () => {
    expect(mapDevTrialError(new Error('DEV_TRIAL_DISABLED'))).toBe(
      'Le serveur n’autorise pas l’activation d’un essai local.',
    )
    expect(
      mapDevTrialError({ status: 403, code: 'dev_trial_disabled', message: 'x' }),
    ).toBe('Le serveur n’autorise pas l’activation d’un essai local.')
  })

  it('401 / 404 / 409 / 500 → messages dédiés', () => {
    expect(mapDevTrialError({ status: 401, code: '' })).toBe(
      'Votre session a expiré. Reconnectez-vous.',
    )
    expect(mapDevTrialError({ status: 404, code: '' })).toBe(
      'Activation locale indisponible sur ce serveur.',
    )
    expect(mapDevTrialError({ status: 409, code: '' })).toBe(
      'L’abonnement actuel ne permet pas d’activer un essai local.',
    )
    expect(mapDevTrialError({ status: 500, code: '' })).toBe(
      'Erreur serveur. Réessayez dans un instant.',
    )
  })

  it('erreur générique → message local', () => {
    expect(mapDevTrialError(new Error('DEV_TRIAL_FAILED'))).toBe(
      'Impossible d’activer l’essai local.',
    )
  })
})

describe('activation → refresh → entitled → onboarding entreprise', () => {
  it('après refresh avec access_granted → resolveProductPhase entitled', () => {
    const updated = sub({
      status: 'trialing',
      access_granted: true,
      configured: false,
      trial_end: '2099-01-01T00:00:00Z',
    })
    expect(resolveProductPhase(updated)).toBe('entitled')
    expect(isEntitledAfterRefresh(updated)).toBe(true)
  })

  it('simule activate → refresh → navigate /onboarding/entreprise (un seul appel)', async () => {
    const activateDevTrial = vi.fn().mockResolvedValue({
      outcome: 'created',
      subscription: sub({ status: 'trialing', access_granted: true }),
    })
    const refresh = vi.fn().mockResolvedValue(
      sub({ status: 'trialing', access_granted: true, configured: false }),
    )
    const navigate = vi.fn()
    let busy = false
    const inflight = { current: false }

    const onActivate = async () => {
      if (inflight.current || busy) return
      inflight.current = true
      busy = true
      try {
        await activateDevTrial()
        const updated = await refresh()
        if (isEntitledAfterRefresh(updated)) {
          navigate('/onboarding/entreprise', { replace: true })
        }
      } finally {
        inflight.current = false
        busy = false
      }
    }

    await Promise.all([onActivate(), onActivate()])
    expect(activateDevTrial).toHaveBeenCalledTimes(1)
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/onboarding/entreprise', { replace: true })
    expect(resolveProductPhase(await refresh.mock.results[0].value)).toBe('entitled')
  })
})
