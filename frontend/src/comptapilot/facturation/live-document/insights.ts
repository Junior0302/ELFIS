/**
 * Insights live document — uniquement dérivables de données draft réelles.
 * Pas d’IA ; pas de similarité inventée ; pas de confiance fictive.
 * F1.3.1 : pas de re-mapping des issues validation (affichées ailleurs).
 */

import type { Insight } from '../../../insight-framework'
import type { ComposerValidationIssue } from '../../../composer-framework'
import {
  draftAmountHt,
  type FacturationWizardDraft,
} from '../workflow'

/** Taux TVA standards FR — hors liste = « inhabituel » (info), sans historique inventé. */
export const STANDARD_FR_VAT_RATES = [0, 5.5, 10, 20] as const

/** Fenêtre « produit récent » si `catalogCreatedAt` est fourni par le catalogue. */
export const RECENT_PRODUCT_DAYS = 30

export type DeriveLiveDocumentInsightsInput = {
  draft: FacturationWizardDraft
  /** Issues validation — conservées pour signature ; non rejouées dans le panneau. */
  issues: ComposerValidationIssue[]
  /** Timestamp local (ms) — injection tests. */
  now?: number
}

function isRecentIso(iso: string | undefined, now: number, days: number): boolean {
  if (!iso) return false
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return false
  return now - t <= days * 24 * 60 * 60 * 1000
}

function vatLooksUnusual(vat: number): boolean {
  if (!Number.isFinite(vat) || vat < 0 || vat > 100) return false
  return !STANDARD_FR_VAT_RATES.some((r) => Math.abs(r - vat) < 0.05)
}

/**
 * Insights à valeur ajoutée seulement — pas de confirmations redondantes,
 * pas de doublon avec ComposerValidation.
 */
export function deriveLiveDocumentInsights(
  input: DeriveLiveDocumentInsightsInput,
): Insight[] {
  const { draft } = input
  const now = input.now ?? Date.now()
  const out: Insight[] = []

  const labeled = draft.products.filter((p) => p.label.trim())

  const vat = Number(draft.vatRate)
  if (vatLooksUnusual(vat) && labeled.length > 0) {
    out.push({
      id: 'live:vat-unusual',
      type: 'attention',
      severity: 'medium',
      title: 'TVA inhabituelle',
      summary: `Taux ${vat} % hors standards courants (0 / 5,5 / 10 / 20 %). Vérifiez si c’est intentionnel.`,
      source: { id: 'composer', label: 'Document' },
      expandable: false,
      context: {
        surface: 'document-composer',
        field: 'vatRate',
        meta: { vatRate: vat },
      },
    })
  }

  const ht = draftAmountHt(draft)
  if (ht > 50_000) {
    out.push({
      id: 'live:amount-high',
      type: 'attention',
      severity: 'medium',
      title: 'Montant élevé',
      summary: `Montant HT ${ht.toLocaleString('fr-FR')} € — contrôle manuel recommandé.`,
      source: { id: 'composer', label: 'Document' },
      expandable: false,
      context: {
        surface: 'document-composer',
        field: 'amount',
        meta: { amountHt: ht },
      },
    })
  }

  const recent = labeled.find((p) => isRecentIso(p.catalogCreatedAt, now, RECENT_PRODUCT_DAYS))
  if (recent) {
    out.push({
      id: 'live:product-recent',
      type: 'information',
      severity: 'low',
      title: 'Produit récent',
      summary: `« ${recent.label} » a une date catalogue récente (≤ ${RECENT_PRODUCT_DAYS} j.).`,
      source: { id: 'catalog', label: 'Catalogue' },
      expandable: false,
      context: {
        surface: 'document-composer',
        entityType: 'product',
        field: 'products',
        meta: { catalogCreatedAt: recent.catalogCreatedAt ?? null },
      },
    })
  }

  return out
}
