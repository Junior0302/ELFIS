import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  PageHeader,
  Section,
  Stack,
} from '../../design-system'
import { ConfirmDialog } from '../../design-system/overlays'
import { SalesFocusCard } from '../../sales/SalesFocusCard'
import {
  intelligencePath,
  severityTone,
  type IntelligenceOverview,
  type SalesInsight,
} from '../../sales/salesIntelligence'
import './sales-workspace.css'

function InsightRow({ item }: { item: SalesInsight }) {
  return (
    <li className="sales-workspace__list-item">
      <header>
        <strong>{item.title}</strong>
        <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>
      </header>
      <p className="muted">{item.summary}</p>
      <div className="sales-deal__header-actions">
        <Link to={intelligencePath(item.id)} className="ds-btn btn secondary btn-sm">
          Détail
        </Link>
        {item.route ? (
          <Link to={item.route} className="ds-btn btn secondary btn-sm">
            Ressource
          </Link>
        ) : null}
      </div>
    </li>
  )
}

export default function SalesIntelligencePage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<IntelligenceOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [category, setCategory] = useState('')
  const [severity, setSeverity] = useState('')
  const [list, setList] = useState<SalesInsight[]>([])

  const load = useCallback(() => {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    void api
      .getSalesIntelligence(token, orgId)
      .then(setData)
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Intelligence indisponible.',
        )
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [token, orgId])

  const loadList = useCallback(() => {
    if (!token || orgId == null) return
    void api
      .listSalesInsights(token, orgId, {
        category: category || undefined,
        severity: severity || undefined,
        limit: 50,
      })
      .then((res) => setList(res.items))
      .catch(() => setList([]))
  }, [token, orgId, category, severity])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    loadList()
  }, [loadList])

  useEffect(() => {
    const onFocus = () => {
      load()
      loadList()
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [load, loadList])

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="SalesPilot"
        title="Priorités commerciales"
        description="Recommandations déterministes — aucune IA générative."
        actions={
          <Button type="button" variant="secondary" onClick={load}>
            Actualiser
          </Button>
        }
      />

      {loading ? (
        <p className="muted">Chargement…</p>
      ) : error && !data ? (
        <EmptyState title="Erreur" description={error} action={<Button onClick={load}>Réessayer</Button>} />
      ) : data ? (
        <Stack gap={5}>
          <SalesFocusCard focus={data.focus} />

          <Section title="Résumé" spacing="compact">
            <dl className="sales-workspace__meta-row">
              <div>
                <dt>Actifs</dt>
                <dd>{data.summary.active_count}</dd>
              </div>
              <div>
                <dt>Critiques</dt>
                <dd>{data.summary.critical_count}</dd>
              </div>
              <div>
                <dt>Élevés</dt>
                <dd>{data.summary.high_count}</dd>
              </div>
              <div>
                <dt>Propositions</dt>
                <dd>{data.summary.proposal_count}</dd>
              </div>
            </dl>
          </Section>

          <Section title="Top recommandations" spacing="compact">
            {data.top_insights.length === 0 ? (
              <EmptyState title="Aucune recommandation" description="État : aucun signal actif." />
            ) : (
              <ul className="sales-workspace__list">
                {data.top_insights.map((i) => (
                  <InsightRow key={i.id} item={i} />
                ))}
              </ul>
            )}
          </Section>

          <Section title="Filtres" spacing="compact">
            <div className="sales-deal__header-actions">
              <label>
                Catégorie{' '}
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="">Toutes</option>
                  <option value="opportunity">Opportunité</option>
                  <option value="pipeline">Pipeline</option>
                  <option value="proposal">Proposition</option>
                  <option value="conversion">Conversion</option>
                  <option value="task">Tâche</option>
                  <option value="activity">Activité</option>
                </select>
              </label>
              <label>
                Sévérité{' '}
                <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                  <option value="">Toutes</option>
                  <option value="critical">critical</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="info">info</option>
                </select>
              </label>
            </div>
            <ul className="sales-workspace__list">
              {list.map((i) => (
                <InsightRow key={i.id} item={i} />
              ))}
            </ul>
          </Section>
        </Stack>
      ) : (
        <EmptyState title="Aucune donnée" />
      )}
    </Container>
  )
}

