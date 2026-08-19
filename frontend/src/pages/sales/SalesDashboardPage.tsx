import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Badge, QuickActionCard, Section } from '../../design-system'
import {
  ElfisButton,
  ElfisButtonLink,
  ElfisDashboardTemplate,
  ElfisEmptyState,
  ElfisLoadingState,
  ElfisMetricCard,
  GridItem,
  MotionPage,
  PlatformGrid,
} from '../../unified-platform'
import {
  activityTypeLabel,
  formatSalesMoney,
  type SalesDashboardActivity,
  type SalesDashboardData,
  type SalesDashboardTask,
} from '../../sales/salesDashboard'
import { SalesFocusCard } from '../../sales/SalesFocusCard'
import { QuickCreateDrawer } from '../../sales/QuickCreateDrawer'
import type { QuickCreateKind } from '../../sales/salesOps'
import {
  intelligencePath,
  severityTone,
  type IntelligenceOverview,
  type SalesInsight,
} from '../../sales/salesIntelligence'

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function ActivityList({
  items,
  emptyTitle,
}: {
  items: SalesDashboardActivity[]
  emptyTitle: string
}) {
  if (!items.length) {
    return <ElfisEmptyState title={emptyTitle} description="Rien à afficher pour cette période." />
  }
  return (
    <ul className="up-dash-list">
      {items.map((item) => (
        <li key={item.id}>
          <Link to="/sales/activities" className="up-dash-list__link">
            <span className="up-dash-list__meta">
              <Badge tone="neutral">{activityTypeLabel(item.activity_type)}</Badge>
              <time dateTime={item.activity_at}>{formatWhen(item.activity_at)}</time>
            </span>
            <strong>{item.subject}</strong>
            {item.result ? <span className="muted">{item.result}</span> : null}
          </Link>
        </li>
      ))}
    </ul>
  )
}

