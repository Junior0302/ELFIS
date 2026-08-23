/**
 * Priorités du jour — dérivées des signaux Financial Engine uniquement.
 * Aucune invention de données.
 */
import type { FinancialAlert, FinancialOverview, Kpi } from '../../services/financialApi'

export type PriorityLevel = 'critical' | 'high' | 'normal' | 'info'

export type DayPriority = {
  id: string
  level: PriorityLevel
  title: string
  reason: string
  amountOrDate?: string
  actionLabel: string
  href: string
  source: string
}

function kpi(overview: FinancialOverview, id: string): Kpi | undefined {
  return overview.kpis.find((k) => k.id === id)
}

function alertLevel(severity: FinancialAlert['severity']): PriorityLevel {
  if (severity === 'critical') return 'critical'
  if (severity === 'warning') return 'high'
  return 'info'
}

export function buildDayPriorities(overview: FinancialOverview): DayPriority[] {
  const out: DayPriority[] = []

  for (const alert of overview.alerts || []) {
    out.push({
      id: `alert:${alert.id}`,
      level: alertLevel(alert.severity),
      title: alert.title,
      reason: alert.message,
      amountOrDate: alert.value != null ? String(alert.value) : undefined,
      actionLabel: alert.action || 'Ouvrir',
      href: routeForAlert(alert),
      source: alert.source || 'financial',
    })
  }

  const unpaid = kpi(overview, 'factures_impayees')
  const unpaidCount = unpaid?.value
  if (
    unpaid &&
    unpaidCount != null &&
    unpaidCount > 0 &&
    !out.some((p) => p.id.includes('impay'))
  ) {
    out.push({
      id: 'kpi:factures_impayees',
      level: unpaid.status === 'critical' ? 'critical' : 'high',
      title: 'Factures impayées',
      reason: unpaid.hint || `${Math.round(unpaidCount)} facture(s) en attente de règlement`,
      amountOrDate: unpaid.format === 'currency' ? undefined : String(Math.round(unpaidCount)),
      actionLabel: 'Voir les impayés',
      href: '/facturation',
      source: 'kpi',
    })
  }

  if (overview.documents_to_process > 0) {
    out.push({
      id: 'docs:to_process',
      level: 'normal',
      title: 'Documents à traiter',
      reason: `${overview.documents_to_process} document(s) comptable(s) en attente`,
      actionLabel: 'Ouvrir les documents',
      href: '/documents',
      source: 'documents',
    })
  }

  if (overview.sync?.status === 'error' || (overview.sync?.errors ?? 0) > 0) {
    out.push({
      id: 'bank:sync_error',
      level: 'high',
      title: 'Synchronisation bancaire',
      reason: 'Échec ou erreurs de synchronisation détectés',
      actionLabel: 'Ouvrir la banque',
      href: '/platform/banking',
      source: 'banking',
    })
  }

  const order: Record<PriorityLevel, number> = { critical: 0, high: 1, normal: 2, info: 3 }
  out.sort((a, b) => order[a.level] - order[b.level])
  return out.slice(0, 8)
}

function routeForAlert(alert: FinancialAlert): string {
  const code = (alert.code || '').toLowerCase()
  if (code.includes('tva') || code.includes('vat')) return '/tva'
  if (code.includes('bank') || code.includes('sync')) return '/platform/banking'
  if (code.includes('doc')) return '/documents'
  if (code.includes('invoice') || code.includes('impay') || code.includes('overdue')) return '/facturation'
  if (code.includes('accounting') || code.includes('ecriture')) return '/accounting/proposals'
  return '/finance'
}

export function mapAlertSeverityToHierarchy(
  severity: FinancialAlert['severity'],
): PriorityLevel {
  return alertLevel(severity)
}
