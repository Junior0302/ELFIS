import { useEffect, useState, type FormEvent } from 'react'
import { api, formatEuro, type BillingOverview, type SalesDoc } from '../api'
import { useAuth } from '../auth'
import SalesDocPreviewModal from '../components/SalesDocPreviewModal'

const emptyForm = {
  doc_type: 'facture',
  customer_name: '',
  customer_email: '',
  customer_id: null as number | null,
  amount_ht: 0,
  vat_rate: 20,
  notes: '',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  sent: 'Envoyé',
  accepted: 'Accepté',
  refused: 'Refusé',
  partial: 'Partiel',
  paid: 'Payé',
  overdue: 'En retard',
  cancelled: 'Annulé',
}

const TYPE_LABELS: Record<string, string> = {
  devis: 'Devis',
  facture: 'Facture',
  avoir: 'Avoir',
}

function statusBadgeClass(status: string) {
  if (status === 'paid' || status === 'accepted') return 'badge ok'
  if (status === 'overdue' || status === 'refused') return 'badge danger'
  if (status === 'sent' || status === 'partial') return 'badge warn'
  return 'badge'
}

export default function FacturationPage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<BillingOverview | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [previewDoc, setPreviewDoc] = useState<SalesDoc | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [typeFilter, setTypeFilter] = useState<'all' | 'devis' | 'facture' | 'avoir'>('all')

  const load = () => {
    if (!token) return
    api
      .billingOverview(token, orgId)
      .then(setData)
      .catch((e) => setError(e.message || 'Erreur facturation'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const fillFromCustomerName = (name: string) => {
    const customer = data?.customers.find((c) => c.name === name)
    setForm((current) => ({
      ...current,
      customer_name: name,
      customer_id: customer?.id ?? null,
      customer_email: customer?.email || current.customer_email,
    }))
  }

  const startEdit = (doc: SalesDoc) => {
    setEditingId(doc.id)
    setPreviewDoc(null)
    setForm({
      doc_type: doc.doc_type,
      customer_name: doc.customer_name,
      customer_email: doc.customer_email || '',
      customer_id: null,
      amount_ht: doc.amount_ht,
      vat_rate: doc.vat_rate,
      notes: doc.notes || '',
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setMessage('')
    setError('')
    try {
      if (editingId) {
        await api.updateSalesDoc(
          editingId,
          {
            customer_name: form.customer_name,
            customer_email: form.customer_email,
            customer_id: form.customer_id,
            amount_ht: form.amount_ht,
            vat_rate: form.vat_rate,
            notes: form.notes,
          },
          token,
          orgId,
        )
        setMessage('Document mis à jour.')
        resetForm()
      } else {
        const created = await api.createSalesDoc(form, token, orgId)
        setMessage(`${TYPE_LABELS[created.doc_type] || created.doc_type} ${created.number} créé.`)
        setPreviewDoc(created)
        resetForm()
      }
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enregistrement impossible')
    }
  }

  const visualize = (doc: SalesDoc) => {
    setPreviewDoc(doc)
  }

  const remove = async (doc: SalesDoc) => {
    const label =
      doc.doc_type === 'devis' ? 'ce devis' : doc.doc_type === 'avoir' ? 'cet avoir' : 'cette facture'
    const confirmed = window.confirm(
      `Supprimer ${label} ${doc.number} ?\n\nClient : ${doc.customer_name}\nMontant TTC : ${formatEuro(doc.amount_ttc)}\n\nCette action est définitive.`,
    )
    if (!confirmed) return
    setBusyId(doc.id)
    setMessage('')
    setError('')
    try {
      await api.deleteSalesDoc(doc.id, token, orgId)
      setMessage(`${doc.number} supprimé.`)
      if (editingId === doc.id) resetForm()
      if (previewDoc?.id === doc.id) setPreviewDoc(null)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
    } finally {
      setBusyId(null)
    }
  }

  const act = async (doc: SalesDoc, action: string, body?: object) => {
    setBusyId(doc.id)
    setMessage('')
    setError('')
    try {
      await api.billingAction(doc.id, action, token, orgId, body)
      setMessage(`Action effectuée sur ${doc.number}.`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible')
    } finally {
      setBusyId(null)
    }
  }

  if (error && !data) return <div className="panel form-error">{error}</div>
  if (!data) return <div className="loading">Chargement facturation…</div>

  const documents =
    typeFilter === 'all'
      ? data.documents
      : data.documents.filter((doc) => doc.doc_type === typeFilter)

  return (
    <div className="billing-page">
      <div className="page-head">
        <div>
          <h2>Facturation</h2>
          <p>Créez devis et factures, suivez les encaissements et relances.</p>
        </div>
      </div>

      <div className="stats billing-stats">
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

      <div className="billing-top">
        <form className="panel billing-create" onSubmit={onSubmit}>
          <h3>{editingId ? 'Modifier le document' : 'Créer un document'}</h3>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="bill_type">Type</label>
              <select
                id="bill_type"
                value={form.doc_type}
                disabled={Boolean(editingId)}
                onChange={(e) => setForm({ ...form, doc_type: e.target.value })}
              >
                <option value="devis">Devis</option>
                <option value="facture">Facture</option>
                <option value="avoir">Avoir</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="bill_client">Client</label>
              <input
                id="bill_client"
                value={form.customer_name}
                onChange={(e) => fillFromCustomerName(e.target.value)}
                list="customers"
                required
              />
              <datalist id="customers">
                {data.customers.map((c) => (
                  <option key={c.id} value={c.name} />
                ))}
              </datalist>
            </div>
            <div className="field">
              <label htmlFor="bill_email">E-mail client</label>
              <input
                id="bill_email"
                type="email"
                value={form.customer_email}
                onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
                placeholder="optionnel"
              />
            </div>
            <div className="field">
              <label htmlFor="bill_ht">Montant HT</label>
              <input
                id="bill_ht"
                type="number"
                step="0.01"
                value={form.amount_ht}
                onChange={(e) => setForm({ ...form, amount_ht: Number(e.target.value) })}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="bill_tva">TVA %</label>
              <input
                id="bill_tva"
                type="number"
                step="0.1"
                value={form.vat_rate}
                onChange={(e) => setForm({ ...form, vat_rate: Number(e.target.value) })}
              />
            </div>
            <div className="field full">
              <label htmlFor="bill_notes">Notes</label>
              <input
                id="bill_notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit">
              {editingId ? 'Enregistrer' : 'Créer'}
            </button>
            {editingId && (
              <button className="btn secondary" type="button" onClick={resetForm}>
                Annuler
              </button>
            )}
          </div>
        </form>

        <aside className="panel billing-pipeline">
          <h3>Répartition</h3>
          <div className="billing-pipeline-stats">
            <div>
              <span>Devis</span>
              <strong>{data.stats.quotes}</strong>
            </div>
            <div>
              <span>Factures</span>
              <strong>{data.stats.invoices}</strong>
            </div>
            <div>
              <span>Avoirs</span>
              <strong>{data.stats.credits}</strong>
            </div>
          </div>
          <p className="muted billing-pipeline-help">
            Devis → envoyer → signer → convertir · Facture → relancer → encaisser
          </p>
        </aside>
      </div>

      {(message || error) && (
        <div className="billing-feedback">
          {message && <div className="auth-alert auth-alert-ok">{message}</div>}
          {error && <div className="auth-alert auth-alert-error">{error}</div>}
        </div>
      )}

      <section className="panel billing-docs">
        <div className="billing-docs-head">
          <h3>Documents</h3>
          <div className="billing-tabs" role="tablist" aria-label="Filtrer par type">
            {(
              [
                ['all', 'Tous'],
                ['devis', 'Devis'],
                ['facture', 'Factures'],
                ['avoir', 'Avoirs'],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={typeFilter === value}
                className={`billing-tab${typeFilter === value ? ' active' : ''}`}
                onClick={() => setTypeFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {documents.length === 0 ? (
          <div className="empty">Aucun document dans ce filtre.</div>
        ) : (
          <div className="billing-table-wrap">
            <table className="billing-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Client</th>
                  <th>Date</th>
                  <th>Statut</th>
                  <th className="num">TTC</th>
                  <th className="num">Payé</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => {
                  const busy = busyId === doc.id
                  return (
                    <tr key={doc.id}>
                      <td>
                        <strong className="billing-doc-number">{doc.number}</strong>
                        <span className="billing-doc-type">
                          {TYPE_LABELS[doc.doc_type] || doc.doc_type}
                        </span>
                      </td>
                      <td>
                        <span className="billing-client">{doc.customer_name}</span>
                        {doc.customer_email ? (
                          <span className="muted billing-email">{doc.customer_email}</span>
                        ) : null}
                      </td>
                      <td>{doc.issue_date}</td>
                      <td>
                        <span className={statusBadgeClass(doc.status)}>
                          {STATUS_LABELS[doc.status] || doc.status}
                        </span>
                      </td>
                      <td className="num">{formatEuro(doc.amount_ttc)}</td>
                      <td className="num muted">{formatEuro(doc.paid_amount)}</td>
                      <td>
                        <div className="billing-row-actions">
                          <button
                            className="btn secondary btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => visualize(doc)}
                          >
                            Visualiser
                          </button>
                          <button
                            className="btn secondary btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => setPreviewDoc(doc)}
                          >
                            Envoyer
                          </button>
                          {doc.doc_type === 'devis' && (
                            <>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'sign')}
                              >
                                Signer
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'convert')}
                              >
                                → Facture
                              </button>
                            </>
                          )}
                          {doc.doc_type === 'facture' && (
                            <>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() =>
                                  void act(doc, 'pay', {
                                    amount: Math.max(doc.amount_ttc - doc.paid_amount, 0),
                                    method: 'virement',
                                  })
                                }
                              >
                                Payer
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'remind')}
                              >
                                Relancer
                              </button>
                              <button
                                className="btn secondary btn-sm"
                                type="button"
                                disabled={busy}
                                onClick={() => void act(doc, 'credit-note')}
                              >
                                Avoir
                              </button>
                            </>
                          )}
                          <button
                            className="btn secondary btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => startEdit(doc)}
                          >
                            Modifier
                          </button>
                          <button
                            className="btn danger-outline btn-sm"
                            type="button"
                            disabled={busy}
                            onClick={() => void remove(doc)}
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {previewDoc && token && orgId && (
        <SalesDocPreviewModal
          doc={previewDoc}
          token={token}
          orgId={orgId}
          onClose={() => setPreviewDoc(null)}
          onEdit={startEdit}
          onSent={(document, log) => {
            setPreviewDoc(document)
            setMessage(
              log.status === 'sent'
                ? `E-mail envoyé à ${log.recipient}`
                : `Envoi ${log.status} pour ${document.number}`,
            )
            load()
          }}
        />
      )}
    </div>
  )
}
