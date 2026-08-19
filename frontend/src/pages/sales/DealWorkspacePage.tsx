import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  Grid,
  MetricCard,
  PageHeader,
  Section,
  Stack,
  Tab,
  TabList,
  TabPanel,
  Tabs,
} from '../../design-system'
import { formatSalesMoney } from '../../sales/salesDashboard'
import { SalesCommentsPanel } from '../../sales/SalesCommentsPanel'
import { SalesCollabActions } from '../../sales/SalesCollabActions'
import {
  DEAL_TABS,
  dealPath,
  parseDealTab,
  type DealWorkspace,
} from '../../sales/salesDeal'
import { workspacePath } from '../../sales/salesWorkspace'
import './sales-workspace.css'

function healthTone(label: string): 'ok' | 'accent' | 'warn' | 'danger' | 'neutral' {
  if (label === 'Excellent') return 'ok'
  if (label === 'Bon') return 'accent'
  if (label === 'Correct' || label === 'À surveiller') return 'warn'
  return 'danger'
}

function riskTone(level: string): 'ok' | 'warn' | 'danger' | 'neutral' {
  if (level === 'low') return 'ok'
  if (level === 'medium') return 'warn'
  return 'danger'
}

function formatDate(value?: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  } catch {
    return value
  }
}

function formatDay(value?: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleDateString('fr-FR')
  } catch {
    return value
  }
}

function bucketLabel(bucket: string): string {
  if (bucket === 'overdue') return 'Retard'
  if (bucket === 'today') return "Aujourd'hui"
  if (bucket === 'upcoming') return 'À venir'
  return 'Autre'
}

