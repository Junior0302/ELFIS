/**
 * Actions Insight standard — libellés FR stables.
 */

import type { InsightAction, InsightActionKind } from './types'

const DEFAULT_LABELS: Record<Exclude<InsightActionKind, 'custom'>, string> = {
  view: 'Voir',
  fix: 'Corriger',
  dismiss: 'Ignorer',
  retry: 'Réessayer',
  open: 'Ouvrir',
  understand: 'Comprendre',
}

export function insightActionLabel(kind: InsightActionKind, custom?: string): string {
  if (kind === 'custom') return custom || 'Action'
  return custom || DEFAULT_LABELS[kind]
}

export function createInsightAction(
  kind: Exclude<InsightActionKind, 'custom'>,
  overrides: Partial<Omit<InsightAction, 'kind'>> & { id?: string } = {},
): InsightAction {
  return {
    id: overrides.id ?? kind,
    kind,
    label: overrides.label ?? DEFAULT_LABELS[kind],
    href: overrides.href,
    onClick: overrides.onClick,
    primary: overrides.primary,
    disabled: overrides.disabled,
    ariaLabel: overrides.ariaLabel,
  }
}

export const INSIGHT_ACTION_KINDS = [
  'view',
  'fix',
  'dismiss',
  'retry',
  'open',
  'understand',
] as const
