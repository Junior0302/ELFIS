import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { accountingIntelligenceApi } from '../services/accountingIntelligenceApi'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../ui/UiStates'

type ProposalItem = {
  proposal_id: string
  document_number?: string | null
  status: string
  confidence?: number | null
  supplier_name?: string | null
}

export default function AccountingHubPage() {
  const { token, orgId } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [proposals, setProposals] = useState<ProposalItem[]>([])
  const [learnedCount, setLearnedCount] = useState(0)

  useEffect(() => {
    if (!token || orgId == null) return
    void api.markAccountingDiscovered(token, orgId).catch(() => undefined)
  }, [token, orgId])

  async function load() {
    if (!token || orgId == null) return
    setLoading(true)
    setError('')
    try {
      const [list, learning] = await Promise.all([
        api.listAccountingProposals({ page: 1, page_size: 8 }, token, orgId),
        accountingIntelligenceApi.learning(token, orgId).catch(() => ({ items: [] })),
      ])
      setProposals(list.proposals || [])
      setLearnedCount(Array.isArray(learning.items) ? learning.items.length : 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chargement impossible')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [token, orgId])

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Comptabilité</h1>
          <p className="muted">
            Propositions, intelligence et historique — données API uniquement, aucune écriture
            automatique.
          </p>
        </div>
      </header>

      <div className="ui-card-grid">
        <Link className="ui-card ui-card-link" to="/accounting/proposals">
          <h3>Propositions</h3>
          <p className="muted">Écritures proposées à valider (V1).</p>
        </Link>
        <Link className="ui-card ui-card-link" to="/accounting/engine">
          <h3>Moteur V2</h3>
          <p className="muted">Générer une proposition avec score de confiance.</p>
        </Link>
        <Link className="ui-card ui-card-link" to="/accounting/intelligence">
          <h3>Explications & Intelligence</h3>
          <p className="muted">Recommandations, feedback, apprentissage.</p>
        </Link>
        <Link className="ui-card ui-card-link" to="/history">
          <h3>Historique</h3>
          <p className="muted">Documents traités et exports.</p>
        </Link>
      </div>

      <section className="panel" style={{ marginTop: '1.5rem' }}>
        <div className="ui-row-between">
          <h2>Dernières propositions</h2>
          <UiBadge tone="ok">{learnedCount} élément(s) appris</UiBadge>
        </div>
        {loading ? <Skeleton rows={4} /> : null}
        {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
        {!loading && !error && proposals.length === 0 ? (
          <EmptyState
            title="Aucune proposition"
            description="Générez une écriture depuis un document analysé ou le moteur V2."
            action={
              <Link className="btn secondary" to="/accounting/engine">
                Ouvrir le moteur
              </Link>
            }
          />
        ) : null}
        {!loading && proposals.length > 0 ? (
          <ul className="ui-list">
            {proposals.map((p) => (
              <li key={p.proposal_id}>
                <Link to={`/accounting/proposals/${p.proposal_id}`}>
                  {p.document_number || p.supplier_name || p.proposal_id} · {p.status} ·{' '}
                  {p.confidence != null ? `${Math.round(Number(p.confidence) * 100)} %` : '—'}
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  )
}
