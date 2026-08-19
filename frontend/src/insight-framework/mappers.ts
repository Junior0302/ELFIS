/**
 * Mappers présentation — données existantes → contrat Insight.
 * Aucun calcul métier ; fallback null si mapping impossible.
 */

import type { ComposerValidationIssue } from '../composer-framework/types'
import type {
  FinancialAlert,
  HealthScore,
} from '../services/financialApi'
import type { DayPriority } from '../comptapilot/financial-command-center/priorities'
import { createInsightAction } from './actions'
import type { Insight, InsightSeverity, InsightType } from './types'

function alertTypeAndSeverity(
  severity: FinancialAlert['severity'],
): { type: InsightType; severity: InsightSeverity } {
  if (severity === 'critical') return { type: 'critical', severity: 'critical' }
  if (severity === 'warning') return { type: 'attention', severity: 'high' }
  return { type: 'information', severity: 'info' }
}

/** Alerte financière Engine → Insight. */
export function mapFinancialAlertToInsight(alert: FinancialAlert): Insight | null {
  if (!alert?.id || !alert.title) return null
  const { type, severity } = alertTypeAndSeverity(alert.severity)
  const actions =
    alert.action && alert.action.trim()
      ? [createInsightAction('open', { label: alert.action.trim(), id: 'open' })]
      : undefined
  return {
    id: `alert:${alert.id}`,
    type,
    severity,
    title: alert.title,
    summary: alert.message || alert.title,
    source: alert.source
      ? { id: alert.source, label: alert.source }
      : undefined,
    timestamp: alert.created_at || undefined,
    actions,
    expandable: false,
    context: {
      surface: 'financial-command-center',
      entityType: 'financial_alert',
      entityId: alert.id,
      meta: {
        code: alert.code || null,
        value: alert.value,
      },
    },
  }
}

function prioritySeverity(level: DayPriority['level']): InsightSeverity {
  if (level === 'critical') return 'critical'
  if (level === 'high') return 'high'
  if (level === 'normal') return 'medium'
  return 'info'
}

function priorityType(level: DayPriority['level']): InsightType {
  if (level === 'critical') return 'critical'
  if (level === 'high') return 'attention'
  if (level === 'normal') return 'suggestion'
  return 'information'
}

/** Priorité du jour → Insight. */
export function mapDayPriorityToInsight(priority: DayPriority): Insight | null {
  if (!priority?.id || !priority.title) return null
  return {
    id: priority.id.startsWith('priority:') ? priority.id : `priority:${priority.id}`,
    type: priorityType(priority.level),
    severity: prioritySeverity(priority.level),
    title: priority.title,
    summary: priority.reason || priority.title,
    details: priority.amountOrDate || undefined,
    source: priority.source
      ? { id: priority.source, label: priority.source }
      : undefined,
    actions: [
      createInsightAction('open', {
        id: 'open',
        label: priority.actionLabel || 'Ouvrir',
        href: priority.href,
        primary: true,
      }),
    ],
    expandable: Boolean(priority.amountOrDate),
    context: { surface: 'financial-command-center', entityType: 'day_priority' },
  }
}

/** Message / conseils Health Score → Insights (présentation). */
export function mapHealthToInsights(
  health: HealthScore | null | undefined,
  recommendations?: string[] | null,
): Insight[] {
  const out: Insight[] = []
  if (!health) return out

  if (health.message && health.message.trim()) {
    out.push({
      id: 'health:message',
      type: 'analysis',
      severity: 'low',
      title: 'Financial Health Score',
      summary: health.message.trim(),
      source: { id: 'financial', label: 'financial' },
      expandable: false,
      context: {
        surface: 'financial-command-center',
        entityType: 'health_score',
        meta: {
          grade: health.grade,
          score: health.score,
          state: health.state,
        },
      },
    })
  }

  const tips = (recommendations || []).filter((r) => typeof r === 'string' && r.trim())
  tips.slice(0, 5).forEach((tip, i) => {
    out.push({
      id: `health:tip:${i}`,
      type: 'suggestion',
      severity: 'medium',
      title: 'Conseil moteur',
      summary: tip.trim(),
      source: { id: 'financial', label: 'financial' },
      context: { surface: 'financial-command-center', entityType: 'health_recommendation' },
    })
  })

  return out
}

function composerTypeAndSeverity(
  severity: ComposerValidationIssue['severity'],
): { type: InsightType; severity: InsightSeverity } {
  if (severity === 'error') return { type: 'critical', severity: 'critical' }
  if (severity === 'warning') return { type: 'attention', severity: 'high' }
  if (severity === 'suggestion') return { type: 'suggestion', severity: 'medium' }
  return { type: 'information', severity: 'info' }
}

/** Issue validation Composer → Insight. */
export function mapComposerIssueToInsight(issue: ComposerValidationIssue): Insight | null {
  if (!issue?.id || !issue.message) return null
  const { type, severity } = composerTypeAndSeverity(issue.severity)
  return {
    id: issue.id.startsWith('composer:') ? issue.id : `composer:${issue.id}`,
    type,
    severity,
    title: issue.message,
    summary: issue.message,
    expandable: false,
    context: {
      surface: 'document-composer',
      field: issue.field,
      entityType: 'validation_issue',
    },
  }
}

export function mapComposerIssuesToInsights(
  issues: ComposerValidationIssue[],
): Insight[] {
  return issues
    .map(mapComposerIssueToInsight)
    .filter((x): x is Insight => x != null)
}

export function mapFinancialAlertsToInsights(
  alerts: FinancialAlert[] | null | undefined,
): Insight[] {
  if (!alerts?.length) return []
  return alerts
    .map(mapFinancialAlertToInsight)
    .filter((x): x is Insight => x != null)
}

export function mapDayPrioritiesToInsights(
  priorities: DayPriority[] | null | undefined,
): Insight[] {
  if (!priorities?.length) return []
  return priorities
    .map(mapDayPriorityToInsight)
    .filter((x): x is Insight => x != null)
}
