import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, formatEuro } from '../api'
import { useAuth } from '../auth'

type Detail = {
  proposal_id: string
  document_type: string
  document_number?: string | null
  supplier_name?: string | null
  customer_name?: string | null
  amount_ht?: number | null
  amount_vat?: number | null
  amount_ttc?: number | null
  currency: string
  status: string
  confidence?: number | null
  requires_review: boolean
  review_reasons: string[]
  document_validation: Record<string, unknown>
  financial_validation: Record<string, unknown>
  disclaimer: string
  allowed_actions: string[]
  entry?: {
    entry_id: string
    journal_code: string
    description: string
    total_debit: number
    total_credit: number
    balanced: boolean
    lines: Array<{
      line_id: string
      line_number: number
      account_code: string
      account_label?: string | null
      debit: number
      credit: number
    }>
  } | null
  reviews: Array<{
    review_id: string
    action: string
    comment?: string | null
    created_at: string
  }>
}

export default function AccountingProposalDetailPage() {
  const { proposalId } = useParams()
  const { token, orgId } = useAuth()
  const [detail, setDetail] = useState<Detail | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const load = () => {
    if (!token || !proposalId) return
    api
      .getAccountingProposal(proposalId, token, orgId)
      .then((d) => setDetail(d as unknown as Detail))
      .catch((e) => setError(e.message || 'Erreur'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId, proposalId])

  const onValidate = async () => {
    if (!token || !proposalId) return
    setBusy(true)
    setError('')
    try {
      const d = await api.validateAccountingProposal(
        proposalId,
        { confirm_balanced_entry: true, confirm_document_reviewed: true },
        token,
        orgId,
      )
      setDetail(d as unknown as Detail)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation impossible')
    } finally {
      setBusy(false)
    }
  }

  const onReject = async () => {
    if (!token || !proposalId || !rejectReason.trim()) return
    setBusy(true)
    try {
      const d = await api.rejectAccountingProposal(
        proposalId,
        { reason: rejectReason.trim() },
        token,
        orgId,
      )
      setDetail(d as unknown as Detail)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rejet impossible')
    } finally {
      setBusy(false)
    }
  }

  const onReopen = async () => {
    if (!token || !proposalId) return
    setBusy(true)
    try {
      const d = await api.reopenAccountingProposal(proposalId, token, orgId)
      setDetail(d as unknown as Detail)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reouverture impossible')
    } finally {
      setBusy(false)
    }
  }

  if (!detail) {
    return (
      <div className="page">
        <p>{error || 'Chargement…'}</p>
        <Link to="/accounting/proposals">Retour</Link>
      </div>
    )
  }

  const entry = detail.entry

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="muted">
            <Link to="/accounting/proposals">← Écritures</Link>
          </p>
          <h1>{detail.document_number || detail.document_type}</h1>
          <p className="muted">{detail.disclaimer}</p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}

      <section className="card-like" style={{ marginBottom: '1.5rem' }}>
        <h2>Document</h2>
        <p>
          Type : <strong>{detail.document_type}</strong>
        </p>
        <p>Fournisseur : {detail.supplier_name || '—'}</p>
        <p>Client : {detail.customer_name || '—'}</p>
        <p>
          HT {formatEuro(detail.amount_ht)} · TVA {formatEuro(detail.amount_vat)} · TTC{' '}
          {formatEuro(detail.amount_ttc)}
        </p>
        <p>
          Statut : <strong>{detail.status}</strong>
          {detail.confidence != null
            ? ` · confiance ${Math.round(detail.confidence * 100)}%`
            : ''}
        </p>
        {detail.requires_review ? (
          <p className="warning">
            Review : {(detail.review_reasons || []).join(', ') || 'nécessaire'}
          </p>
        ) : null}
      </section>

      <section style={{ marginBottom: '1.5rem' }}>
        <h2>Validations</h2>
        <p>
          Documentaire : {String(detail.document_validation?.status || '—')} · Financière :{' '}
          {String(detail.financial_validation?.status || '—')}
        </p>
      </section>

      {entry ? (
        <section style={{ marginBottom: '1.5rem' }}>
          <h2>Proposition d&apos;écriture ({entry.journal_code})</h2>
          <p>{entry.description}</p>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Compte</th>
                <th>Libellé</th>
                <th>Débit</th>
                <th>Crédit</th>
              </tr>
            </thead>
            <tbody>
              {entry.lines.map((l) => (
                <tr key={l.line_id}>
                  <td>{l.line_number}</td>
                  <td>{l.account_code}</td>
                  <td>{l.account_label || '—'}</td>
                  <td>{formatEuro(l.debit)}</td>
                  <td>{formatEuro(l.credit)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>
                  Totaux — {entry.balanced ? 'Équilibrée' : 'Non équilibrée'}
                </td>
                <td>{formatEuro(entry.total_debit)}</td>
                <td>{formatEuro(entry.total_credit)}</td>
              </tr>
            </tfoot>
          </table>
        </section>
      ) : (
        <p className="muted">Aucune écriture proposée.</p>
      )}

      <section style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        {detail.allowed_actions.includes('validate') ? (
          <button type="button" className="btn primary" disabled={busy} onClick={() => void onValidate()}>
            Valider
          </button>
        ) : null}
        {detail.allowed_actions.includes('reject') ? (
          <>
            <input
              placeholder="Motif de rejet"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <button type="button" className="btn" disabled={busy} onClick={() => void onReject()}>
              Rejeter
            </button>
          </>
        ) : null}
        {detail.allowed_actions.includes('reopen') ? (
          <button type="button" className="btn" disabled={busy} onClick={() => void onReopen()}>
            Rouvrir
          </button>
        ) : null}
      </section>

      <section>
        <h2>Historique</h2>
        <ul>
          {detail.reviews.map((r) => (
            <li key={r.review_id}>
              {new Date(r.created_at).toLocaleString('fr-FR')} — {r.action}
              {r.comment ? ` : ${r.comment}` : ''}
            </li>
          ))}
          {!detail.reviews.length ? <li className="muted">Aucun historique</li> : null}
        </ul>
      </section>
    </div>
  )
}