function TaskList({
  items,
  emptyTitle,
}: {
  items: SalesDashboardTask[]
  emptyTitle: string
}) {
  if (!items.length) {
    return <ElfisEmptyState title={emptyTitle} description="Aucune tâche dans ce groupe." />
  }
  return (
    <ul className="up-dash-list">
      {items.map((item) => (
        <li key={item.id}>
          <Link to="/sales/tasks" className="up-dash-list__link">
            <span className="up-dash-list__meta">
              <Badge tone={item.priority === 'high' ? 'danger' : 'neutral'}>{item.priority}</Badge>
              <Badge tone="accent">{item.status}</Badge>
              <time dateTime={item.due_at ?? undefined}>{formatWhen(item.due_at)}</time>
            </span>
            <strong>{item.title}</strong>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default function SalesDashboardPage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<SalesDashboardData | null>(null)
  const [intel, setIntel] = useState<IntelligenceOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [quickKind, setQuickKind] = useState<QuickCreateKind | null>(null)

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    void Promise.all([
      api.getSalesDashboard(token, orgId),
      api.getSalesIntelligence(token, orgId, true).catch(() => null),
    ])
      .then(([dash, intelligence]) => {
        setData(dash)
        setIntel(intelligence)
      })
      .catch((err: unknown) => {
        const message =
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Impossible de charger le dashboard SalesPilot.'
        setError(message)
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [token, orgId])

  useEffect(() => {
    load()
  }, [load])

  const headerBase = {
    title: 'Tableau de bord',
    description: 'Vue d’ensemble commerciale SalesPilot.',
    eyebrow: 'SalesPilot',
  } as const

  if (!token || orgId == null) {
    return (
      <ElfisDashboardTemplate dashboardId="sales" header={{ ...headerBase }}>
        <ElfisEmptyState
          title="Organisation requise"
          description="Sélectionnez une organisation."
        />
      </ElfisDashboardTemplate>
    )
  }

  if (loading) {
    return (
      <ElfisDashboardTemplate
        dashboardId="sales"
        header={{ ...headerBase, description: 'Chargement des indicateurs…' }}
      >
        <div aria-busy="true">
          <ElfisLoadingState
            title="Chargement"
            description="Agrégation des données CRM en cours."
          />
        </div>
      </ElfisDashboardTemplate>
    )
  }

  if (error) {
    return (
      <ElfisDashboardTemplate dashboardId="sales" header={{ ...headerBase }}>
        <ElfisEmptyState
          title="Erreur de chargement"
          description={error}
          action={
            <ElfisButton type="button" onClick={load}>
              Réessayer
            </ElfisButton>
          }
        />
      </ElfisDashboardTemplate>
    )
  }

  if (!data) {
    return null
  }

  const s = data.summary
  const noOpps = s.open_opportunities === 0 && s.won_opportunities === 0 && s.lost_opportunities === 0
  const noActivities =
    data.activities.today.length === 0 &&
    data.activities.tomorrow.length === 0 &&
    data.activities.this_week.length === 0
  const noTasks =
    data.tasks.overdue.length === 0 &&
    data.tasks.today.length === 0 &&
    data.tasks.upcoming.length === 0

  const metrics = (
    <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--metrics">
      <GridItem span={6} spanMd={4} spanLg={2}>
        <Link to="/sales/leads" className="up-dash-metric-link">
          <ElfisMetricCard title="Leads ouverts" value={String(s.open_leads)} />
        </Link>
      </GridItem>
      <GridItem span={6} spanMd={4} spanLg={2}>
        <Link to="/sales/pipeline" className="up-dash-metric-link">
          <ElfisMetricCard title="Opportunités ouvertes" value={String(s.open_opportunities)} />
        </Link>
      </GridItem>
      <GridItem span={6} spanMd={4} spanLg={2}>
        <Link to="/sales/pipeline" className="up-dash-metric-link">
          <ElfisMetricCard
            title="Valeur pipeline"
            value={formatSalesMoney(s.pipeline_value)}
            subtitle={`Pondérée ${formatSalesMoney(s.weighted_pipeline_value)}`}
          />
        </Link>
      </GridItem>
      <GridItem span={6} spanMd={4} spanLg={2}>
        <Link to="/sales/pipeline" className="up-dash-metric-link">
          <ElfisMetricCard
            title="Gagnées / Perdues"
            value={`${s.won_opportunities} / ${s.lost_opportunities}`}
          />
        </Link>
      </GridItem>
      <GridItem span={6} spanMd={4} spanLg={2}>
        <Link to="/sales/tasks" className="up-dash-metric-link">
          <ElfisMetricCard
            title="Tâches en retard"
            value={String(s.overdue_tasks)}
            variant={s.overdue_tasks > 0 ? 'accent' : 'default'}
          />
        </Link>
      </GridItem>
      <GridItem span={6} spanMd={4} spanLg={2}>
        <Link to="/sales/activities" className="up-dash-metric-link">
          <ElfisMetricCard title="Activités aujourd’hui" value={String(s.activities_today)} />
        </Link>
      </GridItem>
    </PlatformGrid>
  )

  const hasInsights = Boolean(intel && intel.top_insights.length > 0)
  const hasFocus = Boolean(intel?.focus)

  return (
    <MotionPage>
      <ElfisDashboardTemplate
        dashboardId="sales"
        header={{
          title: 'Tableau de bord',
          description: 'Indicateurs CRM calculés côté serveur — une seule source de vérité.',
          eyebrow: 'SalesPilot',
        }}
        metrics={
          <Section title="Résumé" description="KPIs live — aucun calcul navigateur." spacing="compact">
            {metrics}
          </Section>
        }
        primaryAnalysis={
          <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--primary">
            <GridItem span={12} spanMd={8}>
              {hasFocus ? <SalesFocusCard focus={intel!.focus} compact /> : null}
              <Section
                title="Pipeline"
                description={data.pipeline?.pipeline_name ?? 'Pipeline commercial'}
                actions={
                  <ElfisButtonLink to="/sales/pipeline" variant="secondary" size="sm">
                    Voir le pipeline
                  </ElfisButtonLink>
                }
              >
                {!data.pipeline || data.pipeline.stages.length === 0 ? (
                  <ElfisEmptyState
                    title="Aucune étape"
                    description="Initialisez le pipeline via l’API bootstrap."
                  />
                ) : (
                  <ul className="up-dash-pipeline">
                    {data.pipeline.stages.map((stage) => (
                      <li key={stage.stage_id} className="up-dash-pipeline__stage">
                        <div className="up-dash-pipeline__head">
                          <strong>{stage.name}</strong>
                          <span className="muted">{stage.probability} %</span>
                        </div>
                        <p>
                          {stage.opportunity_count} opp. · {formatSalesMoney(stage.amount_total)}
                        </p>
                        <p className="muted">Proba. moy. {stage.average_probability} %</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Section>
            </GridItem>
            <GridItem span={12} spanMd={4}>
              <Section
                title="Opportunités récentes"
                actions={
                  <ElfisButtonLink to="/sales/pipeline" variant="secondary" size="sm">
                    Toutes
                  </ElfisButtonLink>
                }
              >
                {noOpps || data.recent_opportunities.length === 0 ? (
                  <ElfisEmptyState
                    title="Aucune opportunité"
                    description="Créez une opportunité pour alimenter le pipeline."
                    action={
                      <ElfisButtonLink to="/sales/pipeline" variant="primary">
                        Aller au pipeline
                      </ElfisButtonLink>
                    }
                  />
                ) : (
                  <ul className="up-dash-list">
                    {data.recent_opportunities.map((opp) => (
                      <li key={opp.id}>
                        <Link to="/sales/pipeline" className="up-dash-list__link">
                          <span className="up-dash-list__meta">
                            <Badge tone="accent">{opp.stage_name ?? opp.status}</Badge>
                            <span>{formatSalesMoney(opp.estimated_amount)}</span>
                          </span>
                          <strong>{opp.name}</strong>
                          <span className="muted">
                            {opp.company_name ?? 'Sans entreprise'} · {opp.probability} %
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </Section>
            </GridItem>
          </PlatformGrid>
        }
        secondaryAnalysis={
          <PlatformGrid columns={12} gap={6} className="up-dash-band up-dash-band--secondary">
            <GridItem span={12} spanMd={6}>
              <Section
                title="Activités"
                description="Aujourd’hui, demain, cette semaine"
                actions={
                  <ElfisButtonLink to="/sales/activities" variant="secondary" size="sm">
                    Voir
                  </ElfisButtonLink>
                }
              >
                {noActivities ? (
                  <ElfisEmptyState
                    title="Aucune activité"
                    description="Planifiez un appel, un email ou une réunion."
                    action={
                      <ElfisButtonLink to="/sales/activities" variant="primary">
                        Activités
                      </ElfisButtonLink>
                    }
                  />
                ) : (
                  <div className="up-dash-buckets">
                    <div>
                      <h3 className="up-dash-buckets__title">Aujourd’hui</h3>
                      <ActivityList items={data.activities.today} emptyTitle="Rien aujourd’hui" />
                    </div>
                    <div>
                      <h3 className="up-dash-buckets__title">Demain</h3>
                      <ActivityList items={data.activities.tomorrow} emptyTitle="Rien demain" />
                    </div>
                    <div>
                      <h3 className="up-dash-buckets__title">Cette semaine</h3>
                      <ActivityList
                        items={data.activities.this_week}
                        emptyTitle="Rien cette semaine"
                      />
                    </div>
                  </div>
                )}
              </Section>
            </GridItem>
            <GridItem span={12} spanMd={6}>
              <Section
                title="Tâches"
                description="En retard, aujourd’hui, à venir"
                actions={
                  <ElfisButtonLink to="/sales/tasks" variant="secondary" size="sm">
                    Voir
                  </ElfisButtonLink>
                }
              >
                {noTasks ? (
                  <ElfisEmptyState
                    title="Aucune tâche"
                    description="Assignez une tâche commerciale pour démarrer."
                    action={
                      <ElfisButtonLink to="/sales/tasks" variant="primary">
                        Tâches
                      </ElfisButtonLink>
                    }
                  />
                ) : (
                  <div className="up-dash-buckets">
                    <div>
                      <h3 className="up-dash-buckets__title">En retard</h3>
                      <TaskList items={data.tasks.overdue} emptyTitle="Aucun retard" />
                    </div>
                    <div>
                      <h3 className="up-dash-buckets__title">Aujourd’hui</h3>
                      <TaskList items={data.tasks.today} emptyTitle="Rien aujourd’hui" />
                    </div>
                    <div>
                      <h3 className="up-dash-buckets__title">À venir</h3>
                      <TaskList items={data.tasks.upcoming} emptyTitle="Rien à venir" />
                    </div>
                  </div>
                )}
              </Section>
            </GridItem>
          </PlatformGrid>
        }
        operations={
          <Section title="Actions rapides" spacing="compact">
            <div className="up-dash-actions">
              <ElfisButton type="button" variant="primary" onClick={() => setQuickKind('lead')}>
                Quick Lead
              </ElfisButton>
              <ElfisButton type="button" variant="secondary" onClick={() => setQuickKind('company')}>
                Quick Entreprise
              </ElfisButton>
              <ElfisButton type="button" variant="secondary" onClick={() => setQuickKind('task')}>
                Quick Tâche
              </ElfisButton>
              <ElfisButton type="button" variant="secondary" onClick={() => setQuickKind('activity')}>
                Quick Activité
              </ElfisButton>
            </div>
            <PlatformGrid columns={12} gap={3}>
              {data.quick_actions.map((action) => (
                <GridItem key={action.id} span={6} spanMd={3}>
                  <QuickActionCard
                    title={action.label}
                    description={action.description}
                    href={action.href}
                    compact
                  />
                </GridItem>
              ))}
            </PlatformGrid>
          </Section>
        }
        recentActivity={
          <>
            {hasInsights ? (
              <Section title="Recommandations prioritaires" spacing="compact">
                <ul className="up-dash-list">
                  {intel!.top_insights.slice(0, 3).map((item: SalesInsight) => (
                    <li key={item.id}>
                      <Link to={intelligencePath(item.id)} className="up-dash-list__link">
                        <span className="up-dash-list__meta">
                          <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>
                          <Badge tone="neutral">{item.category}</Badge>
                        </span>
                        <strong>{item.title}</strong>
                        <span className="muted">{item.summary}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
                <ElfisButtonLink to={intelligencePath()} variant="secondary">
                  Voir toutes les recommandations
                </ElfisButtonLink>
              </Section>
            ) : null}
            <p className="up-dash-generated muted">
              Généré le{' '}
              {new Intl.DateTimeFormat('fr-FR', {
                dateStyle: 'short',
                timeStyle: 'medium',
              }).format(new Date(data.generated_at))}
            </p>
          </>
        }
      >
        <QuickCreateDrawer
          open={quickKind != null}
          kind={quickKind}
          onOpenChange={(open) => {
            if (!open) setQuickKind(null)
          }}
          onCreated={() => {
            setQuickKind(null)
            void load()
          }}
        />
      </ElfisDashboardTemplate>
    </MotionPage>
  )
}
