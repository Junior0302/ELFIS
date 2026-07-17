import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type BillingOverview, type SalesDoc } from '../api'
import { useAuth } from '../auth'
import SalesDocPreviewModal from '../components/SalesDocPreviewModal'

const emptyForm = {
  customer_name: '',
  customer_email: '',
  customer_id: null as number | null,
  amount_ht: 0,
  vat_rate: 20,
  notes: '',
}

export default function DevisPage() {
  const { token, orgId } = useAuth()
  const [data, setData] = useState<BillingOverview | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [previewDoc, setPreviewDoc] = useState<SalesDoc | null>(null)

  const load = (overrides?: { q?: string; status?: string }) => {
    if (!token) return
    api
      .billingOverview(token, orgId, {
        doc_type: 'devis',
        q: overrides?.q ?? query,
        status: overrides?.status ?? (statusFilter || undefined),
      })
      .then(setData)
      .catch((e) => setError(e.message || 'Erreur devis'))
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
        await api.updateSalesDoc(editingId, form, token, orgId)
        setMessage('Devis mis à jour.')
        resetForm()
      } else {
        const created = await api.createSalesDoc(
          { ...form, doc_type: 'devis' },
          token,
          orgId,
        )
        setMessage(`Devis ${created.number} créé.`)
        setPreviewDoc(created)
        resetForm()
      }
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enregistrement impossible')
    }
  }

  const visualize = async (doc: SalesDoc) => {
    if (!token) return
    setError('')
    try {
      const url = await api.openSalesDocPdfBlob(doc.id, token, orgId)
      const opened = window.open(url, '_blank', 'noopener,noreferrer')
      if (!opened) {
        URL.revokeObjectURL(url)
        setPreviewDoc(doc)
        return
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Visualisation impossible')
      setPreviewDoc(doc)
    }
  }

  const remove = async (doc: SalesDoc) => {
    const confirmed = window.confirm(
      `Supprimer ce devis ${doc.number} ?\n\nClient : ${doc.customer_name}\nMontant TTC : ${formatEuro(doc.amount_ttc)}\n\nCette action est définitive.`,
    )
    if (!confirmed) return
    try {
      await api.deleteSalesDoc(doc.id, token, orgId)
      setMessage(`${doc.number} supprimé.`)
      if (editingId === doc.id) resetForm()
      if (previewDoc?.id === doc.id) setPreviewDoc(null)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
    }
  }

  const act = async (doc: SalesDoc, action: string) => {
    try {
      await api.billingAction(doc.id, action, token, orgId)
      setMessage(`Action ${action} OK sur ${doc.number}`)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible')
    }
  }

  if (error && !data) return <div className="panel form-error">{error}</div>
  if (!data) return <div className="loading">Chargement des devis…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Devis</h2>
          <p>
            Liste, recherche, aperçu PDF, modification, suppression et envoi par e-mail. Création
            aussi disponible dans <Link to="/facturation">Facturation</Link>.
          </p>
          <p className="muted" style={{ marginTop: '0.5rem' }}>
            À l’envoi : <strong>1)</strong> votre messagerie personnelle, ou <strong>2)</strong>{' '}
            votre adresse ELFIS Core (après demande dans <Link to="/compte">Mon compte</Link> et
            validation admin).
          </p>
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <span>Devis</span>
          <strong>{data.stats.quotes}</strong>
        </div>
        <div className="stat">
          <span>Affichés</span>
          <strong>{data.documents.length}</strong>
        </div>
        <div className="stat">
          <span>Clients</span>
          <strong>{data.stats.customers}</strong>
        </div>
      </div>

      <form className="panel" onSubmit={onSubmit}>
        <h3>{editingId ? 'Modifier le devis' : 'Nouveau devis'}</h3>
        <div className="form-grid">
          <div className="field">
            <label>Client</label>
            <input
              value={form.customer_name}
              onChange={(e) => fillFromCustomerName(e.target.value)}
              list="devis-customers"
              required
            />
            <datalist id="devis-customers">
              {data.customers.map((c) => (
                <option key={c.id} value={c.name} />
              ))}
            </datalist>
          </div>
          <div className="field">
            <label>Adresse e-mail du client</label>
            <input
              type="email"
              value={form.customer_email}
              onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Montant HT</label>
            <input
              type="number"
              step="0.01"
              value={form.amount_ht}
              onChange={(e) => setForm({ ...form, amount_ht: Number(e.target.value) })}
              required
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
            <input
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
        <div className="actions">
          <button className="btn" type="submit">
            {editingId ? 'Enregistrer' : 'Créer le devis'}
          </button>
          {editingId && (
            <button className="btn secondary" type="button" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
      </form>

      {message && <p className="muted">{message}</p>}
      {error && <p className="form-error">{error}</p>}

      <section className="panel" style={{ marginTop: '1rem' }}>
        <div className="section-heading">
          <h3>Liste des devis</h3>
          <div className="sales-filters">
            <input
              placeholder="Recherche…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">Tous statuts</option>
              <option value="draft">Brouillon</option>
              <option value="sent">Envoyé</option>
              <option value="accepted">Accepté</option>
              <option value="refused">Refusé</option>
            </select>
            <button className="btn secondary" type="button" onClick={() => load()}>
              Filtrer
            </button>
          </div>
        </div>

        {data.documents.length === 0 ? (
          <div className="empty">Aucun devis trouvé.</div>
        ) : (
          <div className="list">
            {data.documents.map((doc) => (
              <div
                key={doc.id}
                className="list-item"
                style={{ gridTemplateColumns: '1.5fr 0.7fr 2fr' }}
              >
                <div>
                  <strong>{doc.number}</strong>
                  <span>
                    {doc.customer_name}
                    {doc.customer_email ? ` · ${doc.customer_email}` : ''} · {doc.issue_date} ·{' '}
                    {doc.status}
                    {doc.signature_status !== 'none' ? ` · signature ${doc.signature_status}` : ''}
                  </span>
                </div>
                <div>
                  <strong>{formatEuro(doc.amount_ttc)}</strong>
                  <span>TTC</span>
                </div>
                <div className="actions" style={{ marginTop: 0, flexWrap: 'wrap' }}>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => void visualize(doc)}
                  >
                    Visualiser
                  </button>
                  <button className="btn secondary" type="button" onClick={() => setPreviewDoc(doc)}>
                    Envoyer
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => void api.downloadSalesDocPdf(doc.id, token!, orgId)}
                  >
                    Télécharger
                  </button>
                  <button className="btn secondary" type="button" onClick={() => startEdit(doc)}>
                    Modifier
                  </button>
                  <button
                    className="btn danger-outline"
                    type="button"
                    onClick={() => void remove(doc)}
                  >
                    Supprimer
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => void act(doc, 'sign')}
                  >
                    Signer
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => void act(doc, 'convert')}
                  >
                    → Facture
                  </button>
                </div>
              </div>
            ))}
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
    </>
  )
}
