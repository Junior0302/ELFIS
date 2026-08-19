/**
 * Helpers totaux / échéance — présentation UI uniquement.
 * Réutilise draftAmount* du workflow (pas de nouveau moteur).
 */

import {
  draftAmountHt,
  draftAmountTtc,
  draftAmountTva,
  type FacturationWizardDraft,
  type WizardSelectedProduct,
} from '../workflow'

export type LiveTotalsSnapshot = {
  ht: number
  tva: number
  ttc: number
  discountTotal: number
  dueDays: number
  /** Date calendaire dérivée de dueDays (locale FR). */
  dueDateLabel: string
}

export function lineDiscountAmount(line: WizardSelectedProduct): number {
  const raw = (Number(line.quantity) || 0) * (Number(line.unitPrice) || 0)
  const discount = Math.min(100, Math.max(0, Number(line.discountPercent) || 0))
  return Math.round(raw * (discount / 100) * 100) / 100
}

export function draftDiscountTotal(draft: FacturationWizardDraft): number {
  const total = draft.products.reduce((sum, p) => sum + lineDiscountAmount(p), 0)
  return Math.round(total * 100) / 100
}

export function formatDueDateLabel(dueDays: number, now = new Date()): string {
  const days = Math.max(0, Math.floor(Number(dueDays) || 0))
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + days)
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function snapshotLiveTotals(
  draft: FacturationWizardDraft,
  now = new Date(),
): LiveTotalsSnapshot {
  return {
    ht: draftAmountHt(draft),
    tva: draftAmountTva(draft),
    ttc: draftAmountTtc(draft),
    discountTotal: draftDiscountTotal(draft),
    dueDays: draft.dueDays,
    dueDateLabel: formatDueDateLabel(draft.dueDays, now),
  }
}
