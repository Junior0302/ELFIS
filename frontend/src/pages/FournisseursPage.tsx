import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type Contact } from '../api'
import { useAuth } from '../auth'
import { ConfirmDialog } from '../design-system'
import { isLaunchDashboardSource, markLaunchDashboardStale } from '../firstExperience'
import { EmptyState } from '../ui/UiStates'

const emptyForm = {
  company_name: '',
  email: '',
  phone: '',
  vat_number: '',
  address_line_1: '',
  siret: '',
}

export default function FournisseursPage() {
  const { token, orgId } = useAuth()
  const [searchParams] = useSearchParams()
  const fromLaunch = isLaunchDashboardSource(searchParams.get('source'))
  const nameId = useId()
  const nameRef = useRef<HTMLInputElement>(null)

  const [contacts, setContacts] = useState<Contact[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [listLoading, setListLoading] = useState(true)
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const load = (search = q) => {
    if (!token) return
    setListLoading(true)
    api
      .listContacts(token, orgId, {
        contact_type: 'supplier',
        q: search.trim() || undefined,
      })
      .then((res) => setContacts(res.contacts.filter((c) => c.status !== 'archived')))
      .catch((e) =>
        setError(e instanceof Error ? e.message : 'Impossible de charger les fournisseurs'),
      )
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

  const startEdit = (c: Contact) => {
    setEditingId(c.id)
    setForm({
      company_name: c.company_name || '',
      email: c.email || '',
      phone: c.phone || '',
      vat_number: c.vat_number || '',
      address_line_1: c.address_line_1 || '',
      siret: c.siret || '',
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!token || busy) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      if (editingId) {
        await api.updateContact(editingId, form, token, orgId)
        setMessage('Fournisseur mis à jour.')
        resetForm()
      } else {
        await api.createContact({ ...form, contact_type: 'supplier' }, token, orgId)
        markLaunchDashboardStale()
        setMessage('Fournisseur ajouté.')
        resetForm()
      }
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur enregistrement')
      nameRef.current?.focus()
    } finally {
      setBusy(false)
    }
  }

  const confirmDelete = async () => {
    if (!token || deleteTargetId == null) return
    setError('')
    setDeleteLoading(true)
    try {
      await api.deleteContact(deleteTargetId, token, orgId)
      if (editingId === deleteTargetId) resetForm()
      markLaunchDashboardStale()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible')
      throw err
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>{fromLaunch ? 'Ajouter votre premier fournisseur' : 'Fournisseurs'}</h2>
          <p>Vue comptable fournisseurs — fiscalité, factures et échéances.</p>
          <p className="muted">Finance · Clients & fournisseurs</p>
          <p className="muted">Données issues d’ELFIS Relations</p>
          <p className="muted">
            Pas d’activités commerciales générales.
          </p>
          <p className="muted">
            <Link to="/platform/relations?tab=supplier">Ouvrir la fiche dans ELFIS Relations</Link>
            {' · '}
            Suggestions OCR sur <Link to="/deposit">Import</Link>.
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

      <section className="panel">
        <h3>{editingId ? 'Modifier le fournisseur' : 'Nouveau fournisseur'}</h3>
        <p className="muted first-experience-hint">Seul le nom est obligatoire.</p>
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor={nameId}>
                Nom <span className="field-required">(obligatoire)</span>
              </label>
              <input
                id={nameId}
                ref={nameRef}
                required
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label>E-mail</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label>Téléphone</label>
              <input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label>N° TVA</label>
              <input
                value={form.vat_number}
                onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field">
              <label>SIRET</label>
              <input
                value={form.siret}
                onChange={(e) => setForm({ ...form, siret: e.target.value })}
                disabled={busy}
              />
            </div>
            <div className="field full">
              <label>Adresse</label>
              <textarea
                rows={2}
                value={form.address_line_1}
                onChange={(e) => setForm({ ...form, address_line_1: e.target.value })}
                disabled={busy}
              />
            </div>
          </div>
          <div className="actions">
            <button className="btn" type="submit" disabled={busy}>
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
          <h3>Liste ({contacts.length})</h3>
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
              aria-label="Rechercher un fournisseur"
            />
            <button className="btn secondary" type="submit">
              Filtrer
            </button>
          </form>
        </div>
        {listLoading ? (
          <p className="loading">Chargement des fournisseurs…</p>
        ) : contacts.length === 0 ? (
          <EmptyState
            title="Aucun fournisseur"
            description="Ajoutez une fiche pour centraliser vos achats sans passer par un dépôt OCR."
            action={
              <button className="btn" type="button" onClick={() => nameRef.current?.focus()}>
                Ajouter un fournisseur
              </button>
            }
          />
        ) : (
          <div className="list">
            {contacts.map((c) => (
              <div key={c.id} className="list-item crm-row">
                <div>
                  <strong>{c.company_name}</strong>
                  <span>
                    {[c.email, c.phone, c.vat_number, c.siret].filter(Boolean).join(' · ') ||
                      'Sans contact'}
                  </span>
                </div>
                <div className="actions" style={{ marginTop: 0 }}>
                  <Link className="btn secondary" to="/deposit">
                    Importer une facture
                  </Link>
                  <button className="btn secondary" type="button" onClick={() => startEdit(c)}>
                    Modifier
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => setDeleteTargetId(c.id)}
                  >
                    Archiver
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
        title="Archiver ce fournisseur ?"
        description="La fiche passera en statut archivé. Les documents liés restent accessibles."
        confirmLabel="Archiver"
        cancelLabel="Annuler"
        tone="danger"
        irreversible
        loading={deleteLoading}
        onConfirm={confirmDelete}
      />
    </>
  )
}
