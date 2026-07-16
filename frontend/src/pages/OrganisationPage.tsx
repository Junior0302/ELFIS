import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, formatEuro, type OrgDetail, type SubscriptionInfo } from '../api'
import { useAuth } from '../auth'
import {
  canOpenSubscriptionPortal,
  formatDate,
  remainingTime,
  subscriptionDeadline,
  subscriptionLabels,
  subscriptionTone,
} from '../subscription'

const emptyForm = {
  name: '',
  legal_name: '',
  siren: '',
  vat_number: '',
  address: '',
  logo: '',
  industry: '',
  country: 'FR',
  currency: 'EUR',
}

export default function OrganisationPage() {
  const { token, orgId, memberships, user } = useAuth()
  const [detail, setDetail] = useState<OrgDetail | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [canEdit, setCanEdit] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [subscriptionError, setSubscriptionError] = useState('')
  const [openingPortal, setOpeningPortal] = useState(false)
  const [now, setNow] = useState(Date.now())
  const activeMembership = memberships.find((item) => item.organization_id === orgId)
  const canManageSubscription = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('subscription.manage'),
  )
  const canOpenPortal = Boolean(subscription && canOpenSubscriptionPortal(subscription.status))
  const canManageTeam = Boolean(
    activeMembership?.permissions.includes('*') ||
      activeMembership?.permissions.includes('users.manage'),
  )

  useEffect(() => {
    if (!orgId || !token) return
    setSubscription(null)
    setSubscriptionError('')
    setError('')
    api
      .orgDetail(orgId, token)
      .then((organization) => {
        setDetail(organization)
        setCanEdit(Boolean(organization.can_edit))
        const org = organization.organization
        setForm({
          name: org.name || '',
          legal_name: org.legal_name || '',
          siren: org.siren || '',
          vat_number: org.vat_number || '',
          address: org.address || '',
          logo: org.logo || '',
          industry: org.industry || '',
          country: org.country || 'FR',
          currency: org.currency || 'EUR',
        })
      })
      .catch((e) => setError(e.message || 'Erreur organisation'))
    api
      .currentSubscription(token, orgId)
      .then(setSubscription)
      .catch((reason) => {
        setSubscriptionError(reason instanceof Error ? reason.message : 'Abonnement indisponible')
      })
  }, [orgId, token])

  useEffect(() => {
    const tickMs = subscription?.status === 'trialing' ? 1000 : 60_000
    const timer = window.setInterval(() => setNow(Date.now()), tickMs)
    return () => window.clearInterval(timer)
  }, [subscription?.status])

  const openPortal = async () => {
    if (!token || !orgId) return
    setOpeningPortal(true)
    setSubscriptionError('')
    try {
      const { url } = await api.createSubscriptionPortal(token, orgId)
      const target = new URL(url, window.location.origin)
      if (!['http:', 'https:'].includes(target.protocol)) throw new Error('URL Stripe invalide')
      window.location.assign(target.toString())
    } catch (reason) {
      setSubscriptionError(reason instanceof Error ? reason.message : 'Portail Stripe indisponible')
      setOpeningPortal(false)
    }
  }

  const onSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!token || !orgId || !canEdit) return
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const { organization } = await api.updateOrganization(orgId, form, token)
      setDetail((current) => (current ? { ...current, organization } : current))
      setMessage('Informations de l’entreprise enregistrées.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Enregistrement impossible')
    } finally {
      setSaving(false)
    }
  }

  if (!user) {
    return (
      <div className="panel">
        <h2>Organisation</h2>
        <p className="muted">
          Retrouvez ici les informations de votre entreprise : identité légale, coordonnées et
          paramètres.
        </p>
      </div>
    )
  }

  if (error && !detail) return <div className="panel form-error">{error}</div>
  if (!detail) return <div className="loading">Chargement organisation…</div>

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Organisation</h2>
          <p>
            Informations de l’entreprise, coordonnées et paramètres. La gestion des utilisateurs se
            fait dans Admin → Équipe.
          </p>
        </div>
        {canManageTeam && (
          <Link className="btn secondary" to="/admin/equipe">
            Gérer l’équipe
          </Link>
        )}
      </div>

      {error && <div className="auth-alert auth-alert-error">{error}</div>}
      {message && <p className="muted">{message}</p>}

      <div className="stats">
        <div className="stat">
          <span>SIREN / SIRET</span>
          <strong style={{ fontSize: '1.1rem' }}>{detail.organization.siren || '—'}</strong>
        </div>
        <div className="stat">
          <span>TVA</span>
          <strong style={{ fontSize: '1.1rem' }}>{detail.organization.vat_number || '—'}</strong>
        </div>
        <div className="stat">
          <span>Pays</span>
          <strong>{detail.organization.country}</strong>
        </div>
        <div className="stat">
          <span>Devise</span>
          <strong>{detail.organization.currency}</strong>
        </div>
      </div>

      <section className="panel organisation-subscription">
        <div>
          <span className="home-eyebrow">Abonnement</span>
          <h3>ComptaPilot {subscription?.plan || detail.subscription?.plan || 'Pro'}</h3>
          {subscription ? (
            <p className="muted">
              {formatEuro(subscription.price_eur || 19)} / mois
              {subscription.status === 'trialing' ? (
                <>
                  {' '}
                  · essai ·{' '}
                  <strong>{remainingTime(subscriptionDeadline(subscription), now) ?? '—'}</strong>{' '}
                  restant
                </>
              ) : (
                <> · échéance {formatDate(subscriptionDeadline(subscription))}</>
              )}
            </p>
          ) : (
            <p className="muted">
              {detail.subscription
                ? `${formatEuro(detail.subscription.price)} / mois`
                : 'Statut détaillé indisponible'}
            </p>
          )}
          {subscriptionError && <small className="form-error">{subscriptionError}</small>}
        </div>
        <div className="organisation-subscription-actions">
          {subscription && (
            <span className={`subscription-badge ${subscriptionTone(subscription.status)}`}>
              {subscriptionLabels[subscription.status]}
            </span>
          )}
          {canManageSubscription && canOpenPortal && (
            <button
              className="btn secondary"
              type="button"
              disabled={openingPortal}
              onClick={() => void openPortal()}
            >
              {openingPortal ? 'Ouverture…' : 'Ouvrir le portail Stripe'}
            </button>
          )}
          {canManageSubscription && !canOpenPortal && (
            <Link className="btn secondary" to="/abonnement">
              Choisir l’abonnement
            </Link>
          )}
        </div>
      </section>

      <form className="panel" onSubmit={onSave} style={{ marginTop: '1rem' }}>
        <div className="section-heading">
          <div>
            <h3>Entreprise</h3>
            <p className="muted">Identité légale, adresse, TVA et logo affichés sur vos documents.</p>
          </div>
        </div>
        <div className="form-grid">
          <div className="field">
            <label>Nom commercial</label>
            <input
              value={form.name}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>Raison sociale</label>
            <input
              value={form.legal_name}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
            />
          </div>
          <div className="field">
            <label>SIREN / SIRET</label>
            <input
              value={form.siren}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, siren: e.target.value })}
            />
          </div>
          <div className="field">
            <label>N° TVA</label>
            <input
              value={form.vat_number}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, vat_number: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Secteur</label>
            <input
              value={form.industry}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Pays</label>
            <input
              value={form.country}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, country: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Devise</label>
            <input
              value={form.currency}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Logo (URL)</label>
            <input
              value={form.logo}
              disabled={!canEdit}
              placeholder="https://…"
              onChange={(e) => setForm({ ...form, logo: e.target.value })}
            />
          </div>
          <div className="field full">
            <label>Adresse</label>
            <textarea
              rows={3}
              value={form.address}
              disabled={!canEdit}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
        </div>
        {canEdit ? (
          <div className="actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        ) : (
          <p className="muted">Lecture seule — demandez un accès paramètres à un administrateur.</p>
        )}
      </form>

      <div className="result-grid" style={{ minHeight: 'auto', marginTop: '1rem' }}>
        <section className="panel">
          <h3>Filiales</h3>
          {detail.companies.length === 0 ? (
            <p className="muted">Aucune filiale rattachée.</p>
          ) : (
            <div className="list">
              {detail.companies.map((c) => (
                <div
                  key={c.id}
                  className="list-item"
                  style={{ gridTemplateColumns: '1fr 0.5fr 0.5fr' }}
                >
                  <strong>{c.name}</strong>
                  <span>{c.country}</span>
                  <span className="muted">
                    {c.parent_company_id ? `fils de #${c.parent_company_id}` : 'siège'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
        <section className="panel">
          <h3>Paramètres</h3>
          <p className="muted">
            Équipes : {detail.teams.map((t) => t.name).join(', ') || '—'}. Agents IA :{' '}
            {detail.ai_agents.length}.
          </p>
          <p style={{ marginTop: '0.75rem' }}>
            Les comptes utilisateurs et les permissions se gèrent uniquement dans{' '}
            <Link to="/admin/equipe">Admin → Équipe</Link>.
          </p>
        </section>
      </div>
    </>
  )
}
