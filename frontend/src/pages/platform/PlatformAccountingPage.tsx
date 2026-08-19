import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { EmptyState, ErrorState, Skeleton, UiBadge } from '../../ui/UiStates'

export default function PlatformAccountingPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [proposals, setProposals] = useState<
    Array<{
      proposal_id: string
      organization_id: number
      status: string
      confidence?: number | null
      requires_review: boolean
      amount_ttc?: number | null
      document_type: string
    }>
  >([])
  const [reviewsTotal, setReviewsTotal] = useState(0)
  const [orgFilter, setOrgFilter] = useState('')

  async function load() {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const orgId = orgFilter ? Number(orgFilter) : undefined
      const [props, reviews] = await Promise.all([
        api.platformAccountingProposals(token, {
          organization_id: orgId,
          page: 1,
          page_size: 50,
        }),
        api.platformAccountingReviews(token, { organization_id: orgId, page: 1, page_size: 1 }),
      ])
      setProposals(props.proposals || [])
      setReviewsTotal(reviews.total || 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'API comptabilité indisponible')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [token])

  return (
    <>
      <div className="platform-title">
        <span>Comptabilité</span>
        <h1>Propositions plateforme</h1>
        <p>Scores, validation et reviews — API `/platform/accounting` uniquement.</p>
      </div>
      <div className="platform-toolbar">
        <input
          placeholder="Filtrer org id"
          value={orgFilter}
          onChange={(e) => setOrgFilter(e.target.value)}
          aria-label="Organisation"
        />
        <button type="button" className="btn secondary" onClick={() => void load()}>
          Filtrer
        </button>
        <UiBadge>{reviewsTotal} reviews</UiBadge>
        <Link className="btn secondary" to="/elfadmin/ia">
          Voir IA / learning
        </Link>
      </div>
      {loading ? <Skeleton rows={6} /> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!loading && !error && proposals.length === 0 ? (
        <EmptyState title="Aucune proposition" description="Aucune donnée pour ce filtre." />
      ) : null}
      {!loading && proposals.length > 0 ? (
        <div className="platform-table-wrap">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Proposition</th>
                <th>Org</th>
                <th>Type</th>
                <th>Statut</th>
                <th>Score</th>
                <th>TTC</th>
              </tr>
            </thead>
            <tbody>
              {proposals.map((p) => (
                <tr key={p.proposal_id}>
                  <td>
                    <code>{p.proposal_id.slice(0, 8)}</code>
                    {p.requires_review ? <UiBadge tone="warn">review</UiBadge> : null}
                  </td>
                  <td>{p.organization_id}</td>
                  <td>{p.document_type}</td>
                  <td>{p.status}</td>
                  <td>
                    {p.confidence != null ? `${Math.round(Number(p.confidence) * 100)} %` : '—'}
                  </td>
                  <td>{p.amount_ttc ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  )
}
