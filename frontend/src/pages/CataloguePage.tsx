import { useEffect, useState, type FormEvent } from 'react'
import { api, formatEuro, type CatalogItem } from '../api'
import { useAuth } from '../auth'

const emptyForm = {
  name: '',
  kind: 'produit',
  unit: 'unité',
  unit_price_ht: 0,
  vat_rate: 20,
  active: true,
}

export default function CataloguePage() {
  const { token, orgId } = useAuth()
  const [items, setItems] = useState<CatalogItem[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => {
    if (!token) return
    api
      .listCatalog(token, orgId)
      .then((res) => setItems(res.items))
      .catch((e) => setError(e.message || 'Impossible de charger le catalogue'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId])

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const startEdit = (item: CatalogItem) => {
    setEditingId(item.id)
    setForm({
      name: item.name,
      kind: item.kind,
      unit: item.unit,
      unit_price_ht: item.unit_price_ht,
      vat_rate: item.vat_rate,
      active: item.active,
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
        await api.updateCatalogItem(editingId, form, token, orgId)
        setMessage('Article mis à jour.')
      } else {
        await api.createCatalogItem(form, token, orgId)
        setMessage('Article ajouté.')
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
    if (!token || !window.confirm('Supprimer cet article ?')) return
    try {
      await api.deleteCatalogItem(id, token, orgId)
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
          <h2>Catalogue</h2>
          <p>Produits et services avec prix HT et TVA.</p>
        </div>
      </div>

      {error && <div className="panel form-error">{error}</div>}
      {message && <div className="panel form-ok">{message}</div>}

      <section className="panel">
        <h3>{editingId ? 'Modifier l’article' : 'Nouvel article'}</h3>
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
              <label>Type</label>
              <select
                value={form.kind}
                onChange={(e) => setForm({ ...form, kind: e.target.value })}
              >
                <option value="produit">Produit</option>
                <option value="service">Service</option>
              </select>
            </div>
            <div className="field">
              <label>Unité</label>
              <input
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Prix HT</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.unit_price_ht}
                onChange={(e) => setForm({ ...form, unit_price_ht: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label>TVA %</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={form.vat_rate}
                onChange={(e) => setForm({ ...form, vat_rate: Number(e.target.value) })}
              />
            </div>
            <div className="field">
              <label className="checkbox-inline">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                />
                Actif
              </label>
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
        <h3>Articles ({items.length})</h3>
        {items.length === 0 ? (
          <div className="empty">Catalogue vide.</div>
        ) : (
          <div className="list">
            {items.map((item) => (
              <div key={item.id} className="list-item crm-row">
                <div>
                  <strong>
                    {item.name}{' '}
                    <span className="badge">{item.kind}</span>
                    {!item.active && <span className="badge warn">inactif</span>}
                  </strong>
                  <span>
                    {formatEuro(item.unit_price_ht)} HT / {item.unit} · TVA {item.vat_rate}%
                  </span>
                </div>
                <div className="actions" style={{ marginTop: 0 }}>
                  <button className="btn secondary" type="button" onClick={() => startEdit(item)}>
                    Modifier
                  </button>
                  <button className="btn secondary" type="button" onClick={() => onDelete(item.id)}>
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
