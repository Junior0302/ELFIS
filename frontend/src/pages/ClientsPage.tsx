import { useEffect, useState, type FormEvent } from 'react'
import { api, type CustomerRecord } from '../api'
import { useAuth } from '../auth'

const emptyForm = {
  name: '',
  email: '',
  phone: '',
  address: '',
  vat_number: '',
}

export default function ClientsPage() {
  const { token, orgId } = useAuth()
  const [customers, setCustomers] = useState<CustomerRecord[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const load = (search = q) => {
    if (!token) return
    api
      .listCustomers(token, orgId, search.trim() || undefined)
      .then((res) => setCustomers(res.customers))
      .catch((e) => setError(e.message || 'Impossible de charger les clients'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const startEdit = (c: CustomerRecord) => {
    setEditingId(c.id)
    setForm({
      name: c.name,
      email: c.email || '',
      phone: c.phone || '',
      address: c.address || '',
      vat_number: c.vat_number || '',
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!token) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      if (editingId) {
        await api.updateCustomer(editingId, form, token, orgId)
        setMessage('Client mis à jour.')
      } else {
        await api.createCustomer(form, token, orgId)
        setMessage('Client créé.')
      }
      resetForm()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur enregistrement')
    } finally {
      setBusy(false)
    }
  }

  const onDelete = async (id: number) => {
    if (!token || !window.confirm('Supprimer ce client ?')) return
    setError('')
    try {
      await api.deleteCustomer(id, token, orgId)
      if (editingId === id) resetForm()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Clients</h2>
          <p>Fiches clients pour la facturation et le suivi commercial.</p>
        </div>
      </div>

      {error && <div className="panel form-error">{error}</div>}
      {message && <div className="panel form-ok">{message}</div>}

      <section className="panel">
        <h3>{editingId ? 'Modifier le client' : 'Nouveau client'}</h3>
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="field">
              <label>Nom</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>E-mail</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Téléphone</label>
              <input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div className="field">
              <label>N° TVA</label>
              <input
                value={form.vat_number}
                onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
              />
            </div>
            <div className="field full">
              <label>Adresse</label>
              <textarea
                rows={2}
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
              />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit" disabled={busy}>
              {editingId ? 'Enregistrer' : 'Ajouter'}
            </button>
            {editingId && (
              <button className="btn secondary" type="button" onClick={resetForm}>
                Annuler
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="dashboard-section-head">
          <h3>Liste ({customers.length})</h3>
          <form
            className="inline-search"
            onSubmit={(e) => {
              e.preventDefault()
              load(q)
            }}
          >
            <input
              placeholder="Rechercher…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <button className="btn secondary" type="submit">
              Filtrer
            </button>
          </form>
        </div>
        {customers.length === 0 ? (
          <div className="empty">Aucun client pour le moment.</div>
        ) : (
          <div className="list">
            {customers.map((c) => (
              <div key={c.id} className="list-item crm-row">
                <div>
                  <strong>{c.name}</strong>
                  <span>
                    {[c.email, c.phone, c.vat_number].filter(Boolean).join(' · ') || 'Sans contact'}
                  </span>
                </div>
                <div className="actions" style={{ marginTop: 0 }}>
                  <button className="btn secondary" type="button" onClick={() => startEdit(c)}>
                    Modifier
                  </button>
                  <button className="btn secondary" type="button" onClick={() => onDelete(c.id)}>
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
