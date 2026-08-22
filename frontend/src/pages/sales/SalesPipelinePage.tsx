import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { dealPath } from '../../sales/salesDeal'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  Grid,
  MetricCard,
  PageHeader,
  QuickActionCard,
  Section,
} from '../../design-system'
import { Drawer } from '../../design-system/overlays/Drawer'
import { formatSalesMoney } from '../../sales/salesDashboard'
import { QuickCreateDrawer } from '../../sales/QuickCreateDrawer'
import type { QuickCreateKind } from '../../sales/salesOps'
import type { PipelineBoard, PipelineCard, PipelineDrawer } from '../../sales/salesPipeline'
import './sales-pipeline.css'

function healthTone(label: string): 'ok' | 'accent' | 'warn' | 'danger' | 'neutral' {
  if (label === 'Excellent') return 'ok'
  if (label === 'Bon') return 'accent'
  if (label === 'À surveiller') return 'warn'
  return 'danger'
}

function riskTone(level: string): 'ok' | 'warn' | 'danger' | 'neutral' {
  if (level === 'low') return 'ok'
  if (level === 'medium') return 'warn'
  return 'danger'
}

function PipelineCardView({
  card,
  onOpen,
  onPeek,
  draggable,
}: {
  card: PipelineCard
  onOpen: (id: number) => void
  onPeek?: (id: number) => void
  draggable: boolean
}) {
  return (
    <article
      className="sales-pipe-card"
      draggable={draggable}
      onDragStart={(e) => {
        if (!draggable) return
        e.dataTransfer.setData(
          'application/x-sales-opp',
          JSON.stringify({ id: card.id, stage_id: card.stage_id }),
        )
        e.dataTransfer.effectAllowed = 'move'
      }}
    >
      <button type="button" className="sales-pipe-card__hit" onClick={() => onOpen(card.id)}>
        <header className="sales-pipe-card__head">
          <strong>{card.company_name || card.name}</strong>
          <span>{formatSalesMoney(card.estimated_amount)}</span>
        </header>
        {card.company_name ? <p className="muted sales-pipe-card__name">{card.name}</p> : null}
        <div className="sales-pipe-card__meta">
          <span>{card.contact_name || 'Sans contact'}</span>
          <span>{card.owner_label || 'Non assigné'}</span>
        </div>
        <div className="sales-pipe-card__badges">
          <Badge tone={healthTone(card.health_label)}>
            {card.health_label} {card.health_score}
          </Badge>
          <Badge tone={riskTone(card.risk_level)}>{card.risk_label}</Badge>
          <Badge tone="neutral">{card.aging_label}</Badge>
          <Badge tone="accent">{card.probability} %</Badge>
        </div>
        <p className="muted sales-pipe-card__line">
          Dernière : {card.last_activity_subject || '—'} · Prochaine :{' '}
          {card.next_activity_subject || '—'}
        </p>
        <p className="muted sales-pipe-card__line">
          Priorité {card.priority}
          {card.source ? ` · ${card.source}` : ''} · {card.days_in_stage} j. dans l’étape
        </p>
        {card.badges?.length ? (
          <div className="sales-pipe-card__badges">
            {card.badges.map((b) => (
              <Badge key={b} tone="neutral">
                {b}
              </Badge>
            ))}
          </div>
        ) : null}
      </button>
      {onPeek ? (
        <button
          type="button"
          className="ds-btn btn ghost btn-sm sales-pipe-card__peek"
          onClick={() => onPeek(card.id)}
        >
          Aperçu
        </button>
      ) : null}
    </article>
  )
}

