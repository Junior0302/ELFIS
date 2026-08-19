/**
 * Statut document vivant — dérivé uniquement de l’état Composer réel.
 * Présentation UX ; aucun calcul métier / API inventée.
 */

import type {
  ComposerAutosaveState,
  ComposerDocStatus,
  ComposerValidationIssue,
} from '../../../composer-framework'

export type LiveDocumentStatusView = {
  status: ComposerDocStatus
  label: string
  /** Explication courte (Insight / ComposerStatus). */
  explanation: string
  /** Icône textuelle discrète (pas d’emoji décoratif). */
  icon: string
}

export type DeriveLiveDocumentStatusInput = {
  createdDocId: number | null
  sent: boolean
  issues: ComposerValidationIssue[]
  autosave: ComposerAutosaveState
  hasDocType: boolean
  hasClient: boolean
  hasProducts: boolean
}

export function deriveLiveDocumentStatus(
  input: DeriveLiveDocumentStatusInput,
): LiveDocumentStatusView {
  if (input.sent) {
    return {
      status: 'sent',
      label: 'Envoyé',
      explanation: 'Document marqué comme envoyé via l’action existante.',
      icon: '↗',
    }
  }

  if (input.autosave.status === 'error') {
    return {
      status: 'error',
      label: 'Erreur',
      explanation: input.autosave.message || 'Échec d’enregistrement — nouvelle tentative possible.',
      icon: '!',
    }
  }

  const blocking = input.issues.filter((i) => i.severity === 'error' || i.severity === 'warning')
  const complete =
    input.hasDocType && input.hasClient && input.hasProducts && blocking.length === 0

  if (!input.createdDocId) {
    if (blocking.length > 0 || !complete) {
      return {
        status: 'validation_required',
        label: 'Validation requise',
        explanation:
          blocking[0]?.message ||
          'Complétez type, client et lignes pour enregistrer un brouillon.',
        icon: '…',
      }
    }
    return {
      status: 'draft',
      label: 'Brouillon',
      explanation: 'Document non encore enregistré côté serveur.',
      icon: '○',
    }
  }

  if (blocking.length > 0) {
    return {
      status: 'validation_required',
      label: 'Validation requise',
      explanation: blocking[0]?.message || 'Des contrôles bloquants restent à traiter.',
      icon: '…',
    }
  }

  if (complete) {
    return {
      status: 'ready',
      label: 'Prêt',
      explanation: 'Brouillon enregistré — prêt pour validation / envoi.',
      icon: '✓',
    }
  }

  return {
    status: 'draft',
    label: 'Brouillon',
    explanation: 'Document en cours d’édition.',
    icon: '○',
  }
}
