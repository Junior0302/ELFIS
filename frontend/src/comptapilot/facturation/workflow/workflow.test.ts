import { describe, expect, it } from 'vitest'
import {
  canLeaveFacturationStep,
  createEmptyFacturationDraft,
  deriveWizardControls,
  DOC_TYPE_CARDS,
  draftAmountHt,
  draftAmountTtc,
  FACTURATION_WORKFLOW_STEPS,
  isInventoryCatalogAvailable,
  resolveCatalogSource,
} from './index'

describe('Facturation workflow F1.0', () => {
  it('expose les 10 étapes officielles', () => {
    expect(FACTURATION_WORKFLOW_STEPS.map((s) => s.id)).toEqual([
      'document-choice',
      'client',
      'products',
      'controls',
      'preview',
      'validation',
      'send',
      'archive',
      'accounting',
      'confirmation',
    ])
  })

  it('expose les 3 cartes de document', () => {
    expect(DOC_TYPE_CARDS.map((c) => c.type)).toEqual(['facture', 'devis', 'avoir'])
  })

  it('garde InventoryPilot non branché', () => {
    expect(isInventoryCatalogAvailable()).toBe(false)
    expect(resolveCatalogSource(false)).toBe('local')
    expect(resolveCatalogSource(true)).toBe('inventory')
  })

  it('calcule totaux depuis le draft réel', () => {
    const draft = createEmptyFacturationDraft({
      products: [
        { catalogItemId: 1, label: 'A', quantity: 2, unitPrice: 50, vatRate: 20 },
        { catalogItemId: null, label: 'B', quantity: 1, unitPrice: 100, vatRate: 20 },
      ],
      vatRate: 20,
    })
    expect(draftAmountHt(draft)).toBe(200)
    expect(draftAmountTtc(draft)).toBe(240)
  })

  it('bloque la sortie des étapes critiques sans données', () => {
    const empty = createEmptyFacturationDraft()
    expect(canLeaveFacturationStep('document-choice', empty)).toBe(false)
    expect(canLeaveFacturationStep('client', empty)).toBe(false)
    expect(canLeaveFacturationStep('products', empty)).toBe(false)

    const ready = createEmptyFacturationDraft({
      docType: 'facture',
      client: {
        customerId: 1,
        relationId: null,
        displayName: 'ACME',
        email: 'a@b.c',
        source: 'billing_customer',
      },
      products: [{ catalogItemId: null, label: 'Presta', quantity: 1, unitPrice: 10, vatRate: 20 }],
    })
    expect(canLeaveFacturationStep('document-choice', ready)).toBe(true)
    expect(canLeaveFacturationStep('client', ready)).toBe(true)
    expect(canLeaveFacturationStep('products', ready)).toBe(true)
  })

  it('dérive contrôles uniquement depuis le draft (pas de faux positifs inventés)', () => {
    const emptyIssues = deriveWizardControls(createEmptyFacturationDraft())
    expect(emptyIssues.some((i) => i.id === 'no-doc-type')).toBe(true)
    expect(emptyIssues.some((i) => i.id === 'no-client')).toBe(true)

    const full = createEmptyFacturationDraft({
      docType: 'facture',
      client: {
        customerId: 1,
        relationId: null,
        displayName: 'ACME',
        email: '',
        source: 'billing_customer',
      },
      products: [{ catalogItemId: null, label: 'X', quantity: 1, unitPrice: 0, vatRate: 20 }],
      vatRate: 20,
    })
    const issues = deriveWizardControls(full)
    expect(issues.some((i) => i.id === 'client-email-missing')).toBe(true)
    expect(issues.some((i) => i.id === 'product-no-price-0')).toBe(true)
    expect(issues.some((i) => i.id === 'similar-doc')).toBe(false)
  })
})