export function SalesInsightDetailPage() {
  const { token, orgId } = useAuth()
  const { id } = useParams<{ id: string }>()
  const insightId = Number(id)
  const [item, setItem] = useState<SalesInsight | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [dismissOpen, setDismissOpen] = useState(false)
  const [dismissReason, setDismissReason] = useState('')

  const load = useCallback(() => {
    if (!token || orgId == null || !Number.isFinite(insightId)) return
    void api
      .getSalesInsight(token, orgId, insightId)
      .then(setItem)
      .catch((err: unknown) => {
        setError(
          err && typeof err === 'object' && 'message' in err
            ? String((err as { message: unknown }).message)
            : 'Insight introuvable',
        )
      })
  }, [token, orgId, insightId])

  useEffect(() => {
    load()
  }, [load])

  const acknowledge = async () => {
    if (!token || orgId == null) return
    setBusy(true)
    try {
      const next = await api.acknowledgeSalesInsight(token, orgId, insightId)
      setItem(next)
    } catch (err: unknown) {
      setError(
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Acknowledge échoué',
      )
    } finally {
      setBusy(false)
    }
  }

  const dismiss = async () => {
    if (!token || orgId == null) return
    setBusy(true)
    try {
      const next = await api.dismissSalesInsight(token, orgId, insightId, dismissReason)
      setItem(next)
    } finally {
      setBusy(false)
    }
  }

  if (!Number.isFinite(insightId)) {
    return (
      <Container>
        <EmptyState title="Identifiant invalide" />
      </Container>
    )
  }

  return (
    <Container className="sales-workspace">
      <PageHeader
        eyebrow="Priorités commerciales"
        title={item?.title || `Insight #${insightId}`}
        description={item?.summary}
        actions={
          <Link to={intelligencePath()} className="ds-btn btn secondary">
            Liste
          </Link>
        }
      />
      {error ? <p className="muted" role="alert">{error}</p> : null}
      {!item ? (
        <p className="muted">Chargement…</p>
      ) : (
        <Stack gap={4}>
          <div className="sales-workspace__header-meta">
            <Badge tone={severityTone(item.severity)}>{item.severity}</Badge>
            <Badge tone="neutral">{item.category}</Badge>
            <Badge tone="neutral">{item.status}</Badge>
          </div>

          <Section title="Explication" spacing="compact">
            <h3>{item.explanation.headline || item.title}</h3>
            <ul>
              {(item.explanation.observed_facts || []).map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <p>
              <strong>Règle :</strong> {item.explanation.rule_applied}
            </p>
            <p>
              <strong>Impact :</strong> {item.explanation.why_it_matters}
            </p>
            <p>
              <strong>Prochaine étape :</strong> {item.explanation.recommended_next_step}
            </p>
            <p className="muted">
              Résolution : {item.resolution_condition || item.explanation.resolution_condition}
            </p>
          </Section>

          <Section title="Preuves" spacing="compact">
            <ul className="sales-workspace__list">
              {(item.evidence || []).map((e, idx) => (
                <li key={idx} className="sales-workspace__list-item">
                  <header>
                    <strong>{String(e.label || e.type)}</strong>
                    <span>{String(e.value ?? '—')}</span>
                  </header>
                </li>
              ))}
            </ul>
          </Section>

          <div className="sales-deal__header-actions">
            {item.route ? (
              <Link to={item.route} className="ds-btn btn primary">
                {(item.recommended_action?.label as string) || 'Ouvrir la ressource'}
              </Link>
            ) : null}
            {item.linked_decision_id ? (
              <Link to={`/decisions/${item.linked_decision_id}`} className="ds-btn btn secondary">
                Voir la décision liée
              </Link>
            ) : null}
            <Button type="button" variant="secondary" disabled={busy} onClick={() => void acknowledge()}>
              Marquer comme vu
            </Button>
            <Button type="button" variant="danger" disabled={busy} onClick={() => setDismissOpen(true)}>
              Écarter
            </Button>
          </div>
        </Stack>
      )}

      <ConfirmDialog
        open={dismissOpen}
        onOpenChange={setDismissOpen}
        title="Écarter cette recommandation"
        description="L’insight pourra réapparaître si la situation s’aggrave réellement."
        confirmLabel="Écarter"
        tone="warning"
        loading={busy}
        details={
          <label>
            Motif (obligatoire si critique)
            <input
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              style={{ display: 'block', width: '100%', marginTop: 8 }}
            />
          </label>
        }
        onConfirm={dismiss}
      />
    </Container>
  )
}
