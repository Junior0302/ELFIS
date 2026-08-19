/**
 * ELFIS Composer Framework V1 — contrats génériques (produit-agnostiques).
 * Réutilisable : facture, devis, produit, client, opportunité, projet…
 */
import type { ReactNode } from 'react'

export type ComposerStepStatus =
  | 'upcoming'
  | 'current'
  | 'completed'
  | 'skipped'
  | 'error'
  | 'blocked'

export type ComposerStepId = string

export type ComposerStepDefinition = {
  id: ComposerStepId
  label: string
  description?: string
  optional?: boolean
  hidden?: boolean
}

export type ComposerActionTone = 'primary' | 'secondary' | 'danger' | 'ghost'

export type ComposerActionDef = {
  id: string
  label: string
  onClick?: () => void
  href?: string
  tone?: ComposerActionTone
  disabled?: boolean
  disabledReason?: string
  loading?: boolean
}

export type ComposerValidationSeverity = 'info' | 'warning' | 'error' | 'suggestion'

export type ComposerValidationIssue = {
  id: string
  severity: ComposerValidationSeverity
  message: string
  field?: string
}

export type ComposerAutosaveState =
  | { status: 'idle' }
  | { status: 'saving' }
  | { status: 'saved'; savedAt: number }
  | { status: 'error'; message: string; onRetry?: () => void }

export type ComposerDocStatus =
  | 'draft'
  | 'ready'
  | 'validation_required'
  | 'error'
  | 'sent'
  | 'unknown'

export type ComposerDefinition = {
  id: string
  /** Nom / titre du document en cours d’édition */
  title: string
  /** Type affiché (ex. Facture, Devis) — générique */
  documentType?: string
  description?: string
  status?: ComposerDocStatus
  statusLabel?: string
  /** Explication courte du statut (données réelles). */
  statusHint?: string
  /** Icône discrète du statut. */
  statusIcon?: string
  steps: readonly ComposerStepDefinition[]
  currentStepId: ComposerStepId
  stepStatuses?: Partial<Record<ComposerStepId, ComposerStepStatus>>
  autosave?: ComposerAutosaveState
  progressPercent?: number
}

export type ComposerFocusExitTarget = {
  id: string
  label: string
  href: string
  description?: string
}

export type ComposerFocusModeConfig = {
  enabled: boolean
  /** Cibles de sortie intelligente */
  exitTargets?: ComposerFocusExitTarget[]
  onExit?: (targetId: string) => void
  /** Masque la nav secondaire du shell parent */
  hideSecondaryNav?: boolean
  /** Masque la sidebar produit (Compta) — Full Focus */
  hideProductSidebar?: boolean
  /** Masque Guide / bannières parasites */
  hideChromeExtras?: boolean
}

export type ComposerPreviewState = 'empty' | 'loading' | 'ready' | 'error'

export type ComposerLayoutProps = {
  definition: ComposerDefinition
  children?: ReactNode
  sidebar?: ReactNode
  inspector?: ReactNode
  preview?: ReactNode
  footer?: ReactNode
  headerExtra?: ReactNode
  toolbar?: ReactNode
  className?: string
  focusMode?: boolean
  /** Preview repliée (laptop / mobile) */
  previewCollapsed?: boolean
  onTogglePreview?: () => void
  showSidebar?: boolean
  showInspector?: boolean
  showPreview?: boolean
  showProgress?: boolean
  /** Actions primaires (max 2 recommandées) + secondaires */
  primaryActions?: ComposerActionDef[]
  secondaryActions?: ComposerActionDef[]
  onSelectStep?: (stepId: ComposerStepId) => void
}

export type ComposerNavigationHandlers = {
  goNext?: () => void
  goBack?: () => void
  goToStep?: (stepId: ComposerStepId) => void
  canGoNext?: boolean
  canGoBack?: boolean
  nextLabel?: string
  backLabel?: string
}
