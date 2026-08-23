import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type CustomerRecord } from '../api'
import { useAuth } from '../auth'
import FirstActionSuccessPanel from '../components/FirstActionSuccessPanel'
import { ConfirmDialog } from '../design-system'
import {
  clientsPageCopy,
  customerSuccessActions,
  isLaunchDashboardSource,
  markLaunchDashboardStale,
  type FirstExperienceAction,
} from '../firstExperience'
import type { LaunchDashboardData } from '../launchDashboard'
import { EmptyState } from '../ui/UiStates'

const emptyForm = {
  name: '',
  email: '',
  phone: '',
  address: '',
  vat_number: '',
}

export default function ClientsPage() {
  const { token, orgId } = useAuth()
  const [searchParams] = useSearchParams()
  const fromLaunch = isLaunchDashboardSource(searchParams.get('source'))
  const nameId = useId()
  const emailId = useId()
  const phoneId = useId()
  const vatId = useId()
  const addressId = useId()
  const nameRef = useRef<HTMLInputElement>(null)

  const [customers, setCustomers] = useState<CustomerRecord[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [listLoading, setListLoading] = useState(true)
  const [created, setCreated] = useState<CustomerRecord | null>(null)
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [successPrimary, setSuccessPrimary] = useState<FirstExperienceAction | null>(null)
  const [successSecondary, setSuccessSecondary] = useState<FirstExperienceAction[]>([])

  const load = (search = q) => {
    if (!token) return
    setListLoading(true)
    api
      .listCustomers(token, orgId, search.trim() || undefined)
      .then((res) => setCustomers(res.customers))
      .catch((e) => setError(e instanceof Error ? e.message : 'Impossible de charger les clients'))
      .finally(() => setListLoading(false))
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
    setCreated(null)
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

  const resolveSuccessActions = async (customer: CustomerRecord) => {
    let launch: LaunchDashboardData | null = null
    if (token && orgId != null) {
      try {
        launch = await api.getLaunchDashboard(token, orgId)
      } catch {
        launch = null
      }
    }
    const actions = customerSuccessActions(customer, launch)
    setSuccessPrimary(actions.primary)
    setSuccessSecondary(actions.secondary)
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!token || busy) return
    setBusy(true)
    setError('')
    setMessage('')
    setCreated(null)
    try {
      if (editingId) {
        await api.updateCustomer(editingId, form, token, orgId)
        setMessage('Client mis à jour.')
        resetForm()
        load()
      } else {
        const customer = await api.createCustomer(form, token, orgId)
        markLaunchDashboardStale()
        resetForm()
        load()
        setCreated(customer)
        await resolveSuccessActions(customer)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur enregistrement')
      nameRef.current?.focus()
    } finally {
      setBusy(false)
    }
  }

  const onDelete = (id: number) => {
    if (!token) return
    setDeleteTargetId(id)
  }

  const confirmDelete = async () => {
    if (!token || deleteTargetId == null) return
    setError('')
    setDeleteLoading(true)
    try {
      await api.deleteCustomer(deleteTargetId, token, orgId)
      if (editingId === deleteTargetId) resetForm()
      if (created?.id === deleteTargetId) setCreated(null)
      markLaunchDashboardStale()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
      throw err
    } finally {
      setDeleteLoading(false)
    }
  }

  const copy = clientsPageCopy({ fromLaunch, hasCustomers: customers.length > 0 })
  const formTitle = editingId ? 'Modifier le client' : fromLaunch && customers.length === 0 ? 'Premier client' : 'Nouveau client'

  return (
    <>
      <div className="page-head">
        <div>
          <h2>{copy.title}</h2>
          <p>{copy.lead}</p>
          <p className="muted">Finance · Clients & fournisseurs</p>
          <p className="muted">Données issues d’ELFIS Relations</p>
          <p className="muted">
            Vue comptable — identité, fiscalité, factures et solde. Pas de pipeline commercial.
          </p>
          {fromLaunch ? (
            <p className="muted first-experience-back">
              <Link to="/dashboard">Retour au Dashboard</Link>
            </p>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="panel form-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? (
        <div className="panel form-ok" role="status">
          {message}
        </div>
      ) : null}

      {created && successPrimary ? (
        <FirstActionSuccessPanel
          title="Client ajouté"
          description="Le client est maintenant disponible pour vos devis et factures :"
          resourceName={created.name}
          primaryAction={successPrimary}
          secondaryActions={successSecondary}
        />
      ) : null}

      <section className="panel">
        <h3>{formTitle}</h3>
        <p className="muted first-experience-hint">
          Seul le nom est obligatoire. Vous pourrez compléter ces informations plus tard.
        </p>
        <form onSubmit={onSubmit} noValidate={false}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor={nameId}>
                Nom <span className="field-required">(obligatoire)</span>
              </label>
              <input
                id={nameId}
                ref={nameRef}
                required
                autoComplete="organization"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                disabled={busy}
                aria-required="true"
              />
            </div>
            <div className="field">
              <label htmlFor={emailId}>
                E-mail <span className="muted">(facultatif)</span>
              </label>
              <input
                id={emailId}
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label htmlFor={phoneId}>
                Téléphone <span className="muted">(facultatif)</span>
              </label>
              <input
                id={phoneId}
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label htmlFor={vatId}>
                N° TVA <span className="muted">(facultatif)</span>
              </label>
              <input
                id={vatId}
                value={form.vat_number}
                onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field full">
              <label htmlFor={addressId}>
                Adresse <span className="muted">(facultatif)</span>
              </label>
              <textarea
                id={addressId}
                rows={2}
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                disabled={busy}
              />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit" disabled={busy} aria-busy={busy}>
              {busy ? 'Enregistrement…' : editingId ? 'Enregistrer' : 'Ajouter'}
            </button>
            {editingId ? (
              <button className="btn secondary" type="button" onClick={resetForm} disabled={busy}>
                Annuler
              </button>
            ) : null}
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
              aria-label="Rechercher un client"
            />
            <button className="btn secondary" type="submit">
              Filtrer
            </button>
          </form>
        </div>
        {listLoading ? (
          <p className="loading" aria-live="polite">
            Chargement des clients…
          </p>
        ) : customers.length === 0 ? (
          <EmptyState
            title="Aucun client pour le moment"
            description="Ajoutez votre premier client pour pouvoir créer des devis et des factures."
            action={
              <a className="btn" href="#client-form-top" onClick={(e) => {
                e.preventDefault()
                nameRef.current?.focus()
              }}>
                Ajouter un client
              </a>
            }
          />
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
                  <Link className="btn secondary" to={`/facturation?customer_id=${c.id}`}>
                    Facturer
                  </Link>
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

      <ConfirmDialog
        open={deleteTargetId != null}
        onOpenChange={(open) => {
          if (!open) setDeleteTargetId(null)
        }}
        title="Supprimer ce client ?"
        description="Le client sera retiré de votre liste. Cette action peut être irréversible selon vos droits."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        tone="danger"
        irreversible
        loading={deleteLoading}
        onConfirm={confirmDelete}
      />
    </>
  )
}
