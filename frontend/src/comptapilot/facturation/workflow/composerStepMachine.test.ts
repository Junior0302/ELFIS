/**
 * Unit — composerStepMachine (F1.3.2)
 */
import { describe, expect, it } from 'vitest'
import {
  COMPOSER_STEP_ORDER,
  nextComposerStep,
  prevComposerStep,
  validateComposerStep,
  deriveGuidedStepStatuses,
  guidedProgressPercent,
  createEmptyFacturationDraft,
} from './index'

describe('composerStepMachine', () => {
  it('ordre 6 étapes', () => {
    expect(COMPOSER_STEP_ORDER).toEqual([
      'client',
      'items',
      'terms',
      'notes_payment',
      'review',
      'finalization',
    ])
  })

  it('next / prev', () => {
    expect(nextComposerStep('client')).toBe('items')
    expect(prevComposerStep('items')).toBe('client')
    expect(nextComposerStep('finalization')).toBeNull()
    expect(prevComposerStep('client')).toBeNull()
  })

  it('validate client / items', () => {
    const empty = createEmptyFacturationDraft({ docType: 'facture' })
    expect(validateComposerStep('client', empty).ok).toBe(false)
    expect(
      validateComposerStep('client', {
        ...empty,
        client: {
          customerId: 1,
          relationId: null,
          displayName: 'A',
          email: '',
          source: 'billing_customer',
        },
      }).ok,
    ).toBe(true)
    expect(validateComposerStep('items', empty).ok).toBe(false)
    expect(validateComposerStep('notes_payment', empty).ok).toBe(true)
  })

  it('statuts completed / current / blocked', () => {
    const s = deriveGuidedStepStatuses('terms')
    expect(s.client).toBe('completed')
    expect(s.items).toBe('completed')
    expect(s.terms).toBe('current')
    expect(s.review).toBe('blocked')
  })

  it('progress percent', () => {
    expect(guidedProgressPercent('client')).toBe(0)
    expect(guidedProgressPercent('finalization')).toBe(100)
  })
})
