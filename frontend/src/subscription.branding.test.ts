import { describe, expect, it } from 'vitest'
import {
  publicPlanDescription,
  subscriptionCheckoutLabel,
  subscriptionPlanDisplay,
} from './subscription'

describe('subscription branding ELFIS', () => {
  it('affiche Starter comme ELFIS Starter sans exposer le code technique', () => {
    expect(subscriptionPlanDisplay('starter').short).toBe('ELFIS Starter')
    expect(subscriptionPlanDisplay('pro').short).toBe('ELFIS Starter')
    expect(subscriptionPlanDisplay('starter').brand).toBe('ELFIS Core')
  })

  it('ne propose plus ComptaPilot dans le CTA checkout', () => {
    expect(subscriptionCheckoutLabel('none', false)).toBe('Démarrer mon essai gratuit')
    expect(subscriptionCheckoutLabel('none', true, '19 €')).toBe('Souscrire à ELFIS Starter — 19 €/mois')
    expect(subscriptionCheckoutLabel('none', true)).not.toMatch(/ComptaPilot/i)
  })

  it('neutralise ComptaPilot dans une description catalogue legacy', () => {
    expect(publicPlanDescription('ComptaPilot IA — 19 €/mois.', 'Formule ELFIS Core')).toBe(
      'ELFIS Core — 19 €/mois.',
    )
  })
})
