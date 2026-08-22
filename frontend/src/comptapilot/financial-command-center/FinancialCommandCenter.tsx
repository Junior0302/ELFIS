import { memo, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth'
import { api } from '../../api'
import {
  financialApi,
  formatEuro,
  formatKpiValue,
  type ActivityItem,
  type FinancialOverview,
  type Kpi,
  type SyncState,
} from '../../services/financialApi'
import { hasFinancialEntitlement } from '../../subscription'
import { useSubscription } from '../../subscriptionContext'
import {
  InsightInline,
  InsightList,
  mapDayPrioritiesToInsights,
  mapFinancialAlertsToInsights,
  mapHealthToInsights,
  type Insight,
  type InsightAction,
} from '../../insight-framework'
import {
  WidgetBadge,
  WidgetChartBody,
  WidgetContainer,
  WidgetGrid,
  type WidgetDefinition,
  type WidgetStatus,
} from '../../widget-framework'
import {
  ElfisButton,
  ElfisButtonLink,
  ElfisDashboardTemplate,
  ElfisMetricCard,
  GridItem,
  MotionPage,
  PlatformGrid,
  ResponsiveChartFrame,
  isUnifiedPlatformUiEnabled,
} from '../../unified-platform'
import {
  HealthScoreGauge,
  RevenueExpensesBar,
  TreasuryLine,
} from './fccCharts'
import { buildDayPriorities } from './priorities'
import './fcc.css'

function renderFccInsightAction(action: InsightAction, _insight: Insight) {
  if (action.href) {
    return (
      <Link
        className={
          action.primary
            ? 'elf-insight-action elf-insight-action--primary'
            : 'elf-insight-action'
        }
        to={action.href}
        aria-label={action.ariaLabel || action.label}
      >
        {action.label}
      </Link>
    )
  }
  return (
    <button
      type="button"
      className={
        action.primary
          ? 'elf-insight-action elf-insight-action--primary'
          : 'elf-insight-action'
      }
      disabled={action.disabled}
      aria-label={action.ariaLabel || action.label}
      onClick={action.onClick}
    >
      {action.label}
    </button>
  )
}

const REFRESH_MS = 60_000

const QUICK_ACTIONS = [
  { label: 'Créer une facture', href: '/facturation/nouveau?type=facture' },
  { label: 'Importer un justificatif', href: '/deposit' },
  { label: 'Impayés', href: '/facturation/documents' },
  { label: 'Valider une écriture', href: '/accounting/proposals' },
  { label: 'Banque', href: '/banque' },
  { label: 'TVA', href: '/tva' },
] as const

function statusFor(
  loading: boolean,
  refreshing: boolean,
  error: string,
  empty: boolean,
): WidgetStatus {
  if (loading) return 'loading'
  if (error) return 'error'
  if (refreshing) return 'refreshing'
  if (empty) return 'empty'
  return 'ready'
}

function TrendLine({ kpi }: { kpi: Kpi }) {
  const { direction, delta_pct, delta } = kpi.trend
  if (direction === 'flat' && (delta_pct == null || delta_pct === 0) && delta === 0) {
    return <span className="muted">Comparaison indisponible</span>
  }
  if (direction === 'flat') return <span className="muted">stable</span>
  const arrow = direction === 'up' ? '▲' : '▼'
  const text =
    delta_pct != null
      ? `${arrow} ${Math.abs(delta_pct).toFixed(1)}%`
      : `${arrow} ${formatEuro(Math.abs(delta))}`
  return (
    <span className={direction === 'up' ? 'fcc-trend--up' : 'fcc-trend--down'}>{text}</span>
  )
}

function kpiMobileClass(id: string): string {
  const key = id.toLowerCase()
  if (key.includes('tresor') || key.includes('cash') || key.includes('banque')) return 'fcc-m-treasury'
  if (key.includes('impay') || key.includes('unpaid') || key.includes('overdue')) return 'fcc-m-unpaid'
  if (key.includes('tva')) return 'fcc-m-tva'
  return 'fcc-m-kpi'
}

/** Signal banque réel exposé par overview (pas inventé). */
function hasBankSyncSignal(sync: SyncState | undefined): boolean {
  if (!sync) return false
  return sync.connections > 0 || Boolean(sync.last_sync_at) || sync.status !== 'none'
}

function defBase(
  id: string,
  title: string,
  category: WidgetDefinition['category'],
  status: WidgetStatus,
  opts: Partial<WidgetDefinition> = {},
): WidgetDefinition {
  return {
    id,
    title,
    category,
    status,
    refreshable: true,
    size: 'md',
    source: 'Financial Engine',
    ...opts,
  }
}

function activityTone(type: string): string {
  const t = type.toLowerCase()
  if (t.includes('invoice') || t.includes('facture') || t.includes('payment') || t.includes('paiement')) {
    return 'ok'
  }
  if (t.includes('error') || t.includes('fail') || t.includes('retard')) return 'danger'
  if (t.includes('warn') || t.includes('pending') || t.includes('attente')) return 'warn'
  return 'info'
}

function activityIcon(type: string): string {
  const t = type.toLowerCase()
  if (t.includes('invoice') || t.includes('facture')) return 'F'
  if (t.includes('payment') || t.includes('paiement') || t.includes('bank') || t.includes('banque'))
    return '€'
  if (t.includes('document') || t.includes('doc')) return 'D'
  if (t.includes('sync')) return 'S'
  return '·'
}

const MemoRevenueExpensesBar = memo(RevenueExpensesBar)
const MemoTreasuryLine = memo(TreasuryLine)
const MemoHealthScoreGauge = memo(HealthScoreGauge)

function ForecastEmptyIllustration() {
  return (
    <div className="fcc-forecast-empty" aria-hidden="true">
      <svg viewBox="0 0 160 88" className="fcc-forecast-empty__svg" role="presentation">
        <defs>
          <linearGradient id="fcc-fc-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--ps-accent, var(--workspace-accent, #16a34a))" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--ps-navy, #0b1f3a)" stopOpacity="0.06" />
          </linearGradient>
        </defs>
        <rect x="8" y="12" width="144" height="64" rx="12" fill="url(#fcc-fc-grad)" />
        <path
          d="M24 58 C44 48, 52 62, 72 44 C88 30, 102 52, 136 28"
          fill="none"
          stroke="var(--ps-accent, var(--workspace-accent, #16a34a))"
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity="0.55"
        />
        <circle cx="136" cy="28" r="4" fill="var(--ps-accent, var(--workspace-accent, #16a34a))" opacity="0.7" />
        <rect x="28" y="68" width="28" height="4" rx="2" fill="rgba(15,23,42,0.08)" />
        <rect x="66" y="68" width="40" height="4" rx="2" fill="rgba(15,23,42,0.06)" />
      </svg>
    </div>
  )
}

function ActivityTimeline({ items }: { items: ActivityItem[] }) {
  return (
    <ol className="fcc-timeline">
      {items.slice(0, 8).map((item, i) => {
        const when = item.created_at || item.date
        const timeLabel = when
          ? new Date(when).toLocaleString('fr-FR', {
              dateStyle: 'short',
              timeStyle: 'short',
            })
          : null
        return (
          <li key={`${item.type}-${item.date}-${i}`} className="fcc-timeline__item">
            <span className="fcc-timeline__icon" aria-hidden="true">
              {activityIcon(item.type)}
            </span>
            <div className="fcc-timeline__body">
              <div className="fcc-timeline__row">
                <strong className="fcc-timeline__label">{item.label}</strong>
                {item.amount ? (
                  <span className="fcc-timeline__amount">{formatEuro(item.amount)}</span>
                ) : null}
              </div>
              <div className="fcc-timeline__meta">
                <WidgetBadge tone={activityTone(item.type)}>{item.type}</WidgetBadge>
                {item.meta ? <span className="fcc-timeline__status">{item.meta}</span> : null}
                {timeLabel ? <time dateTime={when}>{timeLabel}</time> : null}
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

/**
 * Financial Command Center — accueil métier ComptaPilot (S1.2.6 Premium V2).
 * Données uniquement via financialApi (aucun calcul inventé).
 * Hiérarchie : Analyser → Essentiel → Décider → Comprendre → Bas.
 */
export default function FinancialCommandCenter() {
  const { token, orgId, user, memberships } = useAuth()
  const { subscription, loading: subLoading } = useSubscription()
  const [data, setData] = useState<FinancialOverview | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [orgIncomplete, setOrgIncomplete] = useState(false)
  const [exportHint, setExportHint] = useState(false)

  const entitled = hasFinancialEntitlement(subscription, {
    isPlatformAdmin: Boolean(user?.is_platform_admin),
  })

  const orgName = useMemo(() => {
    const m = memberships.find((x) => x.organization_id === orgId)
    return m?.organization_name?.trim() || null
  }, [memberships, orgId])

  const load = useCallback(
    async (refresh = false) => {
      if (!token || orgId == null) return
      if (refresh) setRefreshing(true)
      else setLoading(true)
      setError('')
      try {
        const overview = await financialApi.overview(token, orgId, refresh)
        setData(overview)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Impossible de charger le centre financier')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [token, orgId],
  )

  useEffect(() => {
    if (!entitled) {
      setLoading(false)
      return
    }
    void load()
    const t = window.setInterval(() => void load(true), REFRESH_MS)
    return () => window.clearInterval(t)
  }, [load, entitled])

  useEffect(() => {
    if (!token || orgId == null) return
    void api
      .getLaunchDashboard(token, orgId)
      .then((launch) => {
        setOrgIncomplete(!launch.workspace_ready)
      })
      .catch(() => setOrgIncomplete(false))
  }, [token, orgId])

  useEffect(() => {
    if (!exportHint) return
    const t = window.setTimeout(() => setExportHint(false), 2800)
    return () => window.clearTimeout(t)
  }, [exportHint])

  const priorities = useMemo(() => (data ? buildDayPriorities(data) : []), [data])
  const priorityInsights = useMemo(
    () => mapDayPrioritiesToInsights(priorities),
    [priorities],
  )
  const alertInsights = useMemo(
    () => mapFinancialAlertsToInsights(data?.alerts),
    [data?.alerts],
  )
  const healthInsights = useMemo(
    () => mapHealthToInsights(data?.health, data?.recommendations),
    [data?.health, data?.recommendations],
  )
  const pageStatus = statusFor(loading, refreshing, error, Boolean(data && !data.has_data))

  const revExp = data?.charts?.revenue_vs_expenses ?? []
  const treasury = data?.charts?.treasury ?? []
  const caEvo = data?.charts?.ca_evolution ?? []

  const chartStatus = (points: unknown[]): WidgetStatus => {
    if (loading) return 'loading'
    if (error && !data) return 'error'
    if (points.length === 0) return 'empty'
    if (refreshing) return 'refreshing'
    return 'ready'
  }

  const engineReady = Boolean(data && !error && !loading)
  const lastSyncLabel = useMemo(() => {
    const raw = data?.sync?.last_sync_at || data?.computed_at
    if (!raw) return null
    return new Date(raw).toLocaleString('fr-FR')
  }, [data?.sync?.last_sync_at, data?.computed_at])

  const showBankInEssentiel = Boolean(data && hasBankSyncSignal(data.sync))

  if (subLoading) {
    return <div className="loading">Chargement…</div>
  }

  if (!entitled) {
    return (
      <div className="page panel">
        <h2>Financial Command Center</h2>
        <p className="muted">Abonnement financier requis pour afficher le pilotage.</p>
        <Link className="btn" to="/abonnement">
          Voir l’abonnement
        </Link>
      </div>
    )
  }

  const unified = isUnifiedPlatformUiEnabled()

  const fccStrip = (
    <>
      {orgIncomplete ? (
        <div className="fcc-banner fcc-block fcc-block--banner" role="status">
          <p>Certaines informations nécessaires à ComptaPilot sont manquantes.</p>
          <ElfisButtonLink to="/platform/organization" variant="secondary">
            Compléter dans ELFIS
          </ElfisButtonLink>
        </div>
      ) : null}
      {error && !data ? (
        <div className="panel form-error fcc-block" role="alert">
          {error}{' '}
          <button type="button" className="linkish" onClick={() => void load(true)}>
            Réessayer
          </button>
        </div>
      ) : null}
    </>
  )

  const hasStrip = orgIncomplete || (error && !data)

  return (
    <MotionPage>
    <ElfisDashboardTemplate
      dashboardId="fcc"
      data-fcc="v1"
      data-fcc-layout="s126"
      data-unified-fcc={unified ? '1' : '0'}
      header={{
        title: 'Tableau de bord',
        description: 'Pilotage financier et trésorerie en temps réel — source : Financial Engine.',
        eyebrow: 'Finance',
        meta: (
          <div className="up-dash-meta" data-fcc-header-meta="true">
            {lastSyncLabel ? (
              <span className="up-dash-chip" title="Dernière synchronisation / calcul">
                Sync {lastSyncLabel}
              </span>
            ) : (
              <span className="up-dash-chip muted">Sync —</span>
            )}
            {orgName ? (
              <span className="up-dash-chip" data-fcc-org="true">
                {orgName}
              </span>
            ) : null}
            <span
              className={
                engineReady
                  ? 'up-dash-chip up-dash-chip--ok'
                  : error
                    ? 'up-dash-chip up-dash-chip--danger'
                    : 'up-dash-chip up-dash-chip--pending'
              }
              data-fcc-engine={engineReady ? 'ready' : error ? 'error' : 'pending'}
            >
              {engineReady ? 'Engine Ready' : error ? 'Engine indisponible' : 'Engine…'}
            </span>
            <span className="up-dash-chip up-dash-chip--strong">
              Source : Financial Engine
            </span>
          </div>
        ),
        actions: (
          <div className="up-dash-header-actions">
            <ElfisButtonLink to="/finance" variant="secondary">
              Analyse détaillée
            </ElfisButtonLink>
            <ElfisButton
              type="button"
              disabled={refreshing || loading}
              onClick={() => void load(true)}
            >
              {refreshing ? 'Actualisation…' : 'Actualiser'}
            </ElfisButton>
            <ElfisButton
              type="button"
              variant="secondary"
              aria-disabled="true"
              title="Export bientôt disponible"
              onClick={() => setExportHint(true)}
            >
              Exporter
            </ElfisButton>
            {exportHint ? (
              <span className="up-dash-toast" role="status">
                Export bientôt disponible
              </span>
            ) : null}
          </div>
        ),
      }}
      strip={hasStrip ? fccStrip : undefined}
      metrics={
        <section
          className="up-dash-section"
          aria-labelledby="fcc-essentials"
          data-fcc-section="essentiel"
          data-dashboard-slot="kpi-grid"
        >
          <h3 id="fcc-essentials" className="up-section-title">
            Essentiel
          </h3>
          <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--metrics fcc-kpi-grid">
            {(data?.kpis || []).map((kpi) => (
              <GridItem key={kpi.id} span={6} spanMd={4} spanLg={3}>
                <ElfisMetricCard
                  className={kpiMobileClass(kpi.id)}
                  title={kpi.label}
                  value={formatKpiValue(kpi)}
                  subtitle={kpi.hint || undefined}
                  status={<TrendLine kpi={kpi} />}
                />
              </GridItem>
            ))}
            {loading && !data ? (
              <GridItem span={6} spanMd={4} spanLg={3}>
                <ElfisMetricCard
                  title="Indicateurs"
                  value="…"
                  supportingText="Chargement"
                />
              </GridItem>
            ) : null}
            {data ? (
              <GridItem span={6} spanMd={4} spanLg={3}>
                <ElfisMetricCard
                  title="Documents à traiter"
                  value={String(data.documents_to_process)}
                  subtitle="File documentaire"
                />
              </GridItem>
            ) : null}
            {showBankInEssentiel && data ? (
              <GridItem span={6} spanMd={4} spanLg={3}>
                <ElfisMetricCard
                  title="Banques / sync"
                  value={data.sync.status}
                  subtitle={`${data.sync.connections} connexion(s) · erreurs ${data.sync.errors}`}
                />
              </GridItem>
            ) : null}
          </PlatformGrid>
        </section>
      }
      primaryAnalysis={
        <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--primary" data-fcc-section="primary">
          <GridItem span={12} spanMd={8}>
            <WidgetContainer
              className={`fcc-m-chart fcc-chart--hero up-chart-card up-chart-card--hero${revExp.length > 0 && revExp.length < 2 ? " up-chart-card--weak" : ""}`}
              definition={defBase(
                "chart-rev",
                "Revenus vs dépenses",
                "observe",
                chartStatus(revExp),
                {
                  variant: "chart",
                  size: "full",
                  emptyTitle: "Graphique indisponible",
                  emptyDescription: "Les séries revenus / dépenses ne sont pas encore disponibles.",
                  lastUpdatedAt: data?.computed_at,
                  errorMessage: error || undefined,
                },
              )}
              onRefresh={() => void load(true)}
              onRetry={() => void load(true)}
            >
              <div
                data-chart-card="v1"
                className="up-chart-card__body"
                data-chart-weak={revExp.length > 0 && revExp.length < 2 ? "1" : undefined}
              >
                <WidgetChartBody summary="Comparaison revenus et dépenses par période.">
                  <ResponsiveChartFrame>
                    {(w) => <MemoRevenueExpensesBar points={revExp} width={w} />}
                  </ResponsiveChartFrame>
                </WidgetChartBody>
              </div>
            </WidgetContainer>
          </GridItem>
          <GridItem span={12} spanMd={4} className="fcc-primary-rail">
            <WidgetContainer
              className="fcc-m-priorities"
              definition={defBase(
                "priorities",
                "Priorités du jour",
                "action",
                loading
                  ? "loading"
                  : error && !data
                    ? "error"
                    : priorities.length === 0
                      ? "empty"
                      : refreshing
                        ? "refreshing"
                        : "ready",
                {
                  variant: "list",
                  emptyTitle: "Aucune action urgente aujourd’hui.",
                  emptyDescription: "Les signaux disponibles ne montrent pas d’urgence.",
                  errorMessage: error || undefined,
                  lastUpdatedAt: data?.computed_at,
                  size: "lg",
                },
              )}
              onRefresh={() => void load(true)}
              onRetry={() => void load(true)}
            >
              <InsightList
                className="fcc-priority-list fcc-insight-list"
                insights={priorityInsights}
                emptyMessage="Aucune action urgente aujourd’hui."
                variant="card"
                renderAction={renderFccInsightAction}
              />
            </WidgetContainer>
            <WidgetContainer
              className="fcc-m-alerts"
              definition={defBase(
                "alerts",
                "Alertes financières",
                "alert",
                loading
                  ? "loading"
                  : error && !data
                    ? "error"
                    : refreshing
                      ? "refreshing"
                      : "ready",
                {
                  variant: "list",
                  lastUpdatedAt: data?.computed_at,
                  errorMessage: error || undefined,
                  size: "lg",
                },
              )}
              onRefresh={() => void load(true)}
              onRetry={() => void load(true)}
            >
              <InsightList
                className="fcc-priority-list fcc-insight-list"
                insights={alertInsights}
                emptyMessage="Aucune alerte détectée sur les données disponibles."
                variant="card"
                renderAction={renderFccInsightAction}
              />
            </WidgetContainer>
          </GridItem>
        </PlatformGrid>
      }
      secondaryAnalysis={
        <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--secondary" data-fcc-section="secondary">
          <GridItem span={12} spanMd={6}>
            <WidgetContainer
              className={`fcc-m-chart up-chart-card${treasury.length > 0 && treasury.length < 2 ? " up-chart-card--weak" : ""}`}
              definition={defBase("chart-treasury", "Trésorerie", "observe", chartStatus(treasury), {
                variant: "chart",
                size: "lg",
                emptyTitle: "Graphique indisponible",
                emptyDescription: "La série de trésorerie n’est pas encore disponible.",
                lastUpdatedAt: data?.computed_at,
                errorMessage: error || undefined,
              })}
              onRefresh={() => void load(true)}
              onRetry={() => void load(true)}
            >
              <div data-chart-card="v1" className="up-chart-card__body">
                <WidgetChartBody summary="Évolution de la trésorerie.">
                  <ResponsiveChartFrame>
                    {(w) => <MemoTreasuryLine points={treasury} label="Évolution trésorerie" width={w} />}
                  </ResponsiveChartFrame>
                </WidgetChartBody>
              </div>
            </WidgetContainer>
          </GridItem>
          <GridItem span={12} spanMd={6}>
            <WidgetContainer
              className={`fcc-m-chart up-chart-card${caEvo.length > 0 && caEvo.length < 2 ? " up-chart-card--weak" : ""}`}
              definition={defBase("chart-ca", "Évolution CA", "observe", chartStatus(caEvo), {
                variant: "chart",
                size: "lg",
                emptyTitle: "Graphique indisponible",
                emptyDescription: "La série d’évolution du CA n’est pas encore disponible.",
                lastUpdatedAt: data?.computed_at,
                errorMessage: error || undefined,
              })}
              onRefresh={() => void load(true)}
              onRetry={() => void load(true)}
            >
              <div data-chart-card="v1" className="up-chart-card__body">
                <WidgetChartBody summary="Évolution du chiffre d’affaires.">
                  <ResponsiveChartFrame>
                    {(w) => (
                      <MemoTreasuryLine points={caEvo} label="Évolution du chiffre d’affaires" width={w} />
                    )}
                  </ResponsiveChartFrame>
                </WidgetChartBody>
              </div>
            </WidgetContainer>
          </GridItem>
        </PlatformGrid>
      }
      operations={
        <div className="up-dash-ops" data-fcc-section="operations">
          <WidgetContainer
            className="fcc-m-actions"
            definition={defBase("quick-actions", "Actions rapides", "action", "ready", {
              refreshable: false,
              variant: "standard",
              size: "md",
              source: undefined,
            })}
          >
            <div className="fcc-actions">
              {QUICK_ACTIONS.map((a) => (
                <ElfisButtonLink
                  key={a.href + a.label}
                  className="fcc-action-chip"
                  to={a.href}
                  variant="secondary"
                >
                  {a.label}
                </ElfisButtonLink>
              ))}
            </div>
            <div className="fcc-actions fcc-actions--assistant">
              <ElfisButtonLink to="/copilote" variant="primary">
                Assistant financier
              </ElfisButtonLink>
            </div>
          </WidgetContainer>
          <WidgetGrid className="fcc-understand-grid" columns={3}>
            <WidgetContainer
              className="fcc-m-health"
              definition={defBase(
                "health",
                "Financial Health Score",
                "observe",
                loading ? "loading" : data?.health?.state === "setup" ? "empty" : pageStatus,
                {
                  variant: "score",
                  emptyTitle: data?.health?.message || "Score en configuration",
                  emptyDescription: "Indicateur de pilotage — ne remplace pas un conseil comptable.",
                  lastUpdatedAt: data?.computed_at,
                  size: "lg",
                },
              )}
              onRefresh={() => void load(true)}
            >
              {data?.health?.score != null ? (
                <div className="fcc-health fcc-health--premium">
                  <div className="fcc-health__gauge">
                    <MemoHealthScoreGauge score={data.health.score} grade={data.health.grade} />
                    <p className="fcc-health__score-caption">
                      Score {Math.round(data.health.score)}
                      {data.health.grade ? ` · grade ${data.health.grade}` : ""}
                    </p>
                  </div>
                  <div className="fcc-health__side">
                    <p className="muted fcc-disclaimer">
                      Indicateur de pilotage — ne remplace pas un conseil comptable.
                    </p>
                    {healthInsights.some((i) => i.id === "health:message") ? null : (
                      <p className="fcc-health__explain muted">
                        Synthèse des facteurs de trésorerie, retards et activité disponibles.
                      </p>
                    )}
                    <ul className="fcc-health-factors">
                      {data.health.components.map((c) => {
                        const pct = c.max_score > 0 ? Math.round((c.score / c.max_score) * 100) : 0
                        return (
                          <li key={c.id} title={c.detail}>
                            <div className="fcc-health-factors__row">
                              <span>{c.label}</span>
                              <span className="muted">
                                {c.score}/{c.max_score}
                              </span>
                            </div>
                            <div className="fcc-health-bar" aria-hidden="true">
                              <div className="fcc-health-bar__fill" style={{ width: `${pct}%` }} />
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                    {healthInsights.length ? (
                      <div className="fcc-health__tips">
                        <p className="fcc-health__tips-title">Conseils moteur</p>
                        <InsightList
                          className="fcc-insight-list"
                          insights={healthInsights.slice(0, 4)}
                          variant="inline"
                        />
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </WidgetContainer>
            <WidgetContainer
              className="fcc-m-forecast"
              definition={defBase("forecast", "Prévisions de trésorerie", "forecast", "ready", {
                refreshable: false,
                variant: "standard",
                size: "md",
                source: undefined,
              })}
              footer={
                <div className="fcc-actions">
                  <ElfisButtonLink to="/banque" variant="primary">
                    Connecter une banque
                  </ElfisButtonLink>
                  <ElfisButtonLink to="/finance" variant="secondary">
                    Ouvrir Finance
                  </ElfisButtonLink>
                </div>
              }
            >
              <div className="fcc-forecast-premium" role="status">
                <ForecastEmptyIllustration />
                <p className="ew-empty__title">Prévision indisponible</p>
                <p className="ew-empty__desc">
                  Connectez votre banque et complétez vos échéances pour activer les projections 30 /
                  60 / 90 jours.
                </p>
              </div>
            </WidgetContainer>
            <WidgetContainer
              className="fcc-m-cashflow"
              definition={defBase(
                "cashflows",
                "Encaissements & décaissements prévus",
                "forecast",
                "empty",
                {
                  refreshable: false,
                  variant: "standard",
                  emptyTitle: "Flux prévisionnels indisponibles",
                  emptyDescription:
                    "Aucun échéancier d’encaissements / décaissements n’est exposé par le Financial Engine pour le moment.",
                  size: "md",
                  source: undefined,
                },
              )}
            >
              {null}
            </WidgetContainer>
          </WidgetGrid>
          <WidgetContainer
            className="fcc-m-ops"
            definition={defBase("ops-treat", "Traiter", "observe", pageStatus, {
              variant: "list",
              lastUpdatedAt: data?.computed_at,
              size: "md",
            })}
            onRefresh={() => void load(true)}
          >
            <div className="fcc-ops-stack">
              <div className="fcc-ops-item">
                <p className="fcc-ops-item__label">Documents à traiter</p>
                <p className="fcc-kpi-value">{data ? data.documents_to_process : "—"}</p>
                <ElfisButtonLink to="/documents" variant="secondary">
                  Ouvrir
                </ElfisButtonLink>
              </div>
              <div className="fcc-ops-item">
                <p className="fcc-ops-item__label">Écritures à valider</p>
                <p className="fcc-kpi-value muted">N/A</p>
                <p className="muted fcc-ops-item__hint">Signal non exposé par overview</p>
                <ElfisButtonLink to="/accounting/proposals" variant="secondary">
                  Ouvrir
                </ElfisButtonLink>
              </div>
              <div className="fcc-ops-item">
                <p className="fcc-ops-item__label">Rapprochements</p>
                <p className="fcc-kpi-value muted">N/A</p>
                <p className="muted fcc-ops-item__hint">Signal non exposé par overview</p>
                <ElfisButtonLink to="/banque" variant="secondary">
                  Ouvrir
                </ElfisButtonLink>
              </div>
            </div>
          </WidgetContainer>
        </div>
      }
      recentActivity={
        <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--activity" data-fcc-section="activity">
          <GridItem span={12} spanMd={8}>
            <WidgetContainer
              className="fcc-m-activity"
              definition={defBase(
                "activity",
                "Activité récente",
                "observe",
                loading
                  ? "loading"
                  : !data?.recent_activity?.length
                    ? "empty"
                    : refreshing
                      ? "refreshing"
                      : "ready",
                {
                  variant: "list",
                  lastUpdatedAt: data?.computed_at,
                  emptyTitle: "Aucune activité récente",
                  emptyDescription: "Aucune activité récente sur les données disponibles.",
                  size: "lg",
                },
              )}
              onRefresh={() => void load(true)}
            >
              {data?.recent_activity?.length ? (
                <ActivityTimeline items={data.recent_activity} />
              ) : null}
            </WidgetContainer>
          </GridItem>
          <GridItem span={12} spanMd={4}>
            <WidgetContainer
              className="fcc-m-ops"
              definition={defBase("sync-status", "Synchronisations", "observe", pageStatus, {
                variant: "list",
                lastUpdatedAt: data?.computed_at,
                size: "md",
              })}
              onRefresh={() => void load(true)}
            >
              <div className="fcc-ops-item" data-fcc-sync="true">
                <p className="fcc-ops-item__label">Synchronisations bancaires</p>
                {data ? (
                  <>
                    <p className="fcc-kpi-value">{data.sync.status}</p>
                    <p className="muted fcc-ops-item__hint">
                      {data.sync.connections} connexion(s) · erreurs {data.sync.errors} · OK 7j{" "}
                      {data.sync.ok_runs_7d}
                    </p>
                  </>
                ) : (
                  <p className="fcc-kpi-value muted">—</p>
                )}
                <ElfisButtonLink to="/banque" variant="secondary">
                  Ouvrir
                </ElfisButtonLink>
              </div>
            </WidgetContainer>
            <WidgetContainer
              className="fcc-m-assistant"
              definition={defBase("assistant", "Assistant financier", "explain", "ready", {
                refreshable: false,
                variant: "hero",
                description: "Même moteur que /copilote — aucune affirmation non sourcée ici.",
                source: undefined,
              })}
            >
              <p className="muted">
                Posez une question sur la trésorerie, la TVA ou les impayés à partir des indicateurs
                ci-dessus.
              </p>
              {(() => {
                const tip = healthInsights.find((i) => i.id.startsWith("health:tip:")) || null
                return tip ? <InsightInline insight={tip} className="fcc-assistant-insight" /> : null
              })()}
              <div className="fcc-actions">
                <ElfisButtonLink to="/copilote" variant="primary">
                  Ouvrir l’Assistant financier
                </ElfisButtonLink>
              </div>
            </WidgetContainer>
          </GridItem>
        </PlatformGrid>
      }
    >
    </ElfisDashboardTemplate>
    </MotionPage>
  )
}
