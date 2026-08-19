/**
 * Mapping Accueil (/dashboard) ← Financial Engine overview.
 * Aucun calcul métier ici : uniquement sélection / présentation de valeurs API.
 */
import type { FinancialAlert, FinancialOverview, Kpi } from './services/financialApi'
import { formatEuro, formatKpiValue } from './services/financialApi'

export type DataProvenance = 'real' | 'demo' | 'incomplete' | 'unsynced'

export type HomeKpiCard = {
  id: string
  label: string
  display: string
  hint: string
  status: Kpi['status']
}

export type DashboardHomeView = {
  hasData: boolean
  computedAt: string | null
  provenance: DataProvenance
  provenanceLabel: string
  kpis: HomeKpiCard[]
  healthScore: number | null
  healthGrade: string | null
  healthState: string
  alerts: FinancialAlert[]
  syncStatus: string
  syncLastAt: string | null
  syncAgeHours: number | null
  documentsToProcess: number
  recommendations: string[]
  recentActivity: FinancialOverview['recent_activity']
}

const HOME_KPI_IDS = [
  'tresorerie',
  'revenus',
  'depenses',
  'resultat',
  'tva_estimee',
  'factures_impayees',
] as const

export function kpiById(overview: FinancialOverview, id: string): Kpi | undefined {
  return overview.kpis.find((k) => k.id === id)
}

/** Faits canoniques partagés Accueil / Cockpit / Finance (même overview). */
export type CanonicalFinancialFacts = {
  tresorerie: number | null
  revenus: number | null
  factures_impayees: number | null
  healthScore: number | null
  alertCodes: string[]
}

export function extractCanonicalFinancialFacts(
  overview: FinancialOverview,
): CanonicalFinancialFacts {
  return {
    tresorerie: kpiById(overview, 'tresorerie')?.value ?? null,
    revenus: kpiById(overview, 'revenus')?.value ?? null,
    factures_impayees: kpiById(overview, 'factures_impayees')?.value ?? null,
    healthScore: overview.health?.score ?? null,
    alertCodes: (overview.alerts || []).map((a) => a.code).sort(),
  }
}

export function detectProvenance(overview: FinancialOverview): DataProvenance {
  if (!overview.has_data) return 'incomplete'
  const sync = overview.sync?.status
  if (sync === 'none' || sync === 'stale' || sync === 'error') return 'unsynced'
  // Heuristique douce : aucune banque + CA nul + docs = setup incomplet
  if (overview.sync?.connections === 0 && (kpiById(overview, 'revenus')?.value ?? 0) === 0) {
    return 'incomplete'
  }
  return 'real'
}

export function provenanceLabel(kind: DataProvenance): string {
  switch (kind) {
    case 'real':
      return 'Données réelles (Financial Engine)'
    case 'demo':
      return 'Données de démonstration'
    case 'incomplete':
      return 'Données incomplètes — connectez banque / factures'
    case 'unsynced':
      return 'Synchronisation bancaire absente ou obsolète'
  }
}

export function mapOverviewToHome(overview: FinancialOverview): DashboardHomeView {
  const provenance = detectProvenance(overview)
  const byId = new Map(overview.kpis.map((k) => [k.id, k]))
  const kpis: HomeKpiCard[] = HOME_KPI_IDS.map((id) => {
    const k = byId.get(id)
    if (!k) {
      return {
        id,
        label: id,
        display: '—',
        hint: '',
        status: 'neutral' as const,
      }
    }
    return {
      id: k.id,
      label: k.label,
      display: formatKpiValue(k),
      hint: k.hint,
      status: k.status,
    }
  })

  return {
    hasData: overview.has_data,
    computedAt: overview.computed_at || null,
    provenance,
    provenanceLabel: provenanceLabel(provenance),
    kpis,
    healthScore: overview.health?.score ?? null,
    healthGrade: overview.health?.grade ?? null,
    healthState: overview.health?.state ?? 'setup',
    alerts: (overview.alerts || []).slice(0, 5),
    syncStatus: overview.sync?.status ?? 'none',
    syncLastAt: overview.sync?.last_sync_at ?? null,
    syncAgeHours: overview.sync?.age_hours ?? null,
    documentsToProcess: overview.documents_to_process ?? 0,
    recommendations: (overview.recommendations || []).slice(0, 3),
    recentActivity: (overview.recent_activity || []).slice(0, 6),
  }
}

/** Utilisé par le récap vocal — lit uniquement les valeurs déjà mappées. */
export function homeSpokenSummary(view: DashboardHomeView, orgName: string, firstName: string): string {
  const hello = firstName ? `Bonjour ${firstName}.` : 'Bonjour.'
  const ca = view.kpis.find((k) => k.id === 'revenus')
  const unpaid = view.kpis.find((k) => k.id === 'factures_impayees')
  const treasury = view.kpis.find((k) => k.id === 'tresorerie')
  const parts = [hello, `Pour ${orgName}, voilà l’essentiel.`]
  if (treasury) parts.push(`Trésorerie : ${treasury.display}.`)
  if (ca) parts.push(`Chiffre d’affaires : ${ca.display}.`)
  if (unpaid) parts.push(`Factures impayées : ${unpaid.display}.`)
  if (view.healthScore != null) {
    parts.push(`Score de santé financière : ${Math.round(view.healthScore)} sur 100.`)
  }
  const alert = view.alerts[0]
  if (alert) parts.push(`Alerte : ${alert.title}.`)
  return parts.join(' ')
}

export { formatEuro }
