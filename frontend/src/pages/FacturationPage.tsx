import { useEffect, useState, type FormEvent } from 'react'
import { api, formatEuro, type BillingOverview, type SalesDoc } from '../api'
import { useAuth } from '../auth'

export default function FacturationPage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<BillingOverview | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    doc_type: 'devis',
    customer_name: 'Dupont SAS',
    amount_ht: 1000,
    vat_rate: 20,
    notes: '',
  })

  const load = () => {
    api
      .billingOverview(token, orgId)
      .then(setData)
      .catch((e) => setError(e.message || 'Erreur facturation'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const onCreate = async (e: FormEvent) => {
    e.preventDefault()
    setMessage('')
    try {
      await api.createSalesDoc(form, token, orgId)
      setMessage('Document créé.')
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création impossible')
    }
  }

  const act = async (doc: SalesDoc, action: string, body?: object) => {
    setMessage('')
    try {
      await api.billingAction(doc.id, action, token, orgId, body)
      setMessage(`Action ${action} OK sur ${doc.number}`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible')
    }
  }

  if (error && !data) return <div className="panel form-error">{error}</div>
  if (!data) return <div className="loading">Chargement facturation…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Facturation</h2>
          <p>
            Créez devis et factures, suivez les paiements et repérez rapidement les clients en
            retard.
          </p>
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <span>Documents</span>
          <strong>{data.stats.documents}</strong>
        </div>
        <div className="stat">
          <span>Clients</span>
          <strong>{data.stats.customers}</strong>
        </div>
        <div className="stat">
          <span>Impayés</span>
          <strong>{data.stats.unpaid}</strong>
        </div>
        <div className="stat">
          <span>Montant dû</span>
          <strong>{formatEuro(data.stats.unpaid_amount)}</strong>
        </div>
      </div>

      <div className="result-grid" style={{ minHeight: 'auto' }}>
        <form className="panel" onSubmit={onCreate}>
          <h3>Créer un document</h3>
          <div className="form-grid">
            <div className="field">
              <label>Type</label>
              <select
                value={form.doc_type}
                onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
              >
                <option value="devis">Devis</option>
                <option value="facture">Facture</option>
                <option value="avoir">Avoir</option>
              </select>
            </div>
            <div className="field">
              <label>Client</label>
              <input
                value={form.customer_name}
                onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                list="customers"
              />
              <datalist id="customers">
                {data.customers.map((c) => (
                  <option key={c.id} value={c.name} />
                ))}
              </datalist>
            </div>
            <div className="field">
              <label>Montant HT</label>
              <input
                type="number"
                step="0.01"
                value={form.amount_ht}
                onChange={(e) => setForm({ ...form, amount_ht: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label>TVA %</label>
              <input
                type="number"
                step="0.1"
                value={form.vat_rate}
                onChange={(e) => setForm({ ...form, vat_rate: Number(e.target.value) })}
              />
            </div>
            <div className="field full">
              <label>Notes</label>
              <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit">
              Créer
            </button>
          </div>
        </form>

        <section className="panel">
          <h3>Pipeline</h3>
          <p className="muted">
            Devis → envoyer → signer → convertir en facture → relancer → encaisser · ou créer un avoir.
          </p>
          <div className="stats" style={{ gridTemplateColumns: '1fr 1fr 1fr', marginBottom: 0 }}>
            <div className="stat">
              <span>Devis</span>
              <strong>{data.stats.quotes}</strong>
            </div>
            <div className="stat">
              <span>Factures</span>
              <strong>{data.stats.invoices}</strong>
            </div>
            <div className="stat">
              <span>Avoirs</span>
              <strong>{data.stats.credits}</strong>
            </div>
          </div>
        </section>
      </div>

      {message && <p className="muted">{message}</p>}
      {error && <p className="form-error">{error}</p>}

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h3>Documents</h3>
        {data.documents.length === 0 ? (
          <div className="empty">Aucun document. Créez un devis pour démarrer.</div>
        ) : (
          <div className="list">
            {data.documents.map((doc) => (
              <div key={doc.id} className="list-item" style={{ gridTemplateColumns: '1.4fr 0.7fr 0.7fr 1.8fr' }}>
                <div>
                  <strong>
                    {doc.number} · {doc.doc_type}
                  </strong>
                  <span>
                    {doc.customer_name} · {doc.issue_date} · {doc.status}
                    {doc.signature_status !== 'none' ? ` · signature ${doc.signature_status}` : ''}
                  </span>
                </div>
                <div>
                  <strong>{formatEuro(doc.amount_ttc)}</strong>
                  <span>TTC</span>
                </div>
                <div>
                  <strong>{formatEuro(doc.paid_amount)}</strong>
                  <span>Payé</span>
                </div>
                <div className="actions" style={{ marginTop: 0 }}>
                  <button className="btn secondary" type="button" onClick={() => void act(doc, 'send')}>
                    Envoyer
                  </button>
                  {doc.doc_type === 'devis' && (
                    <>
                      <button className="btn secondary" type="button" onClick={() => void act(doc, 'sign')}>
                        Signer
                      </button>
                      <button className="btn secondary" type="button" onClick={() => void act(doc, 'convert')}>
                        → Facture
                      </button>
                    </>
                  )}
                  {doc.doc_type === 'facture' && (
                    <>
                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() =>
                          void act(doc, 'pay', {
                            amount: Math.max(doc.amount_ttc - doc.paid_amount, 0),
                            method: 'virement',
                          })
                        }
                      >
                        Payer
                      </button>
                      <button className="btn secondary" type="button" onClick={() => void act(doc, 'remind')}>
                        Relancer
                      </button>
                      <button
                        className="btn secondary"
                        type="button"
                        onClick={() => void act(doc, 'credit-note')}
                      >
                        Avoir
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  )
}