export default function SalesPipelinePage() {
  const { token, orgId } = useAuth()
  const navigate = useNavigate()
  const [board, setBoard] = useState<PipelineBoard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [moving, setMoving] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawer, setDrawer] = useState<PipelineDrawer | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 901px)').matches,
  )
  const [quickKind, setQuickKind] = useState<QuickCreateKind | null>(null)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 901px)')
    const onChange = () => setIsDesktop(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    void api
      .getSalesPipeline(token, orgId)
      .then(setBoard)
      .catch((err: unknown) => {
        const message =
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Impossible de charger le pipeline.'
        setError(message)
        setBoard(null)
      })
      .finally(() => setLoading(false))
  }, [token, orgId])

  useEffect(() => {
    load()
  }, [load])

  const openWorkspace = useCallback(
    (opportunityId: number) => {
      navigate(dealPath(opportunityId))
    },
    [navigate],
  )

  const openDrawer = useCallback(
    (opportunityId: number) => {
      if (!token || orgId == null) return
      setDrawerOpen(true)
      setDrawerLoading(true)
      setDrawer(null)
      void api
        .getSalesPipelineDrawer(token, orgId, opportunityId)
        .then(setDrawer)
        .catch(() => setDrawer(null))
        .finally(() => setDrawerLoading(false))
    },
    [token, orgId],
  )

  const moveCard = useCallback(
    async (opportunityId: number, fromStageId: number, toStageId: number) => {
      if (!token || orgId == null || !board || fromStageId === toStageId) return
      const snapshot = structuredClone(board)
      // Optimistic UI
      setBoard((prev) => {
        if (!prev) return prev
        const next = structuredClone(prev)
        let moved: PipelineCard | null = null
        for (const col of next.stages) {
          const idx = col.cards.findIndex((c) => c.id === opportunityId)
          if (idx >= 0) {
            moved = col.cards.splice(idx, 1)[0]
            col.opportunity_count = col.cards.length
            break
          }
        }
        if (moved) {
          moved.stage_id = toStageId
          const target = next.stages.find((s) => s.stage_id === toStageId)
          if (target) {
            target.cards.unshift(moved)
            target.opportunity_count = target.cards.length
          }
        }
        return next
      })
      setMoving(true)
      try {
        await api.moveSalesOpportunityStage(token, orgId, opportunityId, {
          stage_id: toStageId,
          expected_stage_id: fromStageId,
        })
        load()
      } catch {
        setBoard(snapshot)
        setError('Déplacement refusé — pipeline restauré.')
      } finally {
        setMoving(false)
      }
    },
    [token, orgId, board, load],
  )

  const stageOptions = useMemo(
    () => board?.stages.map((s) => ({ id: s.stage_id, name: s.name })) ?? [],
    [board],
  )

  if (!token || orgId == null) {
    return (
      <Container>
        <PageHeader title="Pipeline" description="Suivez l’avancement de vos opportunités" />
        <EmptyState title="Organisation requise" />
      </Container>
    )
  }

  if (loading) {
    return (
      <Container className="sales-pipeline" aria-busy="true">
        <PageHeader title="Pipeline" description="Chargement du board…" />
        <EmptyState title="Chargement" description="Agrégation des opportunités." />
      </Container>
    )
  }

  if (error && !board) {
    return (
      <Container className="sales-pipeline">
        <PageHeader title="Pipeline" />
        <EmptyState
          title="Erreur"
          description={error}
          action={
            <Button type="button" onClick={load}>
              Réessayer
            </Button>
          }
        />
      </Container>
    )
  }

  if (!board) return null

  const s = board.summary

  return (
    <Container className="sales-pipeline" size="xl">
      <PageHeader
        title={board.pipeline_name}
        description="Suivez l’avancement de vos opportunités"
        eyebrow="Commercial"
        actions={
          <div className="sales-deal__header-actions">
            <Button type="button" variant="primary" onClick={() => setQuickKind('opportunity')}>
              Quick Opportunité
            </Button>
            <Button type="button" variant="secondary" onClick={() => setQuickKind('task')}>
              Quick Tâche
            </Button>
            <Button type="button" variant="secondary" onClick={load} disabled={moving}>
              Actualiser
            </Button>
          </div>
        }
      />

      {error ? <p className="sales-pipeline__banner" role="status">{error}</p> : null}

      <Section title="Résumé" spacing="compact">
        <Grid columns={4} gap={3} responsive>
          <MetricCard title="Ouvertes" value={String(s.open_opportunities)} />
          <MetricCard title="Valeur" value={formatSalesMoney(s.pipeline_value)} />
          <MetricCard title="Pondérée" value={formatSalesMoney(s.weighted_pipeline_value)} />
          <MetricCard
            title="Critiques"
            value={String(s.critical_count)}
            variant={s.critical_count > 0 ? 'accent' : 'default'}
          />
        </Grid>
      </Section>

      {isDesktop ? (
        <div className="sales-pipe-board" role="list">
          {board.stages.map((col) => (
            <section
              key={col.stage_id}
              className="sales-pipe-column"
              role="listitem"
              aria-label={col.name}
              onDragOver={(e) => {
                e.preventDefault()
                e.dataTransfer.dropEffect = 'move'
              }}
              onDrop={(e) => {
                e.preventDefault()
                try {
                  const raw = e.dataTransfer.getData('application/x-sales-opp')
                  const parsed = JSON.parse(raw) as { id: number; stage_id: number }
                  void moveCard(parsed.id, parsed.stage_id, col.stage_id)
                } catch {
                  /* ignore */
                }
              }}
            >
              <header className="sales-pipe-column__head">
                <h3>{col.name}</h3>
                <Badge tone="neutral">{col.opportunity_count}</Badge>
              </header>
              <p className="muted sales-pipe-column__stats">
                {formatSalesMoney(col.amount_total)} · pond. {formatSalesMoney(col.weighted_amount)}
              </p>
              <p className="muted sales-pipe-column__stats">
                Proba. moy. {col.average_probability} % · {col.average_days_in_stage} j. moy.
              </p>
              <div className="sales-pipe-column__cards">
                {col.cards.length === 0 ? (
                  <EmptyState title="Vide" description="Glissez une opportunité ici." />
                ) : (
                  col.cards.map((card) => (
                    <PipelineCardView
                      key={card.id}
                      card={card}
                      onOpen={openWorkspace}
                      onPeek={openDrawer}
                      draggable={!moving}
                    />
                  ))
                )}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="sales-pipe-mobile">
          {board.stages.map((col) => (
            <Section
              key={col.stage_id}
              title={col.name}
              description={`${col.opportunity_count} opp. · ${formatSalesMoney(col.amount_total)}`}
              spacing="compact"
            >
              {col.cards.length === 0 ? (
                <EmptyState title="Aucune opportunité" />
              ) : (
                col.cards.map((card) => (
                  <div key={card.id} className="sales-pipe-mobile__row">
                    <PipelineCardView
                      card={card}
                      onOpen={openWorkspace}
                      onPeek={openDrawer}
                      draggable={false}
                    />
                    <label className="sales-pipe-mobile__move">
                      <span className="muted">Étape</span>
                      <select
                        aria-label={`Déplacer ${card.name}`}
                        value={card.stage_id}
                        disabled={moving}
                        onChange={(e) => {
                          void moveCard(card.id, card.stage_id, Number(e.target.value))
                        }}
                      >
                        {stageOptions.map((opt) => (
                          <option key={opt.id} value={opt.id}>
                            {opt.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                ))
              )}
            </Section>
          ))}
        </div>
      )}

      <Drawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        title={drawer?.opportunity.name ?? 'Opportunité'}
        description={drawer?.stage_name}
        size="lg"
        side="right"
        footer={
          drawer ? (
            <div className="sales-pipe-drawer__actions">
              {drawer.quick_actions.map((a) => (
                <QuickActionCard
                  key={a.id}
                  title={a.label}
                  href={a.href}
                  compact
                />
              ))}
              <Link
                to={dealPath(drawer.opportunity.id)}
                className="ds-btn btn secondary btn-sm"
              >
                Ouvrir deal
              </Link>
            </div>
          ) : null
        }
      >
        {drawerLoading ? (
          <EmptyState title="Chargement" />
        ) : !drawer ? (
          <EmptyState title="Introuvable" />
        ) : (
          <div className="sales-pipe-drawer">
            <Section title="Synthèse" spacing="compact">
              <p>
                <strong>{formatSalesMoney(drawer.amount)}</strong> · {drawer.probability} % ·{' '}
                {drawer.opportunity.health_label} ({drawer.opportunity.health_score}) ·{' '}
                {drawer.opportunity.risk_label}
              </p>
              <p className="muted">
                {drawer.company_name || 'Sans entreprise'} · Aging {drawer.opportunity.aging_label}
              </p>
              <label className="sales-pipe-drawer__stage">
                Modifier l’étape
                <select
                  value={drawer.stage_id}
                  disabled={moving}
                  onChange={(e) => {
                    const to = Number(e.target.value)
                    void moveCard(drawer.opportunity.id, drawer.stage_id, to).then(() =>
                      openDrawer(drawer.opportunity.id),
                    )
                  }}
                >
                  {stageOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.name}
                    </option>
                  ))}
                </select>
              </label>
            </Section>

            <Section title="Contacts" spacing="compact">
              {drawer.contacts.length === 0 ? (
                <EmptyState title="Aucun contact" />
              ) : (
                <ul className="sales-pipe-drawer__list">
                  {drawer.contacts.map((c) => (
                    <li key={c.id}>
                      {c.first_name} {c.last_name}
                      {c.job_title ? ` — ${c.job_title}` : ''}
                      <span className="muted">
                        {' '}
                        {c.email || ''} {c.phone || ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section title="Activités" spacing="compact">
              {drawer.activities.length === 0 ? (
                <EmptyState title="Aucune activité" />
              ) : (
                <ul className="sales-pipe-drawer__list">
                  {drawer.activities.map((a) => (
                    <li key={a.id}>
                      <Badge tone="neutral">{a.activity_type}</Badge> {a.subject}
                    </li>
                  ))}
                </ul>
              )}
              <Link to="/sales/activities">Nouvelle activité →</Link>
            </Section>

            <Section title="Tâches" spacing="compact">
              {drawer.tasks.length === 0 ? (
                <EmptyState title="Aucune tâche" />
              ) : (
                <ul className="sales-pipe-drawer__list">
                  {drawer.tasks.map((t) => (
                    <li key={t.id}>
                      {t.title}{' '}
                      <Badge tone="accent">
                        {t.status}/{t.priority}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
              <Link to="/sales/tasks">Nouvelle tâche →</Link>
            </Section>

            <Section title="Notes" spacing="compact">
              {drawer.notes.length === 0 ? (
                <EmptyState title="Aucune note" />
              ) : (
                <ul className="sales-pipe-drawer__list">
                  {drawer.notes.map((n) => (
                    <li key={n.id}>
                      <pre className="sales-pipe-drawer__note">{n.body_markdown}</pre>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </div>
        )}
      </Drawer>

      <QuickCreateDrawer
        open={quickKind != null}
        kind={quickKind}
        onOpenChange={(open) => {
          if (!open) setQuickKind(null)
        }}
        onCreated={() => {
          setQuickKind(null)
          load()
        }}
      />
    </Container>
  )
}
