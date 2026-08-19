/**
 * Tokens Design System pour familles Insight + hiérarchie severity.
 * Couleurs via variables --pilot-* (pas de hex inventés hors DS).
 */

import type {
  InsightIconName,
  InsightSeverity,
  InsightToneTokens,
  InsightType,
} from './types'

const SEVERITY_RANK: Record<InsightSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
}

const SEVERITY_LABEL_FR: Record<InsightSeverity, string> = {
  critical: 'Critique',
  high: 'Élevée',
  medium: 'Moyenne',
  low: 'Faible',
  info: 'Info',
}

const TYPE_DEFAULTS: Record<
  InsightType,
  {
    colorVar: string
    icon: InsightIconName
    labelFr: string
    defaultSeverity: InsightSeverity
    defaultRole: 'status' | 'alert'
  }
> = {
  information: {
    colorVar: 'var(--pilot-info)',
    icon: 'info',
    labelFr: 'Information',
    defaultSeverity: 'info',
    defaultRole: 'status',
  },
  success: {
    colorVar: 'var(--pilot-success)',
    icon: 'success',
    labelFr: 'Succès',
    defaultSeverity: 'info',
    defaultRole: 'status',
  },
  attention: {
    colorVar: 'var(--pilot-warning)',
    icon: 'attention',
    labelFr: 'Attention',
    defaultSeverity: 'high',
    defaultRole: 'status',
  },
  critical: {
    colorVar: 'var(--pilot-danger)',
    icon: 'critical',
    labelFr: 'Critique',
    defaultSeverity: 'critical',
    defaultRole: 'alert',
  },
  suggestion: {
    colorVar: 'var(--pilot-info)',
    icon: 'suggestion',
    labelFr: 'Suggestion',
    defaultSeverity: 'medium',
    defaultRole: 'status',
  },
  opportunity: {
    colorVar: 'var(--pilot-success)',
    icon: 'opportunity',
    labelFr: 'Opportunité',
    defaultSeverity: 'medium',
    defaultRole: 'status',
  },
  analysis: {
    colorVar: 'var(--pilot-info)',
    icon: 'analysis',
    labelFr: 'Analyse',
    defaultSeverity: 'low',
    defaultRole: 'status',
  },
  confirmation: {
    colorVar: 'var(--pilot-warning)',
    icon: 'confirmation',
    labelFr: 'Confirmation',
    defaultSeverity: 'medium',
    defaultRole: 'status',
  },
}

export function severityRank(severity: InsightSeverity): number {
  return SEVERITY_RANK[severity]
}

export function severityLabelFr(severity: InsightSeverity): string {
  return SEVERITY_LABEL_FR[severity]
}

export function insightTypeLabelFr(type: InsightType): string {
  return TYPE_DEFAULTS[type].labelFr
}

export function resolveInsightTone(
  type: InsightType,
  severity: InsightSeverity,
): InsightToneTokens {
  const base = TYPE_DEFAULTS[type]
  const role =
    severity === 'critical' || type === 'critical' ? 'alert' : base.defaultRole
  return {
    type,
    severity,
    colorVar: base.colorVar,
    icon: base.icon,
    priorityRank: severityRank(severity),
    defaultRole: role,
    labelFr: base.labelFr,
    severityLabelFr: severityLabelFr(severity),
  }
}

export function compareInsightPriority(
  a: { severity: InsightSeverity },
  b: { severity: InsightSeverity },
): number {
  return severityRank(a.severity) - severityRank(b.severity)
}

export function sortInsightsByPriority<T extends { severity: InsightSeverity }>(
  items: T[],
): T[] {
  return [...items].sort(compareInsightPriority)
}

export { TYPE_DEFAULTS, SEVERITY_RANK, SEVERITY_LABEL_FR }
