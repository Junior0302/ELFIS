/**
 * Machine d’étapes guidées du Composer (F1.3.2).
 * Distincte de ComposerModalStage (overlay) — ne pas mélanger.
 */

import type { FacturationWizardDraft } from './types'

export type ComposerStep =
  | 'client'
  | 'items'
  | 'terms'
  | 'notes_payment'
  | 'review'
  | 'finalization'

export const COMPOSER_GUIDED_STEPS: readonly {
  id: ComposerStep
  label: string
  title: string
  description: string
}[] = [
  {
    id: 'client',
    label: 'Client',
    title: 'Qui souhaitez-vous facturer ?',
    description: 'Choisissez le destinataire du document — recherche ou création rapide.',
  },
  {
    id: 'items',
    label: 'Produits',
    title: 'Quels produits et services ?',
    description: 'Construisez les lignes : le document à droite se complète au fil de l’eau.',
  },
  {
    id: 'terms',
    label: 'Conditions',
    title: 'Quelles conditions appliquer ?',
    description: 'Définissez l’échéance et le taux de TVA du document.',
  },
  {
    id: 'notes_payment',
    label: 'Notes',
    title: 'Notes et mentions',
    description: 'Ajoutez des mentions libres. Le suivi de paiement reste disponible après enregistrement.',
  },
  {
    id: 'review',
    label: 'Vérification',
    title: 'Tout est prêt à vérifier ?',
    description: 'Parcourez totaux et contrôles avant de finaliser.',
  },
  {
    id: 'finalization',
    label: 'Finalisation',
    title: 'Finalisez votre document',
    description: 'Enregistrez le brouillon ou préparez l’envoi.',
  },
] as const

export const COMPOSER_STEP_ORDER: readonly ComposerStep[] = COMPOSER_GUIDED_STEPS.map(
  (s) => s.id,
)

export function isComposerStep(raw: string): raw is ComposerStep {
  return (COMPOSER_STEP_ORDER as readonly string[]).includes(raw)
}

export function composerStepIndex(step: ComposerStep): number {
  return COMPOSER_STEP_ORDER.indexOf(step)
}

export function nextComposerStep(step: ComposerStep): ComposerStep | null {
  const i = composerStepIndex(step)
  if (i < 0 || i >= COMPOSER_STEP_ORDER.length - 1) return null
  return COMPOSER_STEP_ORDER[i + 1]
}

export function prevComposerStep(step: ComposerStep): ComposerStep | null {
  const i = composerStepIndex(step)
  if (i <= 0) return null
  return COMPOSER_STEP_ORDER[i - 1]
}

export type ComposerStepGate = {
  ok: boolean
  message?: string
}

/** Validation soft par étape — bloquer Continuer uniquement si nécessaire. */
export function validateComposerStep(
  step: ComposerStep,
  draft: FacturationWizardDraft,
  blockingErrors = 0,
): ComposerStepGate {
  switch (step) {
    case 'client':
      if (!draft.client?.displayName?.trim()) {
        return { ok: false, message: 'Sélectionnez un client pour continuer.' }
      }
      return { ok: true }
    case 'items':
      if (!draft.products.some((p) => p.label.trim())) {
        return { ok: false, message: 'Ajoutez au moins une ligne avec un libellé.' }
      }
      return { ok: true }
    case 'terms': {
      const due = Number(draft.dueDays)
      const vat = Number(draft.vatRate)
      if (!Number.isFinite(due) || due < 0) {
        return { ok: false, message: 'Indiquez une échéance valide (jours ≥ 0).' }
      }
      if (!Number.isFinite(vat) || vat < 0 || vat > 100) {
        return { ok: false, message: 'Indiquez un taux de TVA entre 0 et 100 %.' }
      }
      return { ok: true }
    }
    case 'notes_payment':
      return { ok: true }
    case 'review':
      if (blockingErrors > 0) {
        return {
          ok: false,
          message: `${blockingErrors} point${blockingErrors > 1 ? 's' : ''} à corriger avant de finaliser.`,
        }
      }
      if (!draft.client?.displayName?.trim() || !draft.products.some((p) => p.label.trim())) {
        return { ok: false, message: 'Complétez le client et les lignes avant de finaliser.' }
      }
      return { ok: true }
    case 'finalization':
      return { ok: true }
    default:
      return { ok: true }
  }
}

/**
 * Statuts pour la barre de progression :
 * - completed : étapes avant l’actuelle (cliquables)
 * - current : étape active
 * - upcoming / blocked : futures (non cliquables V1)
 */
export function deriveGuidedStepStatuses(
  current: ComposerStep,
): Partial<Record<ComposerStep, 'completed' | 'current' | 'upcoming' | 'blocked'>> {
  const cur = composerStepIndex(current)
  const out: Partial<Record<ComposerStep, 'completed' | 'current' | 'upcoming' | 'blocked'>> = {}
  for (let i = 0; i < COMPOSER_STEP_ORDER.length; i++) {
    const id = COMPOSER_STEP_ORDER[i]
    if (i < cur) out[id] = 'completed'
    else if (i === cur) out[id] = 'current'
    else out[id] = 'blocked'
  }
  return out
}

export function guidedProgressPercent(current: ComposerStep): number {
  const i = composerStepIndex(current)
  if (i < 0) return 0
  return Math.round((i / (COMPOSER_STEP_ORDER.length - 1)) * 100)
}

export function getComposerStepMeta(step: ComposerStep) {
  return COMPOSER_GUIDED_STEPS.find((s) => s.id === step) ?? COMPOSER_GUIDED_STEPS[0]
}
