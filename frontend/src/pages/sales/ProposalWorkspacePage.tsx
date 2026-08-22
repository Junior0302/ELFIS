import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
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
import { dealPath } from '../../sales/salesDeal'
import { ProposalConversionPanel } from '../../sales/ProposalConversionPanel'
import { SalesCommentsPanel } from '../../sales/SalesCommentsPanel'
import { SalesCollabActions } from '../../sales/SalesCollabActions'
import type { ProposalAction, ProposalWorkspace } from '../../sales/salesProposals'
import './sales-workspace.css'

function readinessTone(level: string): 'ok' | 'accent' | 'warn' | 'danger' | 'neutral' {
  if (level === 'ready') return 'ok'
  if (level === 'almost_ready') return 'accent'
  if (level === 'incomplete') return 'warn'
  return 'danger'
}

function formatDate(value?: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return value
  }
}

const ACTION_ROUTE: Record<string, string> = {
  prepare: 'prepare',
  request_review: 'request-review',
  approve: 'approve',
  mark_sent: 'mark-sent',
  mark_viewed: 'mark-viewed',
  start_negotiation: 'start-negotiation',
  accept: 'accept',
  reject: 'reject',
  expire: 'expire',
  cancel: 'cancel',
  generate_pdf: 'generate-pdf',
  new_version: 'versions',
  prepare_conversion: 'prepare-conversion',
}

