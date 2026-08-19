import { useCallback, useEffect, useMemo, useState } from 'react'
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
  Tab,
  TabList,
  TabPanel,
  Tabs,
} from '../../design-system'
import { formatSalesMoney } from '../../sales/salesDashboard'
import { QuickCreateDrawer } from '../../sales/QuickCreateDrawer'
import type { QuickCreateKind } from '../../sales/salesOps'
import { SalesCommentsPanel } from '../../sales/SalesCommentsPanel'
import { SalesCollabActions } from '../../sales/SalesCollabActions'
import {
  entityLabel,
  isWorkspaceEntity,
  parseWorkspaceTab,
  workspacePath,
  WORKSPACE_TABS,
  type RelationshipWorkspace,
  type WorkspaceTabId,
} from '../../sales/salesWorkspace'
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

function bucketLabel(bucket: string): string {
  if (bucket === 'overdue') return 'Retard'
  if (bucket === 'today') return "Aujourd'hui"
  if (bucket === 'upcoming') return 'À venir'
  return 'Autre'
}

export default function RelationshipWorkspacePage() {
  const { token, orgId } = useAuth()
  const { entity: entityParam, id: idParam } = useParams<{ entity: string; id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<RelationshipWorkspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [quickKind, setQuickKind] = useState<QuickCreateKind | null>(null)

  const entityOk = isWorkspaceEntity(entityParam)
  const entityId = Number(idParam)
  const tab = parseWorkspaceTab(searchParams.get('tab'))

  const setTab = useCallback(
    (next: string) => {
      const id = parseWorkspaceTab(next)
      const params = new URLSearchParams(searchParams)
      if (id === 'overview') params.delete('tab')
      else params.set('tab', id)
      setSearchParams(params, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  const load = useCallback(() => {
    if (!token || orgId == null || !entityOk || !Number.isFinite(entityId)) return
    setLoading(true)
    setError('')
    void api
      .getSalesWorkspace(token, orgId, entityParam, entityId)
      .then(setData)
      .catch((err: unknown) => {
        const message =
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Impossible de charger le workspace.'
        setError(message)
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [token, orgId, entityOk, entityParam, entityId])

  useEffect(() => {
    load()
  }, [load])

  const eyebrow = useMemo(() => {
    if (!entityOk) return 'Workspace'
    return `SalesPilot · ${entityLabel(entityParam)}`
  }, [entityOk, entityParam])

  if (!entityOk || !Number.isFinite(entityId)) {
    return (
      <Container className="sales-workspace">
        <EmptyState
          title="Entité invalide"
          description="Le workspace accepte lead, company, person ou opportunity."
          action={
            <Link to="/sales" className="ds-btn btn secondary">
              Retour dashboard
            </Link>
          }
        />
      </Container>
    )
  }

  return (
    <Container className="sales-workspace">
      {loading ? (
        <p className="muted">Chargement du workspace…</p>
      ) : error ? (
        <EmptyState
          title="Workspace indisponible"
          description={error}
          action={
            <Button type="button" onClick={load}>
              Réessayer
            </Button>
          }
        />
      ) : !data ? (
        <EmptyState title="Aucune donnée" description="Workspace vide." />
      ) : (
        <>
          <PageHeader
            eyebrow={eyebrow}
            title={data.header.name}
            description={
              [data.header.status, data.header.pipeline_name, data.header.stage_name]
                .filter(Boolean)
                .join(' · ') || undefined
            }
            actions={
              <div className="sales-deal__header-actions">
                <Button type="button" variant="primary" onClick={() => setQuickKind('task')}>
                  Quick Tâche
                </Button>
                <Button type="button" variant="secondary" onClick={() => setQuickKind('activity')}>
                  Quick Activité
                </Button>
                <Button type="button" variant="secondary" onClick={() => setQuickKind('note')}>
                  Quick Note
                </Button>
                <Link to="/sales/pipeline" className="ds-btn btn secondary">
                  Pipeline
                </Link>
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
              {data.header.owner_label ? (
                <Badge tone="neutral">{data.header.owner_label}</Badge>
              ) : null}
            </div>
          </PageHeader>

          <div className="sales-workspace__layout">
            <aside className="sales-workspace__sidebar">
              <Section title="Fiche" spacing="compact">
                <dl className="sales-workspace__meta-row">
                  <dt>Montant</dt>
                  <dd>{formatSalesMoney(data.header.amount)}</dd>
                  <dt>Création</dt>
                  <dd>{formatDate(data.header.created_at)}</dd>
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

              <Section title="Actions rapides" spacing="compact">
                <div className="sales-workspace__actions">
                  {data.quick_actions.map((a) => (
                    <Link key={a.id} to={a.href} className="ds-btn btn secondary btn-sm">
                      {a.label}
                    </Link>
                  ))}
                </div>
              </Section>

              {entityOk && Number.isFinite(entityId) ? (
                <SalesCollabActions
                  entityType={entityParam === 'opportunity' ? 'opportunity' : entityParam}
                  entityId={entityId}
                  assignResource={
                    entityParam === 'lead' || entityParam === 'opportunity'
                      ? entityParam
                      : undefined
                  }
                  allowReview={entityParam === 'opportunity' || entityParam === 'lead'}
                  onChanged={load}
                />
              ) : null}
            </aside>

            <div className="sales-workspace__main">
              <Grid columns={3} gap={4}>
                <MetricCard title="Contacts" value={String(data.summary.contacts_count)} />
                <MetricCard
                  title="Opportunités ouvertes"
                  value={String(data.summary.open_opportunities)}
                />
                <MetricCard
                  title="Valeur pipeline"
                  value={formatSalesMoney(data.summary.pipeline_value)}
                />
                <MetricCard title="Activités" value={String(data.summary.activities_count)} />
                <MetricCard title="Tâches ouvertes" value={String(data.summary.open_tasks_count)} />
                <MetricCard title="Documents" value={String(data.summary.documents_count)} />
              </Grid>

              <Tabs value={tab} onValueChange={setTab} scrollable>
                <TabList scrollable>
                  {WORKSPACE_TABS.map((t) => (
                    <Tab key={t.id} value={t.id}>
                      {t.label}
                    </Tab>
                  ))}
                </TabList>

                <TabPanel value="overview">
                  <div className="sales-workspace__two-col">
                    <Section title="Activités récentes" spacing="compact">
                      {data.activities.length === 0 ? (
                        <EmptyState title="Aucune activité" description="Créez une activité." />
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
                              <p className="muted">
                                {a.owner_label || '—'}
                                {a.result ? ` · ${a.result}` : ''}
                              </p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </Section>
                    <Section title="Tâches" spacing="compact">
                      {data.tasks.length === 0 ? (
                        <EmptyState title="Aucune tâche" description="Rien à suivre." />
                      ) : (
                        <ul className="sales-workspace__list">
                          {data.tasks.slice(0, 5).map((t) => (
                            <li key={t.id} className="sales-workspace__list-item">
                              <header>
                                <strong>{t.title}</strong>
                                <Badge tone={t.bucket === 'overdue' ? 'danger' : 'neutral'}>
                                  {bucketLabel(t.bucket)}
                                </Badge>
                              </header>
                              <p className="muted">
                                {t.priority} · {t.status}
                              </p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </Section>
                  </div>
                </TabPanel>

                <TabPanel value="contacts">
                  <Section title="Contacts" spacing="compact">
                    {data.contacts.length === 0 ? (
                      <EmptyState title="Aucun contact" description="Ajoutez un contact lié." />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.contacts.map((c) => (
                          <li key={c.id} className="sales-workspace__list-item">
                            <header>
                              <strong>
                                {c.first_name} {c.last_name}
                              </strong>
                              <span className="sales-workspace__header-meta">
                                {c.is_primary ? <Badge tone="accent">Principal</Badge> : null}
                                <Link
                                  to={workspacePath('person', c.id)}
                                  className="ds-btn btn ghost btn-sm"
                                >
                                  Ouvrir
                                </Link>
                              </span>
                            </header>
                            <p className="muted">{c.job_title || 'Sans fonction'}</p>
                            <p className="muted">
                              {c.email || '—'} · {c.phone || '—'}
                              {c.linkedin_url ? ` · ${c.linkedin_url}` : ' · LinkedIn (préparé)'}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="opportunities">
                  <Section title="Opportunités" spacing="compact">
                    {data.opportunities.length === 0 ? (
                      <EmptyState
                        title="Aucune opportunité"
                        description="Créez une opportunité depuis le pipeline."
                      />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.opportunities.map((o) => (
                          <li key={o.id} className="sales-workspace__list-item">
                            <header>
                              <strong>{o.name}</strong>
                              <Link to={o.href} className="ds-btn btn ghost btn-sm">
                                Ouvrir
                              </Link>
                            </header>
                            <p className="muted">
                              {o.stage_name || '—'} · {formatSalesMoney(o.estimated_amount)} ·{' '}
                              {o.probability} % · {o.owner_label || 'Non assigné'}
                            </p>
                            <Badge tone={healthTone(o.health_label)}>
                              {o.health_label} {o.health_score}
                            </Badge>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="activities">
                  <Section title="Activités" spacing="compact">
                    {data.activities.length === 0 ? (
                      <EmptyState title="Aucune activité" description="Timeline compacte vide." />
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
                              Résultat : {a.result || '—'} · Auteur : {a.owner_label || '—'}
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
                      <EmptyState title="Aucune tâche" description="Rien à planifier." />
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
                              Priorité {t.priority} · {t.status}
                              {t.due_at ? ` · échéance ${formatDate(t.due_at)}` : ''}
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
                      <EmptyState title="Aucune note" description="Markdown à venir." />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.notes.map((n) => (
                          <li key={n.id} className="sales-workspace__list-item">
                            <header>
                              <span className="muted">
                                {n.author_label || 'Auteur inconnu'} · {formatDate(n.created_at)}
                              </span>
                            </header>
                            <pre className="sales-workspace__note">{n.body_markdown}</pre>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="documents">
                  <Section title="Documents (Vault)" spacing="compact">
                    {data.attachments.length === 0 ? (
                      <EmptyState
                        title="Aucun document"
                        description="Les pièces jointes pointent vers ELFIS Vault uniquement."
                      />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.attachments.map((doc) => (
                          <li key={doc.id} className="sales-workspace__list-item">
                            <header>
                              <strong>
                                {doc.label || doc.filename || `Vault #${doc.vault_document_id}`}
                              </strong>
                              {doc.open_url ? (
                                <Link to={doc.open_url} className="ds-btn btn ghost btn-sm">
                                  Ouvrir
                                </Link>
                              ) : null}
                            </header>
                            <p className="muted">vault_document_id={doc.vault_document_id}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="timeline">
                  <Section title="Timeline relationnelle" spacing="compact">
                    {data.timeline.length === 0 ? (
                      <EmptyState title="Timeline vide" description="Aucun événement agrégé." />
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

              {entityOk && Number.isFinite(entityId) ? (
                <SalesCommentsPanel entityType={entityParam} entityId={entityId} />
              ) : null}
            </div>
          </div>
        </>
      )}

      <QuickCreateDrawer
        open={quickKind != null}
        kind={quickKind}
        onOpenChange={(open) => {
          if (!open) setQuickKind(null)
        }}
        context={{
          opportunity_id: entityParam === 'opportunity' ? entityId : undefined,
          company_id: entityParam === 'company' ? entityId : undefined,
          entity_type: entityParam,
          entity_id: entityId,
        }}
        onCreated={() => {
          setQuickKind(null)
          load()
        }}
      />
    </Container>
  )
}

/** Exported for tests — tab ids used by routing. */
export function workspaceTabIds(): WorkspaceTabId[] {
  return WORKSPACE_TABS.map((t) => t.id)
}
