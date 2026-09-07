/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SubscriptionInfo } from '../api'

const createSubscriptionCheckout = vi.fn()
const createSubscriptionPortal = vi.fn()
const saasBillingCheckout = vi.fn()
const saasBillingPortal = vi.fn()

const noneSub: SubscriptionInfo = {
  plan: 'starter',
  status: 'none',
  price_eur: 19,
  configured: true,
  trial_end: null,
  current_period_end: null,
  cancel_at_period_end: false,
  access_granted: false,
  trial_used: false,
}

const activeSub: SubscriptionInfo = {
  ...noneSub,
  status: 'active',
  access_granted: true,
  current_period_end: '2026-10-07T00:00:00Z',
}

let subscriptionState: SubscriptionInfo = noneSub

vi.mock('../auth', () => ({
  useAuth: () => ({
    token: 'tok',
    orgId: 9,
    user: { id: 1, is_platform_admin: false },
    memberships: [
      {
        organization_id: 9,
        permissions: ['subscription.manage'],
      },
    ],
  }),
}))

vi.mock('../subscriptionContext', () => ({
  useSubscription: () => ({
    subscription: subscriptionState,
    loading: false,
    refresh: vi.fn().mockResolvedValue(subscriptionState),
    setSubscription: vi.fn(),
    setCheckoutReturnPending: vi.fn(),
    checkoutReturnPending: false,
  }),
}))

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    api: {
      ...actual.api,
      createSubscriptionCheckout: (...args: unknown[]) => createSubscriptionCheckout(...args),
      createSubscriptionPortal: (...args: unknown[]) => createSubscriptionPortal(...args),
      saasBillingCheckout: (...args: unknown[]) => saasBillingCheckout(...args),
      saasBillingPortal: (...args: unknown[]) => saasBillingPortal(...args),
      saasBillingOverview: vi.fn().mockResolvedValue({ overview: {}, plans: [] }),
      saasBillingQuotas: vi.fn().mockResolvedValue({ quotas: {} }),
      saasBillingHistory: vi.fn().mockResolvedValue({ events: [] }),
    },
  }
})

describe('AbonnementPage Stripe officiel /subscriptions', () => {
  beforeEach(() => {
    cleanup()
    subscriptionState = noneSub
    createSubscriptionCheckout.mockReset()
    createSubscriptionPortal.mockReset()
    saasBillingCheckout.mockReset()
    saasBillingPortal.mockReset()
    createSubscriptionCheckout.mockResolvedValue({ url: 'https://checkout.stripe.com/c/test' })
    createSubscriptionPortal.mockResolvedValue({ url: 'https://billing.stripe.com/p/test' })
    vi.spyOn(window.history, 'replaceState').mockImplementation(() => undefined)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('le checkout envoie uniquement les consentements, sans plan_code ni /billing/checkout', async () => {
    const assign = vi.fn()
    vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      origin: 'https://elfis-core.web.app',
      search: '',
      pathname: '/abonnement',
      assign,
    } as Location)

    const user = userEvent.setup()
    const { default: AbonnementPage } = await import('./AbonnementPage')
    render(<AbonnementPage />)

    const boxes = await screen.findAllByRole('checkbox')
    expect(boxes.length).toBeGreaterThanOrEqual(2)
    await user.click(boxes[0])
    await user.click(boxes[1])

    await user.click(screen.getByRole('button', { name: /démarrer mon essai gratuit/i }))

    await waitFor(() => {
      expect(createSubscriptionCheckout).toHaveBeenCalledTimes(1)
    })
    expect(createSubscriptionCheckout).toHaveBeenCalledWith(
      'tok',
      9,
      {
        automatic_renewal_accepted: true,
        terms_accepted: true,
      },
    )
    const payload = createSubscriptionCheckout.mock.calls[0][2] as Record<string, unknown>
    expect(payload).not.toHaveProperty('plan_code')
    expect(saasBillingCheckout).not.toHaveBeenCalled()
    expect(assign).toHaveBeenCalledWith('https://checkout.stripe.com/c/test')
  })

  it('le portail appelle createSubscriptionPortal sans fallback /billing/customer-portal', async () => {
    subscriptionState = activeSub
    const assign = vi.fn()
    vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      origin: 'https://elfis-core.web.app',
      search: '',
      pathname: '/abonnement',
      assign,
    } as Location)

    const user = userEvent.setup()
    const { default: AbonnementPage } = await import('./AbonnementPage')
    render(<AbonnementPage />)

    await user.click(await screen.findByRole('button', { name: /gérer mon abonnement/i }))

    await waitFor(() => {
      expect(createSubscriptionPortal).toHaveBeenCalledTimes(1)
    })
    expect(createSubscriptionPortal).toHaveBeenCalledWith('tok', 9)
    expect(saasBillingPortal).not.toHaveBeenCalled()
    expect(assign).toHaveBeenCalledWith('https://billing.stripe.com/p/test')
  })
})
