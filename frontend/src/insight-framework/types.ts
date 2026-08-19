/**
 * ELFIS Insight Framework V1 — contrat de présentation (produit-agnostique).
 * Indépendant des Pilots : mapping depuis données existantes uniquement.
 * Ne calcule pas, n’invente pas confiance / source / contenu.
 */

import type { ReactNode } from 'react'

/** Familles sémantiques d’insight. */
export type InsightType =
  | 'information'
  | 'success'
  | 'attention'
  | 'critical'
  | 'suggestion'
  | 'opportunity'
  | 'analysis'
  | 'confirmation'

/** Hiérarchie de sévérité / priorité d’affichage. */
export type InsightSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** Confiance — affichée uniquement si fournie par la source. */
export type InsightConfidence = 'high' | 'medium' | 'low'

/** Actions standard configurables. */
export type InsightActionKind =
  | 'view'
  | 'fix'
  | 'dismiss'
  | 'retry'
  | 'open'
  | 'understand'
  | 'custom'

export type InsightAction = {
  id: string
  kind: InsightActionKind
  label: string
  href?: string
  onClick?: () => void
  primary?: boolean
  disabled?: boolean
  /** Accès clavier / lecteur d’écran */
  ariaLabel?: string
}

export type InsightSource = {
  /** Identifiant technique réel (ex. financial, kpi, composer) — jamais inventé. */
  id: string
  /** Libellé affichable si disponible. */
  label?: string
}

export type InsightContext = {
  surface?: string
  field?: string
  entityId?: string
  entityType?: string
  meta?: Record<string, string | number | boolean | null>
}

export type InsightLinkedResource = {
  type: string
  id: string
  href?: string
  label?: string
}

/**
 * Contrat Insight — présentation uniquement.
 * Champs optionnels absents = non affichés (pas de placeholder fictif).
 */
export type Insight = {
  id: string
  type: InsightType
  severity: InsightSeverity
  title: string
  summary: string
  /** Zone « Pourquoi ? » — affichée seulement si présente. */
  details?: string
  source?: InsightSource
  /** Affiché uniquement si fourni. */
  confidence?: InsightConfidence
  timestamp?: string
  actions?: InsightAction[]
  dismissible?: boolean
  expandable?: boolean
  context?: InsightContext
  linkedResource?: InsightLinkedResource
}

export type InsightToneTokens = {
  type: InsightType
  severity: InsightSeverity
  colorVar: string
  icon: InsightIconName
  priorityRank: number
  defaultRole: 'status' | 'alert'
  labelFr: string
  severityLabelFr: string
}

export type InsightIconName =
  | 'info'
  | 'success'
  | 'attention'
  | 'critical'
  | 'suggestion'
  | 'opportunity'
  | 'analysis'
  | 'confirmation'

export type InsightRenderProps = {
  insight: Insight
  className?: string
  onDismiss?: (id: string) => void
  /** Remplace le rendu d’actions (ex. Link router). */
  renderAction?: (action: InsightAction, insight: Insight) => ReactNode
  compact?: boolean
}
