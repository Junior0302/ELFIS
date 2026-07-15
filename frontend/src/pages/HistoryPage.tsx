import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, downloadApiFile, formatEuro, type Invoice } from '../api'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../auth'

export default function HistoryPage() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<Invoice[]>([])
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [reviewOnly, setReviewOnly] = useState(false)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = () => {
    if (!token) return
    api
      .listDocuments({
        q: q || undefined,
        status: status || undefined,
        needs_review: reviewOnly ? true : undefined,
      }, token, orgId)
      .then(setItems)
      .catch((e) => setError(e.message || 'Erreur de chargement'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const onDelete = async (id: number) => {
    if (!window.confirm('Supprimer ce document ?')) return
    setBusyId(id)
    try {
      if (!token) throw new Error('Authentification requise')
      await api.deleteDocument(id, token, orgId)
      setItems((prev) => prev.filter((item) => item.id !== id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Suppression impossible')
    } finally {
      setBusyId(null)
    }
  }

  const download = async (path: string) => {
    if (!token) return
    setError('')
    try {
      await downloadApiFile(path, token, orgId)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Export impossible')
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Comptabilité</h2>
          <p>
            Vos factures fournisseur traitées par l’OCR — contrôlez, exportez en Excel, FEC ou vers
            votre logiciel.
          </p>
        </div>
        <button className="btn secondary" type="button" onClick={() => void download('/exports/history/excel')}>
          Excel
        </button>
        <button className="btn secondary" type="button" onClick={() => void download('/exports/history/fec')}>
          FEC
        </button>
        <button className="btn secondary" type="button" onClick={() => void download('/exports/history/pennylane')}>
          Pennylane
        </button>
        <button className="btn secondary" type="button" onClick={() => void download('/exports/history/sage')}>
          Sage
        </button>
      </div>

      <div className="toolbar">
        <input
          placeholder="Recherche fournisseur, n°, fichier…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les statuts</option>
          <option value="ready">Prêt</option>
          <option value="to_review">À vérifier</option>
          <option value="processing">En cours</option>
          <option value="error">Erreur</option>
        </select>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
          <input type="checkbox" checked={reviewOnly} onChange={(e) => setReviewOnly(e.target.checked)} />
          À vérifier uniquement
        </label>
        <button className="btn" type="button" onClick={load}>
          Filtrer
        </button>
      </div>

      {error && <div className="panel form-error">{error}</div>}

      <section className="panel">
        {items.length === 0 ? (
          <div className="empty">
            Aucun document réel pour l&apos;instant.
            <div style={{ marginTop: '1rem' }}>
              <Link className="btn" to="/deposit">
                Déposer votre première facture
              </Link>
            </div>
          </div>
        ) : (
          <div className="list">
            {items.map((inv) => (
              <div key={inv.id} className="list-item">
                <div>
                  <strong>{inv.supplier || inv.filename}</strong>
                  <span>
                    {inv.invoice_number || '—'} · {inv.invoice_date || '—'} · {inv.document_type}
                  </span>
                </div>
                <div>
                  <strong>{formatEuro(inv.amount_ht)}</strong>
                  <span>HT</span>
                </div>
                <div>
                  <strong>{formatEuro(inv.amount_tva)}</strong>
                  <span>TVA</span>
                </div>
                <div>
                  <StatusBadge needsReview={inv.needs_review} status={inv.status} />
                </div>
                <div className="actions" style={{ marginTop: 0 }}>
                  <Link className="btn secondary" to={`/result/${inv.id}`}>
                    Ouvrir
                  </Link>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => void download(`/exports/${inv.id}/excel`)}
                  >
                    Excel
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    disabled={busyId === inv.id}
                    onClick={() => void onDelete(inv.id)}
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  )
}
