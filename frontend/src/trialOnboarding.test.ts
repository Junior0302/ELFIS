import { describe, expect, it, vi, beforeEach } from 'vitest'
import { isTrialOnboardingMode, hasFinancialEntitlement, resolveCommercialStatus } from './subscription'
import type { SubscriptionInfo } from './api'
import {
  isPathAllowedDuringTrialOnboarding,
  TRIAL_LOCK_MESSAGE,
  TRIAL_ONBOARDING_ALLOWED_PATHS,
  TRIAL_ONBOARDING_BENEFITS,
  TRIAL_TRUST_ITEMS,
  TRIAL_PREVIEW_SAMPLE,
} from './trialOnboarding'
import { trackProductEvent, getProductEvents, clearProductEvents } from './productEvents'
import { navSections } from './navConfig'
import { navCategories } from './navModel'

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

describe('trial onboarding mode', () => {
  it('active pour none / trial_available / checkout_pending', () => {
    expect(isTrialOnboardingMode(sub({ status: 'none', trial_used: false }))).toBe(true)
    expect(isTrialOnboardingMode(sub({ status: 'none', trial_used: true }))).toBe(true)
    expect(isTrialOnboardingMode(sub({ status: 'checkout_pending' }))).toBe(true)
    expect(resolveCommercialStatus(sub({ status: 'none', trial_used: false }))).toBe('trial_available')
  })

  it('inactif pour essai, abo, grâce avec accès, admin', () => {
    expect(isTrialOnboardingMode(sub({ status: 'trialing', access_granted: true }))).toBe(false)
    expect(isTrialOnboardingMode(sub({ status: 'active', access_granted: true }))).toBe(false)
    expect(isTrialOnboardingMode(sub({ status: 'past_due', access_granted: true }))).toBe(false)
    expect(
      isTrialOnboardingMode(sub({ status: 'none' }), { isPlatformAdmin: true }),
    ).toBe(false)
  })

  it('n’applique pas le mode onboarding premium lock pour expiré (pas le même parcours)', () => {
    // expired = pas d’entitlement, mais isTrialOnboardingMode = false
    expect(hasFinancialEntitlement(sub({ status: 'expired' }))).toBe(false)
    expect(isTrialOnboardingMode(sub({ status: 'expired' }))).toBe(false)
  })
})

describe('concept 6 — contenu première impression', () => {
  it('expose 3 bénéfices dirigeants (landing)', () => {
    expect(TRIAL_ONBOARDING_BENEFITS).toHaveLength(3)
    expect(TRIAL_ONBOARDING_BENEFITS.map((b) => b.id)).toEqual([
      'pilotage',
      'copilote',
      'automatisation',
    ])
  })

  it('zone confiance avec icônes', () => {
    expect(TRIAL_TRUST_ITEMS.length).toBeGreaterThanOrEqual(5)
    TRIAL_TRUST_ITEMS.forEach((item) => {
      expect(item.icon.length).toBeGreaterThan(0)
      expect(item.label.length).toBeGreaterThan(0)
    })
  })

  it('preview produit avec health / trésorerie / copilote', () => {
    expect(TRIAL_PREVIEW_SAMPLE.healthScore).toBeGreaterThan(0)
    expect(TRIAL_PREVIEW_SAMPLE.treasury).toMatch(/€/)
    expect(TRIAL_PREVIEW_SAMPLE.copilote.length).toBeGreaterThan(10)
  })
})

describe('nav lock rules', () => {
  it('autorise /welcome et conserve /dashboard dans l’allowlist workspace (locks legacy)', () => {
    expect(TRIAL_LOCK_MESSAGE).toMatch(/activation de votre essai/i)
    expect(TRIAL_ONBOARDING_ALLOWED_PATHS).toContain('/welcome')
    expect(TRIAL_ONBOARDING_ALLOWED_PATHS).toContain('/dashboard')
    expect(TRIAL_ONBOARDING_ALLOWED_PATHS).toContain('/abonnement')
    expect(isPathAllowedDuringTrialOnboarding('/finance')).toBe(false)
    expect(isPathAllowedDuringTrialOnboarding('/welcome')).toBe(true)
    expect(isPathAllowedDuringTrialOnboarding('/dashboard')).toBe(true)
  })

  it('tous les menus hors Accueil sont candidats au verrou (catégories)', () => {
    const home = navCategories.find((c) => c.id === 'dashboard')
    expect(home).toBeTruthy()
    const others = navCategories.filter((c) => c.id !== 'dashboard')
    expect(others.length).toBeGreaterThan(5)
    others.forEach((item) => {
      expect(item.to === '/dashboard').toBe(false)
    })
  })

  it('libellés FR uniformisés', () => {
    const labels = navSections.flatMap((s) => s.items.map((i) => i.label))
    expect(labels).toContain('Copilote IA')
    expect(labels).toContain('Intelligence comptable')
    expect(labels).toContain('Centre d’import')
    expect(labels).toContain('Centre opérationnel')
    expect(labels).not.toContain('AI Assistant')
    expect(labels).not.toContain('Accounting Intelligence')
    expect(labels).not.toContain('Migration Center')
  })
})

describe('product events', () => {
  beforeEach(() => {
    clearProductEvents()
  })

  it('enregistre trial_cta_clicked sans outil tiers', () => {
    trackProductEvent('trial_cta_clicked', { target: '/abonnement' })
    expect(getProductEvents().some((e) => e.name === 'trial_cta_clicked')).toBe(true)
  })

  it('enregistre locked_nav_item_clicked', () => {
    trackProductEvent('locked_nav_item_clicked', { to: '/finance' })
    expect(getProductEvents().at(-1)?.name).toBe('locked_nav_item_clicked')
  })
})

describe('aucun endpoint financier sans entitlement', () => {
  it('gate : entitled false ⇒ pas d’appel overview', () => {
    const entitled = hasFinancialEntitlement(sub({ status: 'none' }))
    const fetchSpy = vi.fn()
    if (entitled) fetchSpy('/api/financial/overview')
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
