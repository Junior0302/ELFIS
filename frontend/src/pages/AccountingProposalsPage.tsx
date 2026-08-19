import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro } from '../api'
import { useAuth } from '../auth'

type ProposalItem = {
  proposal_id: string
  vault_document_id: string
  document_type: string
  document_number?: string | null
  supplier_name?: string | null
  customer_name?: string | null
  amount_ttc?: number | null
  currency: string
  status: string
  confidence?: number | null
  requires_review: boolean
  created_at: string
}

const STATUS_LABEL: Record<string, string> = {
  ready_for_validation: 'Prête',
  requires_review: 'À vérifier',
  validated: 'Validée',
  rejected: 'Rejetée',
  mapping_failed: 'Écriture KO',
  financial_error: 'Montants KO',
  validation_failed: 'Validation KO',
  processing: 'En cours',
  pending: 'En attente',
}

export default function AccountingProposalsPage() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<ProposalItem[]>([])
  const [status, setStatus] = useState('')
  const [reviewOnly, setReviewOnly] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    if (!token) return
    api
      .listAccountingProposals(
        {
          status: status || undefined,
          requires_review: reviewOnly ? true : undefined,
        },
        token,
        orgId,
      )
      .then((res) => setItems(res.proposals))
      .catch((e) => setError(e.message || 'Erreur de chargement'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Écritures comptables</h1>
          <p className="muted">
            Proposition générée par ELFIS IA — vérification humaine requise
          </p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <div className="toolbar" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les statuts</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <label>
          <input
            type="checkbox"
            checked={reviewOnly}
            onChange={(e) => setReviewOnly(e.target.checked)}
          />{' '}
          Review nécessaire
        </label>
        <button type="button" className="btn" onClick={load}>
          Filtrer
        </button>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Tiers</th>
              <th>TTC</th>
              <th>Statut</th>
              <th>Confiance</th>
              <th>Review</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.proposal_id}>
                <td>
                  <div>{p.document_number || p.document_type}</div>
                  <small className="muted">{p.document_type}</small>
                </td>
                <td>{p.supplier_name || p.customer_name || '—'}</td>
                <td>{formatEuro(p.amount_ttc)}</td>
                <td>{STATUS_LABEL[p.status] || p.status}</td>
                <td>
                  {p.confidence != null ? `${Math.round(p.confidence * 100)}%` : '—'}
                </td>
                <td>{p.requires_review ? 'Oui' : 'Non'}</td>
                <td>{new Date(p.created_at).toLocaleDateString('fr-FR')}</td>
                <td>
                  <Link to={`/accounting/proposals/${p.proposal_id}`}>Consulter</Link>
                </td>
              </tr>
            ))}
            {!items.length ? (
              <tr>
                <td colSpan={8} className="muted">
                  Aucune proposition pour le moment.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
