/**
 * ELFIS Wizard Framework V1 — contrats génériques (produit-agnostiques).
 * Réutilisable par ComptaPilot, SalesPilot, InventoryPilot, HR, Project, etc.
 */
import type { ReactNode } from 'react'

export type WizardStepStatus = 'upcoming' | 'current' | 'completed' | 'skipped' | 'error' | 'blocked'

export type WizardStepId = string

export type WizardStepDefinition = {
  id: WizardStepId
  label: string
  description?: string
  /** Étape optionnelle (peut être sautée) */
  optional?: boolean
  /** Masquée dans la sidebar (shell technique) */
  hidden?: boolean
}

export type WizardActionTone = 'primary' | 'secondary' | 'danger' | 'ghost'

export type WizardActionDef = {
  id: string
  label: string
  onClick?: () => void
  href?: string
  tone?: WizardActionTone
  disabled?: boolean
  disabledReason?: string
  loading?: boolean
}

export type WizardValidationIssue = {
  id: string
  severity: 'info' | 'warning' | 'error'
  message: string
  field?: string
}

export type WizardDefinition = {
  id: string
  title: string
  description?: string
  steps: readonly WizardStepDefinition[]
  currentStepId: WizardStepId
  /** Statuts dérivés par étape (optionnel — sinon calculés depuis l’ordre) */
  stepStatuses?: Partial<Record<WizardStepId, WizardStepStatus>>
}

export type WizardNavigationHandlers = {
  goNext?: () => void
  goBack?: () => void
  goToStep?: (stepId: WizardStepId) => void
  canGoNext?: boolean
  canGoBack?: boolean
  nextLabel?: string
  backLabel?: string
}

export type WizardContainerProps = {
  definition: WizardDefinition
  navigation?: WizardNavigationHandlers
  children?: ReactNode
  sidebar?: ReactNode
  footer?: ReactNode
  summary?: ReactNode
  className?: string
  /** Affiche la barre latérale d’étapes (défaut true) */
  showSidebar?: boolean
  /** Affiche la barre de progression (défaut true) */
  showProgress?: boolean
}