export default function ProposalWorkspacePage() {
  const { token, orgId } = useAuth()
  const { id } = useParams<{ id: string }>()
  const proposalId = Number(id)
  const [data, setData] = useState<ProposalWorkspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [conversion, setConversion] = useState<Record<string, unknown> | null>(null)
  const [diff, setDiff] = useState<Record<string, unknown> | null>(null)
  const [tab, setTab] = useState('overview')

  const load = useCallback(() => {
    if (!token || orgId == null || !Number.isFinite(proposalId)) return
    setLoading(true)
    setError('')
    void api
      .getSalesProposalWorkspace(token, orgId, proposalId)
      .then(setData)
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Workspace indisponible.',
        )
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [token, orgId, proposalId])

  useEffect(() => {
    load()
  }, [load])

  const runAction = async (action: ProposalAction) => {
    if (!token || orgId == null || !action.enabled) return
    if (action.requires_confirmation && !window.confirm(`${action.label} ?`)) return
    const route = ACTION_ROUTE[action.id]
    if (!route) return
    setBusy(action.id)
    try {
      if (action.id === 'generate_pdf') {
        await api.generateSalesProposalPdf(token, orgId, proposalId)
      } else if (action.id === 'prepare_conversion') {
        const preview = await api.prepareSalesProposalConversion(token, orgId, proposalId)
        setConversion(preview)
        setTab('conversion')
      } else if (action.id === 'new_version') {
        await api.runSalesProposalAction(token, orgId, proposalId, 'versions')
      } else if (action.id === 'reject') {
        const reason = window.prompt('Motif du refus (obligatoire)') || ''
        if (!reason.trim()) return
        await api.runSalesProposalAction(token, orgId, proposalId, route, { reason })
      } else {
        await api.runSalesProposalAction(token, orgId, proposalId, route)
      }
      load()
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Action échouée.',
      )
    } finally {
      setBusy('')
    }
  }

  const loadDiff = async () => {
    if (!token || orgId == null || !data || data.versions.length < 2) return
    const sorted = [...data.versions].sort((a, b) => a.version_number - b.version_number)
    const from = sorted[sorted.length - 2]
    const to = sorted[sorted.length - 1]
    try {
      const result = await api.compareSalesProposalVersions(
        token,
        orgId,
        proposalId,
        from.id,
        to.id,
      )
      setDiff(result)
      setTab('diff')
    } catch {
      setError('Comparaison impossible.')
    }
  }

  if (!Number.isFinite(proposalId)) {
    return (
      <Container className="sales-workspace">
        <EmptyState title="Proposition invalide" />
      </Container>
    )
  }

  return (
    <Container className="sales-workspace sales-deal">
      {loading ? (
        <p className="muted">Chargement…</p>
      ) : error && !data ? (
        <EmptyState
          title="Erreur"
          description={error}
          action={
            <Button type="button" onClick={load}>
              Réessayer
            </Button>
          }
        />
      ) : !data ? (
        <EmptyState title="Introuvable" />
      ) : (
        <>
          <PageHeader
            eyebrow="Commercial · Proposition"
            title={data.header.proposal_number}
            description={[data.header.title, data.header.company_name, data.header.opportunity_name]
              .filter(Boolean)
              .join(' · ')}
            actions={
              <div className="sales-deal__header-actions">
                <Link to="/sales/proposals" className="ds-btn btn secondary">
                  Liste
                </Link>
                {data.header.opportunity_id ? (
                  <Link
                    to={dealPath(data.header.opportunity_id)}
                    className="ds-btn btn ghost"
                  >
                    Deal
                  </Link>
                ) : null}
              </div>
            }
          >
            <div className="sales-workspace__header-meta">
              <Badge tone="neutral">{data.header.status}</Badge>
              <Badge tone="accent">V{data.header.version_number ?? '—'}</Badge>
              <Badge tone={readinessTone(data.readiness.level)}>
                Readiness {data.readiness.level} {data.readiness.score}
              </Badge>
              <Badge tone="neutral">{formatSalesMoney(data.header.total)}</Badge>
            </div>
          </PageHeader>

          {error ? <p className="muted sales-workspace__banner">{error}</p> : null}

          <div className="sales-workspace__layout">
            <aside className="sales-workspace__sidebar">
              <Stack gap={4}>
                <Section title="Statut" spacing="compact">
                  <dl className="sales-workspace__meta-row">
                    <dt>Statut</dt>
                    <dd>{data.header.status}</dd>
                    <dt>Version</dt>
                    <dd>V{data.header.version_number ?? '—'}</dd>
                    <dt>Total</dt>
                    <dd>{formatSalesMoney(data.header.total)}</dd>
                    <dt>Validité</dt>
                    <dd>{data.header.valid_until || '—'}</dd>
                    <dt>Owner</dt>
                    <dd>{data.header.owner_label || '—'}</dd>
                    <dt>PDF</dt>
                    <dd>
                      {data.current_version?.pdf_vault_document_id
                        ? `#${data.current_version.pdf_vault_document_id}`
                        : 'Aucun'}
                    </dd>
                  </dl>
                </Section>

                <Section title="Readiness" spacing="compact">
                  <Badge tone={readinessTone(data.readiness.level)}>
                    {data.readiness.level} · {data.readiness.score}
                  </Badge>
                  {data.readiness.blockers.length ? (
                    <ul className="sales-workspace__list">
                      {data.readiness.blockers.map((b) => (
                        <li key={b} className="sales-workspace__list-item">
                          {b}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">Aucun blocker</p>
                  )}
                </Section>

                <Section title="Actions" spacing="compact">
                  <div className="sales-workspace__actions">
                    {data.available_actions.map((a) => (
                      <Button
                        key={a.id}
                        type="button"
                        size="sm"
                        variant={a.destructive ? 'danger' : 'secondary'}
                        disabled={!a.enabled || busy === a.id}
                        onClick={() => void runAction(a)}
                        title={a.reason || undefined}
                      >
                        {a.label}
                      </Button>
                    ))}
                    {data.versions.length >= 2 ? (
                      <Button type="button" size="sm" variant="secondary" onClick={() => void loadDiff()}>
                        Comparer versions
                      </Button>
                    ) : null}
                  </div>
                </Section>

                {Number.isFinite(Number(id)) ? (
                  <SalesCollabActions
                    entityType="proposal"
                    entityId={Number(id)}
                    assignResource="proposal"
                    onChanged={load}
                  />
                ) : null}
              </Stack>
            </aside>

            <div className="sales-workspace__main">
              <Grid columns={3} gap={4}>
                <MetricCard title="Total TTC" value={formatSalesMoney(data.totals.total)} />
                <MetricCard title="HT" value={formatSalesMoney(data.totals.subtotal)} />
                <MetricCard title="TVA" value={formatSalesMoney(data.totals.tax_total)} />
              </Grid>

              <Tabs value={tab} onValueChange={setTab} scrollable>
                <TabList scrollable>
                  <Tab value="overview">Vue générale</Tab>
                  <Tab value="lines">Lignes</Tab>
                  <Tab value="conditions">Conditions</Tab>
                  <Tab value="versions">Versions</Tab>
                  <Tab value="diff">Diff</Tab>
                  <Tab value="documents">Documents</Tab>
                  <Tab value="timeline">Timeline</Tab>
                  <Tab value="conversion">Conversion</Tab>
                </TabList>

                <TabPanel value="overview">
                  <Section title="Synthèse" spacing="compact">
                    <p className="muted">
                      Type {data.header.proposal_type} · Devise {data.header.currency}
                    </p>
                    {data.readiness.warnings.map((w) => (
                      <p key={w} className="muted">
                        ⚠ {w}
                      </p>
                    ))}
                  </Section>
                </TabPanel>

                <TabPanel value="lines">
                  <Section title="Lignes" spacing="compact">
                    {data.lines.length === 0 ? (
                      <EmptyState title="Aucune ligne" description="État : no lines." />
                    ) : data.current_version?.locked_at ? (
                      <>
                        <p className="muted sales-workspace__banner">
                          Version verrouillée — édition refusée.
                        </p>
                        <ul className="sales-workspace__list">
                          {data.lines.map((l) => (
                            <li key={l.id} className="sales-workspace__list-item">
                              <header>
                                <strong>{l.name}</strong>
                                <span>{formatSalesMoney(l.total)}</span>
                              </header>
                              <p className="muted">
                                Qté {l.quantity} · PU {formatSalesMoney(l.unit_price)} · Remise{' '}
                                {l.discount_type} {l.discount_value} · TVA {l.tax_rate}%
                              </p>
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.lines.map((l) => (
                          <li key={l.id} className="sales-workspace__list-item">
                            <header>
                              <strong>{l.name}</strong>
                              <span>{formatSalesMoney(l.total)}</span>
                            </header>
                            <p className="muted">
                              Qté {l.quantity} · PU {formatSalesMoney(l.unit_price)} · Remise{' '}
                              {l.discount_type} {l.discount_value} · TVA {l.tax_rate}%
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="conditions">
                  <Section title="Conditions" spacing="compact">
                    <p>
                      <strong>Paiement</strong>
                      <br />
                      {data.current_version?.payment_terms || '—'}
                    </p>
                    <p>
                      <strong>Commerciales</strong>
                      <br />
                      {data.current_version?.terms || '—'}
                    </p>
                    <p>
                      <strong>Notes</strong>
                      <br />
                      {data.current_version?.notes || '—'}
                    </p>
                  </Section>
                </TabPanel>

                <TabPanel value="versions">
                  <Section title="Historique versions" spacing="compact">
                    <ul className="sales-workspace__list">
                      {data.versions.map((v) => (
                        <li key={v.id} className="sales-workspace__list-item">
                          <header>
                            <strong>V{v.version_number}</strong>
                            <Badge tone="neutral">{v.status}</Badge>
                          </header>
                          <p className="muted">
                            {formatSalesMoney(v.total)} · {formatDate(v.created_at)}
                            {v.locked_at ? ' · verrouillée' : ''}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </Section>
                </TabPanel>

                <TabPanel value="diff">
                  <Section title="Diff versions" spacing="compact">
                    {!diff ? (
                      <EmptyState
                        title="Pas de diff chargé"
                        description="Utilisez Comparer versions (à la demande)."
                      />
                    ) : (
                      <pre className="sales-workspace__note">{JSON.stringify(diff.summary ?? diff, null, 2)}</pre>
                    )}
                  </Section>
                </TabPanel>

                <TabPanel value="documents">
                  <Section title="Documents Vault" spacing="compact">
                    {data.documents.length === 0 ? (
                      <EmptyState title="Aucun PDF" description="État : no PDF." />
                    ) : (
                      <ul className="sales-workspace__list">
                        {data.documents.map((d) => (
                          <li key={String(d.vault_document_id)} className="sales-workspace__list-item">
                            <header>
                              <strong>
                                {d.label || `Vault #${d.vault_document_id}`}
                              </strong>
                              {d.open_url ? (
                                <Link to={d.open_url} className="ds-btn btn ghost btn-sm">
                                  Ouvrir
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
                  <Section title="Timeline" spacing="compact">
                    <ul className="sales-workspace__list">
                      {data.timeline.map((ev) => (
                        <li key={String(ev.id)} className="sales-workspace__list-item">
                          <header>
                            <strong>{ev.title}</strong>
                            <span className="muted">{formatDate(ev.occurred_at)}</span>
                          </header>
                          <p className="muted">{ev.event_type}</p>
                        </li>
                      ))}
                    </ul>
                  </Section>
                </TabPanel>

                <TabPanel value="conversion">
                  {token && orgId != null ? (
                    <ProposalConversionPanel
                      token={token}
                      orgId={orgId}
                      proposalId={proposalId}
                      proposalUpdatedAt={data.header.updated_at}
                      onConverted={load}
                    />
                  ) : (
                    <EmptyState title="Session requise" />
                  )}
                  {conversion ? (
                    <details className="sales-workspace__note">
                      <summary>Détail préparation (legacy)</summary>
                      <pre>{JSON.stringify(conversion, null, 2)}</pre>
                    </details>
                  ) : null}
                </TabPanel>
              </Tabs>

              <p className="muted sales-workspace__banner">
                Généré le {formatDate(data.generated_at)} — totaux / readiness / workflow backend.
              </p>

              {Number.isFinite(Number(id)) ? (
                <SalesCommentsPanel entityType="proposal" entityId={Number(id)} />
              ) : null}
            </div>
          </div>
        </>
      )}
    </Container>
  )
}