export default function DealWorkspacePage() {
  const { token, orgId } = useAuth()
  const { id: idParam } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<DealWorkspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const opportunityId = Number(idParam)
  const tab = parseDealTab(searchParams.get('tab'))

  const setTab = useCallback(
    (next: string) => {
      const id = parseDealTab(next)
      const params = new URLSearchParams(searchParams)
      if (id === 'overview') params.delete('tab')
      else params.set('tab', id)
      setSearchParams(params, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  const load = useCallback(() => {
    if (!token || orgId == null || !Number.isFinite(opportunityId)) return
    setLoading(true)
    setError('')
    void api
      .getSalesDealWorkspace(token, orgId, opportunityId)
      .then(setData)
      .catch((err: unknown) => {
        const message =
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Impossible de charger le deal.'
        setError(message)
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [token, orgId, opportunityId])

  useEffect(() => {
    load()
  }, [load])

  if (!Number.isFinite(opportunityId)) {
    return (
      <Container className="sales-workspace sales-deal">
        <EmptyState
          title="Deal invalide"
          description="Identifiant d'opportunité manquant."
          action={
            <Link to="/sales/pipeline" className="ds-btn btn secondary">
              Pipeline
            </Link>
          }
        />
      </Container>
    )
  }

  return (
    <Container className="sales-workspace sales-deal">
      {loading ? (
        <p className="muted">Chargement du deal…</p>
      ) : error ? (
        <EmptyState
          title="Deal indisponible"
          description={error}
          action={
            <Button type="button" onClick={load}>
              Réessayer
            </Button>
          }
        />
      ) : !data ? (
        <EmptyState title="Aucune donnée" description="Deal vide." />
      ) : (
        <>
          <PageHeader
            eyebrow="SalesPilot · Deal Workspace"
            title={data.header.name}
            description={
              [data.header.company_name, data.header.pipeline_name, data.header.stage_name]
                .filter(Boolean)
                .join(' · ') || undefined
            }
            actions={
              <div className="sales-deal__header-actions">
                <Link to="/sales/pipeline" className="ds-btn btn secondary">
                  Pipeline
                </Link>
                {data.header.company_id ? (
                  <Link
                    to={workspacePath('company', data.header.company_id)}
                    className="ds-btn btn ghost"
                  >
                    Relation
                  </Link>
                ) : null}
              </div>
            }
          >
            <div className="sales-workspace__header-meta">
              <Badge tone={healthTone(data.header.health_label)}>
                Health {data.header.health_label} {data.header.health_score}
              </Badge>
              <Badge tone={healthTone(data.header.relationship_label)}>
                Relation {data.header.relationship_label} {data.header.relationship_score}
              </Badge>
              <Badge tone={riskTone(data.header.risk_level)}>{data.header.risk_label}</Badge>
              <Badge tone="accent">
                Forecast {formatSalesMoney(data.header.forecast_amount)}
              </Badge>
              {data.header.owner_label ? (
                <Badge tone="neutral">{data.header.owner_label}</Badge>
              ) : null}
            </div>
          </PageHeader>

          <div className="sales-workspace__layout">
            <aside className="sales-workspace__sidebar">
              <Stack gap={4}>
              <Section title="Fiche deal" spacing="compact">
                <dl className="sales-workspace__meta-row">
                  <dt>Montant</dt>
                  <dd>{formatSalesMoney(data.header.amount)}</dd>
                  <dt>Probabilité</dt>
                  <dd>{data.header.probability} %</dd>
                  <dt>Forecast</dt>
                  <dd>{formatSalesMoney(data.forecast.weighted_amount)}</dd>
                  <dt>Closing estimé</dt>
                  <dd>{formatDay(data.header.expected_close_date)}</dd>
                  <dt>Dernière activité</dt>
                  <dd>{formatDate(data.header.last_activity_at)}</dd>
                </dl>
              </Section>

              <Section title="Health" spacing="compact" className="sales-workspace__score-block">
                <Badge tone={healthTone(data.health.label)}>
                  {data.health.label} · {data.health.score}
                </Badge>
                <p className="muted">{data.health.explanation}</p>
              </Section>

              <Section
                title="Relationship"
                spacing="compact"
                className="sales-workspace__score-block"
              >
                <Badge tone={healthTone(data.relationship.label)}>
                  {data.relationship.label} · {data.relationship.score}
                </Badge>
                <p className="muted">{data.relationship.explanation}</p>
              </Section>

              <Section title="Forecast" spacing="compact" className="sales-workspace__score-block">
                <p>
                  <strong>{formatSalesMoney(data.forecast.weighted_amount)}</strong>
                </p>
                <p className="muted">
                  {data.forecast.label} — {data.forecast.formula}
                </p>
              </Section>

              <Section title="Actions rapides" spacing="compact">
                <div className="sales-workspace__actions">
                  {data.quick_actions.map((a) => (
                    <Link key={a.id} to={a.href} className="ds-btn btn secondary btn-sm">
                      {a.label}
                    </Link>
                  ))}
                </div>
              </Section>
              </Stack>
            </aside>

            <div className="sales-workspace__main">
              <Grid columns={3} gap={4}>
                <MetricCard
                  title="Participants"
                  value={String(data.summary.participants_count)}
                />
                <MetricCard title="Produits" value={String(data.summary.products_count)} />
                <MetricCard
                  title="Prévision pondérée"
                  value={formatSalesMoney(data.summary.forecast_amount)}
                />
                <MetricCard title="Activités" value={String(data.summary.activities_count)} />
                <MetricCard title="Tâches ouvertes" value={String(data.summary.open_tasks_count)} />
                <MetricCard
                  title="Total produits"
                  value={formatSalesMoney(data.summary.products_total)}
                />
              </Grid>

              <Tabs value={tab} onValueChange={setTab} scrollable>
                <TabList scrollable>
                  {DEAL_TABS.map((t) => (
                    <Tab key={t.id} value={t.id}>
                      {t.label}
                    </Tab>
                  ))}
                </TabList>

                <TabPanel value="overview">
                  <div className="sales-workspace__two-col">
                    <Section title="Activités récentes" spacing="compact">
                      {data.activities.length === 0 ? (
                        <EmptyState title="Aucune activité" />
                      ) : (
                        <ul className="sales-workspace__list">
                          {data.activities.slice(0, 5).map((a) => (
                            <li key={a.id} className="sales-workspace__list-item">
                              <header>
                                <strong>
                                  {a.activity_type} — {a.subject}
                                </strong>
                                <span className="muted">{formatDate(a.activity_at)}</span>
                              </header>
                            </li>
                          ))}
                        </ul>
                      )}
                    </Section>
                    <Section title="Produits" spacing="compact">
                      {data.products.length === 0 ? (
                        <EmptyState
                          title="Aucun produit"
                          description="Ajoutez des lignes via l’API produits."
                          action={
                            <Link to={dealPath(opportunityId, 'products')} className="ds-btn btn">
                              Voir produits
                            </Link>
                          }
                        />
                      ) : (
                        <ul className="sales-workspace__list">
                          {data.products.slice(0, 5).map((p) => (
                            <li key={p.id} className="sales-workspace__list-item">
                              <header>
                                <strong>{p.name}</strong>
                                <span>{formatSalesMoney(p.line_total)}</span>
                              </header>
                            </li>
                          ))}
                        </ul>
                      )}
                    </Section>
                  </div>
                </TabPanel>

                <TabPanel value="participants">
                  <Section title="Participants" spacing="compact">
                    {data.participants.length === 0 ? (
                      <EmptyState
                        title="Aucun participant"
                        description="Rôles préparés : décideur, influenceur, technique, acheteur, contact principal."
                      />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.participants.map((p) => (
                          <li
                            key={`${p.person_id}-${p.role}-${p.id ?? 'derived'}`}
                            className="sales-workspace__list-item"
                          >
                            <header>
                              <strong>
                                {p.first_name} {p.last_name}
                              </strong>
                              <span className="sales-workspace__header-meta">
                                <Badge tone={p.is_primary ? 'accent' : 'neutral'}>
                                  {p.role_label}
                                </Badge>
                                <Link to={p.href} className="ds-btn btn ghost btn-sm">
                                  Ouvrir
                                </Link>
                              </span>
                            </header>
                            <p className="muted">{p.job_title || 'Sans fonction'}</p>
                            <p className="muted">
                              {p.email || '—'} · {p.phone || '—'}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="products">
                  <Section title="Produits" spacing="compact">
                    {data.products.length === 0 ? (
                      <EmptyState
                        title="Aucun produit"
                        description="Totaux calculés côté serveur — pas de moteur de devis."
                      />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.products.map((p) => (
                          <li key={p.id} className="sales-workspace__list-item">
                            <header>
                              <strong>{p.name}</strong>
                              <span>{formatSalesMoney(p.line_total)}</span>
                            </header>
                            {p.description ? <p className="muted">{p.description}</p> : null}
                            <p className="muted">
                              Qté {p.quantity} · PU {formatSalesMoney(p.unit_price)} · Remise{' '}
                              {p.discount_percent} %
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="activities">
                  <Section title="Activités" spacing="compact">
                    {data.activities.length === 0 ? (
                      <EmptyState title="Aucune activité" />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.activities.map((a) => (
                          <li key={a.id} className="sales-workspace__list-item">
                            <header>
                              <strong>
                                {a.activity_type} — {a.subject}
                              </strong>
                              <span className="muted">{formatDate(a.activity_at)}</span>
                            </header>
                            <p className="muted">
                              Résultat : {a.result || '—'} · {a.owner_label || '—'}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="tasks">
                  <Section title="Tâches" spacing="compact">
                    {data.tasks.length === 0 ? (
                      <EmptyState title="Aucune tâche" />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.tasks.map((t) => (
                          <li key={t.id} className="sales-workspace__list-item">
                            <header>
                              <strong>{t.title}</strong>
                              <Badge tone={t.bucket === 'overdue' ? 'danger' : 'neutral'}>
                                {bucketLabel(t.bucket)}
                              </Badge>
                            </header>
                            <p className="muted">
                              {t.priority} · {t.status}
                              {t.due_at ? ` · ${formatDate(t.due_at)}` : ''}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="notes">
                  <Section title="Notes" spacing="compact">
                    {data.notes.length === 0 ? (
                      <EmptyState title="Aucune note" />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.notes.map((n) => (
                          <li key={n.id} className="sales-workspace__list-item">
                            <header>
                              <span className="muted">
                                {n.author_label || 'Auteur'} · {formatDate(n.created_at)}
                              </span>
                            </header>
                            <pre className="sales-workspace__note">{n.body_markdown}</pre>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                  {Number.isFinite(opportunityId) ? (
                    <>
                      <SalesCommentsPanel entityType="opportunity" entityId={opportunityId} />
                      <SalesCollabActions
                        entityType="opportunity"
                        entityId={opportunityId}
                        assignResource="opportunity"
                        onChanged={load}
                      />
                    </>
                  ) : null}
                </TabPanel>

                <TabPanel value="documents">
                  <Section title="Documents (Vault)" spacing="compact">
                    {data.attachments.length === 0 ? (
                      <EmptyState title="Aucun document" description="Prévisualisation Vault uniquement." />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.attachments.map((doc) => (
                          <li key={doc.id} className="sales-workspace__list-item">
                            <header>
                              <strong>
                                {doc.label || doc.filename || `Vault #${doc.vault_document_id}`}
                              </strong>
                              {doc.preview_url ? (
                                <Link to={doc.preview_url} className="ds-btn btn ghost btn-sm">
                                  Prévisualiser
                                </Link>
                              ) : null}
                            </header>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="timeline">
                  <Section title="Timeline deal" spacing="compact">
                    {data.timeline.length === 0 ? (
                      <EmptyState title="Timeline vide" />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.timeline.map((ev) => (
                          <li key={ev.id} className="sales-workspace__list-item">
                            <header>
                              <strong>{ev.title}</strong>
                              <span className="muted">{formatDate(ev.occurred_at)}</span>
                            </header>
                            <p className="muted">{ev.event_type}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>
              </Tabs>

              <p className="muted sales-workspace__banner">
                Généré le {formatDate(data.generated_at)} — source de vérité backend.
              </p>
            </div>
          </div>
        </>
      )}
    </Container>
  )
}
