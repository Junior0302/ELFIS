import { useEffect, useState, type FormEvent } from 'react'
import { api, type CommercialActivity, type CustomerRecord } from '../api'
import { useAuth } from '../auth'

const KIND_LABELS: Record<string, string> = {
  vente: 'Vente',
  service: 'Service',
  rdv: 'Rendez-vous',
  suivi: 'Suivi',
}

const STATUS_LABELS: Record<string, string> = {
  planifie: 'Planifié',
  fait: 'Fait',
  annule: 'Annulé',
}

const emptyForm = {
  title: '',
  kind: 'rdv',
  customer_id: '' as string | number,
  scheduled_at: '',
  status: 'planifie',
  notes: '',
}

function fromLocalInput(value: string) {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString()
}

export default function ActivitesPage() {
  const { token, orgId } = useAuth()
  const [activities, setActivities] = useState<CommercialActivity[]>([])
  const [customers, setCustomers] = useState<CustomerRecord[]>([])
  const [form, setForm] = useState(emptyForm)
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => {
    if (!token) return
    Promise.all([
      api.listActivities(token, orgId, statusFilter ? { status: statusFilter } : undefined),
      api.listCustomers(token, orgId),
    ])
      .then(([acts, cust]) => {
        setActivities(acts.activities)
        setCustomers(cust.customers)
      })
      .catch((e) => setError(e.message || 'Impossible de charger les activités'))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, orgId, statusFilter])

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!token) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await api.createActivity(
        {
          title: form.title,
          kind: form.kind,
          customer_id: form.customer_id === '' ? null : Number(form.customer_id),
          scheduled_at: fromLocalInput(form.scheduled_at),
          status: form.status,
          notes: form.notes,
        },
        token,
        orgId,
      )
      setMessage('Activité créée.')
      setForm(emptyForm)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur création')
    } finally {
      setBusy(false)
    }
  }

  const setStatus = async (id: number, status: string) => {
    if (!token) return
    try {
      await api.updateActivity(id, { status }, token, orgId)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Mise à jour impossible')
    }
  }

  const onDelete = async (id: number) => {
    if (!token || !window.confirm('Supprimer cette activité ?')) return
    try {
      await api.deleteActivity(id, token, orgId)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Activités</h2>
          <p>Agenda commercial — liste et création rapide.</p>
        </div>
      </div>

      {error && <div className="panel form-error">{error}</div>}
      {message && <div className="panel form-ok">{message}</div>}

      <section className="panel">
        <h3>Création rapide</h3>
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="field">
              <label>Titre</label>
              <input
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Type</label>
              <select
                value={form.kind}
                onChange={(e) => setForm({ ...form, kind: e.target.value })}
              >
                {Object.entries(KIND_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Client</label>
              <select
                value={form.customer_id}
                onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              >
                <option value="">— Aucun —</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Date / heure</label>
              <input
                type="datetime-local"
                value={form.scheduled_at}
                onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
              />
            </div>
            <div className="field">
              <label>Statut</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field full">
              <label>Notes</label>
              <textarea
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit" disabled={busy}>
              Ajouter
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="dashboard-section-head">
          <h3>Liste ({activities.length})</h3>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filtrer par statut"
          >
            <option value="">Tous les statuts</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {activities.length === 0 ? (
          <div className="empty">Aucune activité.</div>
        ) : (
          <div className="list">
            {activities.map((a) => (
              <div key={a.id} className="list-item crm-row">
                <div>
                  <strong>
                    {a.title}{' '}
                    <span className="badge">{KIND_LABELS[a.kind] || a.kind}</span>
                    <span className="badge">{STATUS_LABELS[a.status] || a.status}</span>
                  </strong>
                  <span>
                    {a.scheduled_at
                      ? new Date(a.scheduled_at).toLocaleString('fr-FR')
                      : 'Sans date'}
                    {a.customer_name ? ` · ${a.customer_name}` : ''}
                    {a.notes ? ` · ${a.notes}` : ''}
                  </span>
                </div>
                <div className="actions" style={{ marginTop: 0 }}>
                  {a.status !== 'fait' && (
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => setStatus(a.id, 'fait')}
                    >
                      Marquer fait
                    </button>
                  )}
                  {a.status !== 'annule' && (
                    <button
                      className="btn secondary"
                      type="button"
                      onClick={() => setStatus(a.id, 'annule')}
                    >
                      Annuler
                    </button>
                  )}
                  <button className="btn secondary" type="button" onClick={() => onDelete(a.id)}>
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
