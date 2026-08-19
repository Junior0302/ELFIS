/**
 * Contrôles intelligents — uniquement dérivés du draft wizard réel.
 * Aucune donnée inventée ; pas de blocage forcé.
 */
import type { WizardValidationIssue } from '../../../wizard-framework'
import {
  draftAmountHt,
  type FacturationWizardDraft,
} from './types'

export function deriveWizardControls(draft: FacturationWizardDraft): WizardValidationIssue[] {
  const issues: WizardValidationIssue[] = []

  if (draft.docType == null) {
    issues.push({
      id: 'no-doc-type',
      severity: 'warning',
      message: 'Aucun type de document sélectionné.',
      field: 'docType',
    })
  }

  const client = draft.client
  if (!client?.displayName?.trim()) {
    issues.push({
      id: 'no-client',
      severity: 'warning',
      message: 'Aucun client sélectionné.',
      field: 'client',
    })
  } else {
    if (!client.email?.trim()) {
      issues.push({
        id: 'client-email-missing',
        severity: 'info',
        message: `Le client « ${client.displayName} » n’a pas d’e-mail — l’envoi sera limité.`,
        field: 'client.email',
      })
    }
  }

  const products = draft.products.filter((p) => p.label.trim())
  if (!products.length) {
    issues.push({
      id: 'no-products',
      severity: 'warning',
      message: 'Aucune ligne produit renseignée.',
      field: 'products',
    })
  }

  products.forEach((p, index) => {
    if (!(Number(p.unitPrice) > 0)) {
      issues.push({
        id: `product-no-price-${index}`,
        severity: 'warning',
        message: `Le produit « ${p.label} » n’a pas de prix unitaire.`,
        field: `products.${index}.unitPrice`,
      })
    }
  })

  const vat = Number(draft.vatRate)
  if (Number.isFinite(vat) && (vat < 0 || vat > 100)) {
    issues.push({
      id: 'vat-out-of-range',
      severity: 'error',
      message: `Taux de TVA inhabituel (${vat} %).`,
      field: 'vatRate',
    })
  } else if (vat === 0 && products.length > 0) {
    issues.push({
      id: 'vat-zero',
      severity: 'info',
      message: 'TVA à 0 % — vérifiez que c’est intentionnel.',
      field: 'vatRate',
    })
  }

  const ht = draftAmountHt(draft)
  if (ht > 50_000) {
    issues.push({
      id: 'amount-unusual',
      severity: 'info',
      message: `Montant HT élevé (${ht.toLocaleString('fr-FR')} €) — contrôle manuel recommandé.`,
      field: 'amount',
    })
  }

  // Similarité document : sans historique API dans le wizard, on n’invente rien.
  return issues
}
